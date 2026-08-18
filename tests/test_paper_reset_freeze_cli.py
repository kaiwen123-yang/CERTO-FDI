"""Behaviour of `python -m certo_fdi_reset.freeze` around the persist-root gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from certo_fdi_reset.freeze import main
from certo_fdi_reset.paths import ENV_PERSIST_ROOT

REPO_ROOT = Path(__file__).resolve().parents[1]


def write_config(tmp_path: Path, **storage_overrides) -> Path:
    """A minimal config laid out like the real repo (configs/ next to contracts/)."""
    base = yaml.safe_load((REPO_ROOT / "configs" / "paper_reset.yaml").read_text())
    base["storage"].update(storage_overrides)
    fake_repo = tmp_path / "repo"
    (fake_repo / "configs").mkdir(parents=True)
    (fake_repo / "contracts").mkdir(parents=True)
    # freeze.py hashes the frozen contract tree; point it at the real one.
    (fake_repo / "contracts" / "paper_reset").symlink_to(REPO_ROOT / "contracts" / "paper_reset")
    path = fake_repo / "configs" / "paper_reset.yaml"
    path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    return path


def test_refuses_when_mountpoint_required_but_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv(ENV_PERSIST_ROOT, raising=False)
    target = tmp_path / "fake_g" / "CERTO-FDI"
    cfg = write_config(
        tmp_path,
        persistent_root=str(target),
        mount_anchor=str(tmp_path / "fake_g"),
        require_real_mountpoint=True,
    )
    assert main(["--config", str(cfg)]) == 2
    assert "requires a real mountpoint" in capsys.readouterr().err
    assert not target.exists(), "must not create the tree when the gate fails"


def test_allow_non_mountpoint_records_the_deviation(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_PERSIST_ROOT, raising=False)
    target = tmp_path / "fake_g" / "CERTO-FDI"
    cfg = write_config(
        tmp_path,
        persistent_root=str(target),
        mount_anchor=str(tmp_path / "fake_g"),
        require_real_mountpoint=True,
    )
    assert main(["--config", str(cfg), "--allow-non-mountpoint"]) == 0

    run_id = yaml.safe_load(cfg.read_text())["run"]["run_id"]
    manifest_path = (
        target / "04_runs" / "paper_reset_public_benchmarks" / run_id / "run_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["storage"]["is_real_mountpoint"] is False
    assert "requires a real mountpoint" in manifest["storage"]["deviation"]
    assert manifest["run_id"] == run_id
    assert manifest["contract_package"]["sha256"]
    assert manifest["contract_package"]["frozen_tree_sha256"]
    assert manifest["decision_code_version"]


def test_env_override_is_recorded_and_bypasses_the_gate(tmp_path, monkeypatch):
    target = tmp_path / "override_root"
    monkeypatch.setenv(ENV_PERSIST_ROOT, str(target))
    cfg = write_config(
        tmp_path, mount_anchor=str(tmp_path / "fake_g"), require_real_mountpoint=True
    )
    assert main(["--config", str(cfg)]) == 0

    run_id = yaml.safe_load(cfg.read_text())["run"]["run_id"]
    manifest = json.loads(
        (
            target / "04_runs" / "paper_reset_public_benchmarks" / run_id / "run_manifest.json"
        ).read_text()
    )
    assert manifest["storage"]["env_override"] == str(target)
    assert str(target) in manifest["storage"]["deviation"]


def test_creates_the_full_contract_15_tree(tmp_path, monkeypatch):
    target = tmp_path / "override_root"
    monkeypatch.setenv(ENV_PERSIST_ROOT, str(target))
    cfg = write_config(
        tmp_path, mount_anchor=str(tmp_path / "fake_g"), require_real_mountpoint=True
    )
    main(["--config", str(cfg)])
    for expected in (
        "01_frozen_sources/literature_reset/metadata",
        "01_frozen_sources/public_baseline_repos",
        "02_research_docs/paper_reset/decisions",
        "03_data/public/voraus_ad",
        "05_reference_results/paper_reset",
        "06_review_exchange/to_review/thin",
    ):
        assert (target / expected).is_dir(), expected


def test_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    target = tmp_path / "override_root"
    monkeypatch.setenv(ENV_PERSIST_ROOT, str(target))
    cfg = write_config(
        tmp_path, mount_anchor=str(tmp_path / "fake_g"), require_real_mountpoint=True
    )
    assert main(["--config", str(cfg), "--dry-run"]) == 0
    assert not target.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["storage"]["persist_root"] == str(target)


def test_gate_passes_when_the_anchor_is_a_real_mountpoint(tmp_path, monkeypatch):
    """A real mountpoint (here: the filesystem root) satisfies the gate."""
    monkeypatch.delenv(ENV_PERSIST_ROOT, raising=False)
    target = tmp_path / "persist"
    cfg = write_config(
        tmp_path,
        persistent_root=str(target),
        mount_anchor="/",
        require_real_mountpoint=True,
    )
    assert main(["--config", str(cfg)]) == 0

    run_id = yaml.safe_load(cfg.read_text())["run"]["run_id"]
    manifest = json.loads(
        (
            target / "04_runs" / "paper_reset_public_benchmarks" / run_id / "run_manifest.json"
        ).read_text()
    )
    assert manifest["storage"]["is_real_mountpoint"] is True
    assert manifest["storage"]["deviation"] is None


def test_real_repo_config_anchors_on_the_contract_drive():
    cfg = yaml.safe_load((REPO_ROOT / "configs" / "paper_reset.yaml").read_text())
    assert cfg["storage"]["require_real_mountpoint"] is True
    assert cfg["storage"]["persistent_root"].startswith(cfg["storage"]["mount_anchor"])
