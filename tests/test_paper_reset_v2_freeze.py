"""Paper Reset V2 protocol-freeze integrity tests.

Guards that (a) the frozen V2 contract package still matches the SHA256SUMS
shipped inside the kickoff ZIP, (b) configs/paper_reset_v2.yaml has not
drifted from the numeric gates encoded in decision.py v2, and (c) the decision
code resolves the contract's terminal states with the frozen priority.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from certo_fdi_reset_v2 import decision as d2

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = REPO_ROOT / "contracts" / "paper_reset_v2"
CONFIG_PATH = REPO_ROOT / "configs" / "paper_reset_v2.yaml"

KICKOFF_ZIP_SHA256 = "a822d62a9167bce97602894249bb4b893a6ac26989f2b03e3206fdfc648f4413"

EXPECTED_CONTRACT_FILES = {
    "01_MASTER_PROMPT.md",
    "02_ONE_SHOT_LAUNCHER.md",
    "03_EXPECTED_DELIVERABLES.md",
    "04_DECISION_RULES.yaml",
    "SHA256SUMS.txt",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(1 << 20):
            h.update(block)
    return h.hexdigest()


@pytest.fixture(scope="module")
def config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contract_rules() -> dict:
    return yaml.safe_load(
        (CONTRACTS / "04_DECISION_RULES.yaml").read_text(encoding="utf-8")
    )


def test_contract_package_present_and_complete():
    assert CONTRACTS.is_dir(), "frozen V2 contract package missing"
    files = {p.name for p in CONTRACTS.iterdir() if p.is_file()}
    assert files == EXPECTED_CONTRACT_FILES, files


def test_every_contract_file_matches_shipped_checksum():
    entries = []
    for line in (CONTRACTS / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(maxsplit=1)
        entries.append((digest, name.lstrip("*")))
    assert entries, "SHA256SUMS.txt is empty"
    for digest, name in entries:
        target = CONTRACTS / name
        assert target.is_file(), f"contract file missing: {name}"
        assert _sha256(target) == digest, f"contract file modified after freeze: {name}"


def test_config_matches_contract_literature_gate(config, contract_rules):
    lit = contract_rules["literature_gate"]
    assert config["literature"]["screened_min"] == lit["screened_min"] == d2.LIT_SCREENED_MIN
    assert config["literature"]["fulltext_min"] == lit["fulltext_min"] == d2.LIT_FULLTEXT_MIN
    assert (
        config["literature"]["direct_neighbors_min"]
        == lit["direct_neighbors_min"]
        == d2.LIT_DIRECT_NEIGHBORS_MIN
    )
    assert (
        config["literature"]["killer_dossiers_min"]
        == lit["killer_dossiers_min"]
        == d2.LIT_KILLER_DOSSIERS_MIN
    )
    assert (
        config["literature"]["direct_2025_2026_min"]
        == lit["direct_2025_2026_min"]
        == d2.LIT_DIRECT_2025_2026_MIN
    )
    assert (
        config["literature"]["dataset_code_papers_min"]
        == lit["dataset_code_papers_min"]
        == d2.LIT_DATASET_CODE_PAPERS_MIN
    )
    assert (
        config["literature"]["citation_chains_min"]
        == lit["citation_chains_min"]
        == d2.LIT_CITATION_CHAINS_MIN
    )


def test_config_matches_contract_survival_gate(config, contract_rules):
    ms_contract = contract_rules["method_survival"]
    ms_config = config["method_survival"]
    assert (
        ms_config["min_datasets_with_gain"]
        == ms_contract["min_datasets_with_gain"]
        == d2.SURVIVAL_MIN_DATASETS_WITH_GAIN
    )
    assert ms_config["auroc_gain"] == ms_contract["auroc_gain"] == d2.SURVIVAL_AUROC_GAIN
    assert ms_config["auprc_gain"] == ms_contract["auprc_gain"] == d2.SURVIVAL_AUPRC_GAIN
    assert (
        ms_config["max_relative_fpr_tpr90_worsening"]
        == ms_contract["max_relative_fpr_tpr90_worsening"]
        == d2.SURVIVAL_MAX_RELATIVE_FPR_TPR90_WORSENING
    )
    assert (
        ms_config["min_concordant_seeds"]
        == ms_contract["min_concordant_seeds"]
        == d2.SURVIVAL_MIN_CONCORDANT_SEEDS
    )
    assert ms_contract["require_random_feature_control"] is True
    assert ms_contract["require_multi_permutation_control"] is True


def test_terminal_states_match_contract(contract_rules):
    contract_states = set(contract_rules["terminal_states"])
    code_states = {s.value for s in d2.FinalStateV2}
    assert code_states == contract_states


def test_mandatory_datasets_match_contract(config, contract_rules):
    assert list(d2.MANDATORY_DATASETS) == contract_rules["benchmark_gate"]["mandatory_datasets"]
    assert config["mandatory_datasets"] == list(d2.MANDATORY_DATASETS)


def test_no_test_anomaly_tuning_frozen(config):
    assert config["training"]["tune_on_test_anomalies"] is False
    assert config["baselines"]["point_adjustment_in_main_results"] is False


def test_decision_blocked_dominates():
    e = d2.DecisionEvidenceV2(
        literature_gate=d2.LiteratureGateV2.BLOCKED_ACCESS,
        benchmark_gate=d2.BenchmarkGateV2.PASS,
        method_survival_gate=d2.MethodSurvivalGate.PASS,
        story_gate=d2.StoryGate.PASS,
        killer_paper_occupies_final_story=True,
    )
    assert d2.resolve_final_state(e) is d2.FinalStateV2.BLOCKED


def test_decision_killer_paper_beats_go():
    counts = d2.LiteratureCounts(500, 100, 35, 15, 25, 20, 10)
    e = d2.DecisionEvidenceV2(
        literature_gate=d2.LiteratureGateV2.PASS,
        benchmark_gate=d2.BenchmarkGateV2.PASS,
        method_survival_gate=d2.MethodSurvivalGate.PASS,
        story_gate=d2.StoryGate.PASS,
        literature_counts=counts,
        killer_paper_occupies_final_story=True,
    )
    assert d2.resolve_final_state(e) is d2.FinalStateV2.NO_GO_NOVELTY_OCCUPIED


def _full_go_evidence(tro: bool) -> d2.DecisionEvidenceV2:
    return d2.DecisionEvidenceV2(
        literature_gate=d2.LiteratureGateV2.PASS,
        benchmark_gate=d2.BenchmarkGateV2.PASS,
        method_survival_gate=d2.MethodSurvivalGate.PASS,
        story_gate=d2.StoryGate.PASS,
        literature_counts=d2.LiteratureCounts(500, 100, 35, 15, 25, 20, 10),
        all_final_contributions_have_neighbors=True,
        no_unresolved_doi_or_status_conflicts=True,
        mandatory_datasets_complete=3,
        native_baseline_per_mandatory_dataset=True,
        universal_baseline_matrix_complete=True,
        deep_models_have_min_seeds=True,
        survival_transfer_or_few_shot_win=True,
        geometry_beats_random_feature_control=True,
        chain_beats_permutation_controls=True,
        gain_not_explained_by_capacity=True,
        coherent_robot_science_question=True,
        not_generic_mtsad_dataset_swap=True,
        explicit_failure_mechanism_targeted=True,
        event_level_results_present=True,
        real_robot_followup_plan=True,
        single_figure_story=True,
        tro_theory_and_system_completeness=tro,
    )


def test_decision_full_pass_is_tro_go():
    assert d2.resolve_final_state(_full_go_evidence(tro=True)) is d2.FinalStateV2.PAPER_GO_TRO_CANDIDATE


def test_decision_without_tro_completeness_is_icra_rss_go():
    assert (
        d2.resolve_final_state(_full_go_evidence(tro=False))
        is d2.FinalStateV2.PAPER_GO_ICRA_RSS_CANDIDATE
    )


def test_decision_short_literature_is_inconclusive():
    e = d2.DecisionEvidenceV2(
        literature_gate=d2.LiteratureGateV2.INCONCLUSIVE,
        benchmark_gate=d2.BenchmarkGateV2.PARTIAL,
        method_survival_gate=d2.MethodSurvivalGate.NOT_RUN,
        story_gate=d2.StoryGate.NOT_EVALUATED,
        literature_counts=d2.LiteratureCounts(499, 100, 35, 15, 25, 20, 10),
    )
    assert (
        d2.resolve_final_state(e)
        is d2.FinalStateV2.LITERATURE_OR_BENCHMARK_INCONCLUSIVE
    )


def test_decision_survival_fail_without_pivot_is_no_go_method():
    e = d2.DecisionEvidenceV2(
        literature_gate=d2.LiteratureGateV2.PASS,
        benchmark_gate=d2.BenchmarkGateV2.PASS,
        method_survival_gate=d2.MethodSurvivalGate.FAIL,
        story_gate=d2.StoryGate.FAIL,
        literature_counts=d2.LiteratureCounts(500, 100, 35, 15, 25, 20, 10),
        mandatory_datasets_complete=3,
        native_baseline_per_mandatory_dataset=True,
        universal_baseline_matrix_complete=True,
        deep_models_have_min_seeds=True,
    )
    assert d2.resolve_final_state(e) is d2.FinalStateV2.NO_GO_CURRENT_METHOD_PUBLIC_DATA


def test_decision_survival_fail_with_benchmark_value_is_pivot():
    e = d2.DecisionEvidenceV2(
        literature_gate=d2.LiteratureGateV2.PASS,
        benchmark_gate=d2.BenchmarkGateV2.PASS,
        method_survival_gate=d2.MethodSurvivalGate.FAIL,
        story_gate=d2.StoryGate.FAIL,
        literature_counts=d2.LiteratureCounts(500, 100, 35, 15, 25, 20, 10),
        mandatory_datasets_complete=3,
        native_baseline_per_mandatory_dataset=True,
        universal_baseline_matrix_complete=True,
        deep_models_have_min_seeds=True,
        benchmark_negative_results_have_standalone_value=True,
    )
    assert d2.resolve_final_state(e) is d2.FinalStateV2.PIVOT_BENCHMARK_DATASET_PAPER


def test_explain_final_state_is_audit_complete():
    e = _full_go_evidence(tro=True)
    out = d2.explain_final_state(e)
    assert out["final_state"] == "PAPER_GO_TRO_CANDIDATE"
    assert out["decision_code_version"] == d2.DECISION_CODE_VERSION
    assert set(out["predicate_matches"]) == {s.value for s in d2.FinalStateV2}
    assert out["priority_order"][0] == "BLOCKED"
