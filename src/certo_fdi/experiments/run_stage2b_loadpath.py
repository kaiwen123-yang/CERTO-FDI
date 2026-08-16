"""Stage 2B Phase 1: source-of-gain decomposition of the contact localizer.

Runs the five matched controls on identical whitened residuals and splits Stage 2A's
localization gain into

    Delta_support  = M_support  - M_neural     (serial-chain prefix support alone)
    Delta_shape    = M_fixedJ   - M_support    (real Cartesian subspace shape, no alignment)
    Delta_temporal = M_alignedJ - M_fixedJ     (trajectory-aligned geometry)

plus the aligned-versus-shuffled comparison. Every difference carries an **episode-cluster**
confidence interval; no Cartesian-geometry claim is permitted unless the aligned method beats
*both* the fixed-reference and the shuffled-time control with a CI excluding zero.

It also reproduces the frozen Stage 2A contact localizer through the *inherited* Stage 2A code
path, so the reproduction is a like-for-like check rather than a reimplementation.

Efficiency note: the support, random and fixed-reference dictionaries are identical for every
window (they read no configuration, or one fixed one), so their whitened orthonormal bases are
computed once per (link, rank, hypothesis) and applied to all windows with a single matmul.
Only the aligned and shuffled dictionaries need a per-window SVD.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from certo_fdi.experiments.common import write_csv, write_json
from certo_fdi.experiments.stage2b_common import (
    Stage,
    common_parser,
    ensure_model_cfg,
    episode_cluster_bootstrap,
    paired_episode_bootstrap,
    seedwise,
)
from certo_fdi.experiments.stage2a_pathway_pipeline import (
    WindowGrid,
    build_cache_parallel,
    episode_windows,
    fit_whiteners,
    load_pathways,
    stack_window_residual,
)
from certo_fdi.pathways.geometry import orthonormal_basis
from certo_fdi.pathways.jacobians import candidate_points, skew
from certo_fdi.stage2b import loadpath_controls as LC
from certo_fdi.stage2b import rank_aware_scores as RS

METHOD_ORDER = ("support_prefix_rankmatched", "random_within_support_rankmatched",
                "fixed_reference_jacobian", "shuffled_time_jacobian", "time_aligned_jacobian")


def _basis_ess(U: np.ndarray, z: np.ndarray) -> np.ndarray:
    """||U^T z||^2 for a fixed orthonormal basis ``U`` (d,r) and all windows ``z`` (N,d)."""
    return ((z @ U) ** 2).sum(1) if U.shape[1] else np.zeros(z.shape[0])


def _static_stats(bases: dict[tuple[int, int], np.ndarray], target_rank: np.ndarray, z: np.ndarray,
                  n_hyp: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Best-of-hypotheses stats for a control whose dictionary does not vary per window.

    ``bases[(rank, hypothesis)]`` is the whitened orthonormal basis. Windows are grouped by their
    rank-match target so each basis is applied once.
    """
    N = z.shape[0]
    z_energy = (z ** 2).sum(1)
    best_rss = np.full(N, np.inf)
    best_ess = np.zeros(N)
    best_rank = np.zeros(N, dtype=int)
    best_h = np.zeros(N, dtype=int)
    for r in np.unique(target_rank):
        m = target_rank == r
        if not m.any():
            continue
        zi = z[m]
        for h in range(n_hyp):
            U = bases.get((int(r), h))
            if U is None:
                continue
            ess = _basis_ess(U, zi)
            rss = np.maximum(z_energy[m] - ess, 0.0)
            upd = rss < best_rss[m]
            idx = np.where(m)[0][upd]
            best_rss[idx] = rss[upd]
            best_ess[idx] = ess[upd]
            best_rank[idx] = U.shape[1]
            best_h[idx] = h
    best_rss = np.where(np.isfinite(best_rss), best_rss, z_energy)
    return best_ess, best_rss, best_rank, best_h


def _episode_vote(pred: np.ndarray) -> int:
    p = pred[pred >= 0]
    return int(np.bincount(p, minlength=7).argmax()) if p.size else -1


