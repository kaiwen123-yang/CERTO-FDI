"""Run layout on the external persistent storage root (never inside the Git worktree).

Ported and adapted from Stage 1 (``src/certo_fdi/paths.py``): the stage name and the set
of run subdirectories changed; the external-root discipline is unchanged.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STAGE = "stage1r_ligra"
RUN_SUBDIRECTORIES = (
    "config",
    "logs",
    "results",
    "figures",
    "tests",
    "environment",
    "manifests",
    "code_provenance",
    "decision",
    "checkpoints",
    "r0_geometry",
    "r1_healthy",
    "r2_anomaly",
    "r3_localization",
    "r4_fewshot",
)


@dataclass(frozen=True)
class RunLayout:
    storage_root: Path
    run_id: str
    run_root: Path

    @property
    def results(self) -> Path:
        return self.run_root / "results"

    def sub(self, name: str) -> Path:
        p = self.run_root / name
        p.mkdir(parents=True, exist_ok=True)
        return p


def git_sha(repo_root: Path | None = None, short: bool = False) -> str:
    command = ["git"]
    if repo_root is not None:
        command.extend(["-C", str(repo_root)])
    command.extend(["rev-parse", "--short" if short else "--verify", "HEAD"])
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "nogit"


def resolve_storage_root(value: str | Path | None = None) -> Path:
    raw = value if value is not None else os.environ.get("CERTO_STORAGE_ROOT")
    if raw is None or not str(raw).strip():
        raise RuntimeError("CERTO_STORAGE_ROOT or --storage-root is required")
    return Path(raw).expanduser().resolve()


def require_external_path(path: str | Path, repo_root: str | Path | None = None) -> Path:
    target = Path(path).expanduser().resolve()
    repository = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    if target == repository or repository in target.parents:
        raise RuntimeError("persistent outputs must live outside the active Git worktree")
    return target


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_or_resume_run(
    storage_root: str | Path,
    run_id: str | None = None,
    stage: str = STAGE,
) -> RunLayout:
    """Create (or resume) a run directory ``<storage>/04_runs/<stage>/<run_id>``."""
    storage = resolve_storage_root(storage_root)
    stage_root = storage / "04_runs" / stage
    stage_root.mkdir(parents=True, exist_ok=True)
    rid = run_id or f"run_{utc_stamp()}_{stage}"
    run_root = stage_root / rid
    for name in RUN_SUBDIRECTORIES:
        (run_root / name).mkdir(parents=True, exist_ok=True)
    (stage_root / "LATEST_RUN.txt").write_text(f"{run_root}\n", encoding="utf-8")
    return RunLayout(storage_root=storage, run_id=rid, run_root=run_root)
