"""Every branch of the frozen Stage 1R-B decision (07_DECISION_RULES.md) with explicit N/A handling."""

from __future__ import annotations

import copy

import pytest

from certo_fdi.experiments.decision_stage1rb import BASELINE, CANDIDATE, DECISIONS, decide

MARGINS = {"axis_auroc_margin": 0.03, "axis_fpr_relative_reduction": 0.25, "sample_efficiency_auroc_tolerance": 0.02, "healthy_rmse_tolerance": 0.10, "localization_top1_margin": 0.10, "localization_chain_distance_margin": 0.25, "parity_band_auroc": 0.02, "frame_drift_ratio_min": 100.0, "min_families": 2, "min_seeds": 2}
GATES_OK = {"provenance": True, "r0": True, "leakage": True, "input_parity": True, "param_parity": True, "tuning_healthy_only": True, "seeds_complete": True, "reproducible": None}
SEEDS = ("260815", "260816", "260817")


def model_metrics(auroc_S1, auroc_S2, auroc_S4, auroc_ALL, auroc_ALL_25, rmse_S0, rmse_S0_25, top1, dist, drift, fam_ood, val_loss=0.2, fpr=0.8):
    by = lambda v: {s: v + 0.001 * i for i, s in enumerate(SEEDS)}
    return {
        "auroc_S1": auroc_S1, "auroc_S2": auroc_S2, "auroc_S4": auroc_S4, "auroc_ALL": auroc_ALL, "auroc_OOD": (auroc_S1 + auroc_S2 + auroc_S4) / 3,
        "fpr90_S1": fpr, "fpr90_S2": fpr, "fpr90_S4": fpr, "auroc_S1_by_seed": by(auroc_S1), "auroc_S2_by_seed": by(auroc_S2), "auroc_S4_by_seed": by(auroc_S4), "auroc_ALL_by_seed": by(auroc_ALL),
        "auroc_ALL_frac0.25": auroc_ALL_25, "auroc_ALL_frac1.00": auroc_ALL, "auroc_ALL_frac0.25_by_seed": by(auroc_ALL_25), "auroc_ALL_frac1.00_by_seed": by(auroc_ALL),
        "rmse_post_S0": rmse_S0, "rmse_ratio_S0": rmse_S0 / 0.59, "rmse_post_S0_frac0.25": rmse_S0_25,
        "loc_cf_top1_ALL": top1, "loc_cf_dist_ALL": dist, "loc_cf_top1_ALL_by_seed": by(top1), "frame_drift_median": drift,
        "auroc_OOD_by_family": dict(fam_ood), "best_val_loss_by_seed": by(val_loss), "all_runs_finite": True,
        "n_seeds_frac0.25": 3, "n_seeds_frac1.00": 3, "auroc_ALL_qddtrue": auroc_ALL + 0.02, "rmse_ratio_S0_qddtrue": rmse_S0 / 0.59 * 0.9,
    }


FAM_BASE = {"F1_actuator": 0.80, "F2_friction": 0.50, "F3_payload": 0.94, "F4_contact": 0.66, "F5_encoder": 0.70, "F6_command": 0.58}
BASE = model_metrics(0.65, 0.73, 0.82, 0.72, 0.65, 0.23, 0.39, 0.40, 1.39, 0.19, FAM_BASE)
DIAG = {"rnea_gru": {"auroc_ALL": 0.66}, "ligra_free_output": {"auroc_ALL": 0.72}}


def test_vocabulary_is_closed():
    assert set(DECISIONS) == {"RESEARCH_GO_LIE_MAIN_CONTRIBUTION", "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE", "PIVOT_CHAIN_ONLY", "FINAL_NO_GO_LIE_MAIN_CONTRIBUTION", "PIVOT_TYPED_CAPACITY_UNRESOLVED", "BLOCKED"}


def test_blocked_on_any_gate_and_on_missing_metrics():
    for g in ("provenance", "r0", "leakage", "input_parity", "param_parity", "tuning_healthy_only", "seeds_complete"):
        gates = dict(GATES_OK)
        gates[g] = False
        ev = decide({BASELINE: BASE, CANDIDATE: BASE}, gates, MARGINS, "RETIRED_BASIS_V1")
        assert ev["decision"] == "BLOCKED" and any(g in r for r in ev["reasons"])
    gates = dict(GATES_OK)
    gates["reproducible"] = False
    assert decide({BASELINE: BASE, CANDIDATE: BASE}, gates, MARGINS, None)["decision"] == "BLOCKED"
    # missing candidate metrics: axes are N/A (never coerced to False) -> BLOCKED, not a pivot
    ev = decide({BASELINE: BASE}, GATES_OK, MARGINS, None)
    assert ev["decision"] == "BLOCKED" and len(ev["axes_not_available"]) == 4
    assert all(v["pass"] is None for v in ev["axes"].values())
    ev = decide({BASELINE: BASE, CANDIDATE: BASE}, GATES_OK, MARGINS, None)
    assert ev["decision_reported"].startswith("NO_GO_CURRENT_LIGRA_V1 + ")