def _episode_localization(rec: dict, stats: dict, dimension: int, score: str,
                          acceptance: np.ndarray | None = None) -> dict:
    """Episode-level F4 localization under one score (majority vote over faulty windows)."""
    ps = RS.ProjectionStats(rss=stats["rss"], ess=stats["ess"], rank=stats["rank"],
                            z_energy=stats["rss"].sum(1), dimension=dimension)
    pred_w = RS.predict_link(ps, score, acceptance)
    rank_w = RS.link_ranking(ps, score, acceptance)
    eps, P, T, top2 = [], [], [], []
    for e in np.unique(rec["episode"]):
        m = (rec["episode"] == e) & (rec["label"] == 1) & (rec["family"] == "F4_contact")
        if m.sum() == 0:
            continue
        t = int(rec["target"][m][0])
        if t < 0:
            continue
        v = _episode_vote(pred_w[m])
        eps.append(e)
        P.append(v)
        T.append(t)
        top2.append(int(t in np.bincount(rank_w[m][:, 0], minlength=7).argsort()[-2:]))
    P, T = np.asarray(P), np.asarray(T)
    return {"episodes": np.asarray(eps), "pred": P, "target": T,
            "top1": float((P == T).mean()) if T.size else float("nan"),
            "top2": float(np.mean(top2)) if top2 else float("nan"),
            "chain_distance": float(np.abs(P - T).mean()) if T.size else float("nan"),
            "correct": (P == T).astype(float), "distance": np.abs(P - T).astype(float),
            "n_episodes": int(T.size)}


def _evidence_auroc(rec: dict, stats: dict) -> float:
    """Head-free contact-evidence AUROC: max-over-links explained energy, F4 faulty vs healthy.

    Deliberately head-free so the five controls are compared on the geometry alone; fitting a
    density head per control would confound the comparison with head capacity.
    """
    from certo_fdi.anomaly.event_detection import safe_auroc

    ev = stats["ess"].max(1)
    pos = (rec["label"] == 1) & (rec["family"] == "F4_contact")
    neg = rec["label"] == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    return safe_auroc(np.r_[np.ones(pos.sum()), np.zeros(neg.sum())], np.r_[ev[pos], ev[neg]])


