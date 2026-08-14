from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STAGE = "stage1_2r_closedloop_certificate"
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
)


@dataclass(frozen=True)
class RunLayout:
    storage_root: Path
    run_id: str
    run_root: Path

    @property
    def results(self) -> Path:
        return self.run_root / "results"


def _git_short_sha(repo_root: Path | None = None) -> str:
    command = ["git"]
    if repo_root is not None:
        command.extend(["-C", str(repo_root)])
    command.extend(["rev-parse", "--short", "HEAD"])
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "nogit"


def resolve_storage_root(value: str | Path | None = None) -> Path:
    raw = value if value is not None else os.environ.get("CERTO_STORAGE_ROOT")
    if raw is None or not str(raw).strip():
        raise RuntimeError("CERTO_STORAGE_ROOT or --storage-root is required")
    return Path(raw).expanduser().resolve()


def require_external_run_root(value: str | Path | None = None) -> Path:
    raw = value if value is not None else os.environ.get("CERTO_RUN_ROOT")
    if raw is None or not str(raw).strip():
        raise RuntimeError("CERTO_RUN_ROOT is required; repository-local results are forbidden")
    run_root = Path(raw).expanduser().resolve()
    repository = Path.cwd().resolve()
    if run_root == repository or repository in run_root.parents:
        raise RuntimeError("CERTO_RUN_ROOT must be outside the active Git worktree")
    return run_root


def create_run_layout(
    storage_root: str | Path,
    repo_root: str | Path | None = None,
    timestamp: str | None = None,
) -> RunLayout:
    storage = resolve_storage_root(storage_root)
    stage_root = storage / "04_runs" / STAGE
    now = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = _git_short_sha(Path(repo_root).resolve() if repo_root else None)
    run_id = f"run_{now}_{sha}"
    run_root = stage_root / run_id
    if run_root.exists():
        raise FileExistsError(f"refusing to reuse existing clean run: {run_root}")
    for name in RUN_SUBDIRECTORIES:
        (run_root / name).mkdir(parents=True, exist_ok=False)
    stage_root.mkdir(parents=True, exist_ok=True)
    (stage_root / "LATEST_RUN.txt").write_text(f"{run_root}\n", encoding="utf-8")
    return RunLayout(storage_root=storage, run_id=run_id, run_root=run_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an immutable CERTO-FDI Stage 1 run")
    parser.add_argument("--create-run", action="store_true", required=True)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()
    layout = create_run_layout(args.storage_root, args.repo_root)
    print(layout.run_root)


if __name__ == "__main__":
    main()
