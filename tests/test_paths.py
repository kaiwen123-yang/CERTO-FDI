from pathlib import Path

import pytest

from certo_fdi.paths import create_run_layout, require_external_run_root


def test_clean_run_creation_is_unique(tmp_path: Path) -> None:
    first = create_run_layout(tmp_path, timestamp="20260815T000000Z")
    assert first.results.is_dir()
    assert (tmp_path / "04_runs/stage1_2r_closedloop_certificate/LATEST_RUN.txt").read_text().strip() == str(first.run_root)
    with pytest.raises(FileExistsError):
        create_run_layout(tmp_path, timestamp="20260815T000000Z")


def test_repository_local_run_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="outside"):
        require_external_run_root(tmp_path / "run")
