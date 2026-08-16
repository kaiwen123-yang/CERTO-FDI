"""Stage 2A Phase 2: reproduce the frozen ``chain_gnn_aug`` baseline (+ diagnostics, learning curve).

The Stage 1R-B best configuration is *reused*, not re-searched: ``chain_gnn_aug`` at
``lr = 2e-3`` with ``reduce_on_plateau``, ``rnea_gru`` at ``lr = 2e-3`` with ``onecycle``.
This phase trains them from scratch in this run, evaluates them through the frozen Stage 1R-B
evaluation path, and compares the primary metrics against the frozen reference. A relative
deviation above 2 % on any of them stops the stage (contract §6.4).

It also produces the §6.6 data-volume diagnostic: a learning curve over 10 / 20 / 40 healthy
train episodes for ``rnea_gru`` and ``chain_gnn_aug``. The frozen pilot has only 40 healthy
train episodes, so the requested 80-episode point is recorded as NOT AVAILABLE, never
extrapolated.

Every job writes a resumable JSON under ``<run>/p2_baseline/runs/``.
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from certo_fdi.experiments.common import seed_everything, write_json
from certo_fdi.experiments.decision_stage2a import reproduction_gate
from certo_fdi.experiments.evaluation_chain_baseline import evaluate_run_stage1rb
from certo_fdi.experiments.stage2a_common import Stage, common_parser, ensure_model_cfg, train_cfg
from certo_fdi.models.chain_gnn import build_model

RESULT_TABLES = ("healthy_prediction", "detection", "ood_healthy", "localization", "localization_detail", "frame_invariance", "latency", "heads")
PRIMARY_VARIANT = "residual_only"
CF_METHOD = "counterfactual_link_masking"


def _val_healthy_rmse(model, bundle, device: str) -> float:
    import torch

    from certo_fdi.data.windows import WindowSet
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import extract_features

    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=device)
    ws = WindowSet(bundle.subset(bundle.val_ids), bundle.window, bundle.stride_train, device, min_start=bundle.eval_min_start)
    return float(np.sqrt(extract_features(model, ws, tc, device).resid_ms.mean()))


def run_job(st: Stage, name: str, frac: float, seed: int, lr: float, scheduler: str, tag: str, out_json: Path, *, full: bool, acceleration_diagnostic: bool) -> dict | None:
    import torch

    from certo_fdi.experiments.pipeline import load_checkpoint, train_model, training_subset

    cfg = ensure_model_cfg(st.cfg)
    bundle = st.bundle
    tcfg = train_cfg(cfg)
    ckpt_dir = st.layout.sub("checkpoints")
    t0 = time.time()
    try:
        seed_everything(seed)
        train_ids = training_subset(bundle, frac, seed)
        ckpt_path = ckpt_dir / f"{name}{('_' + tag) if tag else ''}_seed{seed}_frac{len(train_ids)}ep.pt"
        if ckpt_path.exists() and out_json.exists():
            info = load_checkpoint(name, ckpt_path, bundle, cfg, st.device)
            info.update({"lr": lr, "scheduler": scheduler, "tag": tag})
            st.log(f"loaded checkpoint {ckpt_path.name}")
        else:
            info = train_model(name, seed, train_ids, bundle, cfg, ckpt_dir, st.device, epochs=tcfg["epochs"], batch_size=tcfg["batch_size"], lr=lr,
                               patience=tcfg["patience"], min_epochs=tcfg["min_epochs"], log=st.lines, scheduler=scheduler,
                               weight_decay=tcfg["weight_decay"], grad_clip=tcfg["grad_clip"], tag=tag)
            st.log(f"trained {name} tag={tag} n_train_ep={len(train_ids)} seed={seed}: params={info['n_params']} epochs={info['epochs_run']} best_val_loss={info['best_val_loss']:.4f} ({info['train_seconds']:.0f}s)")
        res: dict[str, Any] = {"train_info": [{k: v for k, v in info.items() if k != "model"}]}
        res["train_info"][0].update({"training_fraction": frac, "seed": seed, "n_train_episodes": len(train_ids), "val_healthy_rmse_nm": _val_healthy_rmse(info["model"], bundle, st.device)})
        brow = {
            "run_id": st.layout.run_id, "git_sha": res["train_info"][0].get("git_sha", ""), "config_sha256": st.cfg_sha,
            "dataset_sha256_or_manifest_sha": st.manifest_sha, "model": info["name"], "seed": seed, "split": "",
            "checkpoint_sha256": info["checkpoint_sha256"], "status": "OK", "provisional": False, "strict_claim": "",
            "training_fraction": frac, "config_tag": tag, "lr": lr, "scheduler": scheduler,
        }
        ev = evaluate_run_stage1rb(info["model"], info, train_ids, bundle, cfg, brow, st.device, full=full, frame_manifest=None,
                                   quantile=float(cfg["anomaly"]["threshold_quantile"]), log=st.lines, acceleration_diagnostic=acceleration_diagnostic)
        res.update(ev)
        write_json(out_json, res)
        st.log(f"job done {out_json.name} ({time.time() - t0:.0f}s)")
        del info
        if st.device.startswith("cuda"):
            torch.cuda.empty_cache()
        return res
    except Exception as e:  # pragma: no cover
        st.log(f"FAILED {name} tag={tag} frac={frac} seed={seed}: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        write_json(out_json.with_suffix(".FAILED.json"), {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()})
        return None


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _by_seed(g: pd.DataFrame, col: str) -> dict[str, float]:
    if g.empty:
        return {}
    gg = g.groupby("seed")[col].mean()
    return {str(int(s)): float(v) for s, v in gg.items() if v == v}


def summarise(tables: dict[str, list[dict]]) -> dict[str, dict[str, Any]]:
    """Frozen Stage 1R-B aggregation (identical definitions, so the comparison is like-for-like)."""
    det, hp, loc = _df(tables["detection"]), _df(tables["healthy_prediction"]), _df(tables["localization"])
    M: dict[str, dict[str, Any]] = {}
    if not det.empty:
        d = det[(det.density_variant == PRIMARY_VARIANT) & (det.family == "ALL") & (det.severity.astype(str) == "ALL") & (det.acceleration_input == "qdd_est")]
        for model, g in d.groupby("model"):
            mm = M.setdefault(model, {})
            g1 = g[g.training_fraction >= 1.0]
            for split in ("S0", "S1", "S2", "S3", "S4", "OOD", "ALL"):
                gs = g1[g1.split == split]
                mm[f"auroc_{split}"] = float(gs["auroc"].mean()) if len(gs) else float("nan")
                mm[f"auroc_{split}_std"] = float(gs["auroc"].std()) if len(gs) > 1 else float("nan")
                mm[f"fpr90_{split}"] = float(gs["fpr_at_tpr90"].mean()) if len(gs) else float("nan")
                mm[f"auroc_{split}_by_seed"] = _by_seed(gs, "auroc")
            for frac in sorted(g.training_fraction.unique()):
                for split in ("ALL", "OOD", "S1"):
                    gf = g[(g.training_fraction == frac) & (g.split == split)]
                    mm[f"auroc_{split}_frac{frac:.2f}"] = float(gf["auroc"].mean()) if len(gf) else float("nan")
                    mm[f"auroc_{split}_frac{frac:.2f}_by_seed"] = _by_seed(gf, "auroc")
        dfam = det[(det.density_variant == PRIMARY_VARIANT) & (det.severity.astype(str) == "ALL") & (det.training_fraction >= 1.0) & (det.acceleration_input == "qdd_est")]
        for model, g in dfam.groupby("model"):
            for split in ("S1", "S2", "S4", "OOD", "ALL"):
                gs = g[g.split == split]
                M.setdefault(model, {})[f"auroc_{split}_by_family"] = {fam: float(gg["auroc"].mean()) for fam, gg in gs.groupby("family")}
    if not loc.empty:
        l = loc[(loc.method == CF_METHOD) & (loc.family == "ALL") & (loc.training_fraction >= 1.0)]
        for model, g in l.groupby("model"):
            for split in ("S0", "OOD", "ALL"):
                gs = g[g.split == split]
                mm = M.setdefault(model, {})
                mm[f"loc_cf_top1_{split}"] = float(gs["top1"].mean()) if len(gs) else float("nan")
                mm[f"loc_cf_top2_{split}"] = float(gs["top2"].mean()) if len(gs) else float("nan")
                mm[f"loc_cf_dist_{split}"] = float(gs["mean_chain_distance"].mean()) if len(gs) else float("nan")
                mm[f"loc_cf_top1_{split}_by_seed"] = _by_seed(gs, "top1")
        lf = loc[(loc.method == CF_METHOD) & (loc.training_fraction >= 1.0) & (loc.split == "ALL")]
        for model, g in lf.groupby("model"):
            M.setdefault(model, {})["loc_cf_top1_ALL_by_family"] = {fam: float(gg["top1"].mean()) for fam, gg in g.groupby("family")}
    if not hp.empty:
        h = hp[hp.acceleration_input == "qdd_est"] if "acceleration_input" in hp else hp
        for model, g in h.groupby("model"):
            mm = M.setdefault(model, {})
            for frac in sorted(g.training_fraction.unique()):
                fs = "" if frac >= 1.0 else f"_frac{frac:.2f}"
                for split in ("S0", "OOD", "VAL", "S1", "S2", "S4"):
                    gs = g[(g.training_fraction == frac) & (g.split == split)]
                    mm[f"rmse_ratio_{split}{fs}"] = float(gs["rmse_ratio_post_over_pre"].mean()) if len(gs) else float("nan")
                    mm[f"rmse_post_{split}{fs}"] = float(gs["torque_rmse_post_nm"].mean()) if len(gs) else float("nan")
    return M


def main() -> int:
    ap = common_parser("Stage 2A Phase 2: frozen chain_gnn_aug baseline reproduction")
    ap.add_argument("--skip-learning-curve", action="store_true")
    args = ap.parse_args()
    st = Stage(args, "baseline")
    if not st.require_freeze():
        return 3
    cfg = st.cfg
    seeds = list(cfg["seed_list"])
    frozen = cfg["models"]["frozen_best_config"]
    runs_dir = st.layout.sub("p2_baseline") / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    n_train = len(st.bundle.train_ids)
    lc_eps = [e for e in cfg["training"]["learning_curve_episodes"] if e <= n_train]
    unavailable = [e for e in cfg["training"]["learning_curve_requested"] if isinstance(e, int) and e > n_train]
    st.log(f"healthy train episodes available: {n_train}; learning-curve points {lc_eps}; NOT AVAILABLE {unavailable}")

    jobs: list[tuple[str, float, int, float, str, str, bool, bool]] = []
    for model in ("chain_gnn_aug", "rnea_gru"):
        fc = frozen[model]
        for seed in seeds:
            jobs.append((model, 1.0, seed, float(fc["lr"]), fc["scheduler"], fc["tag"], True, True))
        if not args.skip_learning_curve:
            for e in lc_eps:
                if e >= n_train:
                    continue
                for seed in seeds:
                    jobs.append((model, e / n_train, seed, float(fc["lr"]), fc["scheduler"], fc["tag"], False, False))
    # analytic physics baseline (no parameters, one job)
    jobs.append(("rnea_only", 1.0, seeds[0], 0.0, "none", "", True, False))

    tables: dict[str, list[dict]] = {k: [] for k in RESULT_TABLES}
    train_infos: list[dict] = []
    t_start = time.time()
    for i, (model, frac, seed, lr, sched, tag, full, accdiag) in enumerate(jobs, 1):
        out = runs_dir / f"{model}_frac{frac:.2f}_seed{seed}.json"
        st.log(f"[{i}/{len(jobs)}] {model} frac={frac:.2f} seed={seed} full={full} ({time.time() - t_start:.0f}s elapsed)")
        res = json.loads(out.read_text()) if out.exists() else run_job(st, model, frac, seed, lr, sched, tag, out, full=full, acceleration_diagnostic=accdiag)
        if res is None:
            continue
        for k in RESULT_TABLES:
            tables[k] += res.get(k, [])
        for ti in res.get("train_info", []):
            train_infos.append({**ti, "job": out.stem})

    summary = summarise(tables)
    write_json(st.layout.results / "stage2a_baseline_metrics_summary.json", summary)

    # ---------------------------------------------------------------- reproduction gate
    ref = dict(cfg["models"]["frozen_reference"]["chain_gnn_aug"])
    m = summary.get("chain_gnn_aug", {})
    ti = [t for t in train_infos if t.get("name") == "chain_gnn_aug" and float(t.get("training_fraction", 0)) >= 1.0]
    observed = {
        "n_params": float(ti[0]["n_params"]) if ti else float("nan"),
        "val_healthy_rmse_nm": float(np.mean([t["val_healthy_rmse_nm"] for t in ti])) if ti else float("nan"),
        "healthy_rmse_S0_nm": m.get("rmse_post_S0", float("nan")),
        "healthy_rmse_ratio_S0": m.get("rmse_ratio_S0", float("nan")),
        "auroc_ALL": m.get("auroc_ALL", float("nan")),
        "auroc_S1": m.get("auroc_S1", float("nan")),
        "auroc_S2_S4": float(np.mean([m.get("auroc_S2", float("nan")), m.get("auroc_S4", float("nan"))])),
        "localization_top1": m.get("loc_cf_top1_ALL", float("nan")),
        "localization_chain_distance": m.get("loc_cf_dist_ALL", float("nan")),
    }
    gate = reproduction_gate(observed, ref, float(cfg["decision"]["reproduction_gate_relative_tolerance"]))

    rows = []
    for r in gate["rows"]:
        rows.append(st.base_row(model="chain_gnn_aug", fault_family="ALL", split="ALL", seed="mean",
                                metric=r["metric"], frozen_reference=r["reference"], observed=r["observed"],
                                relative_deviation=r["relative_deviation"], within_tolerance=r["within_tolerance"],
                                status=r["status"], tolerance=gate["tolerance"],
                                source="Stage 1R-B run_20260815T143902Z_4e94370 (Draft PR #3), identical metric definitions"))
    for model, mm in sorted(summary.items()):
        for split in ("S0", "S1", "S2", "S3", "S4", "OOD", "ALL"):
            if f"auroc_{split}" not in mm:
                continue
            rows.append(st.base_row(model=model, fault_family="ALL", split=split, seed="mean", metric=f"auroc_{split}",
                                    frozen_reference="", observed=mm[f"auroc_{split}"], relative_deviation="", within_tolerance="",
                                    status="OK", tolerance="", source="this run",
                                    auroc_std=mm.get(f"auroc_{split}_std"), fpr_at_tpr90=mm.get(f"fpr90_{split}"),
                                    by_seed=json.dumps(mm.get(f"auroc_{split}_by_seed", {}))))
    st.write_table("stage2a_baseline_reproduction.csv", rows,
                   units="AUROC dimensionless; RMSE in N m; chain distance in links; relative_deviation dimensionless",
                   schema={"metric": "name of the reproduced quantity", "frozen_reference": "Stage 1R-B frozen value", "observed": "value produced in this run", "within_tolerance": f"|rel dev| <= {gate['tolerance']}"})

    # ---------------------------------------------------------------- learning curve
    lc_rows = []
    hp = _df(tables["healthy_prediction"])
    det = _df(tables["detection"])
    for model in ("chain_gnn_aug", "rnea_gru"):
        for e in cfg["training"]["learning_curve_requested"]:
            n_ep = n_train if e == "all" else int(e)
            avail = n_ep <= n_train
            frac = n_ep / n_train
            row = st.base_row(model=model, fault_family="ALL", split="ALL", seed="mean",
                              n_train_episodes=n_ep, requested_point=str(e), available=avail,
                              status="OK" if avail else "NOT_AVAILABLE")
            if avail and not det.empty:
                d = det[(det.model == model) & (det.density_variant == PRIMARY_VARIANT) & (det.family == "ALL") & (det.severity.astype(str) == "ALL") & (det.acceleration_input == "qdd_est") & (np.isclose(det.training_fraction, frac))]
                h = hp[(hp.model == model) & (hp.acceleration_input == "qdd_est") & (np.isclose(hp.training_fraction, frac))]
                for split in ("ALL", "S1", "OOD"):
                    ds = d[d.split == split]
                    row[f"auroc_{split}"] = float(ds["auroc"].mean()) if len(ds) else float("nan")
                    row[f"auroc_{split}_std"] = float(ds["auroc"].std()) if len(ds) > 1 else float("nan")
                hs = h[h.split == "S0"]
                hv = h[h.split == "VAL"]
                row["healthy_rmse_S0_nm"] = float(hs["torque_rmse_post_nm"].mean()) if len(hs) else float("nan")
                row["healthy_rmse_VAL_nm"] = float(hv["torque_rmse_post_nm"].mean()) if len(hv) else float("nan")
                row["rmse_ratio_S0"] = float(hs["rmse_ratio_post_over_pre"].mean()) if len(hs) else float("nan")
                row["n_seeds"] = int(d["seed"].nunique()) if len(d) else 0
            else:
                row["note"] = f"the frozen pilot has only {n_train} healthy train episodes; this point is not available and is never extrapolated"
            lc_rows.append(row)
    st.write_table("stage2a_learning_curve.csv", lc_rows,
                   units="AUROC dimensionless; RMSE in N m; n_train_episodes = healthy training episodes",
                   schema={"available": "False = the frozen dataset cannot supply this point"})

    # ---------------------------------------------------------------- raw tables + leakage manifest
    from certo_fdi.experiments.common import write_csv

    for k, rowsk in tables.items():
        if rowsk:
            write_csv(st.layout.sub("p2_baseline") / f"stage2a_baseline_{k}.csv", rowsk)
    write_csv(st.layout.sub("p2_baseline") / "stage2a_baseline_train_info.csv", train_infos)

    from certo_fdi.models.chain_gnn import ChainGNN

    write_json(st.layout.results / "stage2a_baseline_gate.json", {
        "gate": gate["gate"], "worst_relative_deviation": gate["worst_relative_deviation"], "tolerance": gate["tolerance"],
        "observed": observed, "frozen_reference": ref, "rows": gate["rows"],
        "frozen_config_reused": frozen, "n_jobs": len(jobs), "n_train_episodes": n_train,
        "learning_curve_points": lc_eps, "learning_curve_not_available": unavailable,
        "chain_gnn_aug_input_manifest": ChainGNN.input_field_manifest(),
        "note": "identical metric definitions to Stage 1R-B; a clean retrain in this run, not a checkpoint reuse",
    })
    st.log(f"reproduction gate: {gate['gate']} (worst relative deviation {gate['worst_relative_deviation']:.4f})")
    for r in gate["rows"]:
        st.log(f"  {r['metric']:32s} ref={r['reference']} obs={r['observed']} rel={r['relative_deviation']} {r['status']}")
    st.finish({"gate": gate["gate"]})
    return 0 if gate["gate"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
