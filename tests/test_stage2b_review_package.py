"""The review package matches the §10 topology and its smoke check actually checks things."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from certo_fdi.packaging import build_review_package_stage2b as B
from certo_fdi.stage2b.decision_stage2b import DECISION_VOCABULARY

ROOT = Path(__file__).resolve().parents[1]

#: kickoff §10.1, verbatim
THIN_TOPOLOGY = ["00_READ_ME_FIRST.md", "01_INDEPENDENT_REVIEW_PROMPT.md", "02_EXECUTION_SUMMARY.md",
                 "03_DECISION_MEMO.md", "04_KNOWN_ISSUES.md", "05_CLAIMS_LEDGER.csv", "06_FILE_TREE.txt",
                 "07_MANIFEST.json", "08_SHA256SUMS.txt", "09_GIT_PROVENANCE", "10_CONFIGS",
                 "11_CODE_SNAPSHOT", "12_TEST_REPORTS", "13_CORE_RESULTS", "14_SELECTED_FIGURES",
                 "15_REPRODUCE_REVIEW.sh"]


def test_thin_topology_is_the_contract_topology():
    declared = list(B.REQUIRED_FILES) + list(B.REQUIRED_DIRECTORIES)
    for entry in THIN_TOPOLOGY:
        assert entry in declared, entry
    # the status file is an addition, not a substitution
    assert "REVIEW_PACKAGE_STATUS.json" in B.REQUIRED_FILES
    assert len(set(declared)) == len(declared)


def test_core_results_covers_every_hard_result_file():
    """§13's hard result list must be shippable in the thin package."""
    hard = ["stage2b_input_freeze.json", "stage2b_baseline_reproduction.csv",
            "stage2b_contact_calibration_manifest.csv", "stage2b_loadpath_controls.csv",
            "stage2b_rank_audit.csv", "stage2b_localizer_selection.csv",
            "stage2b_localization_metrics.csv", "stage2b_selective_risk.csv",
            "stage2b_context_calibration.csv", "stage2b_sequential_metrics.csv",
            "stage2b_event_metrics.csv", "stage2b_healthy_learning_curve.csv",
            "stage2b_episode_bootstrap.csv", "stage2b_literature_verification.md",
            "stage2b_claim_ledger.csv", "stage2b_decision_evidence.json",
            "stage2b_decision_memo.md", "stage2b_known_issues.md", "stage2b_run_manifest.json"]
    missing = [h for h in hard if h not in B.CORE_RESULTS]
    assert not missing, missing


def test_the_smoke_script_is_valid_python_and_checks_all_six_contract_items():
    m = re.search(r"python3 - <<'PY'\n(.*?)\nPY\n", B.REPRODUCE_SCRIPT, re.S)
    assert m, "the smoke script must embed a python heredoc"
    body = m.group(1)
    ast.parse(body)                                        # it must at least compile
    for needle, what in [
        ("stage2b_input_freeze", "input hashes"),
        ("dataset_content_manifest_expected", "dataset manifest match"),
        ("stage2b_reproduction_gate", "baseline reproduction gate"),
        ("localizer selection touched a forbidden partition", "selection partition check"),
        ("sequential tuning touched a forbidden partition", "tuning partition check"),
        ("run manifest and decision evidence disagree", "decision/memo agreement"),
        ("missing hard result file", "hard result file existence"),
        ("was rewritten", "historical PR head check"),
    ]:
        assert needle in body, f"the smoke script does not verify: {what}"


def test_the_smoke_script_knows_the_exact_decision_vocabulary():
    m = re.search(r"allowed = \{(.*?)\}", B.REPRODUCE_SCRIPT, re.S)
    assert m
    listed = set(re.findall(r"'([A-Z_]+)'", m.group(1)))
    assert listed == set(DECISION_VOCABULARY)


def test_the_smoke_script_fails_a_package_that_is_missing_a_hard_result(tmp_path):
    """A negative control: the check must reject, not silently pass."""
    pkg = tmp_path / "pkg"
    (pkg / "13_CORE_RESULTS").mkdir(parents=True)
    (pkg / "07_MANIFEST.json").write_text("{}")
    script = pkg / "15_REPRODUCE_REVIEW.sh"
    script.write_text(B.REPRODUCE_SCRIPT)
    script.chmod(0o755)
    p = subprocess.run(["bash", str(script), "--smoke"], cwd=pkg, capture_output=True, text=True)
    assert p.returncode != 0
    assert "missing hard result file" in (p.stdout + p.stderr)