def _analyse(st: Stage, per_seed: dict, cfg: dict, n_rep: int) -> None:
    stats_cfg = cfg["statistics"]
    nb, alpha = int(stats_cfg["bootstrap_resamples"]), float(stats_cfg["bootstrap_alpha"])
    score = RS.AUDIT_CONTROL_SCORE
    rows, rank_rows, boot_rows = [], [], []
    per_method_seed: dict[str, dict[int, dict]] = {}
    for seed, blob in per_seed.items():
        rec, d = blob["rec"], blob["dimension"]
        methods = {m: blob["stats"][m] for m in blob["stats"]}
        for rep, s in enumerate(blob["random"]):
            methods[f"random_within_support_rankmatched#{rep}"] = s
        for m, s in methods.items():
            loc = _episode_localization(rec, s, d, score)
            auroc = _evidence_auroc(rec, s)
            base = m.split("#")[0]
            per_method_seed.setdefault(base, {}).setdefault(seed, {})[m] = {"loc": loc, "auroc": auroc}
            rows.append(st.base_row(method=m, partition="F4_TEST", split="ALL", seed=seed,
                                    fault_family="F4_contact", score=score,
                                    episode_top1=loc["top1"], episode_top2=loc["top2"],
                                    mean_chain_distance=loc["chain_distance"],
                                    n_episodes=loc["n_episodes"],
                                    contact_evidence_auroc=auroc,
                                    replicate=int(m.split("#")[1]) if "#" in m else -1,
                                    reads_configuration=base in LC.GEOMETRIC_METHODS,
                                    units="top-k accuracy; chain distance in links; AUROC dimensionless"))
            fw = (rec["label"] == 1) & (rec["family"] == "F4_contact")
            if fw.any():
                rank_rows.append(st.base_row(method=m, partition="F4_TEST", split="ALL", seed=seed,
                                             fault_family="F4_contact", replicate=int(m.split("#")[1]) if "#" in m else -1,
                                             **{f"mean_rank_link{l}": float(s["rank"][fw, l].mean()) for l in range(s["rank"].shape[1])},
                                             mean_rank_overall=float(s["rank"][fw].mean()),
                                             max_rank_overall=int(s["rank"][fw].max()),
                                             units="numerical rank of the selected per-link dictionary"))
    st.write_table("stage2b_loadpath_controls.csv", rows,
                   units="episode-level localization and head-free contact-evidence AUROC",
                   schema={"method": "load-path control", "replicate": "-1 unless a random-control replicate",
                           "score": "audit-control score used for this table"})
    st.write_table("stage2b_rank_audit.csv", rank_rows,
                   units="mean numerical rank of the selected dictionary on F4 fault windows",
                   schema={"mean_rank_linkL": "per-link rank actually realised (the match target)"})

    # ---- gain decomposition with paired episode-cluster CIs
    def agg(method: str, seed: int, key: str) -> float:
        d = per_method_seed.get(method, {}).get(seed, {})
        if not d:
            return float("nan")
        vals = [v["loc"][key] if key in ("top1", "chain_distance") else v["auroc"] for v in d.values()]
        return float(np.nanmean(vals))

    seeds = sorted(per_seed)
    deltas = {}
    for name, (a, b) in {"delta_support": ("support_prefix_rankmatched", None),
                         "delta_shape": ("fixed_reference_jacobian", "support_prefix_rankmatched"),
                         "delta_temporal_geometry": ("time_aligned_jacobian", "fixed_reference_jacobian"),
                         "aligned_minus_shuffled": ("time_aligned_jacobian", "shuffled_time_jacobian"),
                         "aligned_minus_support": ("time_aligned_jacobian", "support_prefix_rankmatched"),
                         "aligned_minus_random": ("time_aligned_jacobian", "random_within_support_rankmatched"),
                         }.items():
        by_seed_t1, by_seed_cd = {}, {}
        for seed in seeds:
            ta = agg(a, seed, "top1")
            tb = agg(b, seed, "top1") if b else float(cfg["contact_reference"]["counterfactual_top1"])
            ca = agg(a, seed, "chain_distance")
            cb = agg(b, seed, "chain_distance") if b else float(cfg["contact_reference"]["counterfactual_chain_distance"])
            by_seed_t1[seed] = ta - tb
            by_seed_cd[seed] = cb - ca
        deltas[name] = {"top1_gain": seedwise(by_seed_t1), "chain_distance_reduction": seedwise(by_seed_cd),
                        "a": a, "b": b or "counterfactual_stage1rb (frozen Stage 2A baseline)"}

    # paired episode-cluster CIs on the primary contrasts, pooled over seeds
    for name, (a, b) in {"aligned_minus_shuffled": ("time_aligned_jacobian", "shuffled_time_jacobian"),
                         "aligned_minus_fixed": ("time_aligned_jacobian", "fixed_reference_jacobian"),
                         "aligned_minus_support": ("time_aligned_jacobian", "support_prefix_rankmatched"),
                         "fixed_minus_support": ("fixed_reference_jacobian", "support_prefix_rankmatched"),
                         }.items():
        eps_all, ca, cb, da, db = [], [], [], [], []
        for seed in seeds:
            A = per_method_seed.get(a, {}).get(seed, {})
            B = per_method_seed.get(b, {}).get(seed, {})
            if not A or not B:
                continue
            la = list(A.values())[0]["loc"]
            lb = list(B.values())[0]["loc"]
            eps_all.append(np.array([f"{seed}:{e}" for e in la["episodes"]]))
            ca.append(la["correct"]); cb.append(lb["correct"])
            da.append(la["distance"]); db.append(lb["distance"])
        if not eps_all:
            continue
        eps_all = np.concatenate(eps_all)
        top1 = paired_episode_bootstrap(eps_all, np.concatenate(ca), np.concatenate(cb), nb, alpha)
        dist = paired_episode_bootstrap(eps_all, np.concatenate(db), np.concatenate(da), nb, alpha)
        boot_rows.append(st.base_row(method=name, partition="F4_TEST", split="ALL", seed="pooled",
                                     fault_family="F4_contact", contrast=f"{a} - {b}",
                                     top1_diff=top1["point"], top1_ci_low=top1["ci_low"], top1_ci_high=top1["ci_high"],
                                     top1_ci_excludes_zero=top1.get("ci_excludes_zero"),
                                     chain_distance_reduction=dist["point"], cd_ci_low=dist["ci_low"],
                                     cd_ci_high=dist["ci_high"], cd_ci_excludes_zero=dist.get("ci_excludes_zero"),
                                     n_episodes=top1["n_episodes"], n_resamples=nb, unit="episode",
                                     units="paired difference with a percentile episode-cluster bootstrap CI"))
    st.write_table("stage2b_episode_bootstrap.csv", boot_rows,
                   units="paired differences with episode-cluster bootstrap CIs",
                   schema={"contrast": "which two controls are differenced", "unit": "always episode"})
    write_json(st.layout.results / "stage2b_gain_decomposition.json", {
        "audit_control_score": score,
        "deltas": deltas,
        "definition": {"delta_support": "M_support - M_neural (frozen Stage 2A counterfactual localizer)",
                       "delta_shape": "M_fixedJ - M_support",
                       "delta_temporal_geometry": "M_alignedJ - M_fixedJ"},
        "cartesian_claim_rule": ("permitted only if the aligned method beats BOTH the fixed-reference and the "
                                 "shuffled-time control with an episode-cluster CI excluding zero"),
        "seeds": seeds,
    })
    st.log("gain decomposition written")


