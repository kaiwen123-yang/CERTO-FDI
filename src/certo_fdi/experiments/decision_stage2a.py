"""Pre-registered Stage 2A decision rules (contract §8).

This module is committed **before** any Stage 2A model result exists and must not be edited
afterwards to rescue an outcome. It is a pure function of an evidence dictionary and the
thresholds in ``configs/stage2a_pathway_audit.yaml``; every condition is reported with its
truth value and the numbers that produced it.

Allowed terminal states::

    GO_JACOBIAN_PATHWAY_HEAD
    PIVOT_CONTACT_GEOMETRY_ONLY
    PIVOT_CALIBRATION_SEQUENTIAL
    PIVOT_COARSE_EQUIVALENCE_CLASSES
    NO_GO_JACOBIAN_PATHWAY_HEAD
    BLOCKED

Evaluation order (deterministic, declared in advance)::

    BLOCKED
      > NO_GO via an *integrity* trigger          (§8.5 t4, t6)
      > GO                                        (all six §8.1 conditions)
      > PIVOT_CONTACT_GEOMETRY_ONLY               (§8.2)
      > PIVOT_COARSE_EQUIVALENCE_CLASSES          (§8.4)
      > PIVOT_CALIBRATION_SEQUENTIAL              (§8.3)
      > NO_GO via a *performance* trigger         (§8.5 t1, t2, t3, t5)
      > NO_GO (default terminal state)

Why the §8.5 triggers are split. Read literally, "any §8.5 trigger => NO-GO" would make
``PIVOT_CALIBRATION_SEQUENTIAL`` unreachable: §8.3 fires exactly when "the geometry head does
not improve AUROC or localization", which is trigger t1. The pivots in §8.2-§8.4 are strictly
*more specific* refinements of that situation -- they add extra conditions on top of it and say
where the project should go next. They are therefore evaluated before the performance triggers.
The two *integrity* triggers are different in kind: t4 (the geometry only works with the truth
contact point) and t6 (the gain needs a fault-label-trained fuser) both say that an apparent
gain is not real, so nothing may rescue them -- not a pivot and not GO either. In consistent
evidence they cannot co-occur with GO (a deployed candidate-point head that produced the
§8.1 gains falsifies t4 by construction, and §8.1 c6 already forbids t6), but the precedence
is enforced explicitly rather than left to the evidence being self-consistent. This split was
fixed before any Stage 2A result existed; every trigger is reported regardless of which one
decides the outcome.

The thresholds are project decision thresholds, not mathematical theorems; the raw results
are always kept in full so a reviewer can re-derive any of them.
"""

from __future__ import annotations

from typing import Any

