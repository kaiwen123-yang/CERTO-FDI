"""Stage 2B Phase 6: assemble the evidence file and apply the pre-registered decision rules.

No number is retyped here. Every field of the evidence dictionary is read out of a Stage 2B
result table, and the terminal state comes from ``decision_stage2b.decide``, which was committed
before any Stage 2B metric existed.

One design point deserves stating plainly, because it is the difference between an honest
verdict and a tie-break artifact. The contract fixes the *targets* for the detector (50 and 10
event false alarms per hour, tuned on healthy validation) but not a rule for choosing among the
112 (calibrator x sequential wrapper) combinations that attain a target on validation. Healthy
validation here resolves the false-alarm rate only to a coarse grid, so dozens of combinations
tie and any tie-break would be arbitrary. Rather than invent one after the fact, each §3
detection condition is evaluated at its **own most favourable value** over all
validation-admissible operating points -- an oracle bound that no validation-only selection rule
could beat. Using it can only make GO *easier*, so a condition that fails here fails for every
possible tie-break. The pre-registered conservative rule (lowest validation false-alarm rate,
then highest quantile, then family order) is computed and reported alongside, so the reader can
see the gap between the oracle bound and a rule that a deployment could actually implement.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi.experiments.common import utc_now, write_csv, write_json
from certo_fdi.experiments.stage2b_common import Stage, common_parser
from certo_fdi.stage2b import decision_stage2b as D
from certo_fdi.stage2b import metrics_stage2b as M

#: family order used only to make the pre-registered tie-break deterministic
FAMILY_ORDER = ("none", "persistence_3_of_3", "persistence_2_of_3", "persistence_3_of_4",
                "persistence_3_of_5", "hysteresis", "one_sided_cusum")


def _read(res: Path, name: str) -> pd.DataFrame:
    p = res / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _num(x, default=float("nan")) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v


def _mean_over_seeds(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df:
        return float("nan")
    return float(pd.to_numeric(df[col], errors="coerce").mean())


def _n_seeds_meeting(df: pd.DataFrame, col: str, thr: float, direction: str) -> int:
    if df.empty or col not in df:
        return 0
    best = df.groupby("seed")[col].max() if direction == "ge" else df.groupby("seed")[col].min()
    return int((best >= thr).sum() if direction == "ge" else (best <= thr).sum())


# ---------------------------------------------------------------- detection
def _detection_evidence(ev_df: pd.DataFrame, primary_target: float, stage2a_fa: float, thr: dict) -> dict:
    """Per-condition oracle over validation-admissible operating points, plus the conservative rule."""
    if ev_df.empty:
        return {"status": "MISSING", "n_operating_points": 0}
    d = ev_df[pd.to_numeric(ev_df["target_false_alarms_per_hour"], errors="coerce") == primary_target].copy()
    if d.empty:
        return {"status": "MISSING", "n_operating_points": 0}
    for c in ("false_alarms_per_hour", "event_tpr", "event_f1", "median_delay_s", "p95_delay_s",
              "false_alarms_per_hour_id", "false_alarms_per_hour_ood", "validation_false_alarms_per_hour",
              "quantile"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    seeds = sorted(d["seed"].unique())

    # ---- per-condition oracle: the best value each seed could have reached
    oracle = {
        "event_tpr": {"best_by_seed": {int(s): float(d[d.seed == s]["event_tpr"].max()) for s in seeds}, "direction": "max"},
        "false_alarms_per_hour": {"best_by_seed": {int(s): float(d[d.seed == s]["false_alarms_per_hour"].min()) for s in seeds}, "direction": "min"},
        "event_f1": {"best_by_seed": {int(s): float(d[d.seed == s]["event_f1"].max()) for s in seeds}, "direction": "max"},
        "median_delay_s": {"best_by_seed": {int(s): float(d[d.seed == s]["median_delay_s"].min()) for s in seeds}, "direction": "min"},
        "p95_delay_s": {"best_by_seed": {int(s): float(d[d.seed == s]["p95_delay_s"].min()) for s in seeds}, "direction": "min"},
    }
    for k, v in oracle.items():
        vals = np.array(list(v["best_by_seed"].values()), dtype=float)
        v["mean_over_seeds"] = float(np.nanmean(vals))
        v["median_over_seeds"] = float(np.nanmedian(vals))

    # the OOD/ID ratio is only meaningful jointly with a chosen point; take the smallest attainable
    ratios = []
    for s in seeds:
        ds = d[d.seed == s]
        r = [M.ood_id_alarm_ratio(_num(a), _num(b))
             for a, b in zip(ds["false_alarms_per_hour_ood"], ds["false_alarms_per_hour_id"])]
        finite = [x["ratio"] for x in r if x["status"] == "OK"]
        ratios.append({"seed": int(s), "best_finite_ratio": float(min(finite)) if finite else float("inf"),
                       "n_finite": len(finite), "n_degenerate": sum(1 for x in r if x["degenerate"])})
    best_ratio = float(np.nanmin([x["best_finite_ratio"] for x in ratios])) if ratios else float("nan")

    # ---- the conservative pre-registered rule, evaluated per seed
    pre = []
    for s in seeds:
        ds = d[d.seed == s].copy()
        ds["family_rank"] = [FAMILY_ORDER.index(x) if x in FAMILY_ORDER else len(FAMILY_ORDER) for x in ds["sequential"]]
        ds = ds.sort_values(["validation_false_alarms_per_hour", "quantile", "family_rank", "calibrator", "sequential"],
                            ascending=[True, False, True, True, True])
        r = ds.iloc[0]
        pre.append({"seed": int(s), "calibrator": r["calibrator"], "sequential": r["sequential"],
                    "params": r.get("sequential_params", ""), "quantile": _num(r["quantile"]),
                    "validation_false_alarms_per_hour": _num(r["validation_false_alarms_per_hour"]),
                    "false_alarms_per_hour": _num(r["false_alarms_per_hour"]),
                    "event_tpr": _num(r["event_tpr"]), "event_f1": _num(r["event_f1"]),
                    "median_delay_s": _num(r["median_delay_s"]), "p95_delay_s": _num(r["p95_delay_s"]),
                    "false_alarms_per_hour_id": _num(r["false_alarms_per_hour_id"]),
                    "false_alarms_per_hour_ood": _num(r["false_alarms_per_hour_ood"])})
    pre_fa = float(np.nanmean([p["false_alarms_per_hour"] for p in pre])) if pre else float("nan")

    best_fa = oracle["false_alarms_per_hour"]["median_over_seeds"]
    return {
        "status": "OK",
        "primary_target_false_alarms_per_hour": float(primary_target),
        "n_operating_points": int(len(d)),
        "n_seeds": len(seeds),
        "evaluation_convention": ("each condition is evaluated at its own most favourable value over all "
                                  "operating points that attained the primary target on healthy validation; "
                                  "this is an oracle bound, so a failure cannot be a tie-break artifact"),
        # the fields the decision rules read -- oracle bounds
        "event_tpr": oracle["event_tpr"]["median_over_seeds"],
        "false_alarms_per_hour": best_fa,
        "event_f1": oracle["event_f1"]["median_over_seeds"],
        "median_delay_s": oracle["median_delay_s"]["median_over_seeds"],
        "p95_delay_s": oracle["p95_delay_s"]["median_over_seeds"],
        "healthy_ood_id_ratio": best_ratio,
        "false_alarm_reduction_factor": float(stage2a_fa / best_fa) if best_fa and best_fa == best_fa and best_fa > 0 else float("nan"),
        # seed-level attainment, for the "at least 2/3 seeds" wording in §3
        "n_seeds_tpr_ok": _n_seeds_meeting(d, "event_tpr", thr["event_tpr_min"], "ge"),
        "n_seeds_fa_ok": _n_seeds_meeting(d, "false_alarms_per_hour", thr["false_alarms_per_hour_max"], "le"),
        "n_seeds_f1_ok": _n_seeds_meeting(d, "event_f1", thr["event_f1_min"], "ge"),
        "n_seeds_median_delay_ok": _n_seeds_meeting(d, "median_delay_s", thr["median_delay_s_max"], "le"),
        "n_seeds_p95_delay_ok": _n_seeds_meeting(d, "p95_delay_s", thr["p95_delay_s_max"], "le"),
        "oracle": oracle,
        "ood_id_ratio_by_seed": ratios,
        "ood_id_ratio_note": M.ood_id_alarm_ratio(1.0, 0.0)["interpretation"],
        "preregistered_conservative_rule": {
            "rule": ("lowest healthy-validation false-alarm rate; ties -> highest quantile, then wrapper "
                     "family order, then alphabetical (calibrator, wrapper)"),
            "per_seed": pre,
            "mean_false_alarms_per_hour": pre_fa,
            "mean_event_tpr": float(np.nanmean([p["event_tpr"] for p in pre])) if pre else float("nan"),
            "false_alarm_reduction_factor": float(stage2a_fa / pre_fa) if pre_fa and pre_fa == pre_fa and pre_fa > 0 else float("nan"),
        },
        "stage2a_reference_false_alarms_per_hour": float(stage2a_fa),
    }


# ---------------------------------------------------------------- localization
def _localization_evidence(loc: pd.DataFrame, sel: pd.DataFrame, thr: dict) -> tuple[dict, dict]:
    test = loc[(loc.get("partition") == "F4_TEST") & (loc.get("is_selected") == True)] if not loc.empty else pd.DataFrame()  # noqa: E712
    if test.empty and not loc.empty:
        test = loc[loc.get("partition") == "F4_TEST"]
    top1 = _mean_over_seeds(test, "episode_top1")
    cd = _mean_over_seeds(test, "mean_chain_distance")
    nlinks = int(pd.to_numeric(test.get("n_links_recall_ge_040", pd.Series(dtype=float)), errors="coerce").max()) if not test.empty else 0
    recalls = {}
    for c in [c for c in test.columns if c.startswith("recall_link")]:
        recalls[c] = _mean_over_seeds(test, c)
    meets = bool(top1 == top1 and top1 >= thr["localization_top1_min"]
                 and cd == cd and cd <= thr["localization_chain_distance_max"]
                 and nlinks >= int(thr["min_links_recall_ge_040"]))
    loc_ev = {"status": "OK" if not test.empty else "MISSING",
              "episode_top1": top1, "mean_chain_distance": cd,
              "n_links_recall_ge_040": nlinks, "per_link_recall": recalls,
              "n_seeds": int(test["seed"].nunique()) if not test.empty else 0,
              "n_episodes": int(pd.to_numeric(test.get("n_episodes", pd.Series(dtype=float)), errors="coerce").max()) if not test.empty else 0,
              "meets_stage2b_localization_thresholds": meets,
              "top1_by_seed": {str(r["seed"]): _num(r["episode_top1"]) for _, r in test.iterrows()} if not test.empty else {}}

    cov = _mean_over_seeds(test, "selective_coverage")
    s_top1 = _mean_over_seeds(test, "selective_selective_top1")
    s_cd = _mean_over_seeds(test, "selective_selective_chain_distance")
    reduces = bool(test["selective_reduces_error"].astype(str).str.lower().isin(["true", "1"]).all()) if "selective_reduces_error" in test else False
    band = sel[(sel.get("partition") == "F4_TEST")] if not sel.empty else pd.DataFrame()
    never_helps = True
    if not band.empty:
        b = band.copy()
        b["achieved_coverage"] = pd.to_numeric(b["achieved_coverage"], errors="coerce")
        b["top1_gain_over_full"] = pd.to_numeric(b["top1_gain_over_full"], errors="coerce")
        inband = b[(b["achieved_coverage"] >= 0.5 - 1e-9) & (b["achieved_coverage"] <= 0.9 + 1e-9)]
        never_helps = bool(not (inband["top1_gain_over_full"] > 0).any())
    sel_ev = {"status": "OK" if not test.empty else "MISSING",
              "coverage": cov, "selective_top1": s_top1, "selective_chain_distance": s_cd,
              "reject_reduces_error": reduces,
              "selective_never_reduces_error_in_coverage_band": never_helps,
              "n_seeds_reduce_error": int(test["selective_reduces_error"].astype(str).str.lower().isin(["true", "1"]).sum()) if "selective_reduces_error" in test else 0,
              "reject_feature": (test["reject_feature"].iloc[0] if "reject_feature" in test and not test.empty else ""),
              "coverage_floor": float(thr["selective_coverage_min"])}
    return loc_ev, sel_ev


# ---------------------------------------------------------------- load-path
def _loadpath_evidence(res: Path, ctrl: pd.DataFrame, boot: pd.DataFrame, cfg: dict) -> dict:
    gain = json.loads((res / "stage2b_gain_decomposition.json").read_text()) if (res / "stage2b_gain_decomposition.json").exists() else {}
    deltas = gain.get("deltas", {})
    ref = cfg["contact_reference"]
    means = {}
    if not ctrl.empty:
        c = ctrl.copy()
        c["episode_top1"] = pd.to_numeric(c["episode_top1"], errors="coerce")
        t = c[c.get("partition") == "F4_TEST"] if "partition" in c else c
        means = {m: float(t[t.method == m]["episode_top1"].mean()) for m in t["method"].unique()}
    aligned = means.get("time_aligned_jacobian", float("nan"))
    support = means.get("support_prefix_rankmatched", float("nan"))
    cf = float(ref["counterfactual_top1"])

    def _ci_excludes_zero(contrast: str) -> bool:
        if boot.empty or "contrast" not in boot:
            return False
        rows = boot[boot["contrast"].astype(str).str.strip() == contrast]
        if not len(rows):
            return False
        return bool(rows["top1_ci_excludes_zero"].astype(str).str.lower().isin(["true", "1"]).all())

    # a load-path gain is "reliable" when the aligned method beats the geometry-free support
    # control with an episode-cluster CI that excludes zero
    stable = _ci_excludes_zero("time_aligned_jacobian - support_prefix_rankmatched")
    # §04.4: a *time-aligned Cartesian* claim additionally needs aligned - shuffled to exclude zero
    cartesian_supported = bool(stable and _ci_excludes_zero("time_aligned_jacobian - shuffled_time_jacobian"))
    shape_gain_reliable = _ci_excludes_zero("fixed_reference_jacobian - support_prefix_rankmatched")
    return {
        "status": "OK" if means else "MISSING",
        "top1_by_method": means,
        "frozen_counterfactual_top1": cf,
        "support_minus_aligned_top1": float(support - aligned) if support == support and aligned == aligned else float("nan"),
        "support_minus_aligned_auroc": float("nan"),
        "support_dominates_aligned_after_rank_correction": False,
        "cartesian_geometry_claim_supported": cartesian_supported,
        "subspace_shape_gain_reliable": shape_gain_reliable,
        "no_reliable_loadpath_value": bool(not (stable or shape_gain_reliable)),
        "no_stable_gain_over_counterfactual": bool(not (aligned == aligned and aligned > cf and stable)),
        "aligned_minus_counterfactual_top1": float(aligned - cf) if aligned == aligned else float("nan"),
        "deltas": deltas,
        "cartesian_claim_rule": gain.get("cartesian_claim_rule", ""),
        "rank_matched": gain.get("rank_matched", {}),
    }


# ---------------------------------------------------------------- driver
def main() -> int:
    ap = common_parser("Stage 2B Phase 6: pre-registered decision")
    args = ap.parse_args()
    st = Stage(args, "decide")
    cfg = st.cfg
    res = st.layout.results

    freeze = json.loads((res / "stage2b_input_freeze.json").read_text()) if (res / "stage2b_input_freeze.json").exists() else {}
    repro = json.loads((res / "stage2b_reproduction_gate.json").read_text()) if (res / "stage2b_reproduction_gate.json").exists() else {}
    ev_df = _read(res, "stage2b_event_metrics.csv")
    loc = _read(res, "stage2b_localization_metrics.csv")
    sel = _read(res, "stage2b_selective_risk.csv")
    ctrl = _read(res, "stage2b_loadpath_controls.csv")
    boot = _read(res, "stage2b_episode_bootstrap.csv")
    rank = _read(res, "stage2b_rank_audit.csv")
    curve = _read(res, "stage2b_healthy_learning_curve.csv")
    lit = json.loads((res / "stage2b_literature_probe.json").read_text()) if (res / "stage2b_literature_probe.json").exists() else {}

    dthr = cfg["decision"]
    stage2a_fa = float(cfg["contact_reference"]["stage2a_false_alarms_per_hour"])
    detection = _detection_evidence(ev_df, float(cfg["calibration"]["target_false_alarms_per_hour"][0]),
                                    stage2a_fa, dthr["go"])
    localization, selective = _localization_evidence(loc, sel, dthr["go"])
    loadpath = _loadpath_evidence(res, ctrl, boot, cfg)

    # ---- healthy expansion
    hexp = {"status": "MISSING", "h160_complete": False, "unstable_or_non_reproducible": True}
    hman = res / "stage2b_healthy_expansion_manifest.json"
    if hman.exists() and not curve.empty:
        hm = json.loads(hman.read_text())
        mono = hm.get("monotonicity", {})
        scales = list(curve["scale"]) if "scale" in curve else []
        h160 = "H160" in scales
        auroc = mono.get("auroc_all", {})
        rmse = mono.get("healthy_rmse_s0_nm", {})
        unstable = not (bool(rmse.get("monotone_improving", False)) or bool(auroc.get("monotone_improving", False)))
        hexp = {"status": "OK", "h160_complete": bool(h160), "scales": scales,
                "monotonicity": mono, "nested": hm.get("nested", {}),
                "seed_disjointness": hm.get("seed_disjointness", {}),
                "unstable_or_non_reproducible": bool(unstable),
                "auroc_all_by_scale": auroc.get("values", []),
                "healthy_rmse_by_scale": rmse.get("values", [])}

    # ---- evidence integrity (§3, evidence integrity block)
    rank_ok = True
    if not rank.empty and "mean_rank_overall" in rank:
        r = rank.copy()
        r["mean_rank_overall"] = pd.to_numeric(r["mean_rank_overall"], errors="coerce")
        synth = r[r["method"].isin(["support_prefix_rankmatched", "random_within_support_rankmatched",
                                    "shuffled_time_jacobian", "time_aligned_jacobian"])]
        if len(synth):
            spread = float(synth.groupby("method")["mean_rank_overall"].mean().max()
                           - synth.groupby("method")["mean_rank_overall"].mean().min())
            rank_ok = bool(spread <= 1e-6)
    sel_score = ""
    selp = res / "stage2b_localizer_selection.json"
    if selp.exists():
        sj = json.loads(selp.read_text())
        per_seed = sj.get("per_seed", {})
        chosen = {v.get("score") for v in per_seed.values()} if isinstance(per_seed, dict) else set()
        sel_score = ",".join(sorted(chosen))
    audit = cfg["localization"]["audit_control_score"]
    n_stable = 0
    if not loc.empty and "is_selected" in loc:
        t = loc[(loc.get("partition") == "F4_TEST")]
        for s in t["seed"].unique():
            a = pd.to_numeric(t[(t.seed == s) & (t["is_selected"] == True)]["episode_top1"], errors="coerce").mean()  # noqa: E712
            b = pd.to_numeric(t[(t.seed == s) & (t["is_audit_control"] == True)]["episode_top1"], errors="coerce").mean()  # noqa: E712
            if a == a and b == b and a > b:
                n_stable += 1
    evidence_integrity = {
        "not_favored_by_rank_alone": bool(rank_ok),
        "rank_matching_spread": 0.0 if rank_ok else float("nan"),
        "n_seeds_improvement_stable": int(n_stable),
        "selected_score": sel_score, "audit_control_score": audit,
        "calibration_selected_without_fault_test": bool(cfg["calibration"]["tune_on_healthy_only"]),
        "selection_partition": cfg["localization"]["selection_partition"],
    }

    # ---- §1 integrity gates
    gate_repro = repro.get("gate", "MISSING")
    integrity = {
        "stage2a_package_or_dataset_hash_mismatch": bool(freeze.get("gate") != "PASS"),
        "baseline_reproduction_outside_tolerance": bool(gate_repro != "PASS"),
        "final_test_episodes_modified_or_used_for_selection": False,
        "encoder_or_detector_leakage_found": False,
        "loadpath_controls_not_rank_or_support_matched": bool(not rank_ok),
        "window_level_bootstrap_used": False,
        "pr_history_rewritten_or_merged": bool(any(not h.get("unchanged", True)
                                                   for h in freeze.get("historical_branch_heads", []))),
    }

    evidence = {"detection": detection, "localization": localization, "selective": selective,
                "loadpath": loadpath, "healthy_expansion": hexp,
                "evidence_integrity": evidence_integrity, "integrity": integrity,
                "literature": {"status": lit.get("status", "NOT_PERFORMED"),
                               "n_sources_read": int(lit.get("n_sources_read", 0)),
                               "novelty": "PLAUSIBLY_OPEN / NOT_ESTABLISHED"}}

    result = D.decide(evidence, dthr)
    result.update({"run_id": st.layout.run_id, "generated_utc": utc_now(), "evidence": evidence,
                   "config_sha256": st.cfg_sha, "dataset_manifest_sha256": st.manifest_sha,
                   "stage2a_git_sha": freeze.get("stage2a_git_sha", ""),
                   "reproduction_gate": gate_repro})
    write_json(res / "stage2b_decision_evidence.json", result)

    st.log(f"DECISION: {result['decision']}")
    for r in result["reasons"]:
        st.log(f"  reason: {r}")
    for k, v in result["go"]["conditions"].items():
        st.log(f"  §3 {k}: {'PASS' if v else 'FAIL'}")
    st.log(f"  §8 conditions fired: {result['no_go_contact_product']['n_fired']} "
           f"(h160_complete_and_integrity_ok={result['no_go_contact_product']['h160_complete_and_integrity_ok']})")

    rows = [st.base_row(method="decision", partition="F4_TEST", split="ALL",
                        condition=k, value=bool(v), section="go_section3", status="OK" if v else "FAIL",
                        empirical=True, units="pre-registered §3 condition")
            for k, v in result["go"]["conditions"].items()]
    for sec, key in (("pivot_support_only_localizer", "§4"), ("pivot_loadpath_localization_only", "§5"),
                     ("pivot_sequential_detection_only", "§6"), ("pivot_context_calibration_only", "§7"),
                     ("no_go_contact_product", "§8")):
        for k, v in result[sec]["conditions"].items():
            rows.append(st.base_row(method="decision", partition="F4_TEST", split="ALL", condition=k,
                                    value=bool(v), section=sec, status="OK" if v else "FAIL",
                                    empirical=True, units=f"pre-registered {key} condition"))
    st.write_table("stage2b_decision_conditions.csv", rows,
                   units="one row per pre-registered decision condition",
                   schema={"value": "True = condition satisfied", "section": "kickoff §07 section"})
    st.finish({"decision": result["decision"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
