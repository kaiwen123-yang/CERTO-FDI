"""The three mandatory input hashes are pinned in the config and actually present (kickoff §B).

A mismatch here is `BLOCKED_INPUT_PROVENANCE`, never a scientific NO-GO, so the values live in
the frozen config and are asserted rather than recomputed from whatever happens to be on disk.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "stage2b_contact_loadpath.yaml").read_text())
FI = CFG["frozen_inputs"]
STAGE2A_SHA = "bcf2ad5c978f58dc159636d64d0b5c81efb9e396"


def test_config_pins_the_three_contract_hashes():
    assert FI["stage2a_full_zip_sha256"] == "0ae32ba745917d68b2b819e779f2d3430be535ce3d3e018dcde8baa446b04acc"
    assert FI["stage2a_git_sha"] == STAGE2A_SHA
    assert FI["dataset_content_manifest_sha256"] == "8c2ba38b9262080efb981c08cfb7b5d58d2bfd037228a313edcae57f062b4100"
    assert FI["regenerate_frozen_data"] is False


def test_branch_descends_from_the_stage2a_commit():
    """Stage 2B is a stacked branch; if it does not descend from Stage 2A, nothing is comparable."""
    mb = subprocess.run(["git", "-C", str(ROOT), "merge-base", "HEAD", STAGE2A_SHA],
                        check=False, text=True, capture_output=True).stdout.strip()
    assert mb == STAGE2A_SHA, f"merge-base is {mb!r}, expected the Stage 2A head"


def test_historical_branch_heads_are_not_rewritten():
    """PR #1-#4 heads must be exactly where Stage 2A left them."""
    expected = {
        "stage/stage1-closedloop-certificate": "07850efcd8adb82dcaf9048200e53cb8dfa44f00",
        "stage/stage1r-ligra-representation": "4e94370696c193770c8f270c627e50b07cac13ee",
        "stage/stage1r-b-equivariant-capacity-audit": "11134fb695b1c70c9664150d8d70a9670b95de51",
        "stage/stage2a-chain-jacobian-pathway-audit": STAGE2A_SHA,
    }
    for branch, sha in expected.items():
        got = subprocess.run(["git", "-C", str(ROOT), "rev-parse", branch],
                             check=False, text=True, capture_output=True).stdout.strip()
        if not got:
            pytest.skip(f"{branch} not present locally")
        assert got == sha, f"{branch} moved: {got} != {sha}"


def test_kickoff_contracts_are_frozen_with_hashes():
    p = Path("/mnt/g/CERTO-FDI/02_research_docs/stage2b/contracts/STAGE2B_CONTRACT_HASHES.json")
    if not p.exists():
        pytest.skip("contract hashes not on this host")
    d = json.loads(p.read_text())
    assert d["kickoff_zip_sha256"] == FI["stage2b_kickoff_zip_sha256"]
    assert d["n_files"] >= 14
    for name in ("01_MASTER_PROMPT.md", "07_DECISION_RULES.md", "12_STAGE2B_CONFIG_TEMPLATE.yaml"):
        assert name in d["file_sha256"]


def test_frozen_dataset_is_never_regenerated_by_stage2b_code():
    """No Stage 2B module may write into the frozen Stage 1R data root."""
    import inspect
    import certo_fdi.stage2b.contact_calibration as CC
    import certo_fdi.stage2b.healthy_expansion as HE

    for m in (CC, HE):
        src = inspect.getsource(m)
        assert "03_data/stage1r" not in src, m.__name__
        assert "frozen_data_root" not in src, m.__name__


def test_new_partitions_are_written_outside_the_frozen_root():
    assert CFG["paths"]["stage2b_data_root"] != CFG["paths"]["frozen_data_root"]
    assert "stage2b" in CFG["paths"]["stage2b_data_root"]
