"""The frozen Stage 2B-F protocol: estimator identity, naming, precedence, decision guard.

Committed with the rules and BEFORE any Stage 2B-F score exists. These pin the two things that make
this stage trustworthy at all: each estimator is bound to the frozen code that produced the
historical numbers (not a lookalike), and the scientific decision cannot be reached except through
the frozen function after an integrity PASS.
"""

from __future__ import annotations

import ast
import inspect
import subprocess
from pathlib import Path

import numpy as np
import pytest
import yaml

from certo_fdi.pathways import geometry as G
from certo_fdi.stage2b import rank_aware_scores as RS
from certo_fdi.stage2b.decision_stage2b import DECISION_VOCABULARY
from certo_fdi.stage2bf import estimator_identity as EI
from certo_fdi.stage2bf.decision_stage2bf import (
    FORBIDDEN_EVIDENCE_SECTIONS,
    INTEGRITY_PRECEDENCE,
    NOT_RUN,
    PASS_STATE,
    SCIENTIFIC_VOCABULARY,
    combined_terminal,
    evidence_delta,
    integrity_state,
    run_scientific_decision,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "stage2bf_estimator_harmonization.yaml").read_text())


def _ok_evidence() -> dict:
    return {k: True for k in (
        "input_provenance_ok", "base_head_matches", "scientific_code_identical",
        "decision_code_identical", "reference_score_precision_ok", "ridge_reproduction_ok",
        "svd_reproduction_ok", "historical_artifacts_unchanged")}


# ------------------------------------------------------------------ code identity
def test_ridge_wrapper_calls_the_frozen_stage2a_function_not_a_rewrite():
    """The wrapper must delegate to batched_projection; a reimplementation defeats the stage."""
    src = inspect.getsource(EI.stage2a_ridge_residual_norm)
    assert "batched_projection(" in src
    # and it must not build its own normal equations
    for forbidden in ("np.linalg.solve", "np.linalg.inv", "np.linalg.lstsq", "@ D", "D.T @"):
        assert forbidden not in src, f"wrapper appears to reimplement the solve: {forbidden}"


def test_svd_wrapper_calls_the_frozen_stage2b_function():
    src = inspect.getsource(EI.truncated_svd_orthogonal_projection_rss)
    assert "_svd_project(" in src
    assert "np.linalg.svd" not in src


def test_geometry_is_byte_identical_at_stage2a_and_stage2b_commits():
    """Importing geometry.py here IS reusing Stage 2A's frozen code -- asserted, not assumed."""
    def tree(ref, path):
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", f"{ref}:{path}"],
                                       text=True).strip()
    p = "src/certo_fdi/pathways/geometry.py"
    assert tree("bcf2ad5", p) == tree("bee5f9b", p) == tree("HEAD", p)


def test_frozen_scientific_files_match_the_scientific_commit():
    def tree(ref, path):
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", f"{ref}:{path}"],
                                       text=True).strip()
    for p in CFG["frozen_scientific_files"]:
        assert tree("bee5f9b", p) == tree("HEAD", p), p


# ------------------------------------------------------------------ the ridge formula
def test_ridge_lambda_is_exactly_the_frozen_rule():
    assert G.LAMBDA_RELATIVE == 1e-6 and G.CONDITION_MAX == 1e6 and G.LAMBDA_ABSOLUTE_FLOOR == 1e-12
    assert CFG["estimators"]["stage2a_ridge"]["lambda_relative"] == G.LAMBDA_RELATIVE
    assert CFG["estimators"]["stage2a_ridge"]["condition_max"] == G.CONDITION_MAX
    assert CFG["estimators"]["stage2a_ridge"]["lambda_absolute_floor"] == G.LAMBDA_ABSOLUTE_FLOOR
    rng = np.random.default_rng(0)
    for _ in range(20):
        D = rng.normal(size=(12, 3))
        s = np.linalg.svd(D, compute_uv=False)
        expected = max(1e-6 * s[0] ** 2, s[0] ** 2 / 1e6, 1e-12)
        assert float(G.ridge_lambda(D)) == pytest.approx(expected, rel=1e-15)


def test_ridge_lambda_floor_applies_to_a_zero_dictionary():
    assert float(G.ridge_lambda(np.zeros((6, 3)))) == 1e-12


def test_ridge_residual_matches_the_explicit_ridge_solution():
    """The wrapper's output must equal the textbook ridge residual for the same lambda."""
    rng = np.random.default_rng(7)
    D = rng.normal(size=(1, 20, 3))
    z = rng.normal(size=(1, 20))
    out = EI.stage2a_ridge_residual_norm(D, z)
    lam = float(out.ridge_lambda[0])
    theta = np.linalg.solve(D[0].T @ D[0] + lam * np.eye(3), D[0].T @ z[0])
    assert float(out.residual_norm[0]) == pytest.approx(float(np.linalg.norm(z[0] - D[0] @ theta)), rel=1e-9)
    assert float(out.residual_energy[0]) == pytest.approx(float(out.residual_norm[0]) ** 2, rel=1e-9)


