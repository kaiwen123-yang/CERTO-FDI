"""V2-R protocol-freeze integrity tests (contract section 18 items 1-of-16
covered here: contract byte integrity, gate equality config<->rules<->code,
decision purity; further section-18 tests live in test_paper_reset_v2r_audits)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from certo_fdi_reset_v2r import decision as d

REPO = Path(__file__).resolve().parents[1]
CONTRACTS = REPO / "contracts" / "paper_reset_v2r"
CONFIG = REPO / "configs" / "paper_reset_v2r.yaml"

EXPECTED = {
    "01_MASTER_PROMPT.md", "02_ONE_SHOT_LAUNCHER.md", "03_DECISION_RULES.yaml",
    "04_EXPECTED_OUTPUTS.md", "05_INDEPENDENT_REVIEW_PROMPT.md", "SHA256SUMS.txt",
}


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while b := fh.read(1 << 20):
            h.update(b)
    return h.hexdigest()


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load(CONFIG.read_text())


@pytest.fixture(scope="module")
def rules():
    return yaml.safe_load((CONTRACTS / "03_DECISION_RULES.yaml").read_text())


def test_contract_files_present_and_unmodified():
    files = {p.name for p in CONTRACTS.iterdir() if p.is_file()}
    assert files == EXPECTED
    for line in (CONTRACTS / "SHA256SUMS.txt").read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        assert _sha(CONTRACTS / name.lstrip("*")) == digest, name


def test_mead_gate_matches_rules_and_code(cfg, rules):
    r = rules["mead_physics_residual_gate"]
    c = cfg["gates"]["mead_physics_residual"]
    assert r["min_tasks_with_gain"] == c["min_tasks_with_gain"] == d.MEAD_MIN_TASKS_WITH_GAIN
    assert r["tasks_total"] == c["tasks_total"] == d.MEAD_TASKS_TOTAL
    assert r["auroc_gain"] == c["auroc_gain"] == d.MEAD_AUROC_GAIN
    assert r["auprc_gain"] == c["auprc_gain"] == d.MEAD_AUPRC_GAIN
    assert (r["max_relative_fpr_tpr90_worsening"] == c["max_relative_fpr_tpr90_worsening"]
            == d.MEAD_MAX_REL_FPR90_WORSENING)
    assert r["min_concordant_seeds"] == c["min_concordant_seeds"] == d.MEAD_MIN_CONCORDANT_SEEDS
    assert (r["require_earlier_detection_in_min_tasks"]
            == c["require_earlier_detection_in_min_tasks"] == d.MEAD_MIN_TASKS_EARLIER_DETECTION)


def test_ctx_gate_matches(cfg, rules):
    r = rules["context_calibration_gate"]
    c = cfg["gates"]["context_calibration"]
    assert r["min_datasets"] == c["min_datasets"] == d.CTX_MIN_DATASETS
    assert (r["min_false_alarm_reduction_fraction"]
            == c["min_false_alarm_reduction_fraction"] == d.CTX_MIN_FA_REDUCTION)
    assert r["min_frontends"] == c["min_frontends"] == d.CTX_MIN_FRONTENDS


def test_states_match_rules(rules):
    assert {s.value for s in d.AlgorithmState} == set(rules["algorithm_states"])
    assert {s.value for s in d.BenchmarkArtifactState} == set(rules["benchmark_artifact_states"])
    assert {s.value for s in d.SubmissionReadiness} == set(rules["submission_readiness"])
    assert {s.value for s in d.CombinedState} == set(rules["combined_states"])
    assert list(d.MANDATORY_DATASETS) == rules["benchmark_submission_ready"]["mandatory_datasets"]


def _ready_bench(**over):
    base = dict(
        datasets_complete=("voraus_ad", "road", "aursad", "me_ad"),
        native_or_faithful_status_explicit=True, universal_core_matrix_complete=True,
        aursad_dual_protocol_complete=True, mead_progressive_metrics_complete=True,
        claims_match_tables=True, self_contained_evidence_package=True,
        code_snapshot_or_bundle=True, per_seed_predictions_or_metrics=True,
        no_flag_csv_conflicts=True, min_two_cross_dataset_findings=True,
        no_first_claims=True, single_figure_story=True,
        independent_reviewer_smoke_pass=True,
    )
    base.update(over)
    return d.BenchmarkReadinessEvidence(**base)


def test_blocked_dominates():
    e = d.V2REvidence(integrity_or_provenance_blocked=True, bench=_ready_bench())
    assert d.resolve_combined_state(e) is d.CombinedState.BLOCKED
    e2 = d.V2REvidence(historical_state_recompute_matches=False, bench=_ready_bench())
    assert d.resolve_benchmark_state(e2) is d.BenchmarkArtifactState.BLOCKED


def test_ready_path():
    e = d.V2REvidence(bench=_ready_bench())
    assert d.resolve_benchmark_state(e) is d.BenchmarkArtifactState.SUBMISSION_READY
    assert d.resolve_submission_readiness(e) is d.SubmissionReadiness.READY_RAL_ICRA_BENCHMARK
    assert d.resolve_combined_state(e) is d.CombinedState.READY_BENCHMARK_PAPER
    assert d.resolve_algorithm_state(e) is d.AlgorithmState.NO_GO_CURRENT_METHOD_PUBLIC_DATA


def test_tro_requires_mead_gate_and_extras():
    mead_pass = d.MeadPhysicsResidualEvidence(
        tasks_with_auroc_or_auprc_gain=5, concordant_seeds=3,
        fpr90_relative_worsening_max=0.05, tasks_with_earlier_detection_at_fixed_fpr=5,
        blind_all_joint_score_holds=True, permuted_joint_control_clean=True,
        not_capacity_or_context_id_leak=True, ood_not_catastrophic=True)
    e = d.V2REvidence(bench=_ready_bench(), mead=mead_pass,
                      tro_mechanism_beyond_curation=True,
                      tro_unified_protocol_changes_field_conclusions=True,
                      tro_constructive_component_on_two_datasets=True)
    assert d.resolve_submission_readiness(e) is d.SubmissionReadiness.READY_TRO_EVALUATION_PAPER
    assert d.resolve_algorithm_state(e) is d.AlgorithmState.EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL


def test_axes_not_masked_by_combined():
    mead_pass = d.MeadPhysicsResidualEvidence(
        tasks_with_auroc_or_auprc_gain=4, concordant_seeds=2,
        fpr90_relative_worsening_max=0.0, tasks_with_earlier_detection_at_fixed_fpr=4,
        blind_all_joint_score_holds=True, permuted_joint_control_clean=True,
        not_capacity_or_context_id_leak=True, ood_not_catastrophic=True)
    e = d.V2REvidence(mead=mead_pass, bench=_ready_bench(claims_match_tables=False))
    out = d.three_axis(e)
    assert out["combined_state"] == "V2R_REOPEN_METHOD_DISCUSSION"
    assert out["benchmark_artifact_state"] == "BENCHMARK_ARTIFACT_MAJOR_REVISION"
    assert out["algorithm_state"] == "ALGORITHM_EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL"


def test_inconclusive_mead():
    e = d.V2REvidence(mead_inconclusive=True)
    assert d.resolve_algorithm_state(e) is d.AlgorithmState.INCONCLUSIVE