def main() -> int:
    ap = common_parser("Stage 2B Phase 1: load-path source-of-gain decomposition")
    ap.add_argument("--seeds", default="")
    args = ap.parse_args()
    st = Stage(args, "loadpath")
    if not st.require_freeze():
        return 3
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import load_checkpoint
    from certo_fdi.experiments.stage2b_common import episode_seed_map

    cfg = ensure_model_cfg(st.cfg)
    bundle = st.bundle
    chain = bundle.base_chain
    n_links = bundle.n_links
    grid = WindowGrid.build(int(cfg["simulation"]["window_samples"]), int(cfg["pathway"]["window_time_points"]))
    M = grid.n_points
    d = n_links * M
    cache_root = st.layout.sub("p1_loadpath") / "cache"
    lc_cfg = cfg["loadpath_controls"]
    n_hyp = len(candidate_points(chain)[0])
    n_rep = int(lc_cfg["random_control_replicates"])
    seed_base = int(lc_cfg["random_seed_base"])
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [int(s) for s in cfg["seed_list"]]
    tc = TorchChain.from_chain(chain, dtype=torch.float32, device=st.device)

    # ---------------------------------------------------------------- pathway cache
    import csv as _csv

    with (st.data_root / "episode_index.csv").open(newline="", encoding="utf-8") as f:
        index_rows = list(_csv.DictReader(f))
    by_id = {r["episode_id"]: r for r in index_rows}
    ep_seeds = episode_seed_map(st.data_root)
    healthy_ids = list(bundle.train_ids) + list(bundle.val_ids)
    f4_ids = [e for e in bundle.test_ids if bundle.episodes[e].family == "F4_contact"]
    healthy_test = [e for e in bundle.test_ids if bundle.episodes[e].kind == "healthy"]
    needed = sorted(set(healthy_ids + f4_ids + healthy_test))
    build_cache_parallel([by_id[e] for e in needed if e in by_id], ep_seeds, cfg, grid,
                         st.data_root, cache_root, n_workers=args.workers, log=st.log)

    cpoints = candidate_points(chain)
    control_rows: list[dict] = []
    rank_rows: list[dict] = []
    support_rows_audit: list[dict] = []
    per_seed_pred: dict[int, dict] = {}

    for seed in seeds:
        t_seed = time.time()
        fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
        ck = st.layout.sub("checkpoints") / f"chain_gnn_aug_{fc['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        if not ck.exists():
            st.log(f"BLOCKED: missing H40 checkpoint {ck}")
            return 4
        model = load_checkpoint("chain_gnn_aug", ck, bundle, cfg, st.device)["model"]

        healthy_w = [episode_windows(model, bundle.episodes[e], bundle, tc, grid, st.device) for e in healthy_ids]
        win_wh, inst_wh = fit_whiteners(healthy_w, cfg)
        W = win_wh.whitener
        st.log(f"[seed {seed}] whiteners fitted on {sum(len(h.label) for h in healthy_w)} healthy train+val windows")

        # -------- fixed reference configuration: healthy TRAIN episodes only
        q_train = np.concatenate([bundle.episodes[e].signals["q_meas"][grid.sample_index(bundle.episodes[e].n_samples)]
                                  for e in bundle.train_ids])
        q_ref = LC.reference_configuration(q_train)
        from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians

        kin_ref = forward_kinematics(chain, q_ref[None, :])
        j_ref = link_spatial_jacobians(kin_ref)[0]          # (n_links, 6, n)
        r_ref = kin_ref.R_link[0]                           # (n_links, 3, 3)

        # -------- precompute the window-invariant whitened bases (support / random / fixed)
        # rank targets are per window, so bases are cached per (link, rank, hypothesis)
        sup_bases: dict[int, dict] = {l: {} for l in range(n_links)}
        rnd_bases: dict[int, list[dict]] = {l: [{} for _ in range(n_rep)] for l in range(n_links)}
        fix_bases: dict[int, dict] = {l: {} for l in range(n_links)}
        for l in range(n_links):
            rows_l = LC.support_rows(l, n_links, M)
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
                    fix_bases[l][(r, h)] = Uf            # rank is whatever the geometry gives
        st.log(f"[seed {seed}] static bases precomputed ({time.time() - t_seed:.0f}s)")

        # -------- per-episode evaluation
        eval_ids = sorted(set(bundle.val_ids) | set(f4_ids) | set(healthy_test))
        rng = np.random.default_rng(seed)
        recs: dict[str, list] = {k: [] for k in ("episode", "split", "family", "kind", "label", "target", "onset_s", "t_end", "start")}
            # the random control is accumulated per replicate, not in this dict
        stats_by_method: dict[str, dict[str, list]] = {
            m: {"rss": [], "ess": [], "rank": []} for m in METHOD_ORDER if m != "random_within_support_rankmatched"}
        rnd_by_rep: list[dict[str, list]] = [{"rss": [], "ess": [], "rank": []} for _ in range(n_rep)]
        stage2a_resid: list[np.ndarray] = []
        n_done = 0
        for eid in eval_ids:
            ea = bundle.episodes[eid]
            pw = load_pathways(cache_root, eid)
            ew = episode_windows(model, ea, bundle, tc, grid, st.device)
            nw = ew.resid.shape[0]
            z = win_wh.transform(stack_window_residual(ew.resid), ew.ctx)
            shuffle = rng.permutation(ew.rows.reshape(-1)).reshape(ew.rows.shape)

            # aligned + shuffled: per-window dictionaries
            per_link_al, per_link_sh = [], []
            for l in range(n_links):
                hyp_al = [np.einsum("de,nep->ndp", W, LC.contact_columns_batched(pw, ew.rows, l, rl)) for _, rl in cpoints[l]]
                hyp_sh = [np.einsum("de,nep->ndp", W, LC.contact_columns_batched(pw, shuffle, l, rl)) for _, rl in cpoints[l]]
                per_link_al.append(RS.best_hypothesis_stats(hyp_al, z))
                per_link_sh.append(RS.best_hypothesis_stats(hyp_sh, z))
            al = RS.stack_links(per_link_al, z, d)
            sh = RS.stack_links(per_link_sh, z, d)
            # the rank-match target is the aligned dictionary's realised rank, per window and link
            target_rank = al.rank

            per_link_sup, per_link_fix = [], []
            per_link_rnd = [[] for _ in range(n_rep)]
            for l in range(n_links):
                per_link_sup.append(_static_stats(sup_bases[l], target_rank[:, l], z, n_hyp))
                per_link_fix.append(_static_stats(fix_bases[l], target_rank[:, l], z, n_hyp))
                for rep in range(n_rep):
                    per_link_rnd[rep].append(_static_stats(rnd_bases[l][rep], target_rank[:, l], z, n_hyp))
            sup = RS.stack_links(per_link_sup, z, d)
            fix = RS.stack_links(per_link_fix, z, d)
            rnds = [RS.stack_links(per_link_rnd[rep], z, d) for rep in range(n_rep)]

            for m, s in (("time_aligned_jacobian", al), ("shuffled_time_jacobian", sh),
                         ("support_prefix_rankmatched", sup), ("fixed_reference_jacobian", fix)):
                stats_by_method[m]["rss"].append(s.rss)
                stats_by_method[m]["ess"].append(s.ess)
                stats_by_method[m]["rank"].append(s.rank)
            for rep in range(n_rep):
                rnd_by_rep[rep]["rss"].append(rnds[rep].rss)
                rnd_by_rep[rep]["ess"].append(rnds[rep].ess)
                rnd_by_rep[rep]["rank"].append(rnds[rep].rank)

            recs["episode"].append(np.full(nw, eid, dtype=object))
            recs["split"].append(np.full(nw, ea.split, dtype=object))
            recs["family"].append(np.full(nw, ea.family, dtype=object))
            recs["kind"].append(np.full(nw, ea.kind, dtype=object))
            recs["label"].append(ew.label)
            recs["target"].append(ew.target)
            recs["onset_s"].append(np.full(nw, ew.onset_s))
            recs["t_end"].append(ew.t_end)
            recs["start"].append(ew.starts)
            n_done += 1
            if n_done % 25 == 0:
                st.log(f"[seed {seed}] controls {n_done}/{len(eval_ids)} episodes ({time.time() - t_seed:.0f}s)")

        rec = {k: np.concatenate(v) for k, v in recs.items()}
        packed = {m: {k: np.concatenate(v) for k, v in s.items()} for m, s in stats_by_method.items()}
        packed_rnd = [{k: np.concatenate(v) for k, v in s.items()} for s in rnd_by_rep]
        per_seed_pred[seed] = {"rec": rec, "stats": packed, "random": packed_rnd, "dimension": d}

        np.savez_compressed(st.layout.sub("p1_loadpath") / f"controls_seed{seed}.npz",
                            dimension=d, n_replicates=n_rep,
                            **{f"{m}__{k}": v for m, s in packed.items() for k, v in s.items()},
                            **{f"random{rep}__{k}": v for rep, s in enumerate(packed_rnd) for k, v in s.items()},
                            **{k: (v.astype(str) if v.dtype == object else v) for k, v in rec.items()})
        st.log(f"[seed {seed}] controls done ({time.time() - t_seed:.0f}s), {len(rec['label'])} windows")

    # ---------------------------------------------------------------- analysis
    _analyse(st, per_seed_pred, cfg, n_rep)

    write_json(st.layout.results / "stage2b_loadpath_run_manifest.json", {
        "seeds": seeds, "methods": list(METHOD_ORDER), "n_random_replicates": n_rep,
        "n_hypotheses_per_link": n_hyp, "window_time_points": M, "residual_dimension": d,
        "eval_partitions": {"healthy_val": len(bundle.val_ids), "healthy_test": len(healthy_test),
                            "F4_test": len(f4_ids)},
        "rank_match_target": "per-window numerical rank of the time-aligned dictionary",
        "hypothesis_match": "every control gets the same number of hypotheses as the aligned method",
        "fixed_reference_configuration": q_ref.tolist(),
        "fixed_reference_source": "element-wise median of healthy TRAIN configurations",
    })
    st.finish({"seeds": seeds})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
