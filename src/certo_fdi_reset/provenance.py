"""Run identity, hashing, and manifest helpers.

Every CSV/JSON emitted by this stage must carry the provenance columns listed in
``contracts/paper_reset/19_EXPECTED_OUTPUTS_AND_SCHEMAS.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_CSV_COLUMNS: tuple[str, ...] = (
    "run_id",
    "git_sha",
    "config_sha",
    "dataset_id",
    "dataset_version",
    "data_manifest_sha",
    "split",
    "model",
    "seed",
    "status",
    "reproduction_level",
    "provisional",
    "metric",
    "value",
    "unit",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_run_id(stage_suffix: str = "paper_reset") -> str:
    return f"run_{utc_stamp()}_{stage_suffix}"


def sha256_file(path: str | os.PathLike[str], chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_tree(root: str | os.PathLike[str], patterns: tuple[str, ...] = ("*",)) -> str:
    """Order-stable hash over a directory: hashes ``relpath\\0filehash\\n`` lines."""
    root_path = Path(root)
    entries: list[str] = []
    for pattern in patterns:
        for path in sorted(root_path.rglob(pattern)):
            if path.is_file():
                rel = path.relative_to(root_path).as_posix()
                entries.append(f"{rel}\0{sha256_file(path)}")
    return sha256_text("\n".join(sorted(set(entries))))


def git_info(repo: str | os.PathLike[str]) -> dict:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

    return {
        "git_sha": run("rev-parse", "HEAD"),
        "git_branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(run("status", "--porcelain")),
        "git_describe": run("describe", "--always", "--dirty"),
    }


def environment_info() -> dict:
    info = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor_count": os.cpu_count(),
    }
    try:
        import torch

        info["torch"] = torch.__version__
        info["torch_cuda"] = torch.version.cuda
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            info["gpu_capability"] = list(torch.cuda.get_device_capability(0))
    except Exception as exc:  # pragma: no cover - torch is optional for pure-audit runs
        info["torch"] = f"UNAVAILABLE: {type(exc).__name__}"
    return info


def write_manifest(path: str | os.PathLike[str], payload: dict) -> str:
    """Write a JSON manifest atomically and return its SHA256."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)
    return sha256_text(text)
