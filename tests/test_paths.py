from __future__ import annotations

from pathlib import Path

import pytest

from certo_fdi.paths import RUN_SUBDIRECTORIES, create_or_resume_run, require_external_path


def test_run_layout_created_and_resumable(tmp_path: Path):
    layout = create_or_resume_run(tmp_path, "run_test")
    for name in RUN_SUBDIRECTORIES:
        assert (layout.run_root / name).is_dir()
    again = create_or_resume_run(tmp_path, "run_test")
    assert again.run_root == layout.run_root
    assert (tmp_path / "04_runs" / "stage1r_ligra" / "LATEST_RUN.txt").read_text().strip() == str(layout.run_root)


def test_external_path_rejects_worktree(tmp_path: Path):
    with pytest.raises(RuntimeError):
        require_external_path(tmp_path / "inside", repo_root=tmp_path)
    assert require_external_path(tmp_path.parent / "elsewhere", repo_root=tmp_path)
