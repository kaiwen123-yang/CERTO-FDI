"""Stage 1R-B Phase D aggregation: per-job JSONs -> result tables (all stratified by model, seed,
split, fault family, controller-free severity, acceleration input, density variant) and the
per-model metrics summary consumed by ``decision_stage1rb``. Optionally re-evaluates checkpoints."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from certo_fdi.data.schema import FAULT_FAMILIES
from certo_fdi.experiments.common import write_csv, write_json
from certo_fdi.experiments.stage1rb_common import DIAGNOSTIC_MODELS, PRIMARY_MODELS, RESULT_TABLES, Stage, common_parser
from certo_fdi.experiments.evaluation import LOCALIZABLE

PRIMARY_VARIANT = "residual_only"
CF_METHOD = "counterfactual_link_masking"
PATTERN_METHOD = "joint_residual_pattern:pattern"


def _df(rows):
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _by_seed(g: pd.DataFrame, col: str) -> dict[str, float]:
    return {str(int(s)): float(v) for s, v in zip(g["seed"], g[col]) if v == v}


def build_tables(runs_dir: Path) -> tuple[dict[str, list[dict]], list[dict]]:
    tables: dict[str, list[dict]] = {k: [] for k in RESULT_TABLES}
    train_infos: list[dict] = []
    for p in sorted(runs_dir.glob("*.json")):
        if p.name.endswith(".FAILED.json"):
            continue
        res = json.loads(p.read_text())
        for k in RESULT_TABLES:
            tables[k] += res.get(k, [])
        for ti in res.get("train_info", []):
            train_infos.append({**ti, "job": p.stem})
    return tables, train_infos


def metrics_summary(tables: dict[str, list[dict]], train_infos: list[dict]) -> dict[str, dict[str, Any]]:
    det, hp, loc, fr, lat = _df(tables["detection"]), _df(tables["healthy_prediction"]), _df(tables["localization"]), _df(tables["frame_invariance"]), _df(tables["latency"])
    M: dict[str, dict[str, Any]] = {}
    if not det.empty:
        d = det[(det.density_variant == PRIMARY_VARIANT) & (det.family == "ALL") & (det.severity.astype(str) == "ALL")]
        for (model, acc), g in d.groupby(["model", "acceleration_input"]):
            suf = "" if acc == "qdd_est" else "_qddtrue"
            mm = M.setdefault(model, {})
            g1 = g[g.training_fraction >= 1.0]
            for split in ("S0", "S1", "S2", "S3", "S4", "OOD", "ALL"):
                gs = g1[g1.split == split]
                mm[f"auroc_{split}{suf}"] = float(gs["auroc"].mean()) if len(gs) else float("nan")
                mm[f"auroc_{split}{suf}_std"] = float(gs["auroc"].std()) if len(gs) > 1 else float("nan")
                mm[f"fpr90_{split}{suf}"] = float(gs["fpr_at_tpr90"].mean()) if len(gs) else float("nan")
                mm[f"event_auroc_{split}{suf}"] = float(gs["episode_auroc"].mean()) if len(gs) else float("nan")
                mm[f"detection_delay_median_s_{split}{suf}"] = float(gs["detection_delay_median_s"].mean()) if len(gs) and "detection_delay_median_s" in gs else float("nan")
                mm[f"auroc_{split}{suf}_by_seed"] = _by_seed(gs, "auroc")
                mm[f"fpr90_{split}{suf}_by_seed"] = _by_seed(gs, "fpr_at_tpr90")
            for frac in sorted(g.training_fraction.unique()):
                for split in ("ALL", "OOD", "S1"):
                    gf = g[(g.training_fraction == frac) & (g.split == split)]
                    mm[f"auroc_{split}_frac{frac:.2f}{suf}"] = float(gf["auroc"].mean()) if len(gf) else float("nan")
                    mm[f"auroc_{split}_frac{frac:.2f}{suf}_by_seed"] = _by_seed(gf, "auroc")
                    mm[f"n_seeds_frac{frac:.2f}{suf}"] = int(gf["seed"].nunique()) if len(gf) else 0
        dfam = det[(det.density_variant == PRIMARY_VARIANT) & (det.severity.astype(str) == "ALL") & (det.training_fraction >= 1.0) & (det.acceleration_input == "qdd_est")]
        for model, g in dfam.groupby("model"):
            for split in ("S1", "S2", "S4", "OOD", "ALL"):
                gs = g[g.split == split]
                M.setdefault(model, {})[f"auroc_{split}_by_family_seed"] = {fam: _by_seed(gg, "auroc") for fam, gg in gs.groupby("family")}
                M[model][f"auroc_{split}_by_family"] = {fam: float(gg["auroc"].mean()) for fam, gg in gs.groupby("family")}
        # secondary representation variant (reported, not decisive)
        d2 = det[(det.density_variant == "representation") & (det.family == "ALL") & (det.severity.astype(str) == "ALL") & (det.training_fraction >= 1.0) & (det.acceleration_input == "qdd_est")]
        for model, g in d2.groupby("model"):
            for split in ("S1", "S2", "S4", "OOD", "ALL"):
                gs = g[g.split == split]
                M.setdefault(model, {})[f"auroc_{split}_representation"] = float(gs["auroc"].mean()) if len(gs) else float("nan")
    if not loc.empty:
        for method, key in ((CF_METHOD, "loc_cf"), (PATTERN_METHOD, "loc_pattern")):
            l = loc[(loc.method == method) & (loc.family == "ALL") & (loc.training_fraction >= 1.0)]
            if method == PATTERN_METHOD:
                l = l[l.density_variant == PRIMARY_VARIANT]
            for model, g in l.groupby("model"):
                for split in ("S0", "OOD", "ALL"):
                    gs = g[g.split == split]
                    mm = M.setdefault(model, {})
                    mm[f"{key}_top1_{split}"] = float(gs["top1"].mean()) if len(gs) else float("nan")
                    mm[f"{key}_top2_{split}"] = float(gs["top2"].mean()) if len(gs) else float("nan")
                    mm[f"{key}_dist_{split}"] = float(gs["mean_chain_distance"].mean()) if len(gs) else float("nan")
                    mm[f"{key}_top1_{split}_by_seed"] = _by_seed(gs, "top1")
                    mm[f"{key}_dist_{split}_by_seed"] = _by_seed(gs, "mean_chain_distance")
            lf = loc[(loc.method == method) & (loc.training_fraction >= 1.0) & (loc.split == "ALL")]
            if method == PATTERN_METHOD:
                lf = lf[lf.density_variant == PRIMARY_VARIANT]
            for model, g in lf.groupby("model"):
                M.setdefault(model, {})[f"{key}_top1_ALL_by_family"] = {fam: float(gg["top1"].mean()) for fam, gg in g.groupby("family")}
                M[model][f"{key}_top1_ALL_by_family_seed"] = {fam: _by_seed(gg, "top1") for fam, gg in g.groupby("family")}
    if not hp.empty:
        for (model, acc), g in hp.groupby(["model", "acceleration_input"]):
            suf = "" if acc == "qdd_est" else "_qddtrue"
            mm = M.setdefault(model, {})
            for frac in sorted(g.training_fraction.unique()):
                fs = "" if frac >= 1.0 else f"_frac{frac:.2f}"
                for split in ("S0", "OOD", "VAL", "S1", "S2", "S4"):
                    gs = g[(g.training_fraction == frac) & (g.split == split)]
                    mm[f"rmse_ratio_{split}{fs}{suf}"] = float(gs["rmse_ratio_post_over_pre"].mean()) if len(gs) else float("nan")
                    mm[f"rmse_post_{split}{fs}{suf}"] = float(gs["torque_rmse_post_nm"].mean()) if len(gs) else float("nan")
                    mm[f"rmse_post_{split}{fs}{suf}_by_seed"] = _by_seed(gs, "torque_rmse_post_nm")
    if not fr.empty:
        for model, g in fr.groupby("model"):
            mm = M.setdefault(model, {})
            mm["frame_drift_median"] = float(g["delta_tau_relative_drift"].median())
            mm["frame_drift_max"] = float(g["delta_tau_relative_drift"].max())
            mm["frame_score_drift_median"] = float(g["score_drift_in_healthy_std"].median())
    if not lat.empty:
        for model, g in lat[lat.device != "cpu"].groupby("model"):
            mm = M.setdefault(model, {})
            mm["latency_us_per_window_gpu"] = float(g["latency_us_per_window"].mean())
            mm["n_params"] = int(g["n_params"].iloc[0])
    ti = _df(train_infos)
    if not ti.empty:
        for model, g in ti.groupby("name"):
            mm = M.setdefault(model, {})
            g1 = g[g.training_fraction >= 1.0]
            mm["train_seconds_mean"] = float(g1["train_seconds"].mean()) if len(g1) else float("nan")
            mm["best_val_loss_by_seed"] = _by_seed(g1, "best_val_loss") if len(g1) else {}
            mm["val_healthy_rmse_nm_by_seed"] = _by_seed(g1, "val_healthy_rmse_nm") if len(g1) and "val_healthy_rmse_nm" in g1 else {}
            mm["epochs_run_by_seed"] = _by_seed(g1, "epochs_run") if len(g1) else {}
            mm["n_final_runs"] = int(len(g))
            mm["n_params"] = int(g["n_params"].iloc[0]) if "n_params" in g else mm.get("n_params")
            mm["all_runs_finite"] = bool(np.isfinite(g["best_val_loss"].astype(float)).all()) if len(g) else False
    return M


def sample_efficiency_rows(det: pd.DataFrame, hp: pd.DataFrame, base: dict) -> list[dict]:
    rows = []
    if det.empty:
        return rows
    d = det[(det.density_variant == PRIMARY_VARIANT) & (det.family == "ALL") & (det.severity.astype(str) == "ALL") & (det.acceleration_input == "qdd_est")]
    for (model, frac), g in d.groupby(["model", "training_fraction"]):
        row = {**base, "model": model, "seed": "mean", "training_fraction": frac, "n_seeds": int(g["seed"].nunique())}
        for split in ("ALL", "OOD", "S1", "S2", "S4"):
            gs = g[g.split == split]
            row[f"auroc_{split}"] = float(gs["auroc"].mean()) if len(gs) else float("nan")
            row[f"auroc_{split}_std"] = float(gs["auroc"].std()) if len(gs) > 1 else float("nan")
            row[f"fpr90_{split}"] = float(gs["fpr_at_tpr90"].mean()) if len(gs) else float("nan")
        if not hp.empty:
            h = hp[(hp.model == model) & (hp.training_fraction == frac) & (hp.acceleration_input == "qdd_est")]
            for split in ("S0", "OOD", "VAL"):
                hs = h[h.split == split]
                row[f"rmse_ratio_{split}"] = float(hs["rmse_ratio_post_over_pre"].mean()) if len(hs) else float("nan")
                row[f"rmse_post_{split}_nm"] = float(hs["torque_rmse_post_nm"].mean()) if len(hs) else float("nan")
        row["units"] = "window AUROC (residual-only head); RMSE N m"
        rows.append(row)
    return rows


def ablation_rows(det: pd.DataFrame, hp: pd.DataFrame, loc: pd.DataFrame, base: dict) -> list[dict]:
    rows = []
    if det.empty:
        return rows
    d = det[(det.family == "ALL") & (det.severity.astype(str) == "ALL") & (det.training_fraction >= 1.0)]
    for (model, variant, acc, split), g in d.groupby(["model", "density_variant", "acceleration_input", "split"]):
        row = {**base, "model": model, "seed": "mean", "density_variant": variant, "acceleration_input": acc, "split": split, "window_auroc": float(g["auroc"].mean()), "auroc_std": float(g["auroc"].std()) if len(g) > 1 else 0.0, "event_auroc": float(g["episode_auroc"].mean()), "fpr_at_tpr90": float(g["fpr_at_tpr90"].mean()), "n_seeds": int(g["seed"].nunique())}
        if not loc.empty and acc == "qdd_est":
            for method, key in ((CF_METHOD, "cf"), (PATTERN_METHOD, "pattern")):
                l = loc[(loc.model == model) & (loc.method == method) & (loc.family == "ALL") & (loc.split == ("ALL" if split == "ALL" else split if split in ("S0", "OOD") else "ALL")) & (loc.training_fraction >= 1.0)]
                if method == PATTERN_METHOD:
                    l = l[l.density_variant == variant]
                row[f"loc_{key}_top1"] = float(l["top1"].mean()) if len(l) else float("nan")
                row[f"loc_{key}_chain_distance"] = float(l["mean_chain_distance"].mean()) if len(l) else float("nan")
        if not hp.empty:
            h = hp[(hp.model == model) & (hp.split == split) & (hp.training_fraction >= 1.0) & (hp.acceleration_input == acc)]
            row["rmse_ratio_post_over_pre"] = float(h["rmse_ratio_post_over_pre"].mean()) if len(h) else float("nan")
        rows.append(row)
    return rows


def main(argv=None) -> int:
    ap = common_parser("Stage 1R-B aggregation")
    args = ap.parse_args(argv)
    st = Stage(args, "evaluation")
    if not st.require_provenance():
        return 2
    t0 = time.time()
    runs_dir = st.layout.sub("c3_final") / "runs"
    tables, train_infos = build_tables(runs_dir)
    res = st.layout.results
    base = st.base_row()
    write_csv(res / "stage1rb_training_runs.csv", [{**base, "model": ti.get("name"), "seed": ti.get("seed"), "checkpoint_sha256": ti.get("checkpoint_sha256", ""), **{k: v for k, v in ti.items() if k not in ("history", "model")}} for ti in train_infos])
    write_csv(res / "stage1rb_healthy_prediction.csv", tables["healthy_prediction"])
    write_csv(res / "stage1rb_ood_detection.csv", tables["detection"])  # window/event detection metrics for every split (S0..S4, OOD, ALL), family, severity, variant, acceleration input
    write_csv(res / "stage1rb_healthy_ood_alarm_audit.csv", tables["ood_healthy"])
    write_csv(res / "stage1rb_localization.csv", tables["localization"])
    write_csv(res / "stage1rb_localization_detail.csv", tables["localization_detail"])
    write_csv(res / "stage1rb_frame_invariance.csv", tables["frame_invariance"])
    write_csv(res / "stage1rb_latency_and_size.csv", tables["latency"])
    write_csv(res / "stage1rb_density_heads.csv", tables["heads"])
    det, hp, loc = _df(tables["detection"]), _df(tables["healthy_prediction"]), _df(tables["localization"])
    write_csv(res / "stage1rb_sample_efficiency.csv", sample_efficiency_rows(det, hp, base))
    write_csv(res / "stage1rb_ablation_summary.csv", ablation_rows(det, hp, loc, base))
    # qdd diagnostic side-by-side
    diag_rows = []
    if not hp.empty:
        for (model, frac, split), g in hp[hp.split.isin(["S0", "OOD", "VAL"])].groupby(["model", "training_fraction", "split"]):
            r = {**base, "model": model, "seed": "mean", "training_fraction": frac, "split": split}
            for acc in ("qdd_est", "qdd_true"):
                ga = g[g.acceleration_input == acc]
                r[f"rmse_post_nm_{acc}"] = float(ga["torque_rmse_post_nm"].mean()) if len(ga) else float("nan")
                r[f"rmse_ratio_{acc}"] = float(ga["rmse_ratio_post_over_pre"].mean()) if len(ga) else float("nan")
            r["note"] = "qdd_true is an oracle diagnostic only; decisions use qdd_est"
            diag_rows.append(r)
    if not det.empty:
        d = det[(det.density_variant == PRIMARY_VARIANT) & (det.family == "ALL") & (det.severity.astype(str) == "ALL") & (det.split.isin(["S1", "S2", "S4", "OOD", "ALL"]))]
        for (model, frac, split), g in d.groupby(["model", "training_fraction", "split"]):
            r = {**base, "model": model, "seed": "mean", "training_fraction": frac, "split": split}
            for acc in ("qdd_est", "qdd_true"):
                ga = g[g.acceleration_input == acc]
                r[f"auroc_{acc}"] = float(ga["auroc"].mean()) if len(ga) else float("nan")
                r[f"fpr90_{acc}"] = float(ga["fpr_at_tpr90"].mean()) if len(ga) else float("nan")
            r["note"] = "qdd_true is an oracle diagnostic only; decisions use qdd_est"
            diag_rows.append(r)
    write_csv(res / "stage1rb_qdd_diagnostic.csv", diag_rows)
    M = metrics_summary(tables, train_infos)
    write_json(res / "stage1rb_metrics_summary.json", M)
    st.log(f"aggregation done: {len(train_infos)} runs, models={sorted(M.keys())} ({time.time() - t0:.0f}s)")
    st.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
