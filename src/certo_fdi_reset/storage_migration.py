"""Phase M: move a session scratchpad onto the persistent root, verifiably.

The L1 evidence (54 raw API exports per source, the deduplicated library, the
search log) was produced into a session scratchpad under ``/tmp``. That location
is not durable, so ``contracts/paper_reset/01_MASTER_PROMPT.md`` §4.2 requires it
to be migrated to the external storage root under a per-file SHA256 contract
before the rest of the round proceeds.

The rules that shape this module:

* every file is hashed at the source, again in staging, and again at its final
  destination -- a copy that silently truncates must fail loudly, not quietly;
* the destination comes from an explicit classification table, never from
  resemblance: an unrecognised file is quarantined and reported (§4.2.9), so a
  future phase's stray artifact cannot be filed into the frozen literature tree;
* the source is never deleted, not even after a fully successful verification
  (§4.2.7-8) -- deletion is a separate decision at the end of the round;
* verified raw exports are made read-only (§4.3).

    python -m certo_fdi_reset.storage_migration \
        --config configs/paper_reset.yaml --source <scratchpad>
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path

from .config import StageConfig, load_config
from .paths import ENV_PERSIST_ROOT, PersistLayout, is_real_mountpoint
from .provenance import sha256_file, sha256_text, utc_stamp, write_manifest

MIGRATION_SCHEMA_VERSION = "1.0.0"


class ArtifactClass(str, Enum):
    """What a migrated file *is*, which decides where it may live."""

    LITERATURE_RAW_EXPORT = "LITERATURE_RAW_EXPORT"
    LITERATURE_DERIVED_TABLE = "LITERATURE_DERIVED_TABLE"
    LITERATURE_ACCESS_RECORD = "LITERATURE_ACCESS_RECORD"
    RUN_LOG = "RUN_LOG"
    UNCLASSIFIED = "UNCLASSIFIED"


#: Ordered rules. A trailing ``/`` matches a whole subtree; a pattern containing
#: ``*`` is matched against the basename; anything else is an exact relative path.
#: First match wins, so specific rules precede the glob fallbacks.
CLASSIFICATION_RULES: tuple[tuple[str, ArtifactClass], ...] = (
    ("L1_discovery/literature_raw_export/", ArtifactClass.LITERATURE_RAW_EXPORT),
    ("L1_discovery/literature_deduplicated_library.csv", ArtifactClass.LITERATURE_DERIVED_TABLE),
    ("L1_discovery/literature_search_log.csv", ArtifactClass.LITERATURE_DERIVED_TABLE),
    ("L1_discovery/discovery_summary.json", ArtifactClass.LITERATURE_DERIVED_TABLE),
    ("L1_discovery/database_availability.csv", ArtifactClass.LITERATURE_ACCESS_RECORD),
    ("*.log", ArtifactClass.RUN_LOG),
)

#: Classes whose files are frozen evidence and get chmod'ed read-only (§4.3).
IMMUTABLE_CLASSES = frozenset(
    {
        ArtifactClass.LITERATURE_RAW_EXPORT,
        ArtifactClass.LITERATURE_DERIVED_TABLE,
        ArtifactClass.LITERATURE_ACCESS_RECORD,
    }
)

READ_ONLY_MODE = 0o444


def classify(relpath: str) -> ArtifactClass:
    for pattern, artifact_class in CLASSIFICATION_RULES:
        if pattern.endswith("/"):
            if relpath.startswith(pattern):
                return artifact_class
        elif "*" in pattern:
            if fnmatch(Path(relpath).name, pattern):
                return artifact_class
        elif relpath == pattern:
            return artifact_class
    return ArtifactClass.UNCLASSIFIED


def destination_for(
    relpath: str,
    artifact_class: ArtifactClass,
    layout: PersistLayout,
    run_id: str,
) -> Path:
    """Resolve the final path for one file. Never returns a path outside the root."""
    name = Path(relpath).name
    run_dir = layout.run_dir(run_id)
    if artifact_class is ArtifactClass.LITERATURE_RAW_EXPORT:
        return layout.literature_metadata / relpath
    if artifact_class is ArtifactClass.LITERATURE_DERIVED_TABLE:
        return layout.literature_metadata / relpath
    if artifact_class is ArtifactClass.LITERATURE_ACCESS_RECORD:
        return layout.literature_access_manifest / name
    if artifact_class is ArtifactClass.RUN_LOG:
        return run_dir / "logs" / name
    return run_dir / "migrated_unclassified" / relpath


@dataclass
class FileRecord:
    """One file's before/after state. Empty ``after`` fields mean 'not yet copied'."""

    relpath: str
    artifact_class: ArtifactClass
    source_path: Path
    dest_path: Path
    size_before: int
    mtime_before_utc: str
    sha256_before: str
    size_after: int | None = None
    mtime_after_utc: str = ""
    sha256_staged: str = ""
    sha256_after: str = ""
    read_only: bool | None = None
    status: str = "PENDING"
    error: str = ""

    @property
    def verified(self) -> bool:
        return (
            self.status == "VERIFIED"
            and self.sha256_after == self.sha256_before
            and self.size_after == self.size_before
        )