DECISION_VOCABULARY = (
    "GO_JACOBIAN_PATHWAY_HEAD",
    "PIVOT_CONTACT_GEOMETRY_ONLY",
    "PIVOT_CALIBRATION_SEQUENTIAL",
    "PIVOT_COARSE_EQUIVALENCE_CLASSES",
    "NO_GO_JACOBIAN_PATHWAY_HEAD",
    "BLOCKED",
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


def evaluate_go(ev: dict, thr: dict) -> dict:
    """§8.1 -- all six conditions must hold."""
    g = ev.get("geometry_gain", {})
    loc = ev.get("localization_gain", {})
    fa = ev.get("false_alarms", {})
    diag = ev.get("diagnosability", {})
    cov = ev.get("coverage", {})
    ctrl = ev.get("control", {})
    c1 = _finite(g.get("f4_auroc_gain_s1_s4_mean")) and _f(g.get("f4_auroc_gain_s1_s4_mean")) >= _f(thr["f4_auroc_gain_min"]) and int(g.get("f4_auroc_gain_seed_agreement", 0)) >= int(thr["f4_auroc_seed_agreement_min"])
    c2 = (_finite(loc.get("f4_top1_gain")) and _f(loc.get("f4_top1_gain")) >= _f(thr["f4_top1_gain_min"])) or (
        _finite(loc.get("f4_chain_distance_reduction")) and _f(loc.get("f4_chain_distance_reduction")) >= _f(thr["f4_chain_distance_reduction_min"])
    )
    c3 = _finite(fa.get("relative_worsening")) and _f(fa.get("relative_worsening")) <= _f(thr["false_alarm_relative_worsening_max"])
    c4 = bool(diag.get("best_abs_spearman_ci_excludes_zero", False)) and _f(diag.get("best_abs_spearman")) >= _f(thr["diagnosability_abs_spearman_min"])
    c5 = int(cov.get("n_contact_links_with_gain", 0)) >= int(thr["min_contact_links_or_strata"]) or int(cov.get("n_context_strata_with_gain", 0)) >= int(thr["min_contact_links_or_strata"])
    c6 = bool(ctrl.get("primary_detection_is_healthy_only", False)) and bool(ctrl.get("shuffled_control_does_not_reproduce_gain", False)) and not bool(ctrl.get("gain_requires_fault_label_fuser", True))
    conds = {
        "c1_f4_auroc_gain_and_seed_agreement": bool(c1),
        "c2_localization_gain": bool(c2),
        "c3_false_alarms_not_worse": bool(c3),
        "c4_diagnosability_correlation": bool(c4),
        "c5_covers_multiple_links_or_strata": bool(c5),
        "c6_not_explained_by_capacity_or_labels": bool(c6),
    }
    return {"conditions": conds, "pass": all(conds.values())}


def evaluate_no_go(ev: dict, thr: dict) -> dict:
    """§8.5 -- any single trigger is sufficient."""
    g = ev.get("geometry_gain", {})
    loc = ev.get("localization_gain", {})
    diag = ev.get("diagnosability", {})
    fa = ev.get("false_alarms", {})
    ab = ev.get("ablation_ordering", {})
    orc = ev.get("oracle", {})
    ctrl = ev.get("control", {})
    t1 = _finite(g.get("f4_auroc_gain_s1_s4_mean")) and _f(g.get("f4_auroc_gain_s1_s4_mean")) < _f(thr["f4_auroc_gain_below"]) and _finite(loc.get("f4_top1_gain")) and _f(loc.get("f4_top1_gain")) < _f(thr["f4_top1_gain_below"])
    t2 = _finite(diag.get("best_abs_spearman")) and _f(diag.get("best_abs_spearman")) < _f(thr["diagnosability_abs_spearman_below"])
    t3 = bool(ab.get("geometry_only_not_better_than_residual_only", False)) and bool(ab.get("chain_plus_geometry_not_better_than_residual_only", False))
    t4 = bool(orc.get("only_truth_point_oracle_works", False))
    t5 = _finite(fa.get("relative_worsening")) and _f(fa.get("relative_worsening")) > _f(thr["false_alarm_relative_worsening_above"])
    t6 = bool(ctrl.get("gain_requires_fault_label_fuser", False))
    trig = {
        "t1_no_detection_and_no_localization_gain": bool(t1),
        "t2_diagnosability_uncorrelated": bool(t2),
        "t3_geometry_never_beats_residual_only": bool(t3),
        "t4_only_oracle_contact_point_works": bool(t4),
        "t5_false_alarms_much_worse": bool(t5),
        "t6_gain_needs_fault_label_fuser": bool(t6),
    }
    integrity = ("t4_only_oracle_contact_point_works", "t6_gain_needs_fault_label_fuser")
    return {
        "triggers": trig,
        "any": any(trig.values()),
        "integrity_triggered": any(trig[k] for k in integrity),
        "performance_triggered": any(v for k, v in trig.items() if k not in integrity),
        "integrity_trigger_names": list(integrity),
    }


def evaluate_pivot_contact_only(ev: dict, thr: dict) -> dict:
    """§8.2 -- contact detection/localization improves, the other families do not."""
    g = ev.get("geometry_gain", {})
    loc = ev.get("localization_gain", {})
    fam = ev.get("other_families", {})
    contact_ok = (_finite(g.get("f4_auroc_gain_s1_s4_mean")) and _f(g.get("f4_auroc_gain_s1_s4_mean")) >= _f(thr["f4_auroc_gain_min"])) and (
        (_finite(loc.get("f4_top1_gain")) and _f(loc.get("f4_top1_gain")) >= _f(thr["f4_top1_gain_min"]))
        or (_finite(loc.get("f4_chain_distance_reduction")) and _f(loc.get("f4_chain_distance_reduction")) >= _f(thr["f4_chain_distance_reduction_min"]))
    )
    others = int(fam.get("n_families_improved", 0)) >= int(thr["other_family_min_improved"])
    conds = {"contact_improves": bool(contact_ok), "other_families_do_not_improve_stably": bool(not others)}
    return {"conditions": conds, "pass": conds["contact_improves"] and conds["other_families_do_not_improve_stably"]}


def evaluate_pivot_coarse(ev: dict, thr: dict) -> dict:
    """§8.4 -- fine localization/classification fails, coarse classes separate."""
    co = ev.get("coarse", {})
    loc = ev.get("localization_gain", {})
    conds = {
        "coarse_separable": _finite(co.get("balanced_accuracy_best")) and _f(co.get("balanced_accuracy_best")) >= _f(thr["coarse_balanced_accuracy_min"]),
        "coarse_beats_baseline": _finite(co.get("balanced_accuracy_gain_over_baseline")) and _f(co.get("balanced_accuracy_gain_over_baseline")) >= _f(thr["coarse_gain_over_baseline_min"]),
        "fine_localization_fails": _finite(loc.get("f4_top1_best")) and _f(loc.get("f4_top1_best")) <= _f(thr["fine_top1_max"]),
    }
    return {"conditions": conds, "pass": all(conds.values())}


def evaluate_pivot_calibration(ev: dict, thr: dict) -> dict:
    """§8.3 -- geometry does not help, but false alarms / context calibration dominate."""
    g = ev.get("geometry_gain", {})
    loc = ev.get("localization_gain", {})
    fa = ev.get("false_alarms", {})
    conds = {
        "geometry_does_not_help": (not _finite(g.get("f4_auroc_gain_s1_s4_mean")) or _f(g.get("f4_auroc_gain_s1_s4_mean")) < 0.02) and (not _finite(loc.get("f4_top1_gain")) or _f(loc.get("f4_top1_gain")) < 0.05),
        "false_alarm_rate_is_high": _finite(fa.get("baseline_false_alarms_per_hour")) and _f(fa.get("baseline_false_alarms_per_hour")) >= _f(thr["false_alarms_per_hour_min"]),
        "context_calibration_is_the_bottleneck": _finite(fa.get("healthy_ood_over_id_alarm_ratio")) and _f(fa.get("healthy_ood_over_id_alarm_ratio")) >= _f(thr["healthy_ood_alarm_ratio_min"]),
    }
    return {"conditions": conds, "pass": all(conds.values())}


def decide(evidence: dict, decision_cfg: dict) -> dict:
    """Return the frozen decision and the full condition trace."""
    blocked = evidence.get("blocked", {})
    go = evaluate_go(evidence, decision_cfg["go"])
    no_go = evaluate_no_go(evidence, decision_cfg["no_go"])
    p_contact = evaluate_pivot_contact_only(evidence, decision_cfg["pivot_contact_geometry_only"])
    p_coarse = evaluate_pivot_coarse(evidence, decision_cfg["pivot_coarse_equivalence_classes"])
    p_calib = evaluate_pivot_calibration(evidence, decision_cfg["pivot_calibration_sequential"])

    if blocked.get("any", False):
        decision, reason = "BLOCKED", blocked.get("reasons", ["hard stop condition triggered"])
    elif no_go["integrity_triggered"]:
        decision = "NO_GO_JACOBIAN_PATHWAY_HEAD"
        reason = ["integrity trigger: " + k for k in no_go["integrity_trigger_names"] if no_go["triggers"][k]]
    elif go["pass"]:
        decision, reason = "GO_JACOBIAN_PATHWAY_HEAD", ["all six §8.1 conditions hold"]
    elif p_contact["pass"]:
        decision, reason = "PIVOT_CONTACT_GEOMETRY_ONLY", ["contact detection/localization improves; the other families do not"]
    elif p_coarse["pass"]:
        decision, reason = "PIVOT_COARSE_EQUIVALENCE_CLASSES", ["fine localization fails; coarse equivalence classes separate"]
    elif p_calib["pass"]:
        decision, reason = "PIVOT_CALIBRATION_SEQUENTIAL", ["geometry does not help; false alarms / context calibration dominate"]
    elif no_go["performance_triggered"]:
        decision = "NO_GO_JACOBIAN_PATHWAY_HEAD"
        reason = ["performance trigger: " + k for k, v in no_go["triggers"].items() if v and k not in no_go["integrity_trigger_names"]]
    else:
        decision, reason = "NO_GO_JACOBIAN_PATHWAY_HEAD", ["no §8.1-§8.4 condition set is satisfied (default terminal state)"]

    return {
        "decision": decision,
        "decision_vocabulary": list(DECISION_VOCABULARY),
        "reasons": reason,
        "go": go,
        "no_go": no_go,
        "pivot_contact_geometry_only": p_contact,
        "pivot_coarse_equivalence_classes": p_coarse,
        "pivot_calibration_sequential": p_calib,
        "blocked": blocked,
        "evaluation_order": "BLOCKED > NO_GO(integrity: t4,t6) > GO > PIVOT_CONTACT > PIVOT_COARSE > PIVOT_CALIBRATION > NO_GO(performance: t1,t2,t3,t5) > NO_GO(default)",
        "thresholds": decision_cfg,
        "note": "Project decision thresholds, not theorems. Raw results are retained in full; post-hoc threshold changes are forbidden.",
    }


def reproduction_gate(observed: dict, reference: dict, tolerance: float) -> dict:
    """§6.4 -- the frozen ``chain_gnn_aug`` baseline must reproduce within ``tolerance``."""
    rows = []
    worst = 0.0
    for key, ref in reference.items():
        obs = observed.get(key)
        if obs is None or not _finite(obs) or not _finite(ref):
            rows.append({"metric": key, "reference": ref, "observed": obs, "relative_deviation": None, "within_tolerance": None, "status": "MISSING"})
            continue
        rel = abs(_f(obs) - _f(ref)) / max(abs(_f(ref)), 1e-12)
        worst = max(worst, rel)
        rows.append({"metric": key, "reference": _f(ref), "observed": _f(obs), "relative_deviation": rel, "within_tolerance": bool(rel <= tolerance), "status": "OK" if rel <= tolerance else "DEVIATION"})
    # a missing metric can never pass the gate
    passed = bool(rows) and all(r["within_tolerance"] is True for r in rows)
    return {"rows": rows, "worst_relative_deviation": worst, "tolerance": tolerance, "gate": "PASS" if passed else "FAIL"}
