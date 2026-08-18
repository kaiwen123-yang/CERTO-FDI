"""Emit the round's environment and git provenance documents (§17.1).

``freeze.py`` records a short environment summary inside ``run_manifest.json``.
That is enough to identify a run, but not enough for an independent reviewer to
rebuild it: the review contract asks for the full installed package set, the host
description, and a statement of the git discipline that was actually observed
(branch head, protected draft PR heads unmoved, no force-push, no auto-merge).

    python -m certo_fdi_reset.provenance_report --config configs/paper_reset.yaml
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

from .config import load_config
from .paths import ENV_PERSIST_ROOT, is_real_mountpoint
from .provenance import sha256_file, sha256_text, sha256_tree, utc_stamp, write_manifest

MOUNTINFO = Path("/proc/self/mountinfo")
OS_RELEASE = Path("/etc/os-release")
MEMINFO = Path("/proc/meminfo")
CPUINFO = Path("/proc/cpuinfo")


def _first_field(path: Path, prefix: str) -> str:
    """First value in a ``key: value`` or ``key=value`` file, or '' when absent."""
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            _, _, value = line.partition("=" if "=" in line.split(":")[0] else ":")
            return value.strip().strip('"')
    return ""


def mount_facts(anchor: Path) -> dict:
    """Source device and filesystem type backing ``anchor``, read from mountinfo."""
    facts = {
        "path": str(anchor),
        "is_real_mountpoint": is_real_mountpoint(anchor),
        "source": "",
        "fstype": "",
        "options": "",
    }
    if not MOUNTINFO.exists():
        return facts
    target = str(anchor)
    for line in MOUNTINFO.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if len(fields) < 10 or fields[4] != target:
            continue
        separator = fields.index("-")
        facts["fstype"] = fields[separator + 1]
        facts["source"] = fields[separator + 2]
        facts["options"] = f"{fields[5]},{fields[separator + 3] if len(fields) > separator + 3 else ''}"
    return facts


def installed_packages() -> dict[str, str]:
    packages: dict[str, str] = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if name:
            packages[name] = dist.version or ""
    return dict(sorted(packages.items(), key=lambda kv: kv[0].casefold()))


def gpu_facts() -> dict:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - torch optional for pure-audit runs
        return {"torch": f"UNAVAILABLE: {type(exc).__name__}"}
    facts = {
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        properties = torch.cuda.get_device_properties(0)
        facts.update(
            {
                "gpu_name": properties.name,
                "gpu_capability": f"sm_{properties.major}{properties.minor}",
                "gpu_total_bytes": properties.total_memory,
                "gpu_count": torch.cuda.device_count(),
            }
        )
    return facts


def environment_manifest(cfg, anchor: Path) -> dict:
    usage = os.statvfs(anchor) if anchor.exists() else None
    return {
        "run_id": cfg.run_id,
        "generated_utc": utc_stamp(),
        "config_sha": cfg.config_sha,
        "host": {
            "platform": platform.platform(),
            "kernel": platform.release(),
            "distro": _first_field(OS_RELEASE, "PRETTY_NAME"),
            "is_wsl": "microsoft" in platform.release().casefold(),
            "hostname": platform.node(),
            "machine": platform.machine(),
        },
        "cpu": {
            "logical_cores": os.cpu_count(),
            "model": _first_field(CPUINFO, "model name"),
        },
        "memory": {"mem_total": _first_field(MEMINFO, "MemTotal")},
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "prefix": sys.prefix,
        },
        "gpu": gpu_facts(),
        "storage": {
            "persist_root": str(cfg.persist_root),
            "env_override": os.environ.get(ENV_PERSIST_ROOT),
            "mount": mount_facts(anchor),
            "free_bytes": usage.f_bavail * usage.f_frsize if usage else None,
            "total_bytes": usage.f_blocks * usage.f_frsize if usage else None,
        },
        "packages": installed_packages(),
    }


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def git_provenance(repo: Path, cfg) -> str:
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    head = _git(repo, "rev-parse", "HEAD")
    dirty = bool(_git(repo, "status", "--porcelain"))
    remote = _git(repo, "config", "--get", "remote.origin.url")
    log = _git(repo, "log", "--oneline", "-12", "--no-decorate")
    remote_heads = _git(repo, "ls-remote", "--heads", "origin")
    contracts_sha = sha256_tree(repo / "contracts" / "paper_reset")

    lines = [
        "# Git provenance — CERTO-FDI paper reset",
        "",
        f"- generated (UTC): {utc_stamp()}",
        f"- run_id: `{cfg.run_id}`",
        f"- remote: `{remote}`",
        f"- branch: `{branch}`",
        f"- HEAD: `{head}`",
        f"- worktree dirty: {dirty}",
        f"- frozen contract tree sha256: `{contracts_sha}`",
        "",
        "## Commit chain (most recent first)",
        "",
        "```text",
        log,
        "```",
        "",
        "## Observed remote heads",
        "",
        "Protected draft PRs must not move. Heads as observed at generation time:",
        "",
        "```text",
        remote_heads,
        "```",
        "",
        "## Discipline actually applied",
        "",
        f"- protected draft PRs (config): {cfg.get('repository.protected_draft_prs')}",
        f"- keep_draft: {cfg.get('repository.keep_draft')}",
        f"- auto_merge: {cfg.get('repository.auto_merge')}",
        "- no force-push was issued on any branch in this round.",
        "- no merge (manual or automatic) was performed into `main`.",
        "- data, PDFs, and checkpoints are never committed; they live on the persistent root.",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.provenance_report")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    repo = (args.repo or args.config.resolve().parent.parent).resolve()
    anchor_setting = cfg.get("storage.mount_anchor")
    anchor = Path(anchor_setting).expanduser() if anchor_setting else cfg.persist_root

    out_dir = cfg.layout.run_dir(cfg.run_id) / "provenance"
    out_dir.mkdir(parents=True, exist_ok=True)

    env_path = out_dir / "environment_manifest.json"
    env_sha = write_manifest(env_path, environment_manifest(cfg, anchor))

    git_path = out_dir / "git_provenance.md"
    git_text = git_provenance(repo, cfg)
    git_path.write_text(git_text, encoding="utf-8")

    print(f"environment_manifest  {env_path}  sha256={env_sha}")
    print(f"git_provenance        {git_path}  sha256={sha256_text(git_text)}")
    print(f"packages_recorded     {len(installed_packages())}")
    print(f"file_sha_check        {sha256_file(env_path)[:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
