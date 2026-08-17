"""Stage 2B-F Phases 2-4: replay both estimators on identical inputs and build the 2x5 matrix.

Mirrors ``run_stage2b_loadpath.py``'s setup exactly -- same bundle, same frozen checkpoints, same
whitener fitted on the same healthy train+val windows, same pathway cache, same candidate points,
same window grid -- and then, at the one point where Stage 2B computed a score, computes **both**
estimators on the very same ``z`` and ``D``. That is what makes the comparison like-for-like: not
two runs that agree on their inputs, one run that shares them.

Neither estimator is re-derived. ``stage2a_ridge_residual_norm`` wraps the frozen
``pathways.geometry.batched_projection``; ``truncated_svd_orthogonal_projection_rss`` wraps the
frozen ``stage2b.rank_aware_scores.project``.

Phase 2 compares the ridge replay against Stage 2A's frozen ``contact_residual`` arrays.
Phase 3 compares the SVD replay against Stage 2B's frozen ``time_aligned_jacobian__*`` arrays.
Phase 4 emits the 2x5 estimator/control matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from certo_fdi.experiments.common import load_config, write_csv, write_json
from certo_fdi.experiments.stage2a_pathway_pipeline import (
    WindowGrid,
    episode_windows,
    fit_whiteners,
    load_pathways,
    stack_window_residual,
)
from certo_fdi.experiments.stage2b_common import ensure_model_cfg
from certo_fdi.pathways.geometry import orthonormal_basis
from certo_fdi.pathways.jacobians import candidate_points, skew
from certo_fdi.stage2b import loadpath_controls as LC
from certo_fdi.stage2b import rank_aware_scores as RS
from certo_fdi.stage2bf import estimator_identity as EI

METHOD_ORDER = ("support_prefix_rankmatched", "random_within_support_rankmatched",
                "fixed_reference_jacobian", "shuffled_time_jacobian", "time_aligned_jacobian")
N_LINKS = 7


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ dual-estimator projection
def dual_stats(hypotheses: list[np.ndarray], z: np.ndarray) -> dict:
    """Both estimators over one link's candidate dictionaries, on the same ``z``.

    The SVD half is ``RS.best_hypothesis_stats`` verbatim, so the Stage 2B numbers come out of the
    frozen function. The ridge half applies ``EI.stage2a_ridge_residual_norm`` to the *same*
    hypothesis arrays and takes the same ``argmin`` over candidate points, which is how Stage 2A
    reduced candidates.
    """
    ess, rss, rank, best = RS.best_hypothesis_stats(hypotheses, z)
    if not hypotheses:
        n = z.shape[0]
        zero = np.zeros(n)
        return {"svd_rss": rss, "svd_ess": ess, "svd_rank": rank, "svd_best": best,
                "ridge_norm": np.sqrt((z ** 2).sum(1)), "ridge_energy": (z ** 2).sum(1),
                "ridge_lambda": zero, "ridge_best": np.zeros(n, dtype=int)}
    norms, energies, lams = [], [], []
    for D in hypotheses:
        r = EI.stage2a_ridge_residual_norm(D, z)
        norms.append(r.residual_norm)
        energies.append(r.residual_energy)
        lams.append(r.ridge_lambda)
    norms = np.stack(norms, 1)
    idx = np.arange(z.shape[0])
    rbest = np.argmin(norms, axis=1)
    return {"svd_rss": rss, "svd_ess": ess, "svd_rank": rank, "svd_best": best,
            "ridge_norm": norms[idx, rbest],
            "ridge_energy": np.stack(energies, 1)[idx, rbest],
            "ridge_lambda": np.stack(lams, 1)[idx, rbest],
            "ridge_best": rbest.astype(int)}


def dual_static_stats(bases: dict, target_rank: np.ndarray, z: np.ndarray, n_hyp: int) -> dict:
    """Both estimators for a control whose dictionary is a window-invariant orthonormal basis.

    Mirrors ``run_stage2b_loadpath._static_stats``: windows are grouped by their rank-match target
    so each basis is applied once. The ridge half runs the frozen ridge on the same basis. On an
    orthonormal basis every singular value is 1, so the ridge gain is ``1/(1+1e-6)`` and the two
    estimators agree to about 1e-6 here **by construction** -- the mechanism report says so rather
    than presenting these cells as independent evidence.
    """
    N = z.shape[0]
    z_energy = (z ** 2).sum(1)
    out = {"svd_rss": np.full(N, np.inf), "svd_ess": np.zeros(N), "svd_rank": np.zeros(N, dtype=int),
           "svd_best": np.zeros(N, dtype=int),
           "ridge_norm": np.full(N, np.inf), "ridge_energy": np.full(N, np.inf),
           "ridge_lambda": np.zeros(N), "ridge_best": np.zeros(N, dtype=int)}
    for r in np.unique(target_rank):
        m = target_rank == r
        if not m.any():
            continue
        zi = z[m]
        for h in range(n_hyp):
            U = bases.get((int(r), h))
            if U is None:
                continue
            # --- SVD side: identical arithmetic to _static_stats
            ess = ((zi @ U) ** 2).sum(1) if U.shape[1] else np.zeros(zi.shape[0])
            rss = np.maximum(z_energy[m] - ess, 0.0)
            upd = rss < out["svd_rss"][m]
            idx = np.where(m)[0][upd]
            out["svd_rss"][idx] = rss[upd]
            out["svd_ess"][idx] = ess[upd]
            out["svd_rank"][idx] = U.shape[1]
            out["svd_best"][idx] = h
            # --- ridge side: the frozen ridge on the same basis
            if U.shape[1]:
                rr = EI.stage2a_ridge_residual_norm(np.broadcast_to(U, (zi.shape[0],) + U.shape), zi)
                rnorm, renergy, rlam = rr.residual_norm, rr.residual_energy, rr.ridge_lambda
            else:
                rnorm = np.sqrt(z_energy[m])
                renergy = z_energy[m].copy()
                rlam = np.zeros(zi.shape[0])
            rupd = rnorm < out["ridge_norm"][m]
            ridx = np.where(m)[0][rupd]
            out["ridge_norm"][ridx] = rnorm[rupd]
            out["ridge_energy"][ridx] = renergy[rupd]
            out["ridge_lambda"][ridx] = rlam[rupd]
            out["ridge_best"][ridx] = h
    out["svd_rss"] = np.where(np.isfinite(out["svd_rss"]), out["svd_rss"], z_energy)
    out["ridge_norm"] = np.where(np.isfinite(out["ridge_norm"]), out["ridge_norm"], np.sqrt(z_energy))
    out["ridge_energy"] = np.where(np.isfinite(out["ridge_energy"]), out["ridge_energy"], z_energy)
    return out


def stack_dual(per_link: list[dict]) -> dict:
    return {k: np.stack([p[k] for p in per_link], 1) for k in per_link[0]}


# ------------------------------------------------------------------ frozen aggregation
def episode_vote(pred: np.ndarray, n_links: int = N_LINKS) -> int:
    p = np.asarray(pred, dtype=int)
    p = p[p >= 0]
    return int(np.bincount(p, minlength=n_links).argmax()) if p.size else -1


def window_labels(score: np.ndarray) -> np.ndarray:
    """``argmin`` over links; first minimum wins, exactly as both stages do."""
    s = np.asarray(score, dtype=float)
    filled = np.where(np.isfinite(s), s, np.inf)
    valid = np.isfinite(s).all(1)
    return np.where(valid, np.argmin(filled, axis=1), -1).astype(int)


def episode_localization(rec: dict, score: np.ndarray) -> dict:
    """Episode labels, votes and metrics over the F4 faulty windows -- the frozen recipe."""
    pred_w = window_labels(score)
    eps, P, T, votes = [], [], [], []
    for e in sorted(set(rec["episode"].tolist())):
        m = (rec["episode"] == e) & (rec["label"] == 1) & (rec["family"] == "F4_contact")
        if m.sum() == 0:
            continue
        t = int(rec["target"][m][0])
        if t < 0:
            continue
        pv = pred_w[m]
        pv = pv[pv >= 0]
        cnt = np.bincount(pv, minlength=N_LINKS) if pv.size else np.zeros(N_LINKS, dtype=int)
        eps.append(e)
        P.append(episode_vote(pred_w[m]))
        T.append(t)
        votes.append(cnt.astype(int))
    P, T = np.asarray(P, dtype=int), np.asarray(T, dtype=int)
    per_link = {l: (float((P[T == l] == l).mean()) if (T == l).any() else float("nan"))
                for l in range(N_LINKS)}
    return {"episodes": np.asarray(eps), "pred": P, "target": T, "votes": np.asarray(votes),
            "window_pred": pred_w,
            "top1": float((P == T).mean()) if T.size else float("nan"),
            "chain_distance": float(np.abs(P - T).mean()) if T.size else float("nan"),
            "correct": (P == T).astype(float), "distance": np.abs(P - T).astype(float),
            "per_link_recall": per_link, "n_episodes": int(T.size)}


def confusion(pred: np.ndarray, truth: np.ndarray) -> np.ndarray:
    c = np.zeros((N_LINKS, N_LINKS), dtype=int)
    for t, p in zip(np.asarray(truth, int), np.asarray(pred, int)):
        if 0 <= t < N_LINKS and 0 <= p < N_LINKS:
            c[t, p] += 1
    return c


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2B-F phases 2-4: dual-estimator replay")
    ap.add_argument("--config", required=True)
    ap.add_argument("--stage2b-config", required=True)
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--device", default=None)
    ap.add_argument("--seeds", default="")
    args = ap.parse_args()

    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import load_bundle, load_checkpoint

    repo = Path(args.repo_root).resolve()
    fcfg = yaml.safe_load(Path(args.config).read_text())
    cfg, cfg_sha = load_config(args.stage2b_config)
    cfg = ensure_model_cfg(cfg)
    root = Path(args.run_root)
    res, arrays = root / "results", root / "arrays"
    for d in (res, arrays, root / "logs"):
        d.mkdir(parents=True, exist_ok=True)
    log: list[str] = []

    def say(m: str) -> None:
        line = f"[{utc_now()}] {m}"
        print(line, flush=True)
        log.append(line)
        (root / "logs" / "stage2bf_replay.log").write_text("\n".join(log) + "\n", encoding="utf-8")

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    fi = fcfg["frozen_inputs"]
    data_root = Path(fcfg["paths"]["data_root"]) / f"{cfg['frozen_inputs']['dataset_profile']}_seed{cfg['frozen_inputs']['dataset_seed']}"
    stage2b_run = Path(fcfg["paths"]["stage2b_run_root"])
    stage2a_run = Path(fcfg["paths"]["stage2a_run_root"])
    cache_root = stage2b_run / "p1_loadpath" / "cache"      # frozen pathway cache, read-only

    say(f"Stage 2B-F replay start (device {device})")
    say(f"stage2b config sha {cfg_sha[:16]}  data_root {data_root}")
    say(f"reusing frozen pathway cache: {cache_root} ({len(list(cache_root.glob('*.npz')))} episodes)")

    bundle = load_bundle(cfg, data_root)
    chain = bundle.base_chain
    grid = WindowGrid.build(int(cfg["simulation"]["window_samples"]), int(cfg["pathway"]["window_time_points"]))
    M = grid.n_points
    d = bundle.n_links * M
    tc = TorchChain.from_chain(chain, dtype=torch.float32, device=device)
    cpoints = candidate_points(chain)
    n_hyp = len(cpoints[0])
    lc_cfg = cfg["loadpath_controls"]
    n_rep = int(lc_cfg["random_control_replicates"])
    seed_base = int(lc_cfg["random_seed_base"])
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [int(s) for s in cfg["seed_list"]]
    say(f"bundle: train={len(bundle.train_ids)} val={len(bundle.val_ids)} test={len(bundle.test_ids)}; "
        f"d={d} (n_links {bundle.n_links} x M {M}); {n_hyp} candidate points; {n_rep} random replicates")

    healthy_ids = list(bundle.train_ids) + list(bundle.val_ids)
    f4_ids = [e for e in bundle.test_ids if bundle.episodes[e].family == "F4_contact"]
    healthy_test = [e for e in bundle.test_ids if bundle.episodes[e].kind == "healthy"]
    eval_ids = sorted(set(bundle.val_ids) | set(f4_ids) | set(healthy_test))

    per_seed: dict[int, dict] = {}
    for seed in seeds:
        t0 = time.time()
        fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
        ck = stage2b_run / "checkpoints" / f"chain_gnn_aug_{fc['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        if not ck.exists():
            say(f"BLOCKED: missing frozen checkpoint {ck}")
            return 4
        model = load_checkpoint("chain_gnn_aug", ck, bundle, cfg, device)["model"]
        say(f"[seed {seed}] frozen checkpoint {ck.name} sha {hashlib.sha256(ck.read_bytes()).hexdigest()[:16]}")

        healthy_w = [episode_windows(model, bundle.episodes[e], bundle, tc, grid, device) for e in healthy_ids]
        win_wh, _inst = fit_whiteners(healthy_w, cfg)
        W = win_wh.whitener
        say(f"[seed {seed}] whitener refitted on {sum(len(h.label) for h in healthy_w)} healthy train+val windows "
            f"(sha {hashlib.sha256(np.ascontiguousarray(W)).hexdigest()[:16]})")

        # fixed reference configuration: healthy TRAIN episodes only (frozen recipe)
        q_train = np.concatenate([bundle.episodes[e].signals["q_meas"][grid.sample_index(bundle.episodes[e].n_samples)]
                                  for e in bundle.train_ids])
        q_ref = LC.reference_configuration(q_train)
        from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians

        kin_ref = forward_kinematics(chain, q_ref[None, :])
        j_ref = link_spatial_jacobians(kin_ref)[0]
        r_ref = kin_ref.R_link[0]

        sup_bases: dict[int, dict] = {l: {} for l in range(bundle.n_links)}
        rnd_bases: dict[int, list[dict]] = {l: [{} for _ in range(n_rep)] for l in range(bundle.n_links)}
        fix_bases: dict[int, dict] = {l: {} for l in range(bundle.n_links)}
        for l in range(bundle.n_links):
            rows_l = LC.support_rows(l, bundle.n_links, M)
            k = len(rows_l)
            for r in range(0, 4):
                for h in range(n_hyp):
                    b = LC.dct_basis(k, r, offset=h * max(1, k // n_hyp))
                    sup_bases[l][(r, h)] = orthonormal_basis(W @ LC.embed(b, rows_l, d))
                    for rep in range(n_rep):
                        rb = LC.random_basis(k, r, seed=seed_base + 1009 * rep + 97 * h + 7 * l + r)
                        rnd_bases[l][rep][(r, h)] = orthonormal_basis(W @ LC.embed(rb, rows_l, d))
            for h, (_, r_link) in enumerate(cpoints[l]):
                rw = r_ref[l] @ np.asarray(r_link, dtype=float)
                Jp = j_ref[l, 3:, :] - skew(rw) @ j_ref[l, :3, :]
                D = np.tile(-Jp.T, (M, 1))
                Uf = orthonormal_basis(W @ D)
                for r in range(0, 4):
                    fix_bases[l][(r, h)] = Uf
        say(f"[seed {seed}] static bases precomputed ({time.time() - t0:.0f}s)")

        rng = np.random.default_rng(seed)
        recs: dict[str, list] = {k: [] for k in ("episode", "split", "family", "kind", "label",
                                                 "target", "start")}
        by_method: dict[str, dict[str, list]] = {m: {} for m in METHOD_ORDER
                                                 if m != "random_within_support_rankmatched"}
        rnd_by_rep: list[dict[str, list]] = [{} for _ in range(n_rep)]
        n_done = 0
        for eid in eval_ids:
            ea = bundle.episodes[eid]
            pw = load_pathways(cache_root, eid)
            ew = episode_windows(model, ea, bundle, tc, grid, device)
            nw = ew.resid.shape[0]
            z = win_wh.transform(stack_window_residual(ew.resid), ew.ctx)
            shuffle = rng.permutation(ew.rows.reshape(-1)).reshape(ew.rows.shape)

            per_al, per_sh = [], []
            for l in range(bundle.n_links):
                hyp_al = [np.einsum("de,nep->ndp", W, LC.contact_columns_batched(pw, ew.rows, l, rl))
                          for _, rl in cpoints[l]]
                hyp_sh = [np.einsum("de,nep->ndp", W, LC.contact_columns_batched(pw, shuffle, l, rl))
                          for _, rl in cpoints[l]]
                per_al.append(dual_stats(hyp_al, z))
                per_sh.append(dual_stats(hyp_sh, z))
            al, sh = stack_dual(per_al), stack_dual(per_sh)
            target_rank = al["svd_rank"]

            per_sup, per_fix = [], []
            per_rnd = [[] for _ in range(n_rep)]
            for l in range(bundle.n_links):
                per_sup.append(dual_static_stats(sup_bases[l], target_rank[:, l], z, n_hyp))
                per_fix.append(dual_static_stats(fix_bases[l], target_rank[:, l], z, n_hyp))
                for rep in range(n_rep):
                    per_rnd[rep].append(dual_static_stats(rnd_bases[l][rep], target_rank[:, l], z, n_hyp))
            sup, fix = stack_dual(per_sup), stack_dual(per_fix)
            rnds = [stack_dual(per_rnd[rep]) for rep in range(n_rep)]

            for m, s in (("time_aligned_jacobian", al), ("shuffled_time_jacobian", sh),
                         ("support_prefix_rankmatched", sup), ("fixed_reference_jacobian", fix)):
                for k, v in s.items():
                    by_method[m].setdefault(k, []).append(v)
            for rep in range(n_rep):
                for k, v in rnds[rep].items():
                    rnd_by_rep[rep].setdefault(k, []).append(v)

            recs["episode"].append(np.full(nw, eid, dtype=object))
            recs["split"].append(np.full(nw, ea.split, dtype=object))
            recs["family"].append(np.full(nw, ea.family, dtype=object))
            recs["kind"].append(np.full(nw, ea.kind, dtype=object))
            recs["label"].append(ew.label)
            recs["target"].append(ew.target)
            recs["start"].append(ew.starts)
            n_done += 1
            if n_done % 25 == 0:
                say(f"[seed {seed}] {n_done}/{len(eval_ids)} episodes ({time.time() - t0:.0f}s)")

        rec = {k: np.concatenate(v) for k, v in recs.items()}
        packed = {m: {k: np.concatenate(v) for k, v in s.items()} for m, s in by_method.items()}
        packed_rnd = [{k: np.concatenate(v) for k, v in s.items()} for s in rnd_by_rep]
        per_seed[seed] = {"rec": rec, "stats": packed, "random": packed_rnd, "dimension": d}

        np.savez_compressed(arrays / f"stage2bf_dual_scores_seed{seed}.npz", dimension=d,
                            n_replicates=n_rep,
                            **{f"{m}__{k}": v for m, s in packed.items() for k, v in s.items()},
                            **{f"random{rep}__{k}": v for rep, s in enumerate(packed_rnd)
                               for k, v in s.items()},
                            **{k: (v.astype(str) if v.dtype == object else v) for k, v in rec.items()})
        say(f"[seed {seed}] done ({time.time() - t0:.0f}s), {len(rec['label'])} windows")

    write_json(res / "stage2bf_replay_manifest.json", {
        "generated_utc": utc_now(), "seeds": seeds, "methods": list(METHOD_ORDER),
        "n_random_replicates": n_rep, "n_hypotheses_per_link": n_hyp, "residual_dimension": d,
        "window_time_points": M, "device": device, "stage2b_config_sha256": cfg_sha,
        "frozen_pathway_cache": str(cache_root),
        "stage2a_run_root": str(stage2a_run), "stage2b_run_root": str(stage2b_run),
        "estimators": [EI.RIDGE_CANONICAL, EI.SVD_CANONICAL],
        "note": ("both estimators are computed on the same z and the same dictionaries inside one "
                 "loop; neither is re-derived from its formula"),
    })
    say("replay complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