# ------------------------------------------------------------------ the SVD formula
def test_svd_projector_matches_a_hand_built_orthogonal_projection():
    rng = np.random.default_rng(11)
    D = rng.normal(size=(1, 20, 3))
    z = rng.normal(size=(1, 20))
    out = EI.truncated_svd_orthogonal_projection_rss(D, z)
    U, s, _ = np.linalg.svd(D[0], full_matrices=False)
    Uk = U[:, s > s[0] * 1e-8]
    P = Uk @ Uk.T
    assert float(out["residual_energy"][0]) == pytest.approx(float(np.sum((z[0] - P @ z[0]) ** 2)), rel=1e-12)
    assert int(out["rank"][0]) == int(Uk.shape[1])


def test_rank_tolerance_is_the_frozen_constant():
    assert RS.RANK_RTOL == 1e-8 == CFG["estimators"]["stage2b_svd"]["rank_rtol"]


# ------------------------------------------------------------------ the estimators differ
def test_norm_and_energy_are_monotone_and_cannot_reorder_links():
    rng = np.random.default_rng(3)
    v = rng.random((200, 7)) + 0.05
    assert np.array_equal(np.argmin(v, axis=1), np.argmin(v ** 2, axis=1))


@pytest.mark.parametrize("ratio", [1e-3, 1e-4, 1e-5, 1e-6])
def test_ridge_and_svd_differ_on_a_constructed_intermediate_singular_value(ratio):
    """The two estimators MUST disagree in the band; equality here would falsify the whole stage."""
    d = 24
    U = np.linalg.qr(np.random.default_rng(5).normal(size=(d, d)))[0]
    D = (U[:, :2] * np.array([1.0, ratio]))[None]
    z = (U[:, 0] + U[:, 1])[None]                 # equal energy in both directions
    r = float(EI.stage2a_ridge_residual_norm(D, z).residual_energy[0])
    s = float(EI.truncated_svd_orthogonal_projection_rss(D, z)["residual_energy"][0])
    frac = abs(r - s) / float(z[0] @ z[0])
    assert frac > 0.1, f"estimators agreed at sigma ratio {ratio}: gap {frac:.3e}"


@pytest.mark.parametrize("ratio", [1e-1, 1e-2, 1e-9, 1e-10])
def test_ridge_and_svd_agree_outside_the_band(ratio):
    d = 24
    U = np.linalg.qr(np.random.default_rng(5).normal(size=(d, d)))[0]
    D = (U[:, :2] * np.array([1.0, ratio]))[None]
    z = (U[:, 0] + U[:, 1])[None]
    r = float(EI.stage2a_ridge_residual_norm(D, z).residual_energy[0])
    s = float(EI.truncated_svd_orthogonal_projection_rss(D, z)["residual_energy"][0])
    assert abs(r - s) / float(z[0] @ z[0]) < 1e-3


def test_gains_have_the_declared_shapes():
    sig = np.array([1.0, 1e-4, 1e-9])
    g_r = EI.ridge_gain(sig, 1e-6)
    g_s = EI.svd_gain(sig)
    assert np.all((g_r > 0) & (g_r < 1))                 # continuous, never 0 or exactly 1
    assert set(np.unique(g_s)) <= {0.0, 1.0}             # hard
    assert g_s.tolist() == [1.0, 1.0, 0.0]


def test_ridge_on_an_orthonormal_dictionary_nearly_equals_the_projector():
    """The caveat the mechanism report must state: orthonormalised controls collapse the contrast."""
    d = 32
    Q = np.linalg.qr(np.random.default_rng(2).normal(size=(d, 4)))[0]
    z = np.random.default_rng(3).normal(size=(1, d))
    r = float(EI.stage2a_ridge_residual_norm(Q[None], z).residual_energy[0])
    s = float(EI.truncated_svd_orthogonal_projection_rss(Q[None], z)["residual_energy"][0])
    assert abs(r - s) / max(abs(s), 1e-300) < 1e-4
    assert set(CFG["orthonormalised_controls"]) == {
        "support_prefix_rankmatched", "random_within_support_rankmatched", "fixed_reference_jacobian"}
    assert set(CFG["raw_dictionary_controls"]) == {"time_aligned_jacobian", "shuffled_time_jacobian"}


# ------------------------------------------------------------------ candidate reduction
def test_candidate_reduction_takes_the_min_and_reports_the_first_on_a_tie():
    s = np.array([[5.0, 3.0], [3.0, 9.0], [7.0, 1.0]])   # (n_candidates, N)
    best, idx = EI.best_candidate_reduction(s)
    assert best.tolist() == [3.0, 1.0]
    assert idx.tolist() == [1, 2]
    tie = np.array([[2.0], [2.0]])
    assert EI.best_candidate_reduction(tie)[1].tolist() == [0]


