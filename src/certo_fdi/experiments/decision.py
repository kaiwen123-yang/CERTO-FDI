"""Summary tables, claim ledger, and the preregistered Stage 1R decision memo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from certo_fdi.experiments.common import base_row, utc_now, write_csv, write_json
from certo_fdi.paths import git_sha

STRUCTURED_POOL = ["chain_gnn", "chain_gnn_aug"]
ALL_BASELINE_POOL = ["chain_gnn", "chain_gnn_aug", "rnea_gru", "rnea_mlp"]
PRIMARY_VARIANT = "representation"
PRIMARY_LOC_RULE = "pattern"  # unsupervised load-path/peak pattern rule (same for all models); argmax/distal also reported


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _mean_over_seeds(df: pd.DataFrame, value: str, keys: list[str]) -> pd.DataFrame:
    if df.empty or value not in df:
        return pd.DataFrame(columns=keys + [value, f"{value}_std", "n_seeds"])
    g = df.groupby(keys)[value]
    out = g.mean().reset_index()
    out[f"{value}_std"] = g.std().reset_index()[value].fillna(0.0)
    out["n_seeds"] = g.count().reset_index()[value]
    return out


def build_summary_tables(tables: dict[str, list[dict]], layout, repo_root: Path, cfg_sha: str, cfg: dict) -> dict[str, Any]:
    det = _df(tables["event_detection"])
    hp = _df(tables["healthy_prediction"])
    loc = _df(tables["localization"])
    fr = _df(tables["frame_invariance"])
    fs = _df(tables["fewshot"])
    lat = _df(tables["latency"])
    results = layout.results
    summary: dict[str, Any] = {}

    # sample efficiency: AUROC (ALL / OOD / S1) & RMSE ratio by model x fraction (seed mean)
    se_rows = []
    if not det.empty:
        d = det[(det.density_variant == PRIMARY_VARIANT) & (det.family == "ALL") & (det.severity == "ALL")]
        for (model, frac, split), g in d.groupby(["model", "training_fraction", "split"]):
            se_rows.append({**base_row(layout, repo_root, cfg_sha, model=model, split=split, seed="mean"), "training_fraction": frac, "metric": "window_auroc", "value": float(g["auroc"].mean()), "std_over_seeds": float(g["auroc"].std() if len(g) > 1 else 0.0), "n_seeds": int(len(g)), "event_auroc": float(g["episode_auroc"].mean()), "fpr_at_tpr90": float(g["fpr_at_tpr90"].mean()), "event_tpr_at_threshold": float(g["event_tpr"].mean()), "false_alarms_per_hour": float(g["false_alarms_per_hour"].mean()), "density_variant": PRIMARY_VARIANT})
    if not hp.empty:
        for (model, frac, split), g in hp.groupby(["model", "training_fraction", "split"]):
            se_rows.append({**base_row(layout, repo_root, cfg_sha, model=model, split=split, seed="mean"), "training_fraction": frac, "metric": "torque_rmse_post_nm", "value": float(g["torque_rmse_post_nm"].mean()), "std_over_seeds": float(g["torque_rmse_post_nm"].std() if len(g) > 1 else 0.0), "n_seeds": int(len(g)), "rmse_pre_nm": float(g["torque_rmse_pre_nm"].mean()), "rmse_ratio_post_over_pre": float(g["rmse_ratio_post_over_pre"].mean()), "units": "N m"})
    write_csv(results / "stage1r_sample_efficiency.csv", se_rows)
    summary["sample_efficiency"] = se_rows

    # ablation summary at fraction 1.0
    abl_rows = []
    if not det.empty:
        d = det[(det.density_variant.isin([PRIMARY_VARIANT, "residual_only", "representation_unconditional", "residual_plus_gmo", "gmo_only"])) & (det.family == "ALL") & (det.severity == "ALL") & (det.training_fraction >= 1.0)]
        for (model, variant, split), g in d.groupby(["model", "density_variant", "split"]):
            row = {**base_row(layout, repo_root, cfg_sha, model=model, split=split, seed="mean"), "density_variant": variant, "window_auroc": float(g["auroc"].mean()), "auroc_std": float(g["auroc"].std() if len(g) > 1 else 0.0), "event_auroc": float(g["episode_auroc"].mean()), "fpr_at_tpr90": float(g["fpr_at_tpr90"].mean()), "n_seeds": int(len(g))}
            if not loc.empty:
                l = loc[(loc.model == model) & (loc.density_variant == variant) & (loc.rule == PRIMARY_LOC_RULE) & (loc.family == "ALL") & (loc.split == ("ALL" if split == "ALL" else split if split in ("S0", "OOD") else "ALL")) & (loc.training_fraction >= 1.0)]
                row["localization_top1"] = float(l["top1"].mean()) if len(l) else float("nan")
                row["localization_chain_distance"] = float(l["mean_chain_distance"].mean()) if len(l) else float("nan")
            if not hp.empty:
                h = hp[(hp.model == model) & (hp.split == split) & (hp.training_fraction >= 1.0)]
                row["rmse_ratio_post_over_pre"] = float(h["rmse_ratio_post_over_pre"].mean()) if len(h) else float("nan")
            abl_rows.append(row)
    write_csv(results / "stage1r_ablation_summary.csv", abl_rows)
    summary["ablation"] = abl_rows

    # geometry summary (R0 + model-level + frame drift per model)
    geo_rows = []
    r0 = layout.sub("r0_geometry")
    try:
        g = json.loads((r0 / "stage1r_r0_geometry_tests.json").read_text())
        for k, v in g["checks"].items():
            geo_rows.append({**base_row(layout, repo_root, cfg_sha, model="analytic_front_end", split="R0"), "check": k, "value": v, "pass": bool(v)})
        for k, v in g["dynamics_crosscheck"].items():
            geo_rows.append({**base_row(layout, repo_root, cfg_sha, model="analytic_front_end", split="R0"), "check": k, "value": v.get("max_abs_error", v.get("status")), "pass": v.get("pass", v.get("detected"))})
    except FileNotFoundError:
        pass
    try:
        m = json.loads((r0 / "stage1r_r0_model_covariance.json").read_text())
        for name, per in m["models"].items():
            for dn, w in per.items():
                geo_rows.append({**base_row(layout, repo_root, cfg_sha, model=name, split="R0_model"), "check": f"T1_T2_T3_{dn}", "value": json.dumps({k: w[k] for k in ("T1", "T2", "T3")}), "pass": w["pass"]})
    except FileNotFoundError:
        pass
    if not fr.empty:
        for model, g in fr.groupby("model"):
            geo_rows.append({**base_row(layout, repo_root, cfg_sha, model=model, split="S5"), "check": "frame_reparameterization_drift", "value": json.dumps({"delta_tau_relative_drift_median": float(g["delta_tau_relative_drift"].median()), "delta_tau_relative_drift_max": float(g["delta_tau_relative_drift"].max()), "score_drift_in_healthy_std_median": float(g["score_drift_in_healthy_std"].median()), "score_auroc_variant_vs_canonical_mean": float(g["score_auroc_variant_vs_canonical"].mean()), "n": int(len(g))}), "pass": ""})
    write_csv(results / "stage1r_geometry_summary.csv", geo_rows)
    summary["geometry"] = geo_rows

    # ---- per-model seed-mean metrics used by the decision
    metrics: dict[str, dict[str, Any]] = {}
    if not det.empty:
        d = det[(det.density_variant == PRIMARY_VARIANT) & (det.family == "ALL") & (det.severity == "ALL")]
        for model, g in d.groupby("model"):
            mm: dict[str, Any] = {}
            g1 = g[g.training_fraction >= 1.0]
            for split in ("S0", "S1", "S2", "S3", "S4", "OOD", "ALL"):
                gs = g1[g1.split == split]
                mm[f"auroc_{split}"] = float(gs["auroc"].mean()) if len(gs) else float("nan")
                mm[f"fpr90_{split}"] = float(gs["fpr_at_tpr90"].mean()) if len(gs) else float("nan")
                mm[f"event_auroc_{split}"] = float(gs["episode_auroc"].mean()) if len(gs) else float("nan")
                mm[f"auroc_{split}_by_seed"] = {int(s): float(v) for s, v in zip(gs["seed"], gs["auroc"])}
            for frac in sorted(g.training_fraction.unique()):
                gf = g[(g.training_fraction == frac) & (g.split == "ALL")]
                mm[f"auroc_ALL_frac{frac:.2f}"] = float(gf["auroc"].mean()) if len(gf) else float("nan")
                gf = g[(g.training_fraction == frac) & (g.split == "OOD")]
                mm[f"auroc_OOD_frac{frac:.2f}"] = float(gf["auroc"].mean()) if len(gf) else float("nan")
            metrics[model] = mm
        # per family OOD (for the >=2 families / >=2 seeds criterion)
        dfam = det[(det.density_variant == PRIMARY_VARIANT) & (det.severity == "ALL") & (det.split == "OOD") & (det.training_fraction >= 1.0)]
        for model, g in dfam.groupby("model"):
            metrics.setdefault(model, {})["auroc_OOD_by_family_seed"] = {fam: {int(s): float(v) for s, v in zip(gg["seed"], gg["auroc"])} for fam, gg in g.groupby("family")}
    if not loc.empty:
        for rule in ("pattern", "argmax", "distal"):
            l = loc[(loc.density_variant == PRIMARY_VARIANT) & (loc.rule == rule) & (loc.family == "ALL") & (loc.training_fraction >= 1.0)]
            for model, g in l.groupby("model"):
                for split in ("S0", "OOD", "ALL"):
                    gs = g[g.split == split]
                    suffix = "" if rule == PRIMARY_LOC_RULE else f"_{rule}"
                    metrics.setdefault(model, {})[f"loc_top1_{split}{suffix}"] = float(gs["top1"].mean()) if len(gs) else float("nan")
                    metrics.setdefault(model, {})[f"loc_dist_{split}{suffix}"] = float(gs["mean_chain_distance"].mean()) if len(gs) else float("nan")
                    if rule == PRIMARY_LOC_RULE:
                        metrics.setdefault(model, {})[f"loc_top1_{split}_by_seed"] = {int(s): float(v) for s, v in zip(gs["seed"], gs["top1"])}
    if not fr.empty:
        for model, g in fr.groupby("model"):
            metrics.setdefault(model, {})["frame_drift_median"] = float(g["delta_tau_relative_drift"].median())
            metrics.setdefault(model, {})["frame_score_drift_median"] = float(g["score_drift_in_healthy_std"].median())
    if not hp.empty:
        h = hp[hp.training_fraction >= 1.0]
        for model, g in h.groupby("model"):
            for split in ("S0", "OOD", "VAL"):
                gs = g[g.split == split]
                metrics.setdefault(model, {})[f"rmse_ratio_{split}"] = float(gs["rmse_ratio_post_over_pre"].mean()) if len(gs) else float("nan")
    if not fs.empty:
        for (model, k), g in fs[fs.split == "ALL"].groupby(["model", "shots_per_class"]):
            metrics.setdefault(model, {})[f"fewshot_f1_{k}"] = float(g["episode_macro_f1"].mean())
    if not lat.empty:
        for model, g in lat[lat.device != "cpu"].groupby("model"):
            metrics.setdefault(model, {})["latency_us_per_window_gpu"] = float(g["latency_us_per_window"].mean())
            metrics.setdefault(model, {})["n_params"] = int(g["n_params"].iloc[0])
    summary["metrics"] = metrics
    write_json(layout.results / "stage1r_metrics_summary.json", metrics)
    return summary


def _best(metrics: dict, pool: list[str], key: str, higher: bool = True) -> tuple[str | None, float]:
    best_m, best_v = None, float("nan")
    for m in pool:
        v = metrics.get(m, {}).get(key, float("nan"))
        if v != v:
            continue
        if best_m is None or (v > best_v if higher else v < best_v):
            best_m, best_v = m, v
    return best_m, best_v


def decide_and_write_memo(summary: dict, tables: dict[str, list[dict]], layout, repo_root: Path, cfg: dict, cfg_sha: str, profile: str, data_root: Path) -> str:
    metrics = summary["metrics"]
    L = metrics.get("ligra", {})
    ev: dict[str, Any] = {}
    axes: dict[str, bool] = {}
    pts = lambda x: 100.0 * x if x == x else float("nan")

    def axis_detection(split_keys: list[str], name: str) -> None:
        lig = np.nanmean([L.get(f"auroc_{s}", np.nan) for s in split_keys]) if L else float("nan")
        best_m, best_v = None, float("nan")
        best_fpr = float("nan")
        for m in STRUCTURED_POOL:
            v = np.nanmean([metrics.get(m, {}).get(f"auroc_{s}", np.nan) for s in split_keys]) if m in metrics else float("nan")
            if v == v and (best_m is None or v > best_v):
                best_m, best_v = m, v
                best_fpr = np.nanmean([metrics.get(m, {}).get(f"fpr90_{s}", np.nan) for s in split_keys])
        lig_fpr = np.nanmean([L.get(f"fpr90_{s}", np.nan) for s in split_keys]) if L else float("nan")
        gain_pts = pts(lig) - pts(best_v)
        fpr_red = (best_fpr - lig_fpr) / best_fpr if (best_fpr == best_fpr and best_fpr > 0) else float("nan")
        passed = bool((gain_pts == gain_pts and gain_pts >= 3.0) or (fpr_red == fpr_red and fpr_red >= 0.25))
        axes[name] = passed
        ev[name] = {"ligra_auroc": lig, "best_structured_baseline": best_m, "baseline_auroc": best_v, "gain_auroc_points": gain_pts, "ligra_fpr90": lig_fpr, "baseline_fpr90": best_fpr, "fpr_relative_reduction": fpr_red, "gate": "+3 AUROC points or 25% relative FPR@TPR90 reduction", "pass": passed}

    axis_detection(["S1"], "axis1_unseen_configuration_anomaly")
    axis_detection(["S2", "S4"], "axis4_payload_context_shift_robustness")
    # axis 2 sample efficiency: LiGRA @25% within 2 points of best structured baseline @100% (AUROC ALL)
    lig25 = L.get("auroc_ALL_frac0.25", float("nan"))
    best_m, best100 = _best(metrics, STRUCTURED_POOL, "auroc_ALL_frac1.00")
    se_pass = bool(lig25 == lig25 and best100 == best100 and pts(lig25) >= pts(best100) - 2.0)
    # secondary: RMSE-based sample efficiency (25% LiGRA within 2% relative of baseline 100%)
    axes["axis2_sample_efficiency"] = se_pass
    ev["axis2_sample_efficiency"] = {"ligra_auroc_ALL_at_25pct": lig25, "best_structured_baseline": best_m, "baseline_auroc_ALL_at_100pct": best100, "gate": "LiGRA@25% healthy data within 2 AUROC points of baseline@100%", "pass": se_pass, "curves": {m: {k: v for k, v in metrics.get(m, {}).items() if k.startswith("auroc_ALL_frac")} for m in ["ligra"] + ALL_BASELINE_POOL}}
    # axis 3 localization
    lig_top1 = L.get("loc_top1_ALL", float("nan"))
    lig_dist = L.get("loc_dist_ALL", float("nan"))
    bm, b_top1 = _best(metrics, STRUCTURED_POOL, "loc_top1_ALL")
    _, b_dist = _best(metrics, STRUCTURED_POOL, "loc_dist_ALL", higher=False)
    loc_pass = bool((lig_top1 == lig_top1 and b_top1 == b_top1 and pts(lig_top1) - pts(b_top1) >= 10.0) or (lig_dist == lig_dist and b_dist == b_dist and lig_dist <= 0.75 * b_dist))
    axes["axis3_localization"] = loc_pass
    ev["axis3_localization"] = {"ligra_top1": lig_top1, "ligra_chain_distance": lig_dist, "best_structured_baseline": bm, "baseline_top1": b_top1, "baseline_chain_distance": b_dist, "gate": "+10 top-1 points or >=25% chain-distance reduction", "pass": loc_pass}
    n_axes = int(sum(axes.values()))
    # frame drift ratio
    lig_drift = L.get("frame_drift_median", float("nan"))
    gnn_drift = metrics.get("chain_gnn", {}).get("frame_drift_median", float("nan"))
    aug_drift = metrics.get("chain_gnn_aug", {}).get("frame_drift_median", float("nan"))
    drift_ratio = (min(x for x in (gnn_drift, aug_drift) if x == x) / lig_drift) if (lig_drift == lig_drift and lig_drift > 0 and any(x == x for x in (gnn_drift, aug_drift))) else float("nan")
    frame_pass = bool(drift_ratio == drift_ratio and drift_ratio >= 100.0)
    ev["frame_reparameterization"] = {"ligra_median_relative_drift": lig_drift, "chain_gnn_median_relative_drift": gnn_drift, "chain_gnn_aug_median_relative_drift": aug_drift, "ratio_baseline_over_ligra": drift_ratio, "gate": ">=100x smaller drift than unconstrained baselines", "pass": frame_pass}
    # >=2 families and >=2 seeds (OOD detection): LiGRA > best structured baseline per family in >=2 seeds
    fam_wins = []
    lig_fam = L.get("auroc_OOD_by_family_seed", {})
    for fam, by_seed in lig_fam.items():
        wins = 0
        for s, v in by_seed.items():
            best_b = max((metrics.get(m, {}).get("auroc_OOD_by_family_seed", {}).get(fam, {}).get(s, float("-inf")) for m in STRUCTURED_POOL), default=float("-inf"))
            wins += int(v > best_b)
        if wins >= 2:
            fam_wins.append(fam)
    multi_family = len(fam_wins) >= 2
    ev["gain_breadth"] = {"families_with_ligra_gain_in_>=2_seeds": fam_wins, "pass": multi_family, "gate": ">=2 fault families and >=2 seeds"}
    # frame augmentation does not fully erase the advantage: LiGRA vs chain_gnn_aug on the axes won
    aug = metrics.get("chain_gnn_aug", {})
    aug_erases = []
    if aug:
        for name, splits in (("axis1_unseen_configuration_anomaly", ["S1"]), ("axis4_payload_context_shift_robustness", ["S2", "S4"])):
            if axes.get(name):
                lig = np.nanmean([L.get(f"auroc_{s}", np.nan) for s in splits])
                av = np.nanmean([aug.get(f"auroc_{s}", np.nan) for s in splits])
                aug_erases.append(bool(av == av and pts(lig) - pts(av) < 3.0))
        if axes.get("axis3_localization"):
            aug_erases.append(bool(aug.get("loc_top1_ALL", float("nan")) == aug.get("loc_top1_ALL", float("nan")) and pts(lig_top1) - pts(aug.get("loc_top1_ALL", 0)) < 10.0))
    aug_not_erase = not (aug_erases and all(aug_erases)) if aug_erases else True
    ev["frame_augmentation_check"] = {"chain_gnn_aug_erases_each_won_axis": aug_erases, "pass": aug_not_erase}
    # rigidity check (PIVOT-C signal): LiGRA healthy fit worse than baselines
    lig_r = L.get("rmse_ratio_S0", float("nan"))
    best_r_m, best_r = _best(metrics, ALL_BASELINE_POOL, "rmse_ratio_S0", higher=False)
    rigid = bool(lig_r == lig_r and best_r == best_r and lig_r > best_r * 1.10)
    ev["healthy_fit"] = {"ligra_rmse_ratio_S0": lig_r, "best_baseline": best_r_m, "best_baseline_rmse_ratio_S0": best_r, "ligra_worse_than_best_by_>10pct": rigid}
    # gates
    r0_ok = False
    try:
        r0_ok = json.loads((layout.sub("r0_geometry") / "stage1r_r0_geometry_tests.json").read_text())["decision"] == "PASS" and json.loads((layout.sub("r0_geometry") / "stage1r_r0_model_covariance.json").read_text())["decision"] == "PASS"
    except FileNotFoundError:
        pass
    leak_ok = False
    try:
        leak_ok = json.loads((data_root / "split_manifest.json").read_text())["leakage_report"]["all_pass"]
    except FileNotFoundError:
        pass
    have_runs = bool(L) and any(m in metrics for m in STRUCTURED_POOL)
    ev["gates"] = {"r0_analytic_and_model_level_pass": r0_ok, "leakage_tests_pass": leak_ok, "ligra_and_structured_baseline_runs_present": have_runs}
    # decision
    if not (r0_ok and leak_ok and have_runs):
        decision = "BLOCKED"
    elif n_axes >= 3 and multi_family and aug_not_erase and frame_pass:
        decision = "RESEARCH_GO"
    elif n_axes == 0:
        decision = "NO_GO_LIE_MAIN_CONTRIBUTION"
    else:
        # chain structure matches LiGRA on physical OOD tests?
        chain_close = []
        for s in ("S1", "S2", "S3", "S4"):
            lig = L.get(f"auroc_{s}", float("nan"))
            bv = max((metrics.get(m, {}).get(f"auroc_{s}", float("-inf")) for m in STRUCTURED_POOL), default=float("-inf"))
            chain_close.append(bool(lig == lig and bv > float("-inf") and pts(lig) - pts(bv) < 3.0))
        loc_close = bool(lig_top1 == lig_top1 and b_top1 == b_top1 and pts(lig_top1) - pts(b_top1) < 10.0)
        if all(chain_close) and loc_close:
            decision = "PIVOT_CHAIN_ONLY"
        elif (axes["axis1_unseen_configuration_anomaly"] or axes["axis4_payload_context_shift_robustness"]) and not axes["axis3_localization"]:
            decision = "PIVOT_DETECTION_ONLY"
        else:
            decision = "PIVOT_CHAIN_ONLY"
    if profile == "smoke":
        decision_note = "SMOKE profile: numbers are pipeline checks only; the recorded decision is NOT a scientific decision."
    else:
        decision_note = "PILOT profile: preregistered gates applied without retroactive changes."
    ev["decision"] = decision
    ev["n_axes_won"] = n_axes
    ev["axes"] = axes
    write_json(layout.results / "stage1r_decision_evidence.json", ev)

    # ---- claim ledger
    ledger = [
        ("G-01", "Healthy and faulty dynamics obey the same link-frame covariance laws.", "PROVED (analytic) + VERIFIED numerically (R0 healthy & faulty variants)" if r0_ok else "NOT VERIFIED", "R0 frame trials"),
        ("G-02", "LiGRA internal wrench-like messages transform covariantly.", "VERIFIED (T1 float64/float32)" if r0_ok else "NOT VERIFIED", "stage1r_r0_model_covariance.json"),
        ("G-03", "LiGRA torque prediction and anomaly score are frame invariant.", "VERIFIED (T2/T3) + S5 drift ratio %.3g" % drift_ratio if r0_ok else "NOT VERIFIED", "stage1r_frame_invariance.csv"),
        ("G-04", "Gauge covariance implies unseen-configuration generalization.", "FALSE / prohibited (never claimed)", "none"),
        ("A-01", "Faults appear as invariant latent distribution shifts.", f"EMPIRICAL: LiGRA window AUROC ALL={L.get('auroc_ALL', float('nan')):.3f}, OOD={L.get('auroc_OOD', float('nan')):.3f} (per family in stage1r_event_detection.csv)", "stage1r_event_detection.csv"),
        ("A-02", "LiGRA improves healthy sample efficiency.", f"EMPIRICAL: {'SUPPORTED' if axes['axis2_sample_efficiency'] else 'NOT SUPPORTED'} under the pilot gate", "stage1r_sample_efficiency.csv"),
        ("A-03", "LiGRA improves unseen-configuration robustness.", f"EMPIRICAL: {'SUPPORTED' if axes['axis1_unseen_configuration_anomaly'] else 'NOT SUPPORTED'} (S1); context shift {'SUPPORTED' if axes['axis4_payload_context_shift_robustness'] else 'NOT SUPPORTED'} (S2/S4)", "stage1r_event_detection.csv"),
        ("A-04", "LiGRA improves link/joint localization.", f"EMPIRICAL: {'SUPPORTED' if axes['axis3_localization'] else 'NOT SUPPORTED'} (top-1 {lig_top1:.3f} vs {b_top1:.3f})", "stage1r_localization.csv"),
        ("A-05", "Latent link messages are physical wrenches.", "UNPROVED / prohibited by default (torque-only supervision)", "none"),
        ("N-01", "No prior work directly occupies the exact Stage 1R combination.", "PLAUSIBLY OPEN; unchanged by this run (needs primary-source search)", "10_LITERATURE_POSITIONING"),
        ("N-02", "Every component is individually novel.", "FALSE / prohibited", "none"),
        ("S-01", "Strict non-vacuous certificates are necessary before learning.", "FALSE as project gate", "none"),
        ("S-02", "Strict certificate Stage 1 NO-GO invalidates LiGRA.", "FALSE inference; Stage 1R evaluated independently", "this run"),
        ("P-01", "A true physical/statistical symmetry may be relaxed and its breaking informative.", "CONDITIONAL; not exercised in the pilot", "none"),
        ("P-02", "Gauge covariance may be relaxed to detect faults.", "FALSE / prohibited; gauge covariance kept exact", "R0"),
    ]
    write_csv(layout.results / "stage1r_claim_ledger.csv", [{**base_row(layout, repo_root, cfg_sha, model="stage1r"), "claim_id": cid, "claim": c, "status": s, "evidence": e} for cid, c, s, e in ledger])

    # ---- memo
    def f3(x):
        return "n/a" if x is None or (isinstance(x, float) and x != x) else (f"{x:.3f}" if isinstance(x, float) else str(x))

    lines = [
        "# Stage 1R decision memo — LiGRA-FDI pilot",
        "",
        f"- Run: `{layout.run_id}`  ",
        f"- Git SHA: `{git_sha(repo_root)}`  ",
        f"- Config SHA256: `{cfg_sha}`  ",
        f"- Profile: **{profile}**  ",
        f"- Data root: `{data_root}`  ",
        f"- Timestamp (UTC): {utc_now()}",
        "",
        f"## Decision: **{decision}**",
        "",
        decision_note,
        "",
        "Decision vocabulary: RESEARCH_GO | PIVOT_CHAIN_ONLY | PIVOT_DETECTION_ONLY | PIVOT_REDUCED_PUBLIC_DATA | NO_GO_LIE_MAIN_CONTRIBUTION | BLOCKED. "
        "A NO_GO here would reject only the Lie-group representation as the main contribution, not manipulator fault detection.",
        "",
        "## Gates (06 §2)",
        "",
        f"- R0 analytic + model-level covariance: **{'PASS' if r0_ok else 'FAIL'}**",
        f"- Data split / fault-injection leakage tests: **{'PASS' if leak_ok else 'FAIL'}**",
        f"- LiGRA and structured baseline runs present: **{have_runs}**",
        "",
        "## Value axes (LiGRA vs strongest matched non-equivariant *structured* baseline; density head identical)",
        "",
        "| Axis | LiGRA | Best structured baseline | Gate | Pass |",
        "|---|---|---|---|---|",
        f"| 1. Unseen-configuration anomaly (S1 window AUROC) | {f3(ev['axis1_unseen_configuration_anomaly']['ligra_auroc'])} (FPR@TPR90 {f3(ev['axis1_unseen_configuration_anomaly']['ligra_fpr90'])}) | {ev['axis1_unseen_configuration_anomaly']['best_structured_baseline']}: {f3(ev['axis1_unseen_configuration_anomaly']['baseline_auroc'])} (FPR@TPR90 {f3(ev['axis1_unseen_configuration_anomaly']['baseline_fpr90'])}) | +3 pts or −25% FPR | {axes['axis1_unseen_configuration_anomaly']} |",
        f"| 2. Sample efficiency (AUROC ALL, LiGRA@25% vs baseline@100%) | {f3(lig25)} | {best_m}: {f3(best100)} | within 2 pts | {axes['axis2_sample_efficiency']} |",
        f"| 3. Localization (top-1 / chain distance, all localizable families) | {f3(lig_top1)} / {f3(lig_dist)} | {bm}: {f3(b_top1)} / {f3(b_dist)} | +10 pts or −25% distance | {axes['axis3_localization']} |",
        f"| 4. Payload/context shift (mean S2,S4 window AUROC) | {f3(ev['axis4_payload_context_shift_robustness']['ligra_auroc'])} | {ev['axis4_payload_context_shift_robustness']['best_structured_baseline']}: {f3(ev['axis4_payload_context_shift_robustness']['baseline_auroc'])} | +3 pts or −25% FPR | {axes['axis4_payload_context_shift_robustness']} |",
        "",
        f"Axes won: **{n_axes}/4** (GO requires ≥3).  ",
        f"Gain across ≥2 families and ≥2 seeds (OOD): **{multi_family}** ({fam_wins}).  ",
        f"Frame-augmentation baseline does not fully erase the advantage: **{aug_not_erase}**.  ",
        f"Frame-reparameterization drift ratio (baseline/LiGRA): **{f3(drift_ratio)}** (gate ≥100×): **{frame_pass}**.  ",
        f"Healthy-fit rigidity check (PIVOT-C signal: LiGRA RMSE ratio S0 {f3(lig_r)} vs best baseline {best_r_m} {f3(best_r)}): worse by >10%: **{rigid}**.",
        "",
        "## Per-model summary (fraction 1.0, seed means; density variant = representation)",
        "",
        "| model | params | AUROC S0 | AUROC S1 | AUROC S2 | AUROC S3 | AUROC S4 | AUROC OOD | event AUROC ALL | FPR@TPR90 ALL | top-1 loc ALL (pattern / argmax) | RMSE ratio S0 | RMSE ratio OOD | frame drift (median rel.) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for model in ["ligra", "chain_gnn", "chain_gnn_aug", "rnea_gru", "rnea_mlp", "rnea_only", "ligra_free_output", "ligra_mlp_encoder", "ligra_unshared", "gru_no_rnea"]:
        m = metrics.get(model)
        if not m:
            continue
        lines.append(f"| {model} | {m.get('n_params', '')} | {f3(m.get('auroc_S0'))} | {f3(m.get('auroc_S1'))} | {f3(m.get('auroc_S2'))} | {f3(m.get('auroc_S3'))} | {f3(m.get('auroc_S4'))} | {f3(m.get('auroc_OOD'))} | {f3(m.get('event_auroc_ALL'))} | {f3(m.get('fpr90_ALL'))} | {f3(m.get('loc_top1_ALL'))} / {f3(m.get('loc_top1_ALL_argmax'))} | {f3(m.get('rmse_ratio_S0'))} | {f3(m.get('rmse_ratio_OOD'))} | {f3(m.get('frame_drift_median'))} |")
    lines += ["", "## Sample-efficiency curves (window AUROC ALL by healthy training fraction)", "", "| model | 10% | 25% | 50% | 100% |", "|---|---|---|---|---|"]
    for model in ["ligra", "chain_gnn", "chain_gnn_aug", "rnea_gru", "rnea_mlp"]:
        m = metrics.get(model, {})
        lines.append(f"| {model} | {f3(m.get('auroc_ALL_frac0.10'))} | {f3(m.get('auroc_ALL_frac0.25'))} | {f3(m.get('auroc_ALL_frac0.50'))} | {f3(m.get('auroc_ALL_frac1.00'))} |")
    # per-family OOD table
    lines += ["", "## Per-family OOD window AUROC (fraction 1.0, seed means)", ""]
    fams = sorted({f for m in metrics.values() for f in m.get("auroc_OOD_by_family_seed", {})})
    if fams:
        lines.append("| model | " + " | ".join(fams) + " |")
        lines.append("|---|" + "---|" * len(fams))
        for model in ["ligra", "chain_gnn", "chain_gnn_aug", "rnea_gru", "rnea_mlp", "rnea_only"]:
            m = metrics.get(model, {}).get("auroc_OOD_by_family_seed", {})
            if m:
                lines.append(f"| {model} | " + " | ".join(f3(float(np.mean(list(m.get(f, {0: float('nan')}).values())))) for f in fams) + " |")
    lines += [
        "",
        "## Interpretation limits and prohibited claims (kept)",
        "",
        "- Exact gauge covariance was verified (R0/T1–T3); it is an implementation contract, **not** evidence of fault-detection value on its own.",
        "- Healthy and faulty samples obey the same covariance law; gauge-equivariance error is never used as a fault score.",
        "- Internal 6-D messages are latent wrench-like messages; no physical-wrench identification is claimed.",
        "- Cross-configuration results are empirical (T4); per-family shifts are empirical (T5).",
        "- Healthy OOD alarm rates (stage1r_ood_detection.csv) are false alarms, not detections.",
        "- The Stage 1 strict-certificate NO-GO was not used as evidence here.",
        "",
        "## Files",
        "",
        "stage1r_geometry_summary.csv, stage1r_healthy_prediction.csv, stage1r_sample_efficiency.csv, stage1r_frame_invariance.csv, "
        "stage1r_ood_detection.csv, stage1r_event_detection.csv, stage1r_localization.csv, stage1r_fewshot_attribution.csv, "
        "stage1r_latency_and_size.csv, stage1r_ablation_summary.csv, stage1r_claim_ledger.csv, stage1r_decision_evidence.json, stage1r_run_manifest.json",
    ]
    memo = "\n".join(lines) + "\n"
    (layout.results / "stage1r_decision_memo.md").write_text(memo, encoding="utf-8")
    (layout.sub("decision") / "stage1r_decision_memo.md").write_text(memo, encoding="utf-8")
    return decision
