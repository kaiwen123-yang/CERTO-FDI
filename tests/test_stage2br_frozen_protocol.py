"""The frozen Stage 2B-R protocol behaves exactly as written (master prompt §5, §9; rules §A-§F).

Committed together with the rules and BEFORE any Stage 2B-R score exists. These tests pin the
terminal-state vocabulary, the precedence order, every individual trigger, the envelope/tie
arithmetic, and the two properties that make the audit trustworthy at all: thresholds come from
the config rather than from code, and this package cannot reach training or data generation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from certo_fdi.stage2br.decision_stage2br import (
    PASS_STATES,
    RANK_INSTABILITY,
    TERMINAL_STATES,
    episode_is_numerical_tie,
    integrity_state,
    numerical_envelope,
    scientific_decision_is_permitted,
    tie_set,
    tie_tolerance,
)

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "configs" / "stage2br_reproduction_gate.yaml"
CFG = yaml.safe_load(CFG_PATH.read_text())
EPS64 = 2.220446049250313e-16


def _clean_evidence() -> dict:
    """Evidence describing a run in which everything reproduced bit-exactly."""
    return {
        "input_provenance_ok": True,
        "scientific_head_clean": True,
        "reference_evidence_complete": True,
        "score_history_resolvable": True,
        "n_label_differences": 0,
        "n_nontie_label_differences": 0,
        "scores_within_score_tolerance": True,
        "semantic_difference_found": False,
        "rank_threshold_unstable": False,
    }


def _tie_evidence() -> dict:
    """Evidence describing one label difference that is an admissible numerical tie."""
    return {**_clean_evidence(), "n_label_differences": 1, "n_nontie_label_differences": 0}


# --------------------------------------------------------------------- vocabulary and precedence
def test_terminal_state_vocabulary_is_exactly_the_contract_list():
    assert set(TERMINAL_STATES) == {
        "BLOCKED_INPUT_PROVENANCE",
        "BLOCKED_SCIENTIFIC_HEAD_MISMATCH",
        "BLOCKED_MISSING_REFERENCE_EVIDENCE",
        "BLOCKED_UNRESOLVABLE_SCORE_HISTORY",
        "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH",
        "PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP",
        "PASS_EXACT_REPRODUCTION",
    }


def test_config_precedence_matches_the_module_order():
    assert tuple(CFG["integrity_decision_precedence"]) == TERMINAL_STATES


def test_rank_instability_is_a_modifier_not_a_terminal_state():
    assert RANK_INSTABILITY == CFG["rank_instability_label"] == "RANK_THRESHOLD_UNSTABLE"
    assert RANK_INSTABILITY not in TERMINAL_STATES


def test_only_the_two_pass_states_permit_the_scientific_decision():
    for s in TERMINAL_STATES:
        assert scientific_decision_is_permitted(s) is (s in PASS_STATES)
    assert set(PASS_STATES) == {"PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP", "PASS_EXACT_REPRODUCTION"}


# --------------------------------------------------------------------- each trigger, in isolation
@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("input_provenance_ok", False, "BLOCKED_INPUT_PROVENANCE"),
        ("scientific_head_clean", False, "BLOCKED_SCIENTIFIC_HEAD_MISMATCH"),
        ("reference_evidence_complete", False, "BLOCKED_MISSING_REFERENCE_EVIDENCE"),
        ("score_history_resolvable", False, "BLOCKED_UNRESOLVABLE_SCORE_HISTORY"),
        ("semantic_difference_found", True, "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH"),
        ("scores_within_score_tolerance", False, "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH"),
        ("rank_threshold_unstable", True, "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH"),
    ],
)
def test_single_condition_selects_its_state(key, value, expected):
    out = integrity_state({**_clean_evidence(), key: value}, CFG)
    assert out["integrity_state"] == expected


def test_clean_run_is_exact_reproduction():
    out = integrity_state(_clean_evidence(), CFG)
    assert out["integrity_state"] == "PASS_EXACT_REPRODUCTION"
    assert out["reproduction_gate_pass"] is True
    assert out["modifiers"] == []


def test_one_tie_flip_is_the_tie_pass_not_the_exact_pass():
    out = integrity_state(_tie_evidence(), CFG)
    assert out["integrity_state"] == "PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP"
    assert out["reproduction_gate_pass"] is True


def test_a_single_nontie_difference_fails_reproduction():
    ev = {**_tie_evidence(), "n_label_differences": 1, "n_nontie_label_differences": 1}
    out = integrity_state(ev, CFG)
    assert out["integrity_state"] == "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH"
    assert out["reproduction_gate_pass"] is False


def test_rank_instability_cannot_be_classified_as_a_numerical_tie():
    """Master prompt §8.2: a label that moves with the rank threshold is not floating point."""
    ev = {**_tie_evidence(), "rank_threshold_unstable": True}
    out = integrity_state(ev, CFG)
    assert out["integrity_state"] == "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH"
    assert RANK_INSTABILITY in out["modifiers"]
    assert out["reproduction_gate_pass"] is False


def test_precedence_is_strict_when_several_conditions_fire():
    ev = {**_clean_evidence(), "input_provenance_ok": False, "scientific_head_clean": False,
          "reference_evidence_complete": False, "score_history_resolvable": False,
          "n_label_differences": 5, "n_nontie_label_differences": 5}
    assert integrity_state(ev, CFG)["integrity_state"] == "BLOCKED_INPUT_PROVENANCE"
    ev["input_provenance_ok"] = True
    assert integrity_state(ev, CFG)["integrity_state"] == "BLOCKED_SCIENTIFIC_HEAD_MISMATCH"
    ev["scientific_head_clean"] = True
    assert integrity_state(ev, CFG)["integrity_state"] == "BLOCKED_MISSING_REFERENCE_EVIDENCE"
    ev["reference_evidence_complete"] = True
    assert integrity_state(ev, CFG)["integrity_state"] == "BLOCKED_UNRESOLVABLE_SCORE_HISTORY"
    ev["score_history_resolvable"] = True
    assert integrity_state(ev, CFG)["integrity_state"] == "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH"


def test_missing_evidence_never_falls_through_to_a_pass():
    """An empty evidence dict must block, not pass."""
    out = integrity_state({}, CFG)
    assert out["integrity_state"] == "BLOCKED_INPUT_PROVENANCE"
    assert out["reproduction_gate_pass"] is False


# --------------------------------------------------------------------- envelope and tie arithmetic
def test_roundoff_floor_applies_even_when_backends_agree_exactly():
    env = numerical_envelope([1.0, 1.0, 1.0, 1.0, 1.0], 1.0, CFG)
    assert env["backend_range"] == 0.0
    assert env["envelope"] == pytest.approx(CFG["score_equivalence"]["roundoff_factor"] * EPS64)
    assert env["envelope"] > 0.0


def test_envelope_takes_the_backend_spread_when_it_dominates():
    env = numerical_envelope([1.0, 1.0 + 1e-9], 1.0, CFG)
    assert env["envelope"] == pytest.approx(1e-9)


def test_envelope_scales_with_the_episode_score_magnitude():
    small = numerical_envelope([1.0], 1.0, CFG)["envelope"]
    large = numerical_envelope([1.0], 1e6, CFG)["envelope"]
    assert large == pytest.approx(small * 1e6)


def test_tie_tolerance_is_twice_the_larger_envelope():
    assert tie_tolerance(3.0, 7.0, CFG) == pytest.approx(2.0 * 7.0)
    assert CFG["score_equivalence"]["tie_multiplier"] == 2.0


def test_tie_set_is_measured_from_the_minimum_score():
    scores = {0: 10.0, 1: 10.0 + 1e-15, 2: 10.5, 3: 99.0}
    assert tie_set(scores, 1e-12) == [0, 1]
    assert tie_set(scores, 1.0) == [0, 1, 2]


def test_a_synthetic_near_tie_is_classified_as_a_tie():
    """Master prompt §11.12."""
    env = numerical_envelope([5.0, 5.0 + 2e-15], 5.0, CFG)
    tol = tie_tolerance(env["envelope"], env["envelope"], CFG)
    out = episode_is_numerical_tie({
        "margin": 1e-15, "tie_tolerance": tol, "raw_inputs_identical": True,
        "labels_in_common_tie_set": True, "tie_set_stable_across_backends": True,
        "tie_set_stable_across_candidate_orders": True,
        "no_singular_value_near_rank_threshold": True, "rank_threshold_unstable": False}, CFG)
    assert out["is_numerical_tie"] is True


def test_a_synthetic_real_score_mismatch_is_rejected():
    """Master prompt §11.13: a margin far outside the envelope is never a tie."""
    env = numerical_envelope([5.0, 5.0 + 2e-15], 5.0, CFG)
    tol = tie_tolerance(env["envelope"], env["envelope"], CFG)
    out = episode_is_numerical_tie({
        "margin": 0.25, "tie_tolerance": tol, "raw_inputs_identical": True,
        "labels_in_common_tie_set": True, "tie_set_stable_across_backends": True,
        "tie_set_stable_across_candidate_orders": True,
        "no_singular_value_near_rank_threshold": True, "rank_threshold_unstable": False}, CFG)
    assert out["is_numerical_tie"] is False
    assert out["conditions"]["margin_within_tolerance"] is False


@pytest.mark.parametrize("condition", [
    "raw_inputs_identical", "labels_in_common_tie_set", "tie_set_stable_across_backends",
    "tie_set_stable_across_candidate_orders", "no_singular_value_near_rank_threshold",
])
def test_every_tie_condition_is_necessary(condition):
    ep = {"margin": 0.0, "tie_tolerance": 1.0, "raw_inputs_identical": True,
          "labels_in_common_tie_set": True, "tie_set_stable_across_backends": True,
          "tie_set_stable_across_candidate_orders": True,
          "no_singular_value_near_rank_threshold": True, "rank_threshold_unstable": False}
    assert episode_is_numerical_tie(ep, CFG)["is_numerical_tie"] is True
    assert episode_is_numerical_tie({**ep, condition: False}, CFG)["is_numerical_tie"] is False


def test_differing_inputs_are_never_a_tie_however_small_the_margin():
    """Contract §2: an input difference is an implementation mismatch, not a tie."""
    ep = {"margin": 0.0, "tie_tolerance": 1.0, "raw_inputs_identical": False,
          "labels_in_common_tie_set": True, "tie_set_stable_across_backends": True,
          "tie_set_stable_across_candidate_orders": True,
          "no_singular_value_near_rank_threshold": True, "rank_threshold_unstable": False}
    assert episode_is_numerical_tie(ep, CFG)["is_numerical_tie"] is False


# --------------------------------------------------------------------- thresholds live in config
def test_no_numeric_threshold_is_hard_coded_in_the_decision_module():
    """Every tolerance must be read from the config, so it cannot be tuned in code."""
    src = (ROOT / "src" / "certo_fdi" / "stage2br" / "decision_stage2br.py").read_text()
    allowed = {0.0, 1.0, 2.220446049250313e-16}          # neutral constants and eps64
    found = {n.value for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Constant) and isinstance(n.value, float)}
    assert found <= allowed, f"hard-coded float thresholds: {sorted(found - allowed)}"


def test_every_tolerance_used_by_the_audit_is_present_in_the_config():
    se = CFG["score_equivalence"]
    for k in ("raw_array_absolute_scale", "raw_array_relative_tolerance", "score_absolute_scale",
              "score_relative_tolerance", "roundoff_factor", "tie_multiplier"):
        assert k in se, k
    assert list(se["independent_backends"]) == [
        "numpy_svd", "scipy_svd_gesdd", "scipy_svd_gesvd", "scipy_lstsq_gelsd", "scipy_lstsq_gelsy"]
    assert list(se["rank_tolerance_scale_diagnostic"]) == [0.5, 1.0, 2.0]
    assert list(se["blas_threads"]) == [1, 8]
    assert list(se["memory_orders"]) == ["C", "F"]
    assert int(se["process_repeats"]) == 3


def test_frozen_inputs_match_the_kickoff_contract_byte_for_byte():
    fi = CFG["frozen_inputs"]
    assert fi["stage2a_commit"] == "bcf2ad5c978f58dc159636d64d0b5c81efb9e396"
    assert fi["stage2b_scientific_commit"] == "bee5f9b7e21b511c39936a047acaff39cfcfb395"
    assert fi["stage2b_branch_head_at_kickoff"] == "7b8ecd8f2bef1acbe41789e9676a23941a465353"
    assert fi["stage2b_full_zip_sha256"] == "20392940e08a9b6d06135629fa36ef6861aa0ce90ed4c7eef7aa3a9ccbcc1b3d"
    assert fi["dataset_manifest_sha256"] == "8c2ba38b9262080efb981c08cfb7b5d58d2bfd037228a313edcae57f062b4100"
    assert fi["regenerate_data"] is False and fi["retrain_model"] is False


def test_historical_facts_are_recorded_and_not_editable_into_a_pass():
    h = CFG["historical_reproduction"]
    assert h["stage2a_top1_by_seed"] == [0.5416666666666666, 0.625, 0.5833333333333334]
    assert h["stage2b_top1_by_seed"] == [0.5416666666666666, 0.625, 0.5416666666666666]
    assert h["historical_tolerance_relative"] == 0.02        # the old gate is recorded, not relaxed
    assert h["historical_decision"] == "BLOCKED"
    assert h["expected_differing_predictions"] == 1


def test_the_restated_frozen_localizer_matches_the_stage2b_implementation():
    """The config's restatement of the frozen chain must not drift from the real code."""
    from certo_fdi.stage2b import rank_aware_scores as RS

    fl = CFG["frozen_localizer"]
    assert fl["rank_relative_tolerance"] == RS.RANK_RTOL
    assert fl["score"] == RS.AUDIT_CONTROL_SCORE == "raw_projection_residual"
    assert RS.HIGHER_IS_BETTER[fl["score"]] is False        # argmin
    assert fl["score_direction"] == "argmin"


