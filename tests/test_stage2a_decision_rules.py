"""The pre-registered Stage 2A decision rules behave exactly as written (contract §8).

These tests are committed together with the rules and BEFORE any Stage 2A model result
exists; they pin the vocabulary, the evaluation order and each individual condition.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from certo_fdi.experiments.decision_stage2a import DECISION_VOCABULARY, decide, reproduction_gate

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2a_pathway_audit.yaml").read_text())
DEC = CFG["decision"]


def _go_evidence() -> dict:
    return {
        "blocked": {"any": False, "reasons": []},
        "geometry_gain": {"f4_auroc_gain_s1_s4_mean": 0.08, "f4_auroc_gain_seed_agreement": 3},
        "localization_gain": {"f4_top1_gain": 0.20, "f4_chain_distance_reduction": 0.7, "f4_top1_best": 0.55},
        "false_alarms": {"relative_worsening": 0.03, "baseline_false_alarms_per_hour": 12.0, "healthy_ood_over_id_alarm_ratio": 1.4},
        "diagnosability": {"best_abs_spearman": 0.55, "best_abs_spearman_ci_excludes_zero": True},
        "coverage": {"n_contact_links_with_gain": 3, "n_context_strata_with_gain": 2},
        "control": {"primary_detection_is_healthy_only": True, "shuffled_control_does_not_reproduce_gain": True, "gain_requires_fault_label_fuser": False},
        "ablation_ordering": {"geometry_only_not_better_than_residual_only": False, "chain_plus_geometry_not_better_than_residual_only": False},
        "oracle": {"only_truth_point_oracle_works": False},
        "other_families": {"n_families_improved": 3},
        "coarse": {"balanced_accuracy_best": 0.62, "balanced_accuracy_gain_over_baseline": 0.15},
    }


def test_vocabulary_is_exactly_the_contract_list():
    assert set(DECISION_VOCABULARY) == {
        "GO_JACOBIAN_PATHWAY_HEAD", "PIVOT_CONTACT_GEOMETRY_ONLY", "PIVOT_CALIBRATION_SEQUENTIAL",
        "PIVOT_COARSE_EQUIVALENCE_CLASSES", "NO_GO_JACOBIAN_PATHWAY_HEAD", "BLOCKED",
    }


def test_go_requires_every_condition():
    ev = _go_evidence()
    assert decide(ev, DEC)["decision"] == "GO_JACOBIAN_PATHWAY_HEAD"
    # each condition individually blocks GO
    for patch in (
        {"geometry_gain": {"f4_auroc_gain_s1_s4_mean": 0.04, "f4_auroc_gain_seed_agreement": 3}},
        {"geometry_gain": {"f4_auroc_gain_s1_s4_mean": 0.08, "f4_auroc_gain_seed_agreement": 1}},
        {"localization_gain": {"f4_top1_gain": 0.10, "f4_chain_distance_reduction": 0.2, "f4_top1_best": 0.4}},
        {"false_alarms": {"relative_worsening": 0.15, "baseline_false_alarms_per_hour": 12.0, "healthy_ood_over_id_alarm_ratio": 1.4}},
        {"diagnosability": {"best_abs_spearman": 0.35, "best_abs_spearman_ci_excludes_zero": True}},
        {"diagnosability": {"best_abs_spearman": 0.55, "best_abs_spearman_ci_excludes_zero": False}},
        {"coverage": {"n_contact_links_with_gain": 1, "n_context_strata_with_gain": 1}},
        {"control": {"primary_detection_is_healthy_only": True, "shuffled_control_does_not_reproduce_gain": False, "gain_requires_fault_label_fuser": False}},
    ):
        e = {**ev, **patch}
        assert decide(e, DEC)["decision"] != "GO_JACOBIAN_PATHWAY_HEAD", patch


def test_integrity_triggers_dominate_pivots():
    # nothing works and no pivot explains it -> the performance NO-GO is the terminal state
    ev = _go_evidence()
    ev["geometry_gain"] = {"f4_auroc_gain_s1_s4_mean": 0.005, "f4_auroc_gain_seed_agreement": 1}
    ev["localization_gain"] = {"f4_top1_gain": 0.01, "f4_chain_distance_reduction": 0.0, "f4_top1_best": 0.30}
    ev["coarse"] = {"balanced_accuracy_best": 0.28, "balanced_accuracy_gain_over_baseline": 0.01}
    out = decide(ev, DEC)
    assert out["decision"] == "NO_GO_JACOBIAN_PATHWAY_HEAD"
    assert out["no_go"]["triggers"]["t1_no_detection_and_no_localization_gain"]
    assert out["no_go"]["performance_triggered"] and not out["no_go"]["integrity_triggered"]

    # an integrity trigger overrides even a fully satisfied pivot picture
    ev_int = _go_evidence()
    ev_int["geometry_gain"] = {"f4_auroc_gain_s1_s4_mean": 0.03, "f4_auroc_gain_seed_agreement": 2}
    ev_int["localization_gain"] = {"f4_top1_gain": 0.08, "f4_chain_distance_reduction": 0.3, "f4_top1_best": 0.42}
    ev_int["other_families"] = {"n_families_improved": 0}
    assert decide(ev_int, DEC)["decision"] == "PIVOT_CONTACT_GEOMETRY_ONLY"
    ev_int["oracle"] = {"only_truth_point_oracle_works": True}
    assert decide(ev_int, DEC)["decision"] == "NO_GO_JACOBIAN_PATHWAY_HEAD"

    ev2 = _go_evidence()
    ev2["false_alarms"] = {"relative_worsening": 0.4, "baseline_false_alarms_per_hour": 12.0, "healthy_ood_over_id_alarm_ratio": 1.4}
    assert decide(ev2, DEC)["decision"] == "NO_GO_JACOBIAN_PATHWAY_HEAD"

    ev3 = _go_evidence()
    ev3["oracle"] = {"only_truth_point_oracle_works": True}
    assert decide(ev3, DEC)["decision"] == "NO_GO_JACOBIAN_PATHWAY_HEAD"

    ev4 = _go_evidence()
    ev4["control"] = {"primary_detection_is_healthy_only": True, "shuffled_control_does_not_reproduce_gain": True, "gain_requires_fault_label_fuser": True}
    assert decide(ev4, DEC)["decision"] == "NO_GO_JACOBIAN_PATHWAY_HEAD"


def test_pivot_contact_geometry_only():
    ev = _go_evidence()
    ev["geometry_gain"] = {"f4_auroc_gain_s1_s4_mean": 0.03, "f4_auroc_gain_seed_agreement": 2}  # below GO, above pivot
    ev["localization_gain"] = {"f4_top1_gain": 0.08, "f4_chain_distance_reduction": 0.3, "f4_top1_best": 0.42}
    ev["other_families"] = {"n_families_improved": 0}
    out = decide(ev, DEC)
    assert out["decision"] == "PIVOT_CONTACT_GEOMETRY_ONLY"
    # with the other families improving too, the contact-only pivot no longer fires
    ev["other_families"] = {"n_families_improved": 3}
    assert decide(ev, DEC)["decision"] != "PIVOT_CONTACT_GEOMETRY_ONLY"


def test_pivot_coarse_and_calibration():
    ev = _go_evidence()
    ev["geometry_gain"] = {"f4_auroc_gain_s1_s4_mean": 0.025, "f4_auroc_gain_seed_agreement": 2}
    ev["localization_gain"] = {"f4_top1_gain": 0.01, "f4_chain_distance_reduction": 0.0, "f4_top1_best": 0.30}
    ev["other_families"] = {"n_families_improved": 3}
    ev["diagnosability"] = {"best_abs_spearman": 0.30, "best_abs_spearman_ci_excludes_zero": True}
    out = decide(ev, DEC)
    assert out["decision"] == "PIVOT_COARSE_EQUIVALENCE_CLASSES"

    # geometry does not help at all, but the false-alarm rate and the healthy-OOD alarm ratio
    # show that context calibration is the bottleneck -> the more specific calibration pivot
    # wins over the bare performance NO-GO (see the ordering note in decision_stage2a).
    ev2 = _go_evidence()
    ev2["geometry_gain"] = {"f4_auroc_gain_s1_s4_mean": 0.005, "f4_auroc_gain_seed_agreement": 1}
    ev2["localization_gain"] = {"f4_top1_gain": 0.0, "f4_chain_distance_reduction": 0.0, "f4_top1_best": 0.30}
    ev2["diagnosability"] = {"best_abs_spearman": 0.30, "best_abs_spearman_ci_excludes_zero": True}
    ev2["coarse"] = {"balanced_accuracy_best": 0.30, "balanced_accuracy_gain_over_baseline": 0.01}
    ev2["false_alarms"] = {"relative_worsening": 0.05, "baseline_false_alarms_per_hour": 90.0, "healthy_ood_over_id_alarm_ratio": 6.0}
    assert decide(ev2, DEC)["decision"] == "PIVOT_CALIBRATION_SEQUENTIAL"
    # a benign false-alarm picture removes the calibration explanation -> plain NO-GO
    ev2["false_alarms"] = {"relative_worsening": 0.05, "baseline_false_alarms_per_hour": 5.0, "healthy_ood_over_id_alarm_ratio": 1.1}
    assert decide(ev2, DEC)["decision"] == "NO_GO_JACOBIAN_PATHWAY_HEAD"


def test_blocked_dominates_everything():
    ev = _go_evidence()
    ev["blocked"] = {"any": True, "reasons": ["dataset hash mismatch"]}
    out = decide(ev, DEC)
    assert out["decision"] == "BLOCKED" and out["reasons"] == ["dataset hash mismatch"]


def test_missing_evidence_never_produces_go():
    assert decide({"blocked": {"any": False}}, DEC)["decision"] == "NO_GO_JACOBIAN_PATHWAY_HEAD"


def test_reproduction_gate():
    ref = {"auroc_ALL": 0.75, "healthy_rmse_S0_nm": 0.1936}
    g = reproduction_gate({"auroc_ALL": 0.7502, "healthy_rmse_S0_nm": 0.1940}, ref, 0.02)
    assert g["gate"] == "PASS" and g["worst_relative_deviation"] < 0.02
    g2 = reproduction_gate({"auroc_ALL": 0.70, "healthy_rmse_S0_nm": 0.1940}, ref, 0.02)
    assert g2["gate"] == "FAIL"
    g3 = reproduction_gate({"auroc_ALL": None, "healthy_rmse_S0_nm": 0.1940}, ref, 0.02)
    assert g3["gate"] == "FAIL"  # a missing metric can never pass the gate