def test_research_go_requires_three_axes_families_seeds_and_healthy_fit():
    fam = {k: v + 0.05 for k, v in FAM_BASE.items()}
    cand = model_metrics(0.70, 0.78, 0.87, 0.75, 0.71, 0.22, 0.24, 0.55, 1.05, 0.0002, fam)
    ev = decide({BASELINE: BASE, CANDIDATE: cand, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev["decision"] == "RESEARCH_GO_LIE_MAIN_CONTRIBUTION"
    assert len(ev["axes_won"]) == 4 and ev["family_seed_support"]["pass"] is True
    # same numbers but the healthy fit is 15 % worse -> not GO (falls to CHAIN_ONLY via rmse condition)
    worse = dict(cand, rmse_post_S0=0.27)
    ev2 = decide({BASELINE: BASE, CANDIDATE: worse, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev2["decision"] != "RESEARCH_GO_LIE_MAIN_CONTRIBUTION" and ev2["decision"] == "PIVOT_CHAIN_ONLY"
    # advantage driven only by the easy payload family -> support fails -> not GO
    fam_easy = dict(FAM_BASE)
    fam_easy["F3_payload"] = 0.99
    cand2 = model_metrics(0.70, 0.78, 0.87, 0.75, 0.71, 0.22, 0.24, 0.55, 1.05, 0.0002, fam_easy)
    ev3 = decide({BASELINE: BASE, CANDIDATE: cand2, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev3["decision"] != "RESEARCH_GO_LIE_MAIN_CONTRIBUTION" and ev3["family_seed_support"]["pass"] is False
    # only two axes won with support -> partial gain, gap resolution -> implementation-guarantee pivot
    cand3 = model_metrics(0.70, 0.73, 0.82, 0.72, 0.65, 0.23, 0.39, 0.55, 1.05, 0.0002, fam)
    ev4 = decide({BASELINE: BASE, CANDIDATE: cand3, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev4["decision"] == "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE" and "partial_gain_below_bar" in ev4["reasons"][0]


def test_parity_pivot_lie_as_implementation_guarantee():
    cand = model_metrics(0.66, 0.72, 0.83, 0.725, 0.66, 0.235, 0.385, 0.42, 1.30, 0.0002, FAM_BASE)
    ev = decide({BASELINE: BASE, CANDIDATE: cand, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev["decision"] == "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE"
    assert ev["parity_conditions"]["all_axes_within_parity_band"] and ev["frame_drift"]["at_least_100x"]
    # identical numbers but the drift ratio is only 10x -> parity fails -> falls to CHAIN_ONLY (no gain in loc & SE)
    cand2 = dict(cand, frame_drift_median=0.019)
    ev2 = decide({BASELINE: BASE, CANDIDATE: cand2, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev2["decision"] == "PIVOT_CHAIN_ONLY"


def test_pivot_chain_only_and_final_no_go():
    # baseline leads on 3 axes by margin, candidate fit fine -> CHAIN_ONLY (not FINAL_NO_GO: fit not worse)
    cand = model_metrics(0.60, 0.68, 0.77, 0.68, 0.60, 0.23, 0.39, 0.28, 1.80, 0.0002, {k: v - 0.05 for k, v in FAM_BASE.items()})
    ev = decide({BASELINE: BASE, CANDIDATE: cand, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev["decision"] == "PIVOT_CHAIN_ONLY" and ev["chain_only_conditions"]["baseline_leads_on_at_least_3_axes"]
    # additionally worse healthy fit >10 %, no loc/SE improvement -> FINAL_NO_GO
    cand2 = dict(cand, rmse_post_S0=0.30)
    ev2 = decide({BASELINE: BASE, CANDIDATE: cand2, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev2["decision"] == "FINAL_NO_GO_LIE_MAIN_CONTRIBUTION"
    assert all(ev2["final_no_go_conditions"].values())
    # structure effective but typed no gain, mixed small differences -> CHAIN_ONLY
    cand3 = model_metrics(0.64, 0.72, 0.81, 0.71, 0.63, 0.24, 0.40, 0.38, 1.45, 0.05, FAM_BASE)
    ev3 = decide({BASELINE: BASE, CANDIDATE: cand3, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev3["decision"] == "PIVOT_CHAIN_ONLY" and ev3["chain_only_conditions"]["structure_effective_but_typed_no_gain"]


def test_typed_capacity_unresolved_on_training_instability():
    cand = model_metrics(0.55, 0.60, 0.70, 0.60, 0.55, 0.40, 0.50, 0.20, 2.0, 0.0002, {k: v - 0.1 for k, v in FAM_BASE.items()}, val_loss=5.0)
    ev = decide({BASELINE: BASE, CANDIDATE: cand, **DIAG}, GATES_OK, MARGINS, "RETIRED_BASIS_V1")
    assert ev["decision"] == "PIVOT_TYPED_CAPACITY_UNRESOLVED" and ev["candidate_training"]["unstable_or_nonconverged"] is True
    # without the retired-v1 precondition the same evidence is a chain-only pivot / no-go, never 'unresolved'
    ev2 = decide({BASELINE: BASE, CANDIDATE: cand, **DIAG}, GATES_OK, MARGINS, "BASIS_CAPACITY_NOT_REJECTED")
    assert ev2["decision"] in ("PIVOT_CHAIN_ONLY", "FINAL_NO_GO_LIE_MAIN_CONTRIBUTION")


def test_na_values_never_become_booleans():
    cand = copy.deepcopy(BASE)
    for k in list(cand.keys()):
        if k.startswith("loc_cf"):
            cand[k] = float("nan")
    ev = decide({BASELINE: BASE, CANDIDATE: cand, **DIAG}, GATES_OK, MARGINS, None)
    assert ev["axes"]["axis3_localization"]["pass"] is None
    assert "axis3_localization" in ev["axes_not_available"]
    assert ev["decision"] in DECISIONS
