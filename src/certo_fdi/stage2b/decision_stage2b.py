"""Pre-registered Stage 2B decision rules (kickoff contract 07_DECISION_RULES.md).

Committed in the first Stage 2B commit, **before any Stage 2B metric exists**, and not edited
afterwards to rescue an outcome. It is a pure function of an evidence dictionary and the
thresholds in ``configs/stage2b_contact_loadpath.yaml::decision``; every condition is reported
with its truth value and the numbers that produced it.

Allowed terminal states::

    GO_CONTACT_LOADPATH_MONITOR
    PIVOT_SUPPORT_ONLY_LOCALIZER
    PIVOT_LOADPATH_LOCALIZATION_ONLY
    PIVOT_SEQUENTIAL_DETECTION_ONLY
    PIVOT_CONTEXT_CALIBRATION_ONLY
    NO_GO_CONTACT_PRODUCT
    BLOCKED

Evaluation order (deterministic, declared in advance)::

    BLOCKED                              (§1 integrity gates -- never a scientific NO-GO)
      > GO_CONTACT_LOADPATH_MONITOR      (§3, every condition)
      > PIVOT_SUPPORT_ONLY_LOCALIZER     (§4)
      > PIVOT_LOADPATH_LOCALIZATION_ONLY (§5)
      > PIVOT_SEQUENTIAL_DETECTION_ONLY  (§6)
      > PIVOT_CONTEXT_CALIBRATION_ONLY   (§7)
      > NO_GO_CONTACT_PRODUCT            (§8, needs >= 2 conditions and H160 complete)
      > PIVOT_CONTEXT_CALIBRATION_ONLY / NO_GO fallback

Why this order. §1 is explicitly *not* a scientific verdict, so it dominates. §3 is the only
full-product state. §4 is a **naming/attribution** refinement of a passing localizer, so it is
checked before the partial-failure pivots -- a support-only method that meets the localization
bar is still a working localizer, it just may not be called Cartesian geometry. §5 and §6 are
the two complementary half-products (localization works / detection works); §5 precedes §6
because the Stage 2A evidence already showed localization as the strong axis, so a run that
satisfies both partial descriptions is reported by its stronger half. §7 is the weakest
positive claim. §8 requires two independent failure conditions *and* a completed H160 arm, so
it can never fire merely because a run was cut short -- that case falls through to the
calibration pivot or to the explicit default.

The thresholds are project gates, not mathematical theorems. Raw results are retained in full;
post-hoc threshold changes are forbidden.
"""

from __future__ import annotations

from typing import Any

DECISION_VOCABULARY = (
    "GO_CONTACT_LOADPATH_MONITOR",
    "PIVOT_SUPPORT_ONLY_LOCALIZER",
    "PIVOT_LOADPATH_LOCALIZATION_ONLY",
    "PIVOT_SEQUENTIAL_DETECTION_ONLY",
    "PIVOT_CONTEXT_CALIBRATION_ONLY",
    "NO_GO_CONTACT_PRODUCT",
    "BLOCKED",
)

# §1 integrity gates. Each is a boolean the evidence builder must supply; True means "violated".
INTEGRITY_GATES = (
    "stage2a_package_or_dataset_hash_mismatch",
    "baseline_reproduction_outside_tolerance",
    "final_test_episodes_modified_or_used_for_selection",
    "encoder_or_detector_leakage_found",
    "loadpath_controls_not_rank_or_support_matched",
    "window_level_bootstrap_used",
    "pr_history_rewritten_or_merged",
)


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v


def _finite(x: Any) -> bool:
    v = _f(x)
    return v == v and abs(v) != float("inf")


def _ge(x: Any, thr: Any) -> bool:
    return _finite(x) and _f(x) >= _f(thr)


def _le(x: Any, thr: Any) -> bool:
    return _finite(x) and _f(x) <= _f(thr)


