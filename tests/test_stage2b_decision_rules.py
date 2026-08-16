"""The pre-registered Stage 2B decision rules behave exactly as written (kickoff §07).

Committed together with the rules and BEFORE any Stage 2B result exists; they pin the
vocabulary, the evaluation order, every individual condition and the integrity precedence.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from certo_fdi.stage2b.decision_stage2b import (
    DECISION_VOCABULARY,
    INTEGRITY_GATES,
    decide,
    reproduction_gate,
)

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2b_contact_loadpath.yaml").read_text())
DEC = CFG["decision"]


def _go_evidence() -> dict:
    """Evidence that satisfies every §3 condition."""
    return {
        "integrity": {k: False for k in INTEGRITY_GATES},
        "blocked": {"reasons": []},
        "detection": {
            "event_tpr": 0.88, "false_alarms_per_hour": 22.0, "healthy_ood_id_ratio": 1.2,
            "median_delay_s": 0.14, "p95_delay_s": 0.36, "event_f1": 0.71,
            "false_alarm_reduction_factor": 75.0,
        },
        "localization": {
            "episode_top1": 0.71, "mean_chain_distance": 0.58, "n_links_recall_ge_040": 4,
            "meets_stage2b_localization_thresholds": True,
        },
        "selective": {"coverage": 0.78, "selective_top1": 0.82, "selective_chain_distance": 0.41,
                      "reject_reduces_error": True, "selective_never_reduces_error_in_coverage_band": False},
        "loadpath": {"support_minus_aligned_auroc": -0.05, "support_minus_aligned_top1": -0.12,
                     "support_dominates_aligned_after_rank_correction": False,
                     "cartesian_geometry_claim_supported": True,
                     "no_reliable_loadpath_value": False, "no_stable_gain_over_counterfactual": False},
        "evidence_integrity": {"not_favored_by_rank_alone": True, "n_seeds_improvement_stable": 3,
                               "calibration_selected_without_fault_test": True},
        "healthy_expansion": {"h160_complete": True, "unstable_or_non_reproducible": False},
    }


def test_vocabulary_is_exactly_the_contract_list():
    assert set(DECISION_VOCABULARY) == {
        "GO_CONTACT_LOADPATH_MONITOR", "PIVOT_SUPPORT_ONLY_LOCALIZER", "PIVOT_LOADPATH_LOCALIZATION_ONLY",
        "PIVOT_SEQUENTIAL_DETECTION_ONLY", "PIVOT_CONTEXT_CALIBRATION_ONLY", "NO_GO_CONTACT_PRODUCT", "BLOCKED",
    }


def test_go_requires_every_condition():
    ev = _go_evidence()
    out = decide(ev, DEC)
    assert out["decision"] == "GO_CONTACT_LOADPATH_MONITOR", out["go"]["conditions"]
    # each detection / localization / integrity condition individually blocks GO
    for path, key, bad in (
        ("detection", "event_tpr", 0.70),
        ("detection", "false_alarms_per_hour", 90.0),
        ("detection", "healthy_ood_id_ratio", 2.4),
        ("detection", "median_delay_s", 0.40),
        ("detection", "p95_delay_s", 0.90),
        ("detection", "event_f1", 0.40),
        ("localization", "episode_top1", 0.52),
        ("localization", "mean_chain_distance", 1.20),
        ("localization", "n_links_recall_ge_040", 2),
        ("selective", "coverage", 0.40),
        ("selective", "selective_top1", 0.60),
        ("selective", "selective_chain_distance", 0.90),
        ("selective", "reject_reduces_error", False),
        ("evidence_integrity", "not_favored_by_rank_alone", False),
        ("evidence_integrity", "n_seeds_improvement_stable", 1),
        ("evidence_integrity", "calibration_selected_without_fault_test", False),
    ):
        e = {k: dict(v) if isinstance(v, dict) else v for k, v in ev.items()}
        e[path][key] = bad
        assert decide(e, DEC)["decision"] != "GO_CONTACT_LOADPATH_MONITOR", (path, key, bad)


def test_missing_evidence_never_produces_go():
    for ev in ({}, {"integrity": {}}, {"detection": {"event_tpr": 0.99}}):
        assert decide(ev, DEC)["decision"] != "GO_CONTACT_LOADPATH_MONITOR"


def test_every_integrity_gate_forces_blocked():
    for gate in INTEGRITY_GATES:
        ev = _go_evidence()
        ev["integrity"][gate] = True
        out = decide(ev, DEC)
        assert out["decision"] == "BLOCKED", gate
        assert gate in out["reasons"]
    # a free-form blocked reason also forces BLOCKED
    ev = _go_evidence()
    ev["blocked"] = {"reasons": ["stage 2A package hash mismatch"]}
    assert decide(ev, DEC)["decision"] == "BLOCKED"


def test_integrity_dominates_a_perfect_run():
    """An integrity failure is BLOCKED, never a scientific verdict -- even with a perfect GO picture."""
    ev = _go_evidence()
    ev["integrity"]["window_level_bootstrap_used"] = True
    out = decide(ev, DEC)
    assert out["decision"] == "BLOCKED"
    assert out["go"]["pass"] is True  # the GO evidence is still reported, just not acted on


def test_pivot_support_only_localizer():
    ev = _go_evidence()
    # the support control matches the aligned method and no Cartesian claim survives
    ev["loadpath"]["support_minus_aligned_auroc"] = -0.01
    ev["loadpath"]["support_minus_aligned_top1"] = -0.02
    ev["loadpath"]["cartesian_geometry_claim_supported"] = False
    # break one GO condition so GO cannot fire
    ev["detection"]["false_alarms_per_hour"] = 120.0
    assert decide(ev, DEC)["decision"] == "PIVOT_SUPPORT_ONLY_LOCALIZER"
    # if the aligned method is clearly ahead, the support pivot does not fire
    ev["loadpath"]["support_minus_aligned_top1"] = -0.30
    assert decide(ev, DEC)["decision"] != "PIVOT_SUPPORT_ONLY_LOCALIZER"


def test_pivot_loadpath_localization_only():
    ev = _go_evidence()
    ev["detection"]["false_alarms_per_hour"] = 900.0          # detector fails
    ev["loadpath"]["cartesian_geometry_claim_supported"] = True
    ev["loadpath"]["support_minus_aligned_top1"] = -0.30      # support pivot must not fire
    out = decide(ev, DEC)
    assert out["decision"] == "PIVOT_LOADPATH_LOCALIZATION_ONLY"


def test_pivot_sequential_detection_only():
    ev = _go_evidence()
    ev["localization"] = {"episode_top1": 0.42, "mean_chain_distance": 1.4, "n_links_recall_ge_040": 1,
                          "meets_stage2b_localization_thresholds": False}
    ev["selective"] = {"coverage": 0.78, "selective_top1": 0.45, "selective_chain_distance": 1.2,
                       "reject_reduces_error": False, "selective_never_reduces_error_in_coverage_band": True}
    ev["loadpath"]["support_minus_aligned_top1"] = -0.30
    out = decide(ev, DEC)
    assert out["decision"] == "PIVOT_SEQUENTIAL_DETECTION_ONLY"


def test_pivot_context_calibration_only():
    ev = _go_evidence()
    ev["detection"]["event_tpr"] = 0.55                      # detection bar not met
    ev["localization"] = {"episode_top1": 0.40, "mean_chain_distance": 1.6, "n_links_recall_ge_040": 1,
                          "meets_stage2b_localization_thresholds": False}
    ev["selective"] = {"coverage": 0.78, "selective_top1": 0.44, "selective_chain_distance": 1.4,
                       "reject_reduces_error": False, "selective_never_reduces_error_in_coverage_band": False}
    ev["loadpath"] = {"support_minus_aligned_auroc": -0.30, "support_minus_aligned_top1": -0.30,
                      "support_dominates_aligned_after_rank_correction": False,
                      "cartesian_geometry_claim_supported": False,
                      "no_reliable_loadpath_value": True, "no_stable_gain_over_counterfactual": True}
    out = decide(ev, DEC)
    assert out["decision"] == "PIVOT_CONTEXT_CALIBRATION_ONLY"


def test_no_go_needs_two_conditions_and_a_complete_h160():
    ev = _go_evidence()
    ev["detection"] = {"event_tpr": 0.55, "false_alarms_per_hour": 900.0, "healthy_ood_id_ratio": 3.0,
                       "median_delay_s": 0.9, "p95_delay_s": 2.0, "event_f1": 0.2,
                       "false_alarm_reduction_factor": 1.2}
    ev["localization"] = {"episode_top1": 0.30, "mean_chain_distance": 2.0, "n_links_recall_ge_040": 0,
                          "meets_stage2b_localization_thresholds": False}
    ev["selective"] = {"coverage": 0.5, "selective_top1": 0.3, "selective_chain_distance": 2.0,
                       "reject_reduces_error": False, "selective_never_reduces_error_in_coverage_band": True}
    ev["loadpath"] = {"support_minus_aligned_auroc": -0.3, "support_minus_aligned_top1": -0.3,
                      "support_dominates_aligned_after_rank_correction": False,
                      "cartesian_geometry_claim_supported": False,
                      "no_reliable_loadpath_value": False, "no_stable_gain_over_counterfactual": True}
    out = decide(ev, DEC)
    assert out["decision"] == "NO_GO_CONTACT_PRODUCT"
    assert out["no_go_contact_product"]["n_fired"] >= 2
    assert out["no_go_contact_product"]["h160_complete_and_integrity_ok"] is True
    # without a completed H160 the >=2-condition NO-GO cannot be asserted; it falls through
    ev["healthy_expansion"]["h160_complete"] = False
    out2 = decide(ev, DEC)
    assert out2["decision"] == "NO_GO_CONTACT_PRODUCT"
    assert out2["no_go_contact_product"]["pass"] is False
    assert "default terminal state" in " ".join(out2["reasons"])


def test_evaluation_order_is_recorded_and_stable():
    out = decide(_go_evidence(), DEC)
    order = out["evaluation_order"]
    for i, name in enumerate(["BLOCKED", "GO_CONTACT_LOADPATH_MONITOR", "PIVOT_SUPPORT_ONLY_LOCALIZER",
                              "PIVOT_LOADPATH_LOCALIZATION_ONLY", "PIVOT_SEQUENTIAL_DETECTION_ONLY",
                              "PIVOT_CONTEXT_CALIBRATION_ONLY"]):
        assert name in order
    assert order.index("BLOCKED") < order.index("GO_CONTACT_LOADPATH_MONITOR")
    assert order.index("GO_CONTACT_LOADPATH_MONITOR") < order.index("PIVOT_SUPPORT_ONLY_LOCALIZER")


def test_reproduction_gate():
    ref = {"auroc_all": 0.7502198299349684, "healthy_rmse_s0_nm": 0.19359606957017295}
    assert reproduction_gate({"auroc_all": 0.7502, "healthy_rmse_s0_nm": 0.1940}, ref, 0.02)["gate"] == "PASS"
    assert reproduction_gate({"auroc_all": 0.70, "healthy_rmse_s0_nm": 0.1940}, ref, 0.02)["gate"] == "FAIL"
    # a missing metric can never pass
    assert reproduction_gate({"auroc_all": None, "healthy_rmse_s0_nm": 0.1940}, ref, 0.02)["gate"] == "FAIL"
    g = reproduction_gate({"auroc_all": 0.7502198299349684, "healthy_rmse_s0_nm": 0.19359606957017295}, ref, 0.02)
    assert g["worst_relative_deviation"] == 0.0


def test_thresholds_match_the_frozen_contract():
    """The numbers in the config are the ones written in 07_DECISION_RULES.md."""
    go = DEC["go"]
    assert go["event_tpr_min"] == 0.80
    assert go["false_alarms_per_hour_max"] == 50
    assert go["healthy_ood_id_ratio_max"] == 1.5
    assert go["median_delay_s_max"] == 0.20
    assert go["p95_delay_s_max"] == 0.50
    assert go["event_f1_min"] == 0.60
    assert go["localization_top1_min"] == 0.65
    assert go["localization_chain_distance_max"] == 0.75
    assert go["min_links_recall_ge_040"] == 4
    assert go["selective_coverage_min"] == 0.70
    assert go["selective_top1_min"] == 0.75
    assert go["selective_chain_distance_max"] == 0.50
    assert DEC["pivot_support_only"]["auroc_within"] == 0.02
    assert DEC["pivot_support_only"]["top1_within"] == 0.05
    assert DEC["pivot_sequential_detection_only"]["localization_top1_below"] == 0.55
    assert DEC["pivot_context_calibration_only"]["false_alarm_reduction_factor_min"] == 10.0
    assert DEC["no_go_after_h160"]["false_alarms_per_hour_above"] == 200
    assert DEC["no_go_after_h160"]["event_tpr_below"] == 0.70
    assert DEC["no_go_after_h160"]["localization_top1_below"] == 0.50
    assert CFG["statistics"]["independent_unit"] == "episode"
    assert CFG["calibration"]["target_false_alarms_per_hour"] == [50, 10]