# ------------------------------------------------------------------ naming
def test_legacy_mapping_matches_the_config():
    assert EI.LEGACY_NAME_MAPPING == CFG["legacy_name_mapping"]
    assert EI.SVD_CANONICAL == "truncated_svd_orthogonal_projection_rss"
    assert EI.RIDGE_CANONICAL == "stage2a_ridge_residual_norm"


def test_canonical_name_maps_legacy_and_passes_canonical_through():
    assert EI.canonical_name("raw_projection_residual") == EI.SVD_CANONICAL
    assert EI.canonical_name(EI.SVD_CANONICAL) == EI.SVD_CANONICAL
    assert EI.canonical_name("rank_aware_glrt") == "rank_aware_glrt"
    with pytest.raises(KeyError):
        EI.canonical_name("not_a_score")


def test_new_results_may_not_carry_renamed_legacy_names():
    EI.assert_no_legacy_names({"score": EI.SVD_CANONICAL, "n": 3})
    with pytest.raises(ValueError, match="legacy estimator name"):
        EI.assert_no_legacy_names({"score": "raw_projection_residual"})
    with pytest.raises(ValueError):
        EI.assert_no_legacy_names("df_normalized_residual is here")
    # names that did not change are allowed
    EI.assert_no_legacy_names({"score": "rank_aware_glrt", "rule": "minimal_consistent_link"})


def test_identity_map_covers_every_candidate_and_the_ridge_baseline():
    rows = EI.identity_map_rows()
    canon = {r["canonical_name"] for r in rows}
    assert set(CFG["stage2b_candidate_selection"]["candidates"]) <= canon
    assert EI.RIDGE_CANONICAL in canon
    ridge = next(r for r in rows if r["canonical_name"] == EI.RIDGE_CANONICAL)
    assert ridge["selection_role"] == "audit_baseline"
    for r in rows:
        assert r["historical_source_commit"] and r["source_file"]


def test_ridge_is_not_a_stage2b_selection_candidate():
    assert EI.RIDGE_CANONICAL not in CFG["stage2b_candidate_selection"]["candidates"]
    assert CFG["stage2b_candidate_selection"]["ridge_is_audit_only"] is True
    assert CFG["stage2b_candidate_selection"]["final_test_may_not_select"] is True
    assert len(CFG["stage2b_candidate_selection"]["candidates"]) == 5


# ------------------------------------------------------------------ integrity precedence
def test_precedence_matches_the_config_and_the_contract():
    assert tuple(CFG["integrity_precedence"]) == INTEGRITY_PRECEDENCE
    assert INTEGRITY_PRECEDENCE[-1] == PASS_STATE


@pytest.mark.parametrize(("key", "expected"), [
    ("input_provenance_ok", "BLOCKED_INPUT_PROVENANCE"),
    ("base_head_matches", "BLOCKED_BASE_HEAD_MISMATCH"),
    ("scientific_code_identical", "BLOCKED_SCIENTIFIC_CODE_MISMATCH"),
    ("decision_code_identical", "BLOCKED_DECISION_CODE_MISMATCH"),
    ("reference_score_precision_ok", "BLOCKED_MISSING_REFERENCE_SCORE_PRECISION"),
    ("ridge_reproduction_ok", "BLOCKED_STAGE2A_RIDGE_REPRODUCTION"),
    ("svd_reproduction_ok", "BLOCKED_STAGE2B_SVD_REPRODUCTION"),
    ("historical_artifacts_unchanged", "BLOCKED_HISTORICAL_ARTIFACT_MUTATION"),
])
def test_each_failure_selects_its_own_state(key, expected):
    assert integrity_state({**_ok_evidence(), key: False}, CFG)["integrity_state"] == expected


def test_all_gates_passing_gives_the_pass_state():
    out = integrity_state(_ok_evidence(), CFG)
    assert out["integrity_state"] == PASS_STATE
    assert out["scientific_decision_permitted"] is True


def test_precedence_is_strict_when_several_fail():
    ev = {k: False for k in _ok_evidence()}
    assert integrity_state(ev, CFG)["integrity_state"] == "BLOCKED_INPUT_PROVENANCE"
    ev["input_provenance_ok"] = True
    assert integrity_state(ev, CFG)["integrity_state"] == "BLOCKED_BASE_HEAD_MISMATCH"


def test_empty_evidence_blocks_rather_than_passing():
    out = integrity_state({}, CFG)
    assert out["integrity_state"] == "BLOCKED_INPUT_PROVENANCE"
    assert out["scientific_decision_permitted"] is False