# --------------------------------------------------------------------------- §1
def evaluate_integrity(ev: dict) -> dict:
    g = ev.get("integrity", {})
    fired = {k: bool(g.get(k, False)) for k in INTEGRITY_GATES}
    reasons = [k for k, v in fired.items() if v]
    reasons += list(ev.get("blocked", {}).get("reasons", []))
    return {"gates": fired, "any": bool(reasons), "reasons": reasons}


# --------------------------------------------------------------------------- §3
def evaluate_go(ev: dict, thr: dict) -> dict:
    d = ev.get("detection", {})
    l = ev.get("localization", {})
    s = ev.get("selective", {})
    i = ev.get("evidence_integrity", {})
    conds = {
        "d1_event_tpr": _ge(d.get("event_tpr"), thr["event_tpr_min"]),
        "d2_false_alarms_per_hour": _le(d.get("false_alarms_per_hour"), thr["false_alarms_per_hour_max"]),
        "d3_healthy_ood_id_ratio": _le(d.get("healthy_ood_id_ratio"), thr["healthy_ood_id_ratio_max"]),
        "d4_median_delay": _le(d.get("median_delay_s"), thr["median_delay_s_max"]),
        "d5_p95_delay": _le(d.get("p95_delay_s"), thr["p95_delay_s_max"]),
        "d6_event_f1": _ge(d.get("event_f1"), thr["event_f1_min"]),
        "l1_top1": _ge(l.get("episode_top1"), thr["localization_top1_min"]),
        "l2_chain_distance": _le(l.get("mean_chain_distance"), thr["localization_chain_distance_max"]),
        "l3_links_recall": int(l.get("n_links_recall_ge_040", 0)) >= int(thr["min_links_recall_ge_040"]),
        "l4_selective": (_ge(s.get("coverage"), thr["selective_coverage_min"])
                         and _ge(s.get("selective_top1"), thr["selective_top1_min"])
                         and _le(s.get("selective_chain_distance"), thr["selective_chain_distance_max"])),
        "l5_reject_reduces_error": bool(s.get("reject_reduces_error", False)) if thr.get("reject_must_reduce_error", True) else True,
        "e1_not_favored_by_rank_alone": bool(i.get("not_favored_by_rank_alone", False)) if thr.get("not_favored_by_rank_alone", True) else True,
        "e2_stable_over_seeds": int(i.get("n_seeds_improvement_stable", 0)) >= int(thr["stable_over_seeds_min"]),
        "e3_calibration_without_fault_test": bool(i.get("calibration_selected_without_fault_test", False)),
    }
    return {"conditions": conds, "pass": all(conds.values())}


# --------------------------------------------------------------------------- §4
def evaluate_pivot_support_only(ev: dict, thr: dict, go: dict) -> dict:
    c = ev.get("loadpath", {})
    l = ev.get("localization", {})
    within = (_le(abs(_f(c.get("support_minus_aligned_auroc"), 9e9)), thr["auroc_within"])
              and _le(abs(_f(c.get("support_minus_aligned_top1"), 9e9)), thr["top1_within"]))
    dominates = bool(c.get("support_dominates_aligned_after_rank_correction", False))
    meets_abs = bool(l.get("meets_stage2b_localization_thresholds", False))
    no_cartesian = not bool(c.get("cartesian_geometry_claim_supported", False))
    conds = {
        "within_or_dominates": bool(within or dominates),
        "meets_absolute_localization_thresholds": bool(meets_abs),
        "no_supportable_cartesian_geometry_claim": bool(no_cartesian),
    }
    return {"conditions": conds, "pass": all(conds.values())}


# --------------------------------------------------------------------------- §5
def evaluate_pivot_localization_only(ev: dict, thr: dict, go: dict) -> dict:
    gc = go["conditions"]
    loc_ok = all(gc[k] for k in ("l1_top1", "l2_chain_distance", "l3_links_recall", "l4_selective", "l5_reject_reduces_error"))
    det_fail = not all(gc[k] for k in ("d1_event_tpr", "d2_false_alarms_per_hour", "d3_healthy_ood_id_ratio"))
    return {"conditions": {"localization_and_rejection_pass": bool(loc_ok), "detector_fails_a_required_condition": bool(det_fail)},
            "pass": bool(loc_ok and det_fail)}


