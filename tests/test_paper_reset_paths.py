"""Persist-layout and mountpoint-detection tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from certo_fdi_reset.paths import (
    ENV_PERSIST_ROOT,
    PersistLayout,
    PersistRootError,
    is_real_mountpoint,
    resolve_persist_root,
)


def test_env_var_overrides_config_default(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_PERSIST_ROOT, str(tmp_path))
    assert resolve_persist_root("/some/config/default") == tmp_path


def test_config_default_used_when_env_absent(monkeypatch):
    monkeypatch.delenv(ENV_PERSIST_ROOT, raising=False)
    assert resolve_persist_root("/config/root") == Path("/config/root")


def test_missing_root_raises(monkeypatch):
    monkeypatch.delenv(ENV_PERSIST_ROOT, raising=False)
    with pytest.raises(PersistRootError):
        resolve_persist_root(None)


def test_layout_covers_contract_15_tree(tmp_path):
    layout = PersistLayout(tmp_path)
    dirs = layout.all_dirs()
    rels = {d.relative_to(tmp_path).as_posix() for d in dirs}
    for expected in (
        "01_frozen_sources/literature_reset/metadata",
        "01_frozen_sources/literature_reset/open_fulltexts",
        "01_frozen_sources/literature_reset/access_manifest",
        "01_frozen_sources/public_baseline_repos",
        "02_research_docs/paper_reset/literature",
        "02_research_docs/paper_reset/novelty",
        "02_research_docs/paper_reset/datasets",
        "02_research_docs/paper_reset/decisions",
        "03_data/public/voraus_ad",
        "03_data/public/road",
        "03_data/public/aursad",
        "03_data/public/ur5e_graabaek",
        "03_data/public/pyscrew",
        "04_runs/paper_reset_public_benchmarks",
        "05_reference_results/paper_reset",
        "06_review_exchange/to_review/thin",
        "06_review_exchange/to_review/full",
    ):
        assert expected in rels, expected


def test_run_dir_is_under_run_root(tmp_path):
    layout = PersistLayout(tmp_path)
    run_dir = layout.run_dir("run_X")
    assert run_dir.parent == layout.run_root


def test_plain_directory_is_not_a_mountpoint(tmp_path):
    """The exact failure mode seen at kickoff: /mnt/g existing but unmounted."""
    plain = tmp_path / "not_a_mount"
    plain.mkdir()
    assert is_real_mountpoint(plain) is False
    assert is_real_mountpoint(tmp_path / "missing") is False


def test_root_is_a_mountpoint():
    assert is_real_mountpoint(os.sep) is True