# --------------------------------------------------------------------- the hard prohibitions
def test_stage2br_package_cannot_reach_training_or_data_generation():
    """Master prompt §11.1/§11.2: no training or episode generation is callable from this package."""
    forbidden = ("certo_fdi.data.generate", "certo_fdi.data.fault_injection", "certo_fdi.models",
                 "certo_fdi.experiments.training", "torch")
    pkg = ROOT / "src" / "certo_fdi" / "stage2br"
    for path in sorted(pkg.glob("*.py")):
        tree = ast.parse(path.read_text())
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        for n in names:
            assert not any(n == f or n.startswith(f + ".") for f in forbidden), f"{path.name} imports {n}"


def test_config_forbids_training_and_data_generation():
    assert CFG["execution"]["no_training"] is True
    assert CFG["execution"]["no_data_generation"] is True
    assert CFG["frozen_inputs"]["regenerate_data"] is False
    assert CFG["frozen_inputs"]["retrain_model"] is False


def test_blocking_diff_classes_cover_science_config_and_data():
    assert set(CFG["blocking_diff_classes"]) == {
        "SCIENTIFIC_COMPUTATION", "CONFIG_OR_THRESHOLDS", "DATA_OR_SPLITS"}
    assert set(CFG["blocking_diff_classes"]) <= set(CFG["git_diff_audit_classes"])