# --------------------------------------------------------------------------- §6
def evaluate_pivot_sequential_only(ev: dict, thr: dict, go: dict) -> dict:
    gc = go["conditions"]
    det_ok = all(gc[k] for k in ("d1_event_tpr", "d2_false_alarms_per_hour", "d3_healthy_ood_id_ratio", "d4_median_delay", "d5_p95_delay"))
    l = ev.get("localization", {})
    s = ev.get("selective", {})
    loc_fail = (not _ge(l.get("episode_top1"), thr["localization_top1_below"])) or (not bool(s.get("reject_reduces_error", False)))
    return {"conditions": {"detection_and_sequential_pass": bool(det_ok), "localization_below_bar_or_selective_no_gain": bool(loc_fail)},
            "pass": bool(det_ok and loc_fail)}


# --------------------------------------------------------------------------- §7
def evaluate_pivot_context_calibration_only(ev: dict, thr: dict) -> dict:
    d = ev.get("detection", {})
    c = ev.get("loadpath", {})
    l = ev.get("localization", {})
    conds = {
        "false_alarm_reduction_at_least_10x": _ge(d.get("false_alarm_reduction_factor"), thr["false_alarm_reduction_factor_min"]),
        "healthy_ood_id_ratio_ok": _le(d.get("healthy_ood_id_ratio"), thr["healthy_ood_id_ratio_max"]),
        "localization_below_product_thresholds": not bool(l.get("meets_stage2b_localization_thresholds", False)),
        "loadpath_controls_add_no_reliable_value": bool(c.get("no_reliable_loadpath_value", False)),
    }
    return {"conditions": conds, "pass": all(conds.values())}


# --------------------------------------------------------------------------- §8
def evaluate_no_go(ev: dict, thr: dict) -> dict:
    d = ev.get("detection", {})
    l = ev.get("localization", {})
    s = ev.get("selective", {})
    c = ev.get("loadpath", {})
    h = ev.get("healthy_expansion", {})
    conds = {
        "n1_false_alarms_above": _finite(d.get("false_alarms_per_hour")) and _f(d.get("false_alarms_per_hour")) > _f(thr["false_alarms_per_hour_above"]),
        "n2_event_tpr_below": _finite(d.get("event_tpr")) and _f(d.get("event_tpr")) < _f(thr["event_tpr_below"]),
        "n3_top1_below": _finite(l.get("episode_top1")) and _f(l.get("episode_top1")) < _f(thr["localization_top1_below"]),
        "n4_selective_never_helps": bool(s.get("selective_never_reduces_error_in_coverage_band", False)),
        "n5_no_stable_loadpath_gain": bool(c.get("no_stable_gain_over_counterfactual", False)),
        "n6_healthy_curve_unstable": bool(h.get("unstable_or_non_reproducible", False)),
    }
    n = sum(conds.values())
    complete = bool(h.get("h160_complete", False)) and not evaluate_integrity(ev)["any"]
    return {"conditions": conds, "n_fired": int(n), "h160_complete_and_integrity_ok": complete,
            "pass": bool(complete and n >= int(thr.get("n_conditions_required", 2)))}