# ------------------------------------------------------------------ the decision guard
def test_scientific_decision_refuses_without_an_integrity_pass():
    called = []

    def spy(ev, thr):
        called.append(1)
        return {"decision": "GO_CONTACT_LOADPATH_MONITOR"}

    bad = integrity_state({**_ok_evidence(), "ridge_reproduction_ok": False}, CFG)
    out = run_scientific_decision(bad, {}, {}, decide_fn=spy)
    assert out["stage2bf_scientific_decision"] == NOT_RUN
    assert out["decision_function_called"] is False
    assert not called, "the decision function must not be reached when integrity fails"


def test_scientific_decision_runs_only_through_the_frozen_function():
    out = run_scientific_decision(integrity_state(_ok_evidence(), CFG), {}, {},
                                  decide_fn=lambda e, t: {"decision": "NO_GO_CONTACT_PRODUCT"})
    assert out["decision_function_called"] is True
    assert out["stage2bf_scientific_decision"] == "NO_GO_CONTACT_PRODUCT"


def test_a_terminal_state_outside_the_frozen_vocabulary_is_rejected():
    with pytest.raises(ValueError, match="outside the frozen vocabulary"):
        run_scientific_decision(integrity_state(_ok_evidence(), CFG), {}, {},
                                decide_fn=lambda e, t: {"decision": "GO_BECAUSE_I_SAID_SO"})


def test_vocabulary_is_exactly_the_frozen_stage2b_one():
    assert set(SCIENTIFIC_VOCABULARY) == set(DECISION_VOCABULARY)
    assert set(CFG["scientific_decision"]["vocabulary"]) == set(DECISION_VOCABULARY)


def test_no_terminal_state_is_hard_coded_in_the_wrapper():
    """The wrapper may name the vocabulary, but must not assign a decision to a variable."""
    src = (ROOT / "src" / "certo_fdi" / "stage2bf" / "decision_stage2bf.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in ast.walk(node.value):
                if isinstance(t, ast.Constant) and t.value in (
                        "GO_CONTACT_LOADPATH_MONITOR", "NO_GO_CONTACT_PRODUCT",
                        "PIVOT_SUPPORT_ONLY_LOCALIZER"):
                    parent_ok = isinstance(node.targets[0], ast.Name) and node.targets[0].id in (
                        "SCIENTIFIC_VOCABULARY",)
                    assert parent_ok, "a scientific terminal state is assigned in the wrapper"


def test_combined_terminal_format():
    assert combined_terminal(PASS_STATE, "NO_GO_CONTACT_PRODUCT") == \
        "PASS_ESTIMATOR_HARMONIZATION__NO_GO_CONTACT_PRODUCT"


# ------------------------------------------------------------------ evidence delta
def test_evidence_delta_allows_the_gate_and_blocks_a_metric():
    hist = {"reproduction_gate": {"contact_localizer": "FAIL"},
            "evidence": {"detection": {"event_tpr": 0.5}}}
    good = {"reproduction_gate": {"contact_localizer": "PASS"},
            "evidence": {"detection": {"event_tpr": 0.5}}}
    bad = {"reproduction_gate": {"contact_localizer": "PASS"},
           "evidence": {"detection": {"event_tpr": 0.9}}}
    allowed = ("reproduction_gate", "contact_reproduction", "integrity", "schema_and_name_migration")
    assert evidence_delta(hist, good, allowed)["clean"] is True
    out = evidence_delta(hist, bad, allowed)
    assert out["clean"] is False
    assert any(v["path"].endswith("event_tpr") for v in out["violations"])


def test_forbidden_sections_cover_every_scientific_block():
    assert set(FORBIDDEN_EVIDENCE_SECTIONS) == set(CFG["evidence_delta_policy"]["forbidden"]) - {
        "thresholds", "decision_order"}


def test_config_forbids_training_and_regeneration():
    e = CFG["execution"]
    for k in ("train_models", "regenerate_data", "modify_whitening", "modify_dictionaries",
              "modify_candidate_points", "modify_rank_tolerance", "modify_ridge_lambda",
              "modify_stage2b_thresholds"):
        assert e[k] is False, k
    assert CFG["scientific_decision"]["manual_override_forbidden"] is True
    assert CFG["scientific_decision"]["historical_stage2b_decision_remains"] == "BLOCKED"
    assert CFG["statistics"]["window_iid_bootstrap_forbidden"] is True
    assert CFG["statistics"]["independent_unit"] == "episode"


def test_stage2bf_package_cannot_reach_training_or_data_generation():
    forbidden = ("certo_fdi.data.generate", "certo_fdi.data.fault_injection", "certo_fdi.models")
    for path in sorted((ROOT / "src" / "certo_fdi" / "stage2bf").glob("*.py")):
        tree = ast.parse(path.read_text())
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        for n in names:
            assert not any(n == f or n.startswith(f + ".") for f in forbidden), f"{path.name}: {n}"