@dataclass
class MigrationResult:
    run_id: str
    source_root: Path
    dest_root: Path
    started_utc: str
    finished_utc: str = ""
    records: list[FileRecord] = field(default_factory=list)
    staging_dir: Path | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.records) and all(r.verified for r in self.records)

    @property
    def bytes_before(self) -> int:
        return sum(r.size_before for r in self.records)

    @property
    def bytes_after(self) -> int:
        return sum(r.size_after or 0 for r in self.records)

    def by_class(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for record in self.records:
            bucket = out.setdefault(record.artifact_class.value, {"files": 0, "bytes": 0})
            bucket["files"] += 1
            bucket["bytes"] += record.size_before
        return out


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(
        timespec="seconds"
    )


def inventory(source_root: Path) -> list[FileRecord]:
    """Hash every regular file under ``source_root`` (symlinks are not followed)."""
    records: list[FileRecord] = []
    for path in sorted(source_root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(source_root).as_posix()
        records.append(
            FileRecord(
                relpath=rel,
                artifact_class=classify(rel),
                source_path=path,
                dest_path=Path(),  # filled once the layout is known
                size_before=path.stat().st_size,
                mtime_before_utc=_iso_mtime(path),
                sha256_before=sha256_file(path),
            )
        )
    return records


def migrate(
    source_root: Path,
    layout: PersistLayout,
    run_id: str,
    *,
    dry_run: bool = False,
) -> MigrationResult:
    """Copy to staging, verify, then move into place. Source is left untouched."""
    result = MigrationResult(
        run_id=run_id,
        source_root=source_root,
        dest_root=layout.root,
        started_utc=utc_stamp(),
        records=inventory(source_root),
    )
    for record in result.records:
        record.dest_path = destination_for(record.relpath, record.artifact_class, layout, run_id)

    collisions = _detect_collisions(result.records)
    if collisions:
        result.errors.extend(collisions)
        result.finished_utc = utc_stamp()
        return result

    if dry_run:
        for record in result.records:
            record.status = "DRY_RUN"
        result.finished_utc = utc_stamp()
        return result

    # Staging lives on the destination filesystem so the final move is a rename,
    # not a second copy that could half-finish.
    staging = layout.run_dir(run_id) / f".migration_staging_{result.started_utc}"
    staging.mkdir(parents=True, exist_ok=True)
    result.staging_dir = staging

    for record in result.records:
        try:
            staged = staging / record.relpath
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.source_path, staged)
            record.sha256_staged = sha256_file(staged)
            if record.sha256_staged != record.sha256_before:
                record.status = "FAILED_STAGING_HASH"
                record.error = f"staged {record.sha256_staged} != source {record.sha256_before}"
                continue

            record.dest_path.parent.mkdir(parents=True, exist_ok=True)
            _replace_possibly_read_only(staged, record.dest_path)

            record.sha256_after = sha256_file(record.dest_path)
            record.size_after = record.dest_path.stat().st_size
            record.mtime_after_utc = _iso_mtime(record.dest_path)
            if record.sha256_after != record.sha256_before:
                record.status = "FAILED_DEST_HASH"
                record.error = f"dest {record.sha256_after} != source {record.sha256_before}"
                continue
            if record.size_after != record.size_before:
                record.status = "FAILED_SIZE"
                record.error = f"dest {record.size_after} B != source {record.size_before} B"
                continue

            record.status = "VERIFIED"
            if record.artifact_class in IMMUTABLE_CLASSES:
                record.read_only = _make_read_only(record.dest_path)
        except OSError as exc:
            record.status = "FAILED_IO"
            record.error = f"{type(exc).__name__}: {exc}"

    failed = [r for r in result.records if not r.verified]
    if failed:
        result.errors.append(f"{len(failed)} of {len(result.records)} files failed verification")
    else:
        shutil.rmtree(staging, ignore_errors=True)
        result.staging_dir = None

    result.finished_utc = utc_stamp()
    return result


def _detect_collisions(records: list[FileRecord]) -> list[str]:
    """Two distinct sources must never resolve to one destination."""
    seen: dict[Path, str] = {}
    problems: list[str] = []
    for record in records:
        previous = seen.get(record.dest_path)
        if previous is not None and previous != record.relpath:
            problems.append(
                f"destination collision: {previous} and {record.relpath} -> {record.dest_path}"
            )
        seen[record.dest_path] = record.relpath
    return problems


def _replace_possibly_read_only(staged: Path, dest: Path) -> None:
    """Move ``staged`` onto ``dest``, clearing a previous run's read-only bit."""
    if dest.exists():
        try:
            dest.chmod(0o644)
        except OSError:
            pass
    os.replace(staged, dest)


def _make_read_only(path: Path) -> bool:
    """chmod 0444. Returns False when the filesystem refuses (drvfs without metadata)."""
    try:
        path.chmod(READ_ONLY_MODE)
    except OSError:
        return False
    return path.stat().st_mode & 0o222 == 0


INVENTORY_COLUMNS: tuple[str, ...] = (
    "relpath",
    "artifact_class",
    "size_bytes",
    "mtime_utc",
    "sha256",
    "source_path",
    "dest_path",
    "status",
)


def write_inventory(path: Path, records: list[FileRecord], *, phase: str) -> str:
    """Write the before/after inventory. ``phase`` selects which side is reported."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=INVENTORY_COLUMNS)
        writer.writeheader()
        for record in records:
            before = phase == "before"
            writer.writerow(
                {
                    "relpath": record.relpath,
                    "artifact_class": record.artifact_class.value,
                    "size_bytes": record.size_before if before else (record.size_after or 0),
                    "mtime_utc": record.mtime_before_utc if before else record.mtime_after_utc,
                    "sha256": record.sha256_before if before else record.sha256_after,
                    "source_path": str(record.source_path),
                    "dest_path": str(record.dest_path),
                    "status": record.status,
                }
            )
    return sha256_file(path)


def build_manifest(result: MigrationResult, cfg: StageConfig, inventory_shas: dict) -> dict:
    return {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "run_id": result.run_id,
        "started_utc": result.started_utc,
        "finished_utc": result.finished_utc,
        "source_root": str(result.source_root),
        "dest_root": str(result.dest_root),
        "config_sha": cfg.config_sha,
        "source_retained": result.source_root.exists(),
        "status": "VERIFIED" if result.ok else "FAILED",
        "counts": {
            "files": len(result.records),
            "verified": sum(1 for r in result.records if r.verified),
            "failed": sum(1 for r in result.records if not r.verified),
            "bytes_before": result.bytes_before,
            "bytes_after": result.bytes_after,
        },
        "by_artifact_class": result.by_class(),
        "read_only_applied": sum(1 for r in result.records if r.read_only),
        "read_only_refused": sum(1 for r in result.records if r.read_only is False),
        "errors": result.errors,
        "failures": [
            {"relpath": r.relpath, "status": r.status, "error": r.error}
            for r in result.records
            if not r.verified
        ],
        "inventories": inventory_shas,
        "files": [
            {
                "relpath": r.relpath,
                "artifact_class": r.artifact_class.value,
                "sha256": r.sha256_before,
                "size_bytes": r.size_before,
                "dest_path": str(r.dest_path),
                "status": r.status,
            }
            for r in result.records
        ],
    }


def render_report(result: MigrationResult, manifest: dict) -> str:
    lines = [
        "# Storage migration report — Phase M",
        "",
        f"- run_id: `{result.run_id}`",
        f"- status: **{manifest['status']}**",
        f"- source: `{result.source_root}`",
        f"- destination root: `{result.dest_root}`",
        f"- window (UTC): {result.started_utc} → {result.finished_utc}",
        "",
        "## Counts",
        "",
        "| metric | value |",
        "| --- | --- |",
        f"| files inventoried | {manifest['counts']['files']} |",
        f"| files verified (source SHA256 == destination SHA256) | {manifest['counts']['verified']} |",
        f"| files failed | {manifest['counts']['failed']} |",
        f"| bytes before | {manifest['counts']['bytes_before']:,} |",
        f"| bytes after | {manifest['counts']['bytes_after']:,} |",
        f"| read-only applied | {manifest['read_only_applied']} |",
        f"| read-only refused by filesystem | {manifest['read_only_refused']} |",
        "",
        "## By artifact class",
        "",
        "| artifact class | files | bytes |",
        "| --- | ---: | ---: |",
    ]
    for name, bucket in sorted(manifest["by_artifact_class"].items()):
        lines.append(f"| {name} | {bucket['files']} | {bucket['bytes']:,} |")
    lines += [
        "",
        "## Source retention",
        "",
        "The scratchpad is **not** deleted by this tool, and must survive until the",
        "round's review package has been verified (01_MASTER_PROMPT §4.2.7-8).",
        f"Source still present at report time: `{manifest['source_retained']}`.",
        "",
    ]
    if manifest["failures"]:
        lines += ["## Failures", "", "| relpath | status | error |", "| --- | --- | --- |"]
        lines += [
            f"| `{f['relpath']}` | {f['status']} | {f['error']} |" for f in manifest["failures"]
        ]
        lines.append("")
    if result.errors:
        lines += ["## Errors", ""] + [f"- {e}" for e in result.errors] + [""]
    return "\n".join(lines)


def update_run_manifest(run_manifest_path: Path, manifest: dict, manifest_sha: str) -> str | None:
    """Record the migration inside the existing run manifest, preserving all keys."""
    if not run_manifest_path.exists():
        return None
    payload = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    payload["storage_migration"] = {
        "status": manifest["status"],
        "source_root": manifest["source_root"],
        "files": manifest["counts"]["files"],
        "bytes": manifest["counts"]["bytes_before"],
        "verified": manifest["counts"]["verified"],
        "failed": manifest["counts"]["failed"],
        "source_retained": manifest["source_retained"],
        "manifest_sha256": manifest_sha,
        "finished_utc": manifest["finished_utc"],
    }
    return write_manifest(run_manifest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.storage_migration")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Scratchpad directory to migrate. Located by the operator, never guessed here.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    layout = cfg.layout
    run_id = cfg.run_id
    source = args.source.expanduser().resolve()

    if not source.is_dir():
        print(f"ERROR: source scratchpad not found: {source}", file=sys.stderr)
        return 2

    anchor = cfg.get("storage.mount_anchor")
    requires_mount = bool(cfg.get("storage.require_real_mountpoint", False))
    override_active = ENV_PERSIST_ROOT in os.environ
    if requires_mount and not override_active and anchor and not is_real_mountpoint(Path(anchor)):
        print(
            f"BLOCKED_PERSISTENT_STORAGE: {anchor} is not a real mountpoint; refusing to write "
            f"bulk data to the Linux root disk.",
            file=sys.stderr,
        )
        return 2

    result = migrate(source, layout, run_id, dry_run=args.dry_run)
    out_dir = layout.run_dir(run_id) / "storage"

    if args.dry_run:
        print(f"DRY RUN: {len(result.records)} files, {result.bytes_before:,} bytes")
        for name, bucket in sorted(result.by_class().items()):
            print(f"  {name:28s} {bucket['files']:4d} files  {bucket['bytes']:>12,} B")
        for record in result.records[:5]:
            print(f"  e.g. {record.relpath} -> {record.dest_path}")
        for error in result.errors:
            print(f"  ERROR: {error}")
        return 1 if result.errors else 0

    inventory_shas = {
        "storage_migration_inventory_before.csv": write_inventory(
            out_dir / "storage_migration_inventory_before.csv", result.records, phase="before"
        ),
        "storage_migration_inventory_after.csv": write_inventory(
            out_dir / "storage_migration_inventory_after.csv", result.records, phase="after"
        ),
    }
    manifest = build_manifest(result, cfg, inventory_shas)
    manifest_path = out_dir / "storage_migration_manifest.json"
    manifest_sha = write_manifest(manifest_path, manifest)

    report_path = out_dir / "storage_migration_report.md"
    report_text = render_report(result, manifest)
    report_path.write_text(report_text, encoding="utf-8")

    run_manifest_path = layout.run_dir(run_id) / "run_manifest.json"
    run_manifest_sha = update_run_manifest(run_manifest_path, manifest, manifest_sha)

    print(f"status            {manifest['status']}")
    print(f"files             {manifest['counts']['files']}")
    print(f"verified          {manifest['counts']['verified']}")
    print(f"failed            {manifest['counts']['failed']}")
    print(f"bytes             {manifest['counts']['bytes_before']:,}")
    print(f"read_only_ok      {manifest['read_only_applied']}")
    print(f"source_retained   {manifest['source_retained']}")
    print(f"report            {report_path}")
    print(f"manifest          {manifest_path}  sha256={manifest_sha}")
    print(f"report_sha256     {sha256_text(report_text)}")
    if run_manifest_sha:
        print(f"run_manifest      {run_manifest_path}  sha256={run_manifest_sha}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