# --------------------------------------------------------------------------- driver
def decide(evidence: dict, decision_cfg: dict) -> dict:
    integrity = evaluate_integrity(evidence)
    go = evaluate_go(evidence, decision_cfg["go"])
    p_support = evaluate_pivot_support_only(evidence, decision_cfg["pivot_support_only"], go)
    p_loc = evaluate_pivot_localization_only(evidence, decision_cfg["pivot_sequential_detection_only"], go)
    p_seq = evaluate_pivot_sequential_only(evidence, decision_cfg["pivot_sequential_detection_only"], go)
    p_cal = evaluate_pivot_context_calibration_only(evidence, decision_cfg["pivot_context_calibration_only"])
    no_go = evaluate_no_go(evidence, decision_cfg["no_go_after_h160"])

    if integrity["any"]:
        decision, reasons = "BLOCKED", integrity["reasons"]
    elif go["pass"]:
        decision, reasons = "GO_CONTACT_LOADPATH_MONITOR", ["every §3 condition holds"]
    elif p_support["pass"]:
        decision, reasons = "PIVOT_SUPPORT_ONLY_LOCALIZER", [
            "a support-only / rank-matched control matches the time-aligned Jacobian and meets the "
            "localization thresholds; the method must be described as serial-chain load-path "
            "localization, not Jacobian geometry"]
    elif p_loc["pass"]:
        decision, reasons = "PIVOT_LOADPATH_LOCALIZATION_ONLY", [
            "localization and rejection pass; the detector fails a required condition -- the product is an "
            "alarm-triggered contact-link localizer, not an autonomous monitor"]
    elif p_seq["pass"]:
        decision, reasons = "PIVOT_SEQUENTIAL_DETECTION_ONLY", [
            "detection and sequential monitoring pass; localization stays below the bar or selective "
            "localization does not reduce error"]
    elif p_cal["pass"]:
        decision, reasons = "PIVOT_CONTEXT_CALIBRATION_ONLY", [
            "context/sequential calibration cuts false alarms by >=10x with an acceptable OOD/ID ratio, but "
            "contact localization stays below product thresholds and the load-path controls add no reliable value"]
    elif no_go["pass"]:
        decision = "NO_GO_CONTACT_PRODUCT"
        reasons = [k for k, v in no_go["conditions"].items() if v]
    else:
        decision = "NO_GO_CONTACT_PRODUCT"
        reasons = ["no §3-§7 condition set is satisfied and §8 could not be evaluated as a two-condition "
                   "failure (default terminal state)"]

    return {
        "decision": decision,
        "decision_vocabulary": list(DECISION_VOCABULARY),
        "reasons": reasons,
        "integrity": integrity,
        "go": go,
        "pivot_support_only_localizer": p_support,
        "pivot_loadpath_localization_only": p_loc,
        "pivot_sequential_detection_only": p_seq,
        "pivot_context_calibration_only": p_cal,
        "no_go_contact_product": no_go,
        "evaluation_order": ("BLOCKED > GO_CONTACT_LOADPATH_MONITOR > PIVOT_SUPPORT_ONLY_LOCALIZER > "
                             "PIVOT_LOADPATH_LOCALIZATION_ONLY > PIVOT_SEQUENTIAL_DETECTION_ONLY > "
                             "PIVOT_CONTEXT_CALIBRATION_ONLY > NO_GO_CONTACT_PRODUCT(>=2 conditions) > "
                             "NO_GO_CONTACT_PRODUCT(default)"),
        "thresholds": decision_cfg,
        "note": ("Project decision gates, not theorems. Raw results are retained in full; post-hoc threshold "
                 "changes are forbidden. §1 integrity failures are BLOCKED, never a scientific NO-GO."),
    }


def reproduction_gate(observed: dict, reference: dict, tolerance: float) -> dict:
    """Phase 0 gate: every frozen reference metric must reproduce within ``tolerance`` relative."""
    rows, worst = [], 0.0
    for key, ref in reference.items():
        obs = observed.get(key)
        if obs is None or not _finite(obs) or not _finite(ref):
            rows.append({"metric": key, "reference": ref, "observed": obs, "relative_deviation": None,
                         "within_tolerance": None, "status": "MISSING"})
            continue
        rel = abs(_f(obs) - _f(ref)) / max(abs(_f(ref)), 1e-12)
        worst = max(worst, rel)
        rows.append({"metric": key, "reference": _f(ref), "observed": _f(obs), "relative_deviation": rel,
                     "within_tolerance": bool(rel <= tolerance), "status": "OK" if rel <= tolerance else "DEVIATION"})
    passed = bool(rows) and all(r["within_tolerance"] is True for r in rows)
    return {"rows": rows, "worst_relative_deviation": worst, "tolerance": tolerance,
            "gate": "PASS" if passed else "FAIL"}
