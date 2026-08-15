"""Shared experiment utilities: config loading, provenance, result-row schema, seeding."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml

from certo_fdi.paths import RunLayout, git_sha

RESULT_ROW_BASE_FIELDS = (
    "run_id",
    "git_sha",
    "config_sha256",
    "seed",
    "split",
    "model",
    "checkpoint_sha256",
    "status",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config(path: str | Path) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    cfg = yaml.safe_load(raw)
    return cfg, sha256_bytes(raw)


def config_hash(cfg: dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(cfg, sort_keys=True, default=str).encode("utf-8"))


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except Exception:  # pragma: no cover
        pass


def package_versions(names: Iterable[str] = ("numpy", "scipy", "pandas", "sympy", "torch", "mujoco", "pin", "h5py", "scikit-learn", "pytest", "pyyaml")) -> dict[str, str]:
    out = {}
    for name in names:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = "NOT_INSTALLED"
    return out


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.run(cmd, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    except OSError as e:  # pragma: no cover
        return f"ERROR: {e}\n"


def capture_environment(layout: RunLayout, repo_root: Path, phase: str, extra: dict | None = None) -> dict:
    env_dir = layout.sub("environment")
    sha = git_sha(repo_root)
    status = _run(["git", "status", "--short"], repo_root)
    storage_root = layout.storage_root
    mount = _run(["findmnt", "-T", str(storage_root), "-n", "-o", "FSTYPE,OPTIONS"]).strip()
    gpu = _run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"]).strip()
    report = {
        "phase": phase,
        "timestamp_utc": utc_now(),
        "run_id": layout.run_id,
        "run_root": str(layout.run_root),
        "storage_root": str(storage_root),
        "storage_filesystem": mount.split()[0] if mount else "unknown",
        "storage_mount_options": mount,
        "repo_root": str(repo_root),
        "git_sha": sha,
        "git_dirty": bool(status.strip()),
        "git_branch": _run(["git", "branch", "--show-current"], repo_root).strip(),
        "host_mode": "WSL" if "microsoft" in platform.release().lower() else "UBUNTU",
        "kernel": platform.release(),
        "python": platform.python_version(),
        "executable": sys.executable,
        "gpu": gpu,
        "packages": package_versions(),
        "cpu_count": os.cpu_count(),
    }
    if extra:
        report.update(extra)
    (env_dir / f"host_report_{phase}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (env_dir / "pip_freeze.txt").write_text(_run([sys.executable, "-m", "pip", "freeze"]), encoding="utf-8")
    (env_dir / "uname.txt").write_text(_run(["uname", "-a"]), encoding="utf-8")
    (env_dir / "git_log.txt").write_text(_run(["git", "log", "--oneline", "--decorate", "-30"], repo_root), encoding="utf-8")
    (env_dir / "git_status.txt").write_text(status or "CLEAN\n", encoding="utf-8")
    (env_dir / "nvidia_smi.txt").write_text(_run(["nvidia-smi"]), encoding="utf-8")
    try:
        (env_dir / "os_release.txt").write_text(Path("/etc/os-release").read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        pass
    return report


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    if fieldnames is None:
        seen: list[str] = []
        for r in rows:
            for k in r:
                if k not in seen:
                    seen.append(k)
        fieldnames = seen
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_json(path: str | Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _json_default(o: Any):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def base_row(layout: RunLayout, repo_root: Path, cfg_sha: str, *, seed: int | str = "", split: str = "", model: str = "", checkpoint_sha256: str = "", status: str = "OK") -> dict[str, Any]:
    return {
        "run_id": layout.run_id,
        "git_sha": git_sha(repo_root),
        "config_sha256": cfg_sha,
        "seed": seed,
        "split": split,
        "model": model,
        "checkpoint_sha256": checkpoint_sha256,
        "status": status,
    }
