"""Protocol-freeze integrity tests.

Guards that (a) the frozen contract package in the repo still matches the
SHA256SUMS shipped inside the kickoff ZIP, and (b) configs/paper_reset.yaml has
not drifted away from the numeric gates encoded in decision.py.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = REPO_ROOT / "contracts" / "paper_reset"
CONFIG_PATH = REPO_ROOT / "configs" / "paper_reset.yaml"

KICKOFF_ZIP_SHA256 = "dbb066041c50f7020b59a16a2a282d143844df2e64f0b478cd385b6f01b8e245"

# Files 00-25 plus the checksum file itself.
EXPECTED_CONTRACT_FILE_COUNT = 27


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(1 << 20):
            h.update(block)
    return h.hexdigest()


@pytest.fixture(scope="module")
def config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_contract_package_present_and_complete():
    assert CONTRACTS.is_dir(), "frozen contract package missing"
    files = sorted(p.name for p in CONTRACTS.iterdir() if p.is_file())
    assert len(files) == EXPECTED_CONTRACT_FILE_COUNT, files
    assert "01_MASTER_PROMPT.md" in files
    assert "SHA256SUMS.txt" in files


def test_every_contract_file_matches_shipped_checksum():
    sums_path = CONTRACTS / "SHA256SUMS.txt"
    entries = []
    for line in sums_path.read_text(encoding="utf-8").splitlines():
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


def test_config_records_the_verified_kickoff_zip(config):
    assert config["run"]["contract_package_sha256"] == KICKOFF_ZIP_SHA256


def test_config_gates_match_frozen_decision_code(config):
    from certo_fdi_reset import decision

    survival = config["candidate_survival"]
    assert survival["min_auroc_gain"] == decision.CANDIDATE_MIN_AUROC_GAIN
    assert survival["min_auprc_gain"] == decision.CANDIDATE_MIN_AUPRC_GAIN
    assert (
        survival["max_fpr_at_tpr90_degradation"]
        == decision.CANDIDATE_MAX_FPR_AT_TPR90_DEGRADATION
    )
    assert survival["min_mandatory_datasets"] == decision.CANDIDATE_MIN_DATASETS
    assert survival["sample_efficiency_fraction"] == decision.CANDIDATE_SAMPLE_EFFICIENCY_FRACTION

    tolerance = config["reproduction_tolerance"]
    assert tolerance["abs"] == decision.REPRODUCTION_ABS_TOLERANCE
    assert tolerance["rel"] == decision.REPRODUCTION_REL_TOLERANCE

    assert tuple(config["mandatory_datasets"]) == decision.MANDATORY_DATASETS


def test_config_matches_contract_18_literature_thresholds(config):
    template = yaml.safe_load(
        (CONTRACTS / "18_CONFIG_TEMPLATE.yaml").read_text(encoding="utf-8")
    )
    for key, expected in template["literature"].items():
        if key == "seed_queries_file":
            continue  # repo-relative path differs from the bare contract filename
        assert config["literature"][key] == expected, key
    assert config["training"]["seeds"] == template["training"]["seeds"]
    assert config["training"]["healthy_fractions"] == template["training"]["healthy_fractions"]
    assert config["training"]["tune_on_test_anomalies"] is False
    assert config["metrics"]["primary"] == template["metrics"]["primary"]
    assert config["metrics"]["secondary"] == template["metrics"]["secondary"]


def test_historical_draft_prs_are_declared_protected(config):
    assert config["repository"]["protected_draft_prs"] == [1, 2, 3, 4, 5, 6, 7]
    assert config["repository"]["auto_merge"] is False
    assert config["repository"]["keep_draft"] is True


def test_baseline_registry_ids_are_covered_by_config(config):
    import csv

    with (CONTRACTS / "10_BASELINE_REGISTRY.csv").open(encoding="utf-8") as fh:
        registry_ids = {row["baseline_id"] for row in csv.DictReader(fh)}
    configured = set()
    for tier in config["baseline_tiers"].values():
        configured.update(tier)
    missing = registry_ids - configured
    assert not missing, f"baseline registry entries absent from config: {sorted(missing)}"


def test_mandatory_datasets_match_registry_priority(config):
    import csv

    with (CONTRACTS / "08_PUBLIC_DATASET_REGISTRY.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    mandatory = {r["dataset_id"] for r in rows if r["priority"].startswith("MANDATORY")}
    assert mandatory == set(config["mandatory_datasets"])
    # SARCOS must never be listed as a fault/anomaly dataset.
    sarcos = next(r for r in rows if r["dataset_id"] == "sarcos")
    assert sarcos["priority"] == "NORMAL_ONLY_OPTIONAL"
    assert "sarcos" not in config["mandatory_datasets"]
    assert "sarcos" not in config["supplementary_datasets"]
