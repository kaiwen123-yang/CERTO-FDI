"""Stage 1R-B Phase A orchestrator: gauge-invariant Gram audit, oracle torque-correction
ceilings (old 12-column basis vs free local wrench), analytic mismatch-wrench projection, and
the frozen retirement rules (05_CAPACITY_AUDIT_AND_ORACLE_PROTOCOL.md §5).

No network is trained here. Only healthy episodes are read; regularization strengths are
selected on healthy validation windows by held-out-timestep prediction error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch

from certo_fdi.data.franka_generator import reference_chain
from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch
from certo_fdi.experiments.common import capture_environment, load_config, utc_now, write_csv, write_json
from certo_fdi.experiments.pipeline import DataBundle, load_bundle
from certo_fdi.experiments.r0_model_covariance import tool_chain
from certo_fdi.geometry.frame_reparameterization import sample_link_frames
from certo_fdi.models.basis_capacity_audit import (
    ANALYTIC_BASIS_DIM,
    BASIS_NAMES,
    DEPENDENCY_NAMES,
    chain_projection,
    gram_audit,
    invariant_column_scale,
    mismatch_wrench,
    oracle_operators,
    projection_residual,
    solve_min_norm,
    solve_regularized,
    stable_nullspace,
)
from certo_fdi.models.covariant_basis import covariant_basis
from certo_fdi.paths import create_or_resume_run, git_sha

REQUIRED_COLUMNS = ("run_id", "git_sha", "config_sha256", "dataset_sha256_or_manifest_sha", "model", "seed", "status", "provisional", "strict_claim")


def _log(layout, lines: list[str], msg: str) -> None:
    line = f"[{utc_now()}] {msg}"
    print(line, flush=True)
    lines.append(line)
    (layout.sub("logs") / "stage1rb_basis_audit.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _q(x: np.ndarray, qs=(0.5, 0.9, 0.99)) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {f"p{int(q * 100)}": float("nan") for q in qs} | {"max": float("nan"), "mean": float("nan")}
    return {f"p{int(q * 100)}": float(np.quantile(x, q)) for q in qs} | {"max": float(x.max()), "mean": float(x.mean())}


def _episode_typed(ep, base_chain, t_idx: np.ndarray, device: str, *, truth: bool = False, dtype=torch.float64):
    """Typed RNEA batch (float64) of one episode at sample indices ``t_idx`` with its declared tool inertia."""
    chain = tool_chain(base_chain, ep.tool_id)
    tc = TorchChain.from_chain(chain, dtype=dtype, device=device)
    if truth:
        with h5py.File(ep_path(ep), "r") as f:
            q = f["signals"]["q_true"][()][t_idx]
            qd = f["signals"]["qd_true"][()][t_idx]
            qdd = f["signals"]["qdd_true"][()][t_idx]
    else:
        q, qd, qdd = ep.signals["q_meas"][t_idx], ep.signals["qd_meas"][t_idx], ep.signals["qdd_est"][t_idx]
    tq = lambda a: torch.as_tensor(np.asarray(a, dtype=np.float64), dtype=dtype, device=device)
    tb = rnea_batch(tc, tq(q), tq(qd), tq(qdd))
    return tc, tb


_EP_PATHS: dict[str, str] = {}


def ep_path(ep) -> str:
    return _EP_PATHS[ep.episode_id]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--storage-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--max-oracle-episodes-per-split", type=int, default=None, help="debug only; the pilot audit uses all healthy episodes")
    args = ap.parse_args(argv)

    cfg, cfg_sha = load_config(args.config)
    repo_root = Path(args.repo_root).resolve()
    layout = create_or_resume_run(args.storage_root, args.run_id, stage=cfg["stage"])
    lines: list[str] = []
    (layout.sub("config") / Path(args.config).name).write_bytes(Path(args.config).read_bytes())
    capture_environment(layout, repo_root, "stage1rb_basis_audit_start", {"config_sha256": cfg_sha})
    ba = cfg["basis_audit"]
    dev = args.device
    fi = cfg["frozen_inputs"]
    data_root = Path(args.data_root or cfg["paths"]["data_root"]) / f"{fi['dataset_profile']}_seed{fi['dataset_seed']}"

    # ------------------------------------------------------------- provenance gate
    dm = json.loads((data_root / "dataset_manifest.json").read_text())
    mjcf_now = hashlib.sha256(Path(cfg["paths"]["mjcf_path"]).read_bytes()).hexdigest()
    prov = {
        "dataset_manifest_config_sha256": dm["config_sha256"], "expected_pilot_config_sha256": fi["pilot_config_sha256"],
        "dataset_manifest_mjcf_sha256": dm["mjcf_sha256"], "mjcf_sha256_now": mjcf_now, "expected_mjcf_sha256": fi["mjcf_sha256"],
        "n_planned": dm["n_planned"], "n_generated": dm["n_generated_now"], "dataset_git_sha": dm["git_sha"],
    }
    ver_path = layout.run_root / "provenance" / "dataset_verification.json"
    ver = json.loads(ver_path.read_text()) if ver_path.exists() else {}
    prov["dataset_verification_status"] = ver.get("status", "MISSING")
    prov["postgmo_manifest_sha256"] = ver.get("postgmo_manifest_sha256", "")
    ok = dm["config_sha256"] == fi["pilot_config_sha256"] and dm["mjcf_sha256"] == fi["mjcf_sha256"] == mjcf_now and str(ver.get("status", "")).startswith("PASS")
    prov["gate"] = "PASS" if ok else "BLOCKED"
    write_json(layout.results / "stage1rb_provenance_gate.json", prov)
    if not ok:
        _log(layout, lines, f"BLOCKED: provenance gate failed {json.dumps(prov)}")
        return 2
    manifest_sha = ver["postgmo_manifest_sha256"]
    _log(layout, lines, f"provenance gate PASS; post-GMO dataset manifest sha {manifest_sha[:16]}…")

    def base(**kw) -> dict[str, Any]:
        row = {"run_id": layout.run_id, "git_sha": git_sha(repo_root), "config_sha256": cfg_sha, "dataset_sha256_or_manifest_sha": manifest_sha, "model": "ligra_v1_basis12", "seed": "", "status": "OK", "provisional": False, "strict_claim": ""}
        row.update(kw)
        return row

    # ------------------------------------------------------------- data (healthy only)
    t0 = time.time()
    bundle: DataBundle = load_bundle(cfg, data_root, only_kinds=("healthy",))
    import csv as _csv

    for r in _csv.DictReader((data_root / "episode_index.csv").open(newline="", encoding="utf-8")):
        _EP_PATHS[r["episode_id"]] = r["path"]
    healthy_ids = {"train": bundle.train_ids, "val": bundle.val_ids, "test": bundle.test_ids}
    _log(layout, lines, f"healthy episodes: train={len(bundle.train_ids)} val={len(bundle.val_ids)} test={len(bundle.test_ids)} ({time.time() - t0:.0f}s)")
    n = bundle.n_links
    sub = int(ba["time_subsample"])
    t_idx = np.arange(0, 6000, sub)
    W = int(ba["oracle_window_samples"])
    stride = int(ba["oracle_window_stride"])
    rank_tol = float(ba["rank_tolerance"])

    # ------------------------------------------------------------- A1a: invariant column scale (healthy TRAIN)
    acc = []
    for eid in bundle.train_ids:
        tc, tb = _episode_typed(bundle.episodes[eid], bundle.base_chain, t_idx, dev)
        acc.append(invariant_column_scale(tc, tb) ** 2)
    col_scale = torch.stack(acc).mean(0).sqrt()
    _log(layout, lines, "invariant column scales: " + json.dumps({k: float(v) for k, v in zip(BASIS_NAMES, col_scale.cpu())}))

    # ------------------------------------------------------------- A1b: Gram audit over all healthy episodes
    per_link_G: dict[int, list[torch.Tensor]] = {i: [] for i in range(n)}
    stats_rows = []
    sample_records = []  # (split, partition, episode, link, rank, cond_full, cond_plus, sigma_min_plus, lam_max, window)
    dep_acc: dict[str, list[np.ndarray]] = {k: [] for k in DEPENDENCY_NAMES}
    corr_acc = torch.zeros(n, ANALYTIC_BASIS_DIM, ANALYTIC_BASIS_DIM, dtype=torch.float64)
    corr_cnt = 0
    eval_acc: dict[int, list[np.ndarray]] = {i: [] for i in range(n)}
    for part, ids in healthy_ids.items():
        for eid in ids:
            ep = bundle.episodes[eid]
            tc, tb = _episode_typed(ep, bundle.base_chain, t_idx, dev)
            g = gram_audit(tc, tb, col_scale, rank_tol=rank_tol, keep_gram=True)
            for i in range(n):
                per_link_G[i].append(g.gram[:, i].cpu())
                eval_acc[i].append(g.evals[:, i].cpu().numpy())
            corr_acc += g.corr.abs().mean(0).cpu()
            corr_cnt += 1
            for k in DEPENDENCY_NAMES:
                dep_acc[k].append(g.dependency_relative_residuals[k].cpu().numpy())
            wid = (t_idx // W).astype(int)
            rk, cf, cp, sm, lm = g.rank.cpu().numpy(), g.cond_full.cpu().numpy(), g.cond_plus.cpu().numpy(), g.sigma_min_plus.cpu().numpy(), g.evals[..., -1].cpu().numpy()
            for i in range(n):
                sample_records.append(np.stack([np.full(len(t_idx), i), rk[:, i], cf[:, i], cp[:, i], sm[:, i], lm[:, i], wid], 1))
                for w_ in np.unique(wid):
                    m = wid == w_
                    stats_rows.append({"partition": part, "split": ep.split, "episode_id": eid, "link": i, "window": int(w_), "rank_min": int(rk[m, i].min()), "rank_max": int(rk[m, i].max()), "cond_full_median": float(np.median(cf[m, i])), "cond_plus_median": float(np.median(cp[m, i])), "sigma_min_plus_median": float(np.median(sm[m, i])), "lambda_max_median": float(np.median(lm[m, i]))})
    _log(layout, lines, f"Gram audit done on {corr_cnt} healthy episodes ({time.time() - t0:.0f}s)")
    corr_mean = (corr_acc / max(corr_cnt, 1)).numpy()
    thr_c = float(ba["condition_threshold"])

    # aggregate table
    import pandas as pd

    win = pd.DataFrame(stats_rows)
    leaf_links = [i for i in range(n) if len(bundle.base_chain.children(i)) == 0]
    win["stratum_leaf"] = np.where(win.link.isin(leaf_links), "leaf", "non_leaf")
    rank_rows = []

    def agg(df: pd.DataFrame, tag: dict) -> None:
        if df.empty:
            return
        row = base(**tag)
        row.update({"n_window_links": int(len(df)), "n_episodes": int(df.episode_id.nunique()),
                    "rank_min": int(df.rank_min.min()), "rank_max": int(df.rank_max.max()), "rank_mode": int(df.rank_max.mode().iloc[0]),
                    **{f"rank_frac_{r}": float((df.rank_max == r).mean()) for r in range(0, 7)},
                    "nullity_min": int(ANALYTIC_BASIS_DIM - df.rank_max.max()), "nullity_max": int(ANALYTIC_BASIS_DIM - df.rank_min.min()),
                    "cond_full_median": float(df.cond_full_median.median()), "cond_full_p90": float(df.cond_full_median.quantile(0.9)),
                    "frac_windows_cond_full_gt_threshold": float((df.cond_full_median > thr_c).mean()),
                    "cond_plus_median": float(df.cond_plus_median.median()), "cond_plus_p90": float(df.cond_plus_median.quantile(0.9)), "cond_plus_p99": float(df.cond_plus_median.quantile(0.99)),
                    "frac_windows_cond_plus_gt_threshold": float((df.cond_plus_median > thr_c).mean()),
                    "sigma_min_plus_median": float(df.sigma_min_plus_median.median()), "sigma_min_plus_p10": float(df.sigma_min_plus_median.quantile(0.1)),
                    "lambda_max_median": float(df.lambda_max_median.median()), "condition_threshold": thr_c, "rank_tolerance": rank_tol,
                    "units": "Gram = B^T I^{-1} B of the RMS-normalized 12-column basis (dimensionless, gauge-invariant); window = 128 samples"})
        rank_rows.append(row)

    agg(win, {"stratum": "ALL", "link": "ALL", "split": "ALL"})
    for lf, df in win.groupby("stratum_leaf"):
        agg(df, {"stratum": lf, "link": "ALL", "split": "ALL"})
    for i, df in win.groupby("link"):
        agg(df, {"stratum": "leaf" if i in leaf_links else "non_leaf", "link": int(i), "split": "ALL"})
    for sp, df in win.groupby("split"):
        agg(df, {"stratum": "ALL", "link": "ALL", "split": sp})
        for lf, d2 in df.groupby("stratum_leaf"):
            agg(d2, {"stratum": lf, "link": "ALL", "split": sp})
    for part, ids in healthy_ids.items():
        agg(win[win.partition == part], {"stratum": "ALL", "link": "ALL", "split": f"partition:{part}"})
    write_csv(layout.results / "stage1rb_basis_rank_condition.csv", rank_rows)
    win.to_csv(layout.sub("r0_geometry") / "stage1rb_basis_gram_per_window_link.csv", index=False)

    # dependencies + stable null space + random frame invariance
    dep_json: dict[str, Any] = {"basis_columns": BASIS_NAMES, "column_scale_invariant_rms": {k: float(v) for k, v in zip(BASIS_NAMES, col_scale.cpu())}, "explicit_dependencies": {}, "stable_nullspace_per_link": {}, "mean_abs_normalized_correlation_per_link": {}, "random_frame_invariance": {}}
    tol_dep = float(ba["stable_redundancy_tolerance"])
    for k in DEPENDENCY_NAMES:
        arr = np.concatenate(dep_acc[k], 0)  # (N, n)
        per_link = {}
        for i in range(n):
            x = arr[:, i]
            x = x[np.isfinite(x)]
            per_link[f"link{i}"] = {"n": int(x.size), "max": float(x.max()) if x.size else None, "p99": float(np.quantile(x, 0.99)) if x.size else None, "fraction_below_tol": float((x < tol_dep).mean()) if x.size else None}
        dep_json["explicit_dependencies"][k] = per_link
    for i in range(n):
        G = torch.cat(per_link_G[i], 0)
        pe, pv = stable_nullspace(G, rank_tol)
        stable = int((pe > 0.99).sum())
        vecs = []
        for j in range(stable):
            v = pv[:, j].numpy()
            v = v / np.abs(v).max()
            vecs.append({BASIS_NAMES[c]: round(float(v[c]), 6) for c in range(ANALYTIC_BASIS_DIM) if abs(v[c]) > 1e-6})
        ev = np.concatenate(eval_acc[i], 0)
        dep_json["stable_nullspace_per_link"][f"link{i}"] = {"is_leaf": i in leaf_links, "is_root": bundle.base_chain.parent[i] < 0, "n_samples": int(G.shape[0]), "mean_null_projector_eigenvalues": [round(float(x), 6) for x in pe], "n_stable_null_directions(eig>0.99)": stable, "stable_null_directions_normalized": vecs,
                                                             "eigenvalue_quantiles_by_index": {f"lambda_{j}": _q(ev[:, j], (0.1, 0.5, 0.9)) for j in range(ANALYTIC_BASIS_DIM)}}
        dep_json["mean_abs_normalized_correlation_per_link"][f"link{i}"] = {f"{BASIS_NAMES[a]}|{BASIS_NAMES[b]}": round(float(corr_mean[i, a, b]), 4) for a in range(ANALYTIC_BASIS_DIM) for b in range(a + 1, ANALYTIC_BASIS_DIM) if corr_mean[i, a, b] > 0.9}
    # random legal SE(3) per-link reparameterizations: Gram, rank and dependency residuals unchanged
    rng = np.random.default_rng(260815)
    ep0 = bundle.episodes[bundle.train_ids[0]]
    ch0 = tool_chain(bundle.base_chain, ep0.tool_id)
    tq = lambda a: torch.as_tensor(np.asarray(a, dtype=np.float64), dtype=torch.float64, device=dev)
    sel = np.arange(0, 6000, 97)
    tc_c = TorchChain.from_chain(ch0, dtype=torch.float64, device=dev)
    tb_c = rnea_batch(tc_c, tq(ep0.signals["q_meas"][sel]), tq(ep0.signals["qd_meas"][sel]), tq(ep0.signals["qdd_est"][sel]))
    g_c = gram_audit(tc_c, tb_c, col_scale, rank_tol=rank_tol, keep_gram=True)
    trials = []
    for t_ in range(int(ba["random_frame_trials"])):
        new, _ = ch0.reparameterize(sample_link_frames(ch0, rng, rotation_angle_max_deg=float(cfg["frame_trials"]["rotation_angle_max_deg"]), translation_fraction_of_link_length=float(cfg["frame_trials"]["translation_fraction_of_link_length"])))
        tc_n = TorchChain.from_chain(new, dtype=torch.float64, device=dev)
        tb_n = rnea_batch(tc_n, tq(ep0.signals["q_meas"][sel]), tq(ep0.signals["qd_meas"][sel]), tq(ep0.signals["qdd_est"][sel]))
        g_n = gram_audit(tc_n, tb_n, col_scale, rank_tol=rank_tol, keep_gram=True)
        trials.append({"trial": t_, "gram_max_rel_dev": float((g_n.gram - g_c.gram).abs().max() / g_c.gram.abs().max()), "eig_max_rel_dev": float((g_n.evals - g_c.evals).abs().max() / g_c.evals.abs().max()), "rank_identical": bool(torch.equal(g_n.rank, g_c.rank)),
                       "dependency_residual_max_abs_dev": max(float(np.nanmax(np.abs((g_n.dependency_relative_residuals[k] - g_c.dependency_relative_residuals[k]).cpu().numpy()))) for k in DEPENDENCY_NAMES)})
    # span check for the reduced basis (drop F_body): rank of the 11-column Gram equals rank of the 12-column Gram
    Bc = covariant_basis(tc_c, tb_c) / col_scale
    keep_r = [k for k in range(ANALYTIC_BASIS_DIM) if BASIS_NAMES[k] != "F_body"]
    Iinv_c = torch.linalg.inv(tb_c.inertia)
    G11 = Bc[..., keep_r].transpose(-1, -2) @ Iinv_c @ Bc[..., keep_r]
    ev11 = torch.linalg.eigvalsh(0.5 * (G11 + G11.transpose(-1, -2)))
    rank11 = (ev11 > rank_tol * ev11[..., -1:].clamp_min(1e-300)).sum(-1)
    span_identical = bool(torch.equal(rank11, g_c.rank))
    dep_json["reduced_basis_span_check"] = {"dropped_column": "F_body", "n_samples": int(len(sel)), "rank12_equals_rank11_everywhere": span_identical, "rank12_min_max": [int(g_c.rank.min()), int(g_c.rank.max())], "rank11_min_max": [int(rank11.min()), int(rank11.max())]}
    tol_fi = float(ba["frame_invariance_tolerance"])
    dep_json["random_frame_invariance"] = {"n_trials": len(trials), "n_samples": int(len(sel)), "tolerance": tol_fi, "trials": trials, "pass": bool(all(t["gram_max_rel_dev"] < tol_fi and t["rank_identical"] for t in trials))}
    write_json(layout.results / "stage1rb_basis_dependencies.json", dep_json)
    _log(layout, lines, f"dependencies/nullspace/frame-invariance written; frame invariance pass={dep_json['random_frame_invariance']['pass']}")

    # ------------------------------------------------------------- A2: oracle torque capacity
    # per-joint weights from healthy TRAIN residual std (same normalization as the training loss)
    res_tr = np.concatenate([bundle.episodes[e].signals["tau_meas"] - bundle.episodes[e].signals["tau_nominal"] for e in bundle.train_ids], 0)
    sigma_j = torch.as_tensor(res_tr.std(0).clip(1e-3), dtype=torch.float64, device=dev)  # (n,)
    _log(layout, lines, f"healthy train residual std per joint (N m): {np.round(res_tr.std(0), 4).tolist()}")

    keep_reduced = [k for k in range(ANALYTIC_BASIS_DIM) if BASIS_NAMES[k] != "F_body"]

    def window_operators(ids: list[str]) -> dict[str, torch.Tensor]:
        Mb_l, Mf_l, Mr_l, e_l, meta = [], [], [], [], []
        for eid in ids:
            ep = bundle.episodes[eid]
            starts = np.arange(0, 6000 - W + 1, stride)
            t_all = np.concatenate([np.arange(s, s + W) for s in starts])
            tc, tb = _episode_typed(ep, bundle.base_chain, t_all, dev)
            Mb, Mf = oracle_operators(tc, tb, col_scale)
            Mr, _ = oracle_operators(tc, tb, col_scale, keep_columns=keep_reduced)
            nw = len(starts)
            e = torch.as_tensor((ep.signals["tau_meas"] - ep.signals["tau_nominal"])[t_all], dtype=torch.float64, device=dev)
            Mb_l.append(Mb.reshape(nw, W, n, -1) / sigma_j[None, None, :, None])
            Mf_l.append(Mf.reshape(nw, W, n, -1) / sigma_j[None, None, :, None])
            Mr_l.append(Mr.reshape(nw, W, n, -1) / sigma_j[None, None, :, None])
            e_l.append(e.reshape(nw, W, n) / sigma_j)
            meta += [(eid, ep.split, int(s)) for s in starts]
        return {"Mb": torch.cat(Mb_l), "Mf": torch.cat(Mf_l), "Mr": torch.cat(Mr_l), "e": torch.cat(e_l), "meta": meta}

    def rmse_rows(pred: torch.Tensor, e: torch.Tensor) -> dict[str, torch.Tensor]:
        # weighted (loss units) and physical (N m) errors; per window
        r_w = e - pred
        r_nm = r_w * sigma_j
        e_nm = e * sigma_j
        return {"rmse_w": (r_w**2).mean((1, 2)).sqrt(), "rmse_nm": (r_nm**2).mean((1, 2)).sqrt(), "pre_rmse_nm": (e_nm**2).mean((1, 2)).sqrt(), "rel": (r_nm**2).sum((1, 2)).sqrt() / (e_nm**2).sum((1, 2)).sqrt().clamp_min(1e-12)}

    lam1_grid = [float(x) for x in ba["lambda_tikhonov_grid"]]
    lam2_grid = [float(x) for x in ba["lambda_smoothness_grid"]]
    period = int(ba["oracle_heldout_period"])
    max_eps = args.max_oracle_episodes_per_split
    val_ids = bundle.val_ids[:max_eps] if max_eps else bundle.val_ids
    ops_val = window_operators(val_ids)
    nwv = ops_val["e"].shape[0]
    mask = torch.ones(nwv, W, dtype=torch.float64, device=dev)
    mask[:, period - 1::period] = 0.0
    held = mask == 0
    grid_rows = []
    curves: dict[str, list[dict]] = {"basis12": [], "free6": [], "basis11_no_Fbody": []}
    _log(layout, lines, f"oracle lambda selection on {nwv} healthy VAL windows ({len(val_ids)} episodes), grid {len(lam1_grid)}x{len(lam2_grid)}")
    grid_chunk = int(ba.get("oracle_grid_chunk_windows", 184))
    chunks = [slice(c0, min(c0 + grid_chunk, nwv)) for c0 in range(0, nwv, grid_chunk)]
    for name, key in (("basis12", "Mb"), ("free6", "Mf"), ("basis11_no_Fbody", "Mr")):
        M = ops_val[key]
        for l1 in lam1_grid:
            for l2 in lam2_grid:
                tt = time.time()
                acc = {"held_w": 0.0, "held_nm": 0.0, "n_held": 0, "in_w": 0.0, "in_nm": 0.0, "pre_nm": 0.0, "n_in": 0, "edf": 0.0}
                for sl in chunks:
                    e_c = ops_val["e"][sl]
                    o_m = solve_regularized(M[sl], e_c, l1, l2, row_mask=mask[sl], want_edf=False)
                    r_held = (e_c - o_m["pred"])[held[sl]].reshape(-1, n)
                    acc["held_w"] += float((r_held**2).sum())
                    acc["held_nm"] += float(((r_held * sigma_j) ** 2).sum())
                    acc["n_held"] += int(r_held.numel())
                    o_f = solve_regularized(M[sl], e_c, l1, l2, want_edf=True)
                    rr = rmse_rows(o_f["pred"], e_c)
                    nw_c = int(e_c.shape[0])
                    acc["in_w"] += float((rr["rmse_w"] ** 2).sum()) * W * n
                    acc["in_nm"] += float((rr["rmse_nm"] ** 2).sum()) * W * n
                    acc["pre_nm"] += float((rr["pre_rmse_nm"] ** 2).sum()) * W * n
                    acc["n_in"] += nw_c * W * n
                    acc["edf"] += float(o_f["edf"].sum())
                    del o_m, o_f
                row = base(model=f"oracle_{name}", split="VAL", **{"lambda_tikhonov": l1, "lambda_smoothness": l2, "heldout_rmse_weighted": (acc["held_w"] / max(acc["n_held"], 1)) ** 0.5, "heldout_rmse_nm": (acc["held_nm"] / max(acc["n_held"], 1)) ** 0.5, "insample_rmse_weighted": (acc["in_w"] / acc["n_in"]) ** 0.5, "insample_rmse_nm": (acc["in_nm"] / acc["n_in"]) ** 0.5, "pre_rmse_nm": (acc["pre_nm"] / acc["n_in"]) ** 0.5, "edf_mean_per_window": acc["edf"] / nwv, "edf_per_observation": acc["edf"] / nwv / (W * n), "n_windows": int(nwv), "phase": "lambda_grid", "solve_seconds": time.time() - tt})
                grid_rows.append(row)
                curves[name].append(row)
                _log(layout, lines, f"grid {name} l1={l1} l2={l2}: heldout {row['heldout_rmse_nm']:.4f} insample {row['insample_rmse_nm']:.4f} edf/obs {row['edf_per_observation']:.3f} ({row['solve_seconds']:.0f}s)")
        torch.cuda.empty_cache() if dev.startswith("cuda") else None
    chosen = {}
    heldout_best = {}
    for name in ("basis12", "free6", "basis11_no_Fbody"):
        rows_ = curves[name]
        best = min(rows_, key=lambda r: (r["heldout_rmse_weighted"], -r["lambda_tikhonov"], -r["lambda_smoothness"]))
        chosen[name] = (best["lambda_tikhonov"], best["lambda_smoothness"])
        heldout_best[name] = {"heldout_rmse_nm": best["heldout_rmse_nm"], "insample_rmse_nm": best["insample_rmse_nm"], "edf_per_observation": best["edf_per_observation"]}
        _log(layout, lines, f"selected {name}: lambda1={best['lambda_tikhonov']} lambda2={best['lambda_smoothness']} heldout_rmse={best['heldout_rmse_nm']:.4f} Nm insample={best['insample_rmse_nm']:.4f} Nm edf/obs={best['edf_per_observation']:.3f}")
    # matched effective-DoF partners (secondary, capacity-fair): the grid point of the *other* oracle whose
    # VAL edf/observation is closest to the selected basis12 point (and vice versa)
    target_edf = heldout_best["basis12"]["edf_per_observation"]
    matched = {}
    for name in ("free6", "basis11_no_Fbody"):
        m = min(curves[name], key=lambda r: abs(r["edf_per_observation"] - target_edf))
        matched[name] = (m["lambda_tikhonov"], m["lambda_smoothness"])
        _log(layout, lines, f"matched-edf partner for {name}: lambda=({m['lambda_tikhonov']}, {m['lambda_smoothness']}) edf/obs={m['edf_per_observation']:.3f} (target {target_edf:.3f})")
    m = min(curves["basis12"], key=lambda r: abs(r["edf_per_observation"] - heldout_best["free6"]["edf_per_observation"]))
    matched["basis12_at_free_edf"] = (m["lambda_tikhonov"], m["lambda_smoothness"])
    del ops_val
    torch.cuda.empty_cache() if dev.startswith("cuda") else None

    # final evaluation at the selected lambdas on train / val / test (S0 + OOD), reduced basis, zero-regularization bound
    keep_reduced = [k for k in range(ANALYTIC_BASIS_DIM) if BASIS_NAMES[k] != "F_body"]
    final_rows = []
    per_window_rows = []
    zero_rank_stats = {"basis12": [99, -1], "free6": [99, -1]}
    chunk_eps = 4
    for part, ids in healthy_ids.items():
        ids = ids[:max_eps] if max_eps else ids
        for c0 in range(0, len(ids), chunk_eps):
            cids = ids[c0:c0 + chunk_eps]
            ops = window_operators(cids)
            outs = {}
            plan = [
                ("basis12", "Mb", chosen["basis12"]), ("free6", "Mf", chosen["free6"]), ("basis11_no_Fbody", "Mr", chosen["basis11_no_Fbody"]),
                ("basis11_no_Fbody_at_basis_lambda", "Mr", chosen["basis12"]), ("basis11_no_Fbody_matched_edf", "Mr", matched["basis11_no_Fbody"]),
                ("free6_at_basis_lambda", "Mf", chosen["basis12"]), ("free6_matched_edf", "Mf", matched["free6"]),
                ("basis12_at_free_lambda", "Mb", chosen["free6"]), ("basis12_at_free_edf", "Mb", matched["basis12_at_free_edf"]),
            ]
            for name, key, (l1, l2) in plan:
                o = solve_regularized(ops[key], ops["e"], l1, l2, want_edf=True)
                outs[name] = {**rmse_rows(o["pred"], ops["e"]), "edf": o["edf"], "lam": (l1, l2)}
            # zero regularization (min-norm per time step): upper bound only
            for name, M in (("basis12", ops["Mb"]), ("free6", ops["Mf"])):
                mn = solve_min_norm(M, ops["e"])
                rr = rmse_rows(mn["pred"], ops["e"])
                outs[f"{name}_zero_reg"] = {**rr, "edf": torch.full((M.shape[0],), float("nan"), device=dev), "lam": (0.0, 0.0)}
                zero_rank_stats[name][0] = min(zero_rank_stats[name][0], int(mn["rank"].min()))
                zero_rank_stats[name][1] = max(zero_rank_stats[name][1], int(mn["rank"].max()))
            for w_i, (eid, split, start) in enumerate(ops["meta"]):
                rowp = {"partition": part, "split": split, "episode_id": eid, "start": start, "in_eval_region": bool(start >= bundle.eval_min_start)}
                for name, o in outs.items():
                    rowp[f"{name}_rmse_nm"] = float(o["rmse_nm"][w_i])
                    rowp[f"{name}_rel_residual"] = float(o["rel"][w_i])
                    rowp[f"{name}_edf"] = float(o["edf"][w_i])
                rowp["pre_rmse_nm"] = float(outs["basis12"]["pre_rmse_nm"][w_i])
                per_window_rows.append(rowp)
            del ops, outs
            torch.cuda.empty_cache() if dev.startswith("cuda") else None
        _log(layout, lines, f"oracle final fits done for partition {part} ({time.time() - t0:.0f}s)")
    pw = pd.DataFrame(per_window_rows)
    pw.to_csv(layout.sub("r0_geometry") / "stage1rb_oracle_per_window.csv", index=False)
    oracle_names = [c[:-8] for c in pw.columns if c.endswith("_rmse_nm") and c != "pre_rmse_nm"]

    lam_of = {"basis12": chosen["basis12"], "free6": chosen["free6"], "basis11_no_Fbody": chosen["basis11_no_Fbody"], "basis11_no_Fbody_at_basis_lambda": chosen["basis12"], "basis11_no_Fbody_matched_edf": matched["basis11_no_Fbody"], "free6_at_basis_lambda": chosen["basis12"], "free6_matched_edf": matched["free6"], "basis12_at_free_lambda": chosen["free6"], "basis12_at_free_edf": matched["basis12_at_free_edf"]}

    def orow(df: pd.DataFrame, name: str, tag: dict) -> dict:
        lam = lam_of.get(name, (0.0, 0.0))
        return base(model=f"oracle_{name}", **tag, **{"lambda_tikhonov": lam[0], "lambda_smoothness": lam[1], "n_windows": int(len(df)), "n_episodes": int(df.episode_id.nunique()),
                    "rmse_nm": float(np.sqrt((df[f"{name}_rmse_nm"] ** 2).mean())), "pre_rmse_nm": float(np.sqrt((df["pre_rmse_nm"] ** 2).mean())), "rmse_ratio_post_over_pre": float(np.sqrt((df[f"{name}_rmse_nm"] ** 2).mean()) / np.sqrt((df["pre_rmse_nm"] ** 2).mean())),
                    "rel_residual_median": float(df[f"{name}_rel_residual"].median()), "rel_residual_p90": float(df[f"{name}_rel_residual"].quantile(0.9)), "edf_mean_per_window": float(df[f"{name}_edf"].mean()), "edf_per_observation": float(df[f"{name}_edf"].mean() / (W * n)), "phase": "final_fit", "units": "N m; rel_residual = |e - pred|_2 / |e|_2 per window; edf = tr(H)"})

    for name in oracle_names:
        for part in ("train", "val", "test"):
            d = pw[pw.partition == part]
            final_rows.append(orow(d, name, {"split": part.upper()}))
            if part == "test":
                final_rows.append(orow(d[d.split == "S0"], name, {"split": "TEST_S0"}))
                final_rows.append(orow(d[d.split != "S0"], name, {"split": "TEST_OOD"}))
                for sp, d2 in d.groupby("split"):
                    final_rows.append(orow(d2, name, {"split": f"TEST_{sp}"}))
                final_rows.append(orow(d[d.in_eval_region], name, {"split": "TEST_eval_region"}))
    write_csv(layout.results / "stage1rb_oracle_torque_capacity.csv", grid_rows + final_rows)

    # ------------------------------------------------------------- Oracle B: analytic mismatch wrench projection
    from certo_fdi.data.franka_generator import apply_truth_inertials
    from certo_fdi.dynamics.mujoco_backend import MujocoPlant

    truth = dm["truth_parameters_hidden_from_models"]
    plant = MujocoPlant(cfg["paths"]["mjcf_path"])
    nominal_chain = reference_chain(cfg["paths"]["mjcf_path"])
    apply_truth_inertials(plant, truth)
    truth_chain = plant.chain
    dI = torch.as_tensor(truth_chain.spatial_inertias() - nominal_chain.spatial_inertias(), dtype=torch.float64, device=dev)  # (n,6,6), tool cancels
    proj_rows_raw = []
    tau_expl = []
    for part, ids in healthy_ids.items():
        for eid in ids:
            ep = bundle.episodes[eid]
            for kin in ("measured", "truth"):
                tc, tb = _episode_typed(ep, bundle.base_chain, t_idx, dev, truth=(kin == "truth"))
                dF = mismatch_wrench(dI, tb)
                B = covariant_basis(tc, tb) / col_scale
                I_inv = torch.linalg.inv(tb.inertia)
                rel, _ = projection_residual(dF, B, I_inv)
                # magnitude of the mismatch wrench (I^{-1} metric) and its torque footprint through the chain
                P = chain_projection(tc, tb.X, tb.S)
                tau_d = (P @ dF.reshape(dF.shape[0], -1, 1))[..., 0]  # (N,n)
                e_t = torch.as_tensor((ep.signals["tau_meas"] - ep.signals["tau_nominal"])[t_idx], dtype=torch.float64, device=dev)
                for i in range(n):
                    proj_rows_raw.append({"partition": part, "split": ep.split, "episode_id": eid, "kinematics": kin, "link": i, "rel_median": float(rel[:, i].median()), "rel_p90": float(rel[:, i].quantile(0.9)), "rel_max": float(rel[:, i].max()), "dF_norm_Iinv_rms": float(torch.einsum("bi,bij,bj->b", dF[:, i], I_inv[:, i], dF[:, i]).clamp_min(0).mean().sqrt())})
                if kin == "measured":
                    tau_expl.append({"partition": part, "split": ep.split, "episode_id": eid, "rms_residual_nm": float((e_t**2).mean().sqrt()), "rms_inertial_mismatch_torque_nm": float((tau_d**2).mean().sqrt()), "rms_residual_minus_inertial_nm": float(((e_t - tau_d) ** 2).mean().sqrt()), "residual_explained_fraction": float(1.0 - ((e_t - tau_d) ** 2).sum() / (e_t**2).sum())})
    pr = pd.DataFrame(proj_rows_raw)
    te = pd.DataFrame(tau_expl)
    wp_rows = []
    thr_p = float(ba["mismatch_projection_threshold"])
    for kin, d in pr.groupby("kinematics"):
        wp_rows.append(base(model="oracle_B_inertial_mismatch_projection", split="ALL", **{"kinematics": kin, "link": "ALL", "target": "dF_i = dI_i A_i + ad*_V dI_i V_i (truth-vs-nominal inertial mismatch, tool cancels)", "rel_residual_median": float(d.rel_median.median()), "rel_residual_p90": float(d.rel_p90.median()), "rel_residual_max": float(d.rel_max.max()), "n_episodes": int(d.episode_id.nunique()), "threshold": thr_p, "exceeds_threshold": bool(d.rel_median.median() > thr_p), "units": "relative residual in the I^{-1} metric"}))
        for i, d2 in d.groupby("link"):
            wp_rows.append(base(model="oracle_B_inertial_mismatch_projection", split="ALL", **{"kinematics": kin, "link": int(i), "target": "inertial mismatch wrench", "rel_residual_median": float(d2.rel_median.median()), "rel_residual_p90": float(d2.rel_p90.median()), "rel_residual_max": float(d2.rel_max.max()), "dF_norm_Iinv_rms_median": float(d2.dF_norm_Iinv_rms.median()), "n_episodes": int(d2.episode_id.nunique()), "threshold": thr_p, "exceeds_threshold": bool(d2.rel_median.median() > thr_p)}))
        for sp, d2 in d.groupby("split"):
            wp_rows.append(base(model="oracle_B_inertial_mismatch_projection", split=sp, **{"kinematics": kin, "link": "ALL", "target": "inertial mismatch wrench", "rel_residual_median": float(d2.rel_median.median()), "rel_residual_p90": float(d2.rel_p90.median()), "n_episodes": int(d2.episode_id.nunique()), "threshold": thr_p, "exceeds_threshold": bool(d2.rel_median.median() > thr_p)}))
    wp_rows.append(base(model="oracle_B_friction_mismatch_projection", split="ALL", status="NOT_AVAILABLE", **{"kinematics": "n/a", "link": "ALL", "target": "joint-space friction mismatch (Stribeck absent from nominal, +-15% viscous/Coulomb, temperature) is a joint torque, not a link wrench: any wrench f with S_i^T f = d tau_i represents it, so a wrench projection residual is not defined", "rel_residual_median": float("nan"), "n_episodes": 0, "threshold": thr_p, "exceeds_threshold": False}))
    for part, d in te.groupby("partition"):
        wp_rows.append(base(model="healthy_residual_decomposition", split=part.upper(), **{"kinematics": "measured", "link": "ALL", "target": "e_tau vs chain-projected inertial mismatch torque S^T P(dF)", "rms_residual_nm": float(np.sqrt((d.rms_residual_nm**2).mean())), "rms_inertial_mismatch_torque_nm": float(np.sqrt((d.rms_inertial_mismatch_torque_nm**2).mean())), "rms_residual_minus_inertial_nm": float(np.sqrt((d.rms_residual_minus_inertial_nm**2).mean())), "residual_explained_fraction_median": float(d.residual_explained_fraction.median()), "n_episodes": int(len(d)), "units": "N m"}))
    write_csv(layout.results / "stage1rb_oracle_wrench_projection.csv", wp_rows)
    pr.to_csv(layout.sub("r0_geometry") / "stage1rb_oracle_B_per_episode_link.csv", index=False)
    _log(layout, lines, f"oracle B written ({time.time() - t0:.0f}s)")

    # ------------------------------------------------------------- retirement rules (frozen 05 §5)
    fr = {r["model"]: r for r in final_rows if r["split"] == "TEST"}
    fr_s0 = {r["model"]: r for r in final_rows if r["split"] == "TEST_S0"}
    test_basis, test_free = fr["oracle_basis12"]["rmse_nm"], fr["oracle_free6"]["rmse_nm"]
    rule1 = {"basis_test_rmse_nm": test_basis, "free_test_rmse_nm": test_free, "ratio": test_basis / test_free, "threshold_ratio": 1.0 + float(ba["oracle_rmse_relative_margin"]), "basis_test_S0_rmse_nm": fr_s0["oracle_basis12"]["rmse_nm"], "free_test_S0_rmse_nm": fr_s0["oracle_free6"]["rmse_nm"],
             "basis_edf_per_obs": fr["oracle_basis12"]["edf_per_observation"], "free_edf_per_obs": fr["oracle_free6"]["edf_per_observation"],
             "fires": bool(test_basis > (1.0 + float(ba["oracle_rmse_relative_margin"])) * test_free),
             "secondary_matched_edf": {"free_test_rmse_nm_at_basis_edf": fr["oracle_free6_matched_edf"]["rmse_nm"], "free_edf_per_obs_matched": fr["oracle_free6_matched_edf"]["edf_per_observation"], "ratio_basis_over_free_matched_edf": test_basis / fr["oracle_free6_matched_edf"]["rmse_nm"], "basis_test_rmse_nm_at_free_edf": fr["oracle_basis12_at_free_edf"]["rmse_nm"], "basis_edf_per_obs_at_free_edf": fr["oracle_basis12_at_free_edf"]["edf_per_observation"], "ratio_basis_at_free_edf_over_free": fr["oracle_basis12_at_free_edf"]["rmse_nm"] / test_free},
             "secondary_matched_lambda": {"free_test_rmse_nm_at_basis_lambda": fr["oracle_free6_at_basis_lambda"]["rmse_nm"], "basis_test_rmse_nm_at_free_lambda": fr["oracle_basis12_at_free_lambda"]["rmse_nm"]},
             "secondary_heldout_prediction_val": {k: v for k, v in heldout_best.items()},
             "reading": "the literal rule compares each oracle at its own validation-selected regularization; the secondary entries compare at matched effective degrees of freedom / matched lambda, which separates span capacity from the amount of fitting freedom"}
    pwt = pw[pw.partition == "test"]
    frac2 = float((pwt["basis12_rel_residual"] > (1.0 + float(ba["window_relative_residual_margin"])) * pwt["free6_rel_residual"]).mean())
    frac2_all = float((pw["basis12_rel_residual"] > (1.0 + float(ba["window_relative_residual_margin"])) * pw["free6_rel_residual"]).mean())
    frac2_medf = float((pwt["basis12_rel_residual"] > (1.0 + float(ba["window_relative_residual_margin"])) * pwt["free6_matched_edf_rel_residual"]).mean())
    frac2_rev = float((pwt["free6_rel_residual"] > (1.0 + float(ba["window_relative_residual_margin"])) * pwt["basis12_at_free_edf_rel_residual"]).mean())
    rule2 = {"fraction_test_windows_basis_rel_residual_gt_1p2_free": frac2, "fraction_all_healthy_windows": frac2_all, "threshold_fraction": float(ba["window_relative_residual_fraction"]), "fires": bool(frac2 > float(ba["window_relative_residual_fraction"])),
             "secondary_matched_edf": {"fraction_test_windows_basis_gt_1p2_free_at_matched_edf": frac2_medf, "fraction_test_windows_free_gt_1p2_basis_at_free_edf": frac2_rev}}
    all_row = next(r for r in rank_rows if r["stratum"] == "ALL" and r["link"] == "ALL" and r["split"] == "ALL")
    rule3 = {"fraction_window_links_cond_full_gt_1e8": all_row["frac_windows_cond_full_gt_threshold"], "fraction_window_links_cond_plus_gt_1e8": all_row["frac_windows_cond_plus_gt_threshold"], "cond_full_median": all_row["cond_full_median"], "cond_plus_median": all_row["cond_plus_median"], "threshold_fraction": float(ba["condition_window_fraction"]), "note": "cond_full uses the whole 12-eigenvalue spectrum (exactly singular Gram -> numerically ~1e15+); cond_plus uses the numerically nonzero spectrum", "fires": bool(all_row["frac_windows_cond_full_gt_threshold"] > float(ba["condition_window_fraction"])), "fires_on_nonzero_spectrum_only": bool(all_row["frac_windows_cond_plus_gt_threshold"] > float(ba["condition_window_fraction"]))}
    dep0 = dep_json["explicit_dependencies"][DEPENDENCY_NAMES[0]]
    stable_frac = min(v["fraction_below_tol"] for v in dep0.values() if v["fraction_below_tol"] is not None)
    red_ratio_own = fr["oracle_basis11_no_Fbody"]["rmse_nm"] / test_basis
    red_ratio_lam = fr["oracle_basis11_no_Fbody_at_basis_lambda"]["rmse_nm"] / test_basis
    red_ratio_edf = fr["oracle_basis11_no_Fbody_matched_edf"]["rmse_nm"] / test_basis
    tol4 = float(ba["reduced_basis_no_loss_tolerance"])
    rule4 = {"exact_dependency": DEPENDENCY_NAMES[0], "min_fraction_of_samples_with_relative_residual_below_tol": stable_frac, "tol": tol_dep, "full_basis_test_rmse_nm": test_basis, "full_basis_edf_per_obs": fr["oracle_basis12"]["edf_per_observation"],
             "reduced_basis_test_rmse_nm_own_lambda": fr["oracle_basis11_no_Fbody"]["rmse_nm"], "reduced_edf_per_obs_own_lambda": fr["oracle_basis11_no_Fbody"]["edf_per_observation"], "reduced_over_full_ratio_own_lambda": red_ratio_own,
             "reduced_basis_test_rmse_nm_same_lambda": fr["oracle_basis11_no_Fbody_at_basis_lambda"]["rmse_nm"], "reduced_over_full_ratio_same_lambda": red_ratio_lam,
             "reduced_basis_test_rmse_nm_matched_edf": fr["oracle_basis11_no_Fbody_matched_edf"]["rmse_nm"], "reduced_edf_per_obs_matched": fr["oracle_basis11_no_Fbody_matched_edf"]["edf_per_observation"], "reduced_over_full_ratio_matched_edf": red_ratio_edf,
             "span_identical_rank_check": dep_json["reduced_basis_span_check"],
             "no_loss_tolerance": tol4, "criterion": "stable exact dependency (>=99% samples below tol) AND reduced basis at its own validation-selected lambda OR at matched edf loses < tol relative test RMSE",
             "fires": bool(stable_frac >= float(ba["stable_redundancy_min_fraction"]) and (red_ratio_own <= 1.0 + tol4 or red_ratio_edf <= 1.0 + tol4))}
    prm = pr[pr.kinematics == "measured"]
    rule5 = {"median_relative_projection_residual_measured_kinematics": float(prm.rel_median.median()), "median_relative_projection_residual_truth_kinematics": float(pr[pr.kinematics == "truth"].rel_median.median()), "threshold": thr_p, "fires": bool(prm.rel_median.median() > thr_p)}
    rules = {"rule1_oracle_test_rmse_gap": rule1, "rule2_window_relative_residual": rule2, "rule3_gram_condition": rule3, "rule4_stable_exact_redundancy": rule4, "rule5_mismatch_projection_residual": rule5}
    fired = [k for k, v in rules.items() if v["fires"]]
    verdict = "RETIRED_BASIS_V1" if fired else "BASIS_CAPACITY_NOT_REJECTED"
    # capacity interpretation (not a rule): oracle ceilings vs the pilot's achieved healthy fits
    interp = {"basis_oracle_test_rmse_ratio_post_over_pre": fr["oracle_basis12"]["rmse_ratio_post_over_pre"], "free_oracle_test_rmse_ratio_post_over_pre": fr["oracle_free6"]["rmse_ratio_post_over_pre"], "pilot_ligra_v1_S0_rmse_ratio_seed_mean": 0.599, "pilot_chain_gnn_aug_S0_rmse_ratio_seed_mean": 0.391, "pilot_ligra_free_output_S0_rmse_ratio_seed_mean": 0.316,
              "basis_oracle_test_S0_rmse_ratio": fr_s0["oracle_basis12"]["rmse_ratio_post_over_pre"], "free_oracle_test_S0_rmse_ratio": fr_s0["oracle_free6"]["rmse_ratio_post_over_pre"], "zero_regularization_note": "zero-regularization min-norm fits are exact when rank(M_t)=7 (7 joints) and are reported as an upper bound only", "zero_reg_rank_of_M_t_min_max": {nm: {"rank_min": v[0], "rank_max": v[1], "n_joints": n} for nm, v in zero_rank_stats.items()}, "zero_reg_test_rmse_nm": {nm: fr[f"oracle_{nm}_zero_reg"]["rmse_nm"] for nm in ("basis12", "free6")}}
    evidence = {"run_id": layout.run_id, "git_sha": git_sha(repo_root), "config_sha256": cfg_sha, "dataset_manifest_sha256": manifest_sha, "timestamp_utc": utc_now(), "verdict": verdict, "rules_fired": fired, "rules": rules, "selected_lambdas": chosen, "interpretation": interp, "n_healthy_episodes": {k: len(v) for k, v in healthy_ids.items()}, "oracle_windows": {"window_samples": W, "stride": stride, "heldout_period": period, "n_windows_by_partition": {p: int((pw.partition == p).sum()) for p in ("train", "val", "test")}}, "random_frame_invariance_pass": dep_json["random_frame_invariance"]["pass"]}
    write_json(layout.results / "stage1rb_basis_audit_evidence.json", evidence)

    # memo
    md = [f"# Stage 1R-B Phase A — LiGRA-v1 12-column basis capacity audit", "", f"- run_id: `{layout.run_id}`  git: `{git_sha(repo_root)}`  config sha256: `{cfg_sha}`", f"- dataset: frozen Stage 1R pilot ({sum(len(v) for v in healthy_ids.values())} healthy episodes used; post-GMO manifest sha `{manifest_sha}`)", f"- generated {utc_now()}; no network trained; fault episodes never read", "", f"## Verdict: **{verdict}**", "", f"Rules fired (05 §5): {', '.join(fired) if fired else 'none'}", "",
          "## A1 gauge-invariant Gram (RMS-normalized columns, float64)", "", "| stratum | link | split | n(window,link) | rank min/mode/max | nullity | cond_full median | frac cond_full>1e8 | cond_plus median / p90 / p99 | frac cond_plus>1e8 | sigma_min+ median |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rank_rows:
        if r["split"] in ("ALL",) or r["link"] == "ALL":
            md.append(f"| {r['stratum']} | {r['link']} | {r['split']} | {r['n_window_links']} | {r['rank_min']}/{r['rank_mode']}/{r['rank_max']} | {r['nullity_min']}–{r['nullity_max']} | {r['cond_full_median']:.2e} | {r['frac_windows_cond_full_gt_threshold']:.3f} | {r['cond_plus_median']:.2e} / {r['cond_plus_p90']:.2e} / {r['cond_plus_p99']:.2e} | {r['frac_windows_cond_plus_gt_threshold']:.3f} | {r['sigma_min_plus_median']:.2e} |")
    md += ["", "### Exact algebraic dependencies (relative residual in the I^{-1} metric, all healthy samples)", "", "| dependency | max over links of p99 | min over links of fraction < 1e-8 |", "|---|---|---|"]
    for k, per in dep_json["explicit_dependencies"].items():
        vals = [v for v in per.values() if v["p99"] is not None]
        md.append(f"| {k} | {max(v['p99'] for v in vals):.2e} | {min(v['fraction_below_tol'] for v in vals):.4f} |")
    md += ["", "Stable null directions per link (eigenvalues of the mean null-space projector > 0.99):", ""]
    for k, v in dep_json["stable_nullspace_per_link"].items():
        md.append(f"- {k} (leaf={v['is_leaf']}, root={v['is_root']}): {v['n_stable_null_directions(eig>0.99)']} stable null direction(s): {json.dumps(v['stable_null_directions_normalized'])}")
    fi_ = dep_json["random_frame_invariance"]
    md += ["", f"Random legal per-link SE(3) reparameterizations ({fi_['n_trials']} trials): max relative Gram deviation {max(t['gram_max_rel_dev'] for t in fi_['trials']):.2e}, ranks identical in all trials: {all(t['rank_identical'] for t in fi_['trials'])} → **{'PASS' if fi_['pass'] else 'FAIL'}**", "",
           "## A2 oracle torque-correction ceilings (healthy windows, 128 samples, exact chain projection)", "", f"Regularization selected on healthy VAL windows by held-out-timestep RMSE (every {period}th sample held out): basis12 λ=(Tikhonov {chosen['basis12'][0]}, smooth {chosen['basis12'][1]}); free6 λ=({chosen['free6'][0]}, {chosen['free6'][1]}).", "",
           "| oracle | split | n windows | RMSE (N m) | pre RMSE (N m) | ratio post/pre | rel. residual median | edf / observation |", "|---|---|---|---|---|---|---|---|"]
    for r in final_rows:
        if r["split"] in ("TRAIN", "VAL", "TEST", "TEST_S0", "TEST_OOD"):
            md.append(f"| {r['model']} | {r['split']} | {r['n_windows']} | {r['rmse_nm']:.4f} | {r['pre_rmse_nm']:.4f} | {r['rmse_ratio_post_over_pre']:.3f} | {r['rel_residual_median']:.3f} | {r['edf_per_observation']:.3f} |")
    md += ["", "Validation grid (held-out RMSE, in-sample RMSE, edf per observation) — full table in stage1rb_oracle_torque_capacity.csv (phase=lambda_grid).", "", "| oracle | λ1 | λ2 | held-out RMSE (N m) | in-sample RMSE (N m) | edf/obs |", "|---|---|---|---|---|---|"]
    for name in ("basis12", "free6"):
        for r in sorted(curves[name], key=lambda r: r["heldout_rmse_nm"])[:6]:
            md.append(f"| {name} | {r['lambda_tikhonov']} | {r['lambda_smoothness']} | {r['heldout_rmse_nm']:.4f} | {r['insample_rmse_nm']:.4f} | {r['edf_per_observation']:.3f} |")
    md += ["", "## Oracle B — analytic inertial mismatch wrench projection", "", "| kinematics | link | rel. residual median | p90 | max | exceeds 0.10 |", "|---|---|---|---|---|---|"]
    for r in wp_rows:
        if r["model"] == "oracle_B_inertial_mismatch_projection" and r["split"] == "ALL":
            md.append(f"| {r['kinematics']} | {r['link']} | {r['rel_residual_median']:.4f} | {r['rel_residual_p90']:.4f} | {r.get('rel_residual_max', float('nan')):.4f} | {r['exceeds_threshold']} |")
    for r in wp_rows:
        if r["model"] == "healthy_residual_decomposition":
            md.append(f"\n- healthy residual decomposition ({r['split']}): RMS e_tau {r['rms_residual_nm']:.4f} N m; chain-projected inertial mismatch torque RMS {r['rms_inertial_mismatch_torque_nm']:.4f} N m; RMS(e_tau − inertial) {r['rms_residual_minus_inertial_nm']:.4f} N m; explained fraction (median over episodes) {r['residual_explained_fraction_median']:.3f}")
    md += ["- friction/joint-space mismatch as a link wrench: **NOT_AVAILABLE** (not a physically defined wrench target; see CSV row).", "", "## Rules", "", "```json", json.dumps(rules, indent=2), "```", "", "## Interpretation (evidence, not a new claim)", "", "```json", json.dumps(interp, indent=2), "```", "", "The verdict retires (or does not retire) only the hand-built 12-column basis of LiGRA-v1. It says nothing about typed equivariance in general; LiGRA-v1 is not retrained regardless of the outcome (master prompt §6 A3)."]
    (layout.results / "stage1rb_basis_audit_memo.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    capture_environment(layout, repo_root, "stage1rb_basis_audit_end")
    _log(layout, lines, f"Phase A DONE verdict={verdict} fired={fired} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
