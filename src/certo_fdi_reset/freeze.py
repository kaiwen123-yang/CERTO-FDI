"""Phase 0 bootstrap: verify the persist root, build its tree, write the run manifest.

    python -m certo_fdi_reset.freeze --config configs/paper_reset.yaml

Refuses to run when ``storage.mount_anchor`` is required to be a real mountpoint
and is not one -- the failure mode that
``contracts/paper_reset/22_BOOTSTRAP_FROM_ZERO.sh`` guards with ``mountpoint -q``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from .config import load_config
from .decision import DECISION_CODE_VERSION
from .paths import ENV_PERSIST_ROOT, is_real_mountpoint
from .provenance import (
    environment_info,
    git_info,
    sha256_tree,
    utc_stamp,
    write_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.freeze")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--allow-non-mountpoint",
        action="store_true",
        help=(
            "Proceed even though the persist root is not a real mountpoint. "
            "The deviation is recorded in the run manifest."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    repo_root = args.config.resolve().parent.parent
    root = cfg.persist_root
    run_id = cfg.run_id
    layout = cfg.layout

    override_active = ENV_PERSIST_ROOT in os.environ
    configured_default = cfg.get("storage.persistent_root")
    requires_mount = bool(cfg.get("storage.require_real_mountpoint", False))

    # Only the configured default carries the mountpoint requirement; an explicit
    # CERTO_PERSIST_ROOT override is the sanctioned escape hatch (01_MASTER_PROMPT §2).
    # The anchor is the path that must itself be a mountpoint -- typically the drive
    # mount above the project directory. It is declared in config, never hard-coded.
    anchor_setting = cfg.get("storage.mount_anchor")
    mount_anchor = Path(anchor_setting).expanduser() if anchor_setting else root
    mounted = is_real_mountpoint(mount_anchor)
    deviation = None

    if requires_mount and not override_active and not mounted:
        message = (
            f"persist root {root} requires a real mountpoint but {mount_anchor} is not one"
        )
        if not args.allow_non_mountpoint:
            print(f"ERROR: {message}", file=sys.stderr)
            print(
                f"Mount the volume at {mount_anchor} (on WSL: "
                f"`sudo mount -t drvfs <DRIVE>: {mount_anchor}`), or set "
                f"{ENV_PERSIST_ROOT}, or pass --allow-non-mountpoint.",
                file=sys.stderr,
            )
            return 2
        deviation = message

    if override_active:
        deviation = (
            f"{ENV_PERSIST_ROOT}={os.environ[ENV_PERSIST_ROOT]} overrides "
            f"storage.persistent_root={configured_default}"
        )

    created = []
    for directory in layout.all_dirs():
        if not directory.exists():
            created.append(str(directory))
        if not args.dry_run:
            directory.mkdir(parents=True, exist_ok=True)

    run_dir = layout.run_dir(run_id)
    if not args.dry_run:
        run_dir.mkdir(parents=True, exist_ok=True)

    usage = shutil.disk_usage(root if root.exists() else Path.cwd())
    manifest = {
        "run_id": run_id,
        "stage": cfg.raw.get("stage"),
        "manifest_written_utc": utc_stamp(),
        "protocol_freeze_utc": cfg.get("run.protocol_freeze_utc"),
        "config": {
            "path": str(cfg.source_path),
            "config_sha": cfg.config_sha,
        },
        "contract_package": {
            "name": cfg.get("run.contract_package"),
            "sha256": cfg.get("run.contract_package_sha256"),
            "frozen_tree_sha256": sha256_tree(repo_root / "contracts" / "paper_reset"),
        },
        "decision_code_version": DECISION_CODE_VERSION,
        "git": git_info(repo_root),
        "environment": environment_info(),
        "storage": {
            "persist_root": str(root),
            "configured_default": configured_default,
            "env_override": os.environ.get(ENV_PERSIST_ROOT),
            "mount_anchor": str(mount_anchor),
            "is_real_mountpoint": mounted,
            "requires_real_mountpoint": requires_mount,
            "deviation": deviation,
            "free_bytes": usage.free,
            "total_bytes": usage.total,
            "run_dir": str(run_dir),
            "directories_created": created,
        },
    }

    if args.dry_run:
        import json

        print(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    manifest_path = run_dir / "run_manifest.json"
    manifest_sha = write_manifest(manifest_path, manifest)
    print(f"run_id            {run_id}")
    print(f"persist_root      {root}")
    print(f"real_mountpoint   {mounted}")
    if deviation:
        print(f"DEVIATION         {deviation}")
    print(f"directories_made  {len(created)}")
    print(f"manifest          {manifest_path}")
    print(f"manifest_sha256   {manifest_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
