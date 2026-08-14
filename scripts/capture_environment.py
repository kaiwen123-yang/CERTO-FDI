#!/usr/bin/env python3
"""Capture the reproducibility record required for an external Stage 1 run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def _run(command: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.stdout.rstrip() + "\n"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _package_versions() -> dict[str, str]:
    names = (
        "numpy",
        "scipy",
        "pandas",
        "sympy",
        "jax",
        "jaxlib",
        "cvxpy",
        "osqp",
        "clarabel",
        "pytest",
    )
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--phase", choices=("start", "final"), required=True)
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    storage_root = Path(args.storage_root).resolve()
    worktree_root = Path(args.repo_root).resolve()
    environment = run_root / "environment"
    environment.mkdir(parents=True, exist_ok=True)

    common_git_dir = Path(
        _run(["git", "rev-parse", "--git-common-dir"], worktree_root).strip()
    ).resolve()
    canonical_repo_root = common_git_dir.parent
    status = _run(["git", "status", "--short"], worktree_root)
    git_sha = _run(["git", "rev-parse", "HEAD"], worktree_root).strip()
    mount_info = _run(["findmnt", "-T", str(storage_root)])
    filesystem = "unknown"
    mount_fields = _run(
        ["findmnt", "-T", str(storage_root), "-n", "-o", "FSTYPE,OPTIONS"]
    ).strip()
    if mount_fields:
        filesystem = mount_fields.split()[0]

    host_path = environment / "host_report.json"
    started_at = _utc_now()
    if host_path.exists():
        prior = json.loads(host_path.read_text(encoding="utf-8"))
        started_at = prior.get("started_at_utc", started_at)
    report = {
        "dirty": bool(status.strip()),
        "ended_at_utc": _utc_now() if args.phase == "final" else None,
        "g_filesystem": filesystem,
        "g_free_bytes": shutil.disk_usage(storage_root).free,
        "git_sha": git_sha,
        "host_mode": "WSL" if "microsoft" in platform.release().lower() else "UBUNTU",
        "kernel": platform.release(),
        "python": platform.python_version(),
        "repo_root": str(canonical_repo_root),
        "run_root": str(run_root),
        "seed": args.seed,
        "started_at_utc": started_at,
        "storage_root": str(storage_root),
        "worktree_root": str(worktree_root),
    }
    host_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    text_outputs = {
        "os_release.txt": Path("/etc/os-release").read_text(encoding="utf-8"),
        "uname.txt": _run(["uname", "-a"]),
        "python_version.txt": sys.version + "\n",
        "pip_freeze.txt": _run([sys.executable, "-m", "pip", "freeze"]),
        "cpu_info.txt": Path("/proc/cpuinfo").read_text(encoding="utf-8"),
        "memory_info.txt": Path("/proc/meminfo").read_text(encoding="utf-8"),
        "mount_info.txt": mount_info,
        "git_status.txt": status or "CLEAN\n",
        "git_log.txt": _run(["git", "log", "--oneline", "--decorate", "-20"], worktree_root),
        "command_history.sh": (
            "#!/usr/bin/env bash\n"
            "# High-level executed commands; secrets excluded.\n"
            "python -m pytest -q -m 'not slow'\n"
            "python -m certo_fdi.experiments.run_stage1 --config configs/experiments/smoke.yaml\n"
            "python -m certo_fdi.packaging.build_review_package --milestone FINAL\n"
        ),
    }
    for name, contents in text_outputs.items():
        (environment / name).write_text(contents, encoding="utf-8")
    (environment / "package_versions.json").write_text(
        json.dumps(_package_versions(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