def test_the_smoke_script_rejects_a_decision_outside_the_vocabulary(tmp_path):
    pkg = tmp_path / "pkg"
    core = pkg / "13_CORE_RESULTS"
    core.mkdir(parents=True)
    (pkg / "07_MANIFEST.json").write_text("{}")
    header = ("run_id,git_sha,config_sha,dataset_manifest_sha,partition,split,seed,method,fault_family,"
              "status,provisional,strict,empirical\n")
    row = "r,g,c,d,F4_CAL,ALL,1,m,F4_contact,OK,False,False,True\n"
    for name in ["stage2b_baseline_reproduction.csv", "stage2b_contact_calibration_manifest.csv",
                 "stage2b_loadpath_controls.csv", "stage2b_rank_audit.csv", "stage2b_localizer_selection.csv",
                 "stage2b_localization_metrics.csv", "stage2b_selective_risk.csv",
                 "stage2b_context_calibration.csv", "stage2b_event_metrics.csv",
                 "stage2b_healthy_learning_curve.csv", "stage2b_episode_bootstrap.csv",
                 "stage2b_claim_ledger.csv"]:
        (core / name).write_text(header + row)
    (core / "stage2b_sequential_metrics.csv").write_text(
        header.replace(",partition,", ",partition,").replace("F4_CAL", "healthy_val")
        + row.replace("F4_CAL", "healthy_val"))
    (core / "stage2b_input_freeze.json").write_text(json.dumps(
        {"gate": "PASS", "stage2a_git_sha": "abc", "dataset_content_manifest_sha256": "x",
         "dataset_content_manifest_expected": "x", "historical_branch_heads": []}))
    (core / "stage2b_decision_evidence.json").write_text(json.dumps({"decision": "GO_EVERYTHING_IS_FINE"}))
    (core / "stage2b_decision_memo.md").write_text("# whatever\n")
    (core / "stage2b_known_issues.md").write_text("# issues\n")
    (core / "stage2b_run_manifest.json").write_text(json.dumps({"decision": "GO_EVERYTHING_IS_FINE"}))
    (core / "stage2b_literature_verification.md").write_text("# lit\n")
    script = pkg / "15_REPRODUCE_REVIEW.sh"
    script.write_text(B.REPRODUCE_SCRIPT)
    p = subprocess.run(["bash", str(script), "--smoke"], cwd=pkg, capture_output=True, text=True)
    assert p.returncode != 0
    assert "not in the pre-registered vocabulary" in (p.stdout + p.stderr)


def test_the_smoke_script_rejects_selection_on_the_final_test_partition(tmp_path):
    pkg = tmp_path / "pkg"
    core = pkg / "13_CORE_RESULTS"
    core.mkdir(parents=True)
    (pkg / "07_MANIFEST.json").write_text("{}")
    header = ("run_id,git_sha,config_sha,dataset_manifest_sha,partition,split,seed,method,fault_family,"
              "status,provisional,strict,empirical\n")
    for name in ["stage2b_baseline_reproduction.csv", "stage2b_contact_calibration_manifest.csv",
                 "stage2b_loadpath_controls.csv", "stage2b_rank_audit.csv",
                 "stage2b_localization_metrics.csv", "stage2b_selective_risk.csv",
                 "stage2b_context_calibration.csv", "stage2b_event_metrics.csv",
                 "stage2b_healthy_learning_curve.csv", "stage2b_episode_bootstrap.csv",
                 "stage2b_claim_ledger.csv"]:
        (core / name).write_text(header + "r,g,c,d,F4_TEST,ALL,1,m,F4_contact,OK,False,False,True\n")
    # the offending file: the localizer was selected on the final test set
    (core / "stage2b_localizer_selection.csv").write_text(
        header + "r,g,c,d,F4_TEST,ALL,1,m,F4_contact,OK,False,False,True\n")
    (core / "stage2b_sequential_metrics.csv").write_text(
        header + "r,g,c,d,healthy_val,ALL,1,m,,OK,False,False,True\n")
    (core / "stage2b_input_freeze.json").write_text(json.dumps(
        {"gate": "PASS", "stage2a_git_sha": "abc", "dataset_content_manifest_sha256": "x",
         "dataset_content_manifest_expected": "x", "historical_branch_heads": []}))
    (core / "stage2b_decision_evidence.json").write_text(json.dumps({"decision": "NO_GO_CONTACT_PRODUCT"}))
    (core / "stage2b_decision_memo.md").write_text("# Stage 2B decision memo — NO_GO_CONTACT_PRODUCT\n")
    (core / "stage2b_known_issues.md").write_text("# issues\n")
    (core / "stage2b_run_manifest.json").write_text(json.dumps({"decision": "NO_GO_CONTACT_PRODUCT"}))
    (core / "stage2b_literature_verification.md").write_text("# lit\n")
    script = pkg / "15_REPRODUCE_REVIEW.sh"
    script.write_text(B.REPRODUCE_SCRIPT)
    p = subprocess.run(["bash", str(script), "--smoke"], cwd=pkg, capture_output=True, text=True)
    assert p.returncode != 0
    assert "forbidden partition" in (p.stdout + p.stderr)


def test_the_builder_refuses_a_decision_outside_the_vocabulary(tmp_path, monkeypatch):
    run = tmp_path / "04_runs" / "stage2b_contact_loadpath_sequential" / "run_x"
    (run / "results").mkdir(parents=True)
    (run / "results" / "stage2b_run_manifest.json").write_text(json.dumps({"decision": "GO_SHIP_IT"}))
    with pytest.raises(ValueError, match="pre-registered vocabulary"):
        B.build(run, ROOT)


def test_the_review_prompt_names_the_overturned_conclusion_and_the_hard_rules():
    p = B.REVIEW_PROMPT
    assert "overturns a conclusion of the previous stage" in p
    for rule in ["final F4 test set selected nothing", "healthy validation episodes only",
                 "episode, never the window", "exact conditional CFAR",
                 "physical wrenches", "Draft, unmerged"]:
        assert rule in p, rule
    assert "first" not in p.lower().split("the most valuable")[0].replace("first commit", "")


def test_full_package_ships_partition_manifests_but_not_episode_binaries():
    src = Path(B.__file__).read_text()
    assert "24_GENERATED_PARTITIONS" in src
    assert '"manifest.json", "episode_index.csv"' in src
    # episode .h5 files are excluded from the phase artefact copy
    assert 'exclude_suffixes=(".npz", ".h5")' in src


def test_every_required_test_suite_exists():
    from certo_fdi.experiments.run_stage2b_tests import REQUIRED_SUITES

    missing = [s for s in REQUIRED_SUITES if not (ROOT / "tests" / s).is_file()]
    assert not missing, missing
    assert len(REQUIRED_SUITES) == 12
