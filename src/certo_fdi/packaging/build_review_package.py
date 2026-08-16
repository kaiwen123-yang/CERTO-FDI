"""Build validated Thin and Full Stage 1R review packages on the persistent storage root.

Ported from Stage 1 (``src/certo_fdi/packaging/build_review_package.py``) and adapted to the
Stage 1R run layout, required-file topology, and decision vocabulary.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from certo_fdi.packaging.validate_review_package import sha256_file, validate_zip

DECISIONS = ("RESEARCH_GO", "PIVOT_CHAIN_ONLY", "PIVOT_DETECTION_ONLY", "PIVOT_REDUCED_PUBLIC_DATA", "NO_GO_LIE_MAIN_CONTRIBUTION", "BLOCKED")
CORE_RESULT_FILES = (
    "stage1r_geometry_summary.csv", "stage1r_healthy_prediction.csv", "stage1r_sample_efficiency.csv", "stage1r_frame_invariance.csv",
    "stage1r_ood_detection.csv", "stage1r_event_detection.csv", "stage1r_localization.csv", "stage1r_fewshot_attribution.csv",
    "stage1r_latency_and_size.csv", "stage1r_ablation_summary.csv", "stage1r_claim_ledger.csv", "stage1r_decision_memo.md", "stage1r_run_manifest.json",
    "stage1r_r0_geometry_tests.json", "stage1r_r0_frame_trials.csv", "stage1r_r0_dynamics_crosscheck.csv", "R0_DECISION.md",
)


def _copy_contents(source: Path, destination: Path, *, exclude_suffixes: tuple[str, ...] = ()) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return
    for item in source.rglob("*"):
        if item.is_file() and item.suffix in exclude_suffixes:
            continue
        target = destination / item.relative_to(source)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _git(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *arguments], text=True, stderr=subprocess.STDOUT)


def _write_git_archive(repo: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar") as temporary, tempfile.TemporaryDirectory(prefix="certo_git_archive_") as extracted:
        subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", "HEAD"], check=True, stdout=temporary)
        temporary.flush()
        with tarfile.open(temporary.name) as archive:
            archive.extractall(extracted, filter="data")
        _copy_contents(Path(extracted), destination)


def _write_manifest(root: Path) -> None:
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in {"09_MANIFEST.json", "10_SHA256SUMS.txt"}:
            relative = path.relative_to(root).as_posix()
            files[relative] = {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
    (root / "09_MANIFEST.json").write_text(json.dumps({"files": files, "file_count": len(files)}, indent=2, sort_keys=True), encoding="utf-8")
    checksum_lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "10_SHA256SUMS.txt":
            checksum_lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "10_SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")


def _write_tree(root: Path) -> None:
    lines = [f"{path.relative_to(root).as_posix()}{'/' if path.is_dir() else ''}" for path in sorted(root.rglob("*")) if path.name not in {"08_FILE_TREE.txt", "09_MANIFEST.json", "10_SHA256SUMS.txt"}]
    (root / "08_FILE_TREE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _zip_tree(root: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_dir():
                info = zipfile.ZipInfo(relative + "/")
                info.date_time = datetime.now().timetuple()[:6]
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
                archive.writestr(info, b"")
            elif path.is_file():
                info = zipfile.ZipInfo(relative)
                info.date_time = datetime.now().timetuple()[:6]
                info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


REPRODUCE_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = "--smoke" ] || { echo 'use --smoke' >&2; exit 2; }
python3 - <<'PY'
import csv, json, pathlib
r = pathlib.Path('.')
required = ['stage1r_event_detection.csv', 'stage1r_healthy_prediction.csv', 'stage1r_localization.csv', 'stage1r_frame_invariance.csv', 'stage1r_claim_ledger.csv', 'stage1r_r0_geometry_tests.json', 'stage1r_run_manifest.json']
common = {'run_id', 'git_sha', 'config_sha256', 'seed', 'split', 'model', 'checkpoint_sha256', 'status'}
for name in required:
    p = r / '16_CORE_RESULTS' / name
    if not p.is_file():
        raise SystemExit(f'missing {name}')
    if p.suffix == '.csv':
        with p.open(newline='', encoding='utf-8') as h:
            reader = csv.DictReader(h)
            fields = set(reader.fieldnames or [])
            if not common <= fields:
                raise SystemExit(f'bad schema {name}: missing {common - fields}')
            if name == 'stage1r_event_detection.csv':
                for row in reader:
                    a = row.get('auroc', '')
                    if a not in ('', 'nan') and not (0.0 <= float(a) <= 1.0):
                        raise SystemExit('auroc out of range')
r0 = json.loads((r / '16_CORE_RESULTS' / 'stage1r_r0_geometry_tests.json').read_text())
if r0.get('decision') != 'PASS':
    raise SystemExit('R0 did not pass')
manifest = json.loads((r / '16_CORE_RESULTS' / 'stage1r_run_manifest.json').read_text())
assert manifest.get('decision') in ('RESEARCH_GO', 'PIVOT_CHAIN_ONLY', 'PIVOT_DETECTION_ONLY', 'PIVOT_REDUCED_PUBLIC_DATA', 'NO_GO_LIE_MAIN_CONTRIBUTION', 'BLOCKED')
json.loads((r / '09_MANIFEST.json').read_text())
print('REVIEW_SMOKE=PASS')
PY
"""


def _populate_common(root: Path, run_root: Path, repo: Path, storage_root: Path, kickoff_dir: Path | None, known_issues: str) -> None:
    results = run_root / "results"
    root.mkdir(parents=True, exist_ok=False)
    (root / "00_READ_ME_FIRST.md").write_text(
        "# CERTO-FDI Stage 1R review package (LiGRA-FDI pilot)\n\n"
        "This package is evidence for independent adversarial review. It is not authorization to merge, to claim novelty, "
        "or to proceed to a full study. Start with 01_REVIEW_PROMPT.md, then 03_DECISION_MEMO.md and 16_CORE_RESULTS/.\n\n"
        "Hard rules: healthy and faulty samples obey the same link-frame covariance law; gauge-equivariance error is never a fault score; "
        "internal 6-D messages are latent wrench-like messages, not identified physical wrenches; the Stage 1 strict-certificate NO-GO is not evidence about Stage 1R.\n",
        encoding="utf-8",
    )
    if kickoff_dir and (kickoff_dir / "09_INDEPENDENT_REVIEW_PROMPT.md").is_file():
        _copy_file(kickoff_dir / "09_INDEPENDENT_REVIEW_PROMPT.md", root / "01_REVIEW_PROMPT.md")
    else:
        (root / "01_REVIEW_PROMPT.md").write_text("# Independent review prompt\n\nDo not assume LiGRA is correct or novel. Reproduce and challenge every geometry, architecture, data, statistical, value and literature claim.\n", encoding="utf-8")
    manifest_path = results / "stage1r_run_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    summary = {"run_root": str(run_root), "repo_root": str(repo), "git_sha": _git(repo, "rev-parse", "HEAD").strip(), "branch": _git(repo, "branch", "--show-current").strip(), "dirty": bool(_git(repo, "status", "--porcelain").strip()), "decision": manifest.get("decision"), "profile": manifest.get("profile"), "data_root": manifest.get("data_root")}
    (root / "02_EXECUTION_SUMMARY.md").write_text("# Execution summary\n\n```json\n" + json.dumps(summary, indent=2, sort_keys=True) + "\n```\n", encoding="utf-8")
    _copy_file(results / "stage1r_decision_memo.md", root / "03_DECISION_MEMO.md")
    (root / "04_KNOWN_ISSUES.md").write_text(known_issues, encoding="utf-8")
    if kickoff_dir and (kickoff_dir / "02_MATHEMATICAL_CONTRACT.md").is_file():
        _copy_file(kickoff_dir / "02_MATHEMATICAL_CONTRACT.md", root / "05_MATHEMATICAL_CONTRACT.md")
    else:
        (root / "05_MATHEMATICAL_CONTRACT.md").write_text("(mathematical contract not found on storage root)\n", encoding="utf-8")
    _copy_file(results / "stage1r_claim_ledger.csv", root / "06_CLAIMS_LEDGER.csv")
    arch = "# Architecture and configuration\n\n"
    if kickoff_dir and (kickoff_dir / "03_LIGRA_NETWORK_ARCHITECTURE.md").is_file():
        arch += (kickoff_dir / "03_LIGRA_NETWORK_ARCHITECTURE.md").read_text(encoding="utf-8") + "\n\n"
    arch += "## Implemented configuration\n\nSee 14_CONFIGS/ (run config) and 13_CODE_SNAPSHOT/src/certo_fdi/models/ (LiGRA, chain GNN, baselines).\n"
    (root / "07_ARCHITECTURE_AND_CONFIG.md").write_text(arch, encoding="utf-8")
    for directory in ("11_ENVIRONMENT", "12_GIT_PROVENANCE", "13_CODE_SNAPSHOT", "14_CONFIGS", "15_TEST_REPORTS", "16_CORE_RESULTS", "17_SELECTED_FIGURES", "18_DATASET_MANIFESTS"):
        (root / directory).mkdir()
    _copy_contents(run_root / "environment", root / "11_ENVIRONMENT")
    provenance = root / "12_GIT_PROVENANCE"
    (provenance / "git_status.txt").write_text(_git(repo, "status", "--short", "--branch"))
    (provenance / "git_log.txt").write_text(_git(repo, "log", "--oneline", "--decorate", "-30"))
    (provenance / "git_remote.txt").write_text(_git(repo, "remote", "-v"))
    (provenance / "working_tree.patch").write_text(_git(repo, "diff", "--binary"))
    _write_git_archive(repo, root / "13_CODE_SNAPSHOT")
    _copy_contents(repo / "configs", root / "14_CONFIGS" / "repository_configs")
    _copy_contents(run_root / "config", root / "14_CONFIGS" / "run_config")
    _copy_contents(run_root / "tests", root / "15_TEST_REPORTS")
    for name in CORE_RESULT_FILES:
        if (results / name).is_file():
            _copy_file(results / name, root / "16_CORE_RESULTS" / name)
    for extra in ("stage1r_decision_evidence.json", "stage1r_metrics_summary.json", "stage1r_r0_model_covariance.json", "model_parameter_audit.json", "stage1r_density_heads.csv", "stage1r_training_runs.csv"):
        if (results / extra).is_file():
            _copy_file(results / extra, root / "16_CORE_RESULTS" / extra)
    _copy_contents(run_root / "figures", root / "17_SELECTED_FIGURES")
    data_root = Path(str(manifest.get("data_root", "")))
    if data_root.is_dir():
        for name in ("dataset_manifest.json", "model_parameter_audit.json", "episode_index.csv", "split_manifest.json", "fault_manifest.json", "frame_variant_manifest.json"):
            if (data_root / name).is_file():
                _copy_file(data_root / name, root / "18_DATASET_MANIFESTS" / name)
    reproduce = root / "19_REPRODUCE_REVIEW.sh"
    reproduce.write_text(REPRODUCE_SCRIPT, encoding="utf-8")
    try:
        reproduce.chmod(reproduce.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except PermissionError:
        pass  # drvfs: zip metadata is set explicitly in _zip_tree


def _populate_full(root: Path, run_root: Path, storage_root: Path, bundle: Path) -> None:
    for directory in ("20_FULL_RESULTS", "21_RUN_LOGS", "22_CHECKPOINTS", "23_GIT_BUNDLE", "25_R0_GEOMETRY", "26_PER_RUN_RESULTS"):
        (root / directory).mkdir(exist_ok=True)
    _copy_contents(run_root / "results", root / "20_FULL_RESULTS")
    _copy_contents(run_root / "logs", root / "21_RUN_LOGS")
    _copy_contents(run_root / "checkpoints", root / "22_CHECKPOINTS")
    _copy_contents(run_root / "r0_geometry", root / "25_R0_GEOMETRY")
    _copy_contents(run_root / "r1_healthy", root / "26_PER_RUN_RESULTS")
    _copy_file(bundle, root / "23_GIT_BUNDLE" / bundle.name)
    frozen = storage_root / "01_frozen_sources"
    for name in ("source_index.csv", "SHA256SUMS.txt"):
        if (frozen / name).is_file():
            _copy_file(frozen / name, root / "22_CHECKPOINTS" / f"frozen_{name}")
    rows = []
    for path in sorted(run_root.rglob("*")):
        if path.is_file():
            rows.append([str(path), path.stat().st_size, sha256_file(path)])
    with (root / "24_LARGE_FILE_MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["absolute_path", "size_bytes", "sha256"])
        writer.writerows(rows)


def _build_one(package_type: str, base_name: str, run_root: Path, repo: Path, storage_root: Path, staging_root: Path, destination_root: Path, bundle: Path, kickoff_dir: Path | None, known_issues: str) -> dict[str, object]:
    tree = staging_root / f"{base_name}_{package_type}"
    _populate_common(tree, run_root, repo, storage_root, kickoff_dir, known_issues)
    if package_type == "FULL":
        _populate_full(tree, run_root, storage_root, bundle)
    status_path = tree / "REVIEW_PACKAGE_STATUS.json"
    status_path.write_text(json.dumps({"validation_status": "PENDING_SECOND_PASS"}, indent=2), encoding="utf-8")
    _write_tree(tree)
    _write_manifest(tree)
    temporary_zip = staging_root / f"{base_name}_{package_type}.zip"
    _zip_tree(tree, temporary_zip)
    validate_zip(temporary_zip)
    status_path.write_text(json.dumps({"validation_status": "PASS", "checks": ["zip_crc", "fresh_extract", "sha256_manifest", "required_topology", "reproduce_smoke", "secret_scan"]}, indent=2, sort_keys=True), encoding="utf-8")
    _write_tree(tree)
    _write_manifest(tree)
    temporary_zip.unlink()
    _zip_tree(tree, temporary_zip)
    result = validate_zip(temporary_zip)
    destination = destination_root / temporary_zip.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary_zip, destination)
    result["archive"] = str(destination)
    return result


def _append_package_index(storage_root: Path, results: list[dict[str, object]], milestone: str, run_id: str, git_sha: str, scientific_status: str, created: str) -> None:
    index = storage_root / "06_review_exchange" / "package_index.csv"
    fields = ["package_name", "type", "milestone", "run_id", "git_sha", "sha256", "size_bytes", "created_at_utc", "validation_status", "scientific_status", "absolute_path"]
    write_header = not index.exists() or index.stat().st_size == 0
    with index.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if write_header:
            writer.writeheader()
        for result in results:
            path = Path(str(result["archive"]))
            package_type = "THIN" if path.name.endswith("_THIN.zip") else "FULL"
            writer.writerow({"package_name": path.name, "type": package_type, "milestone": milestone, "run_id": run_id, "git_sha": git_sha, "sha256": result["sha256"], "size_bytes": result["size_bytes"], "created_at_utc": created, "validation_status": result["validation_status"], "scientific_status": scientific_status, "absolute_path": path})
            (storage_root / "06_review_exchange" / f"LATEST_{package_type}_PACKAGE.txt").write_text(f"{path}\n", encoding="utf-8")


def build_packages(run_root: str | Path, repo_root: str | Path, milestone: str = "PILOT", kickoff_dir: str | Path | None = None, known_issues_path: str | Path | None = None) -> list[dict[str, object]]:
    run = Path(run_root).resolve()
    repo = Path(repo_root).resolve()
    storage = run.parents[2]
    git_sha = _git(repo, "rev-parse", "HEAD").strip()
    short_sha = git_sha[:7]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"CERTO_FDI_stage1r_ligra_{milestone}_{timestamp}_{short_sha}"
    exchange = storage / "06_review_exchange"
    staging_parent = exchange / "package_staging" / "working"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{base}_", dir=staging_parent))
    bundle_dir = storage / "07_backups" / "git_bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = bundle_dir / f"CERTO-FDI_{run.name}_{short_sha}.bundle"
    subprocess.run(["git", "-C", str(repo), "bundle", "create", str(bundle), "--all"], check=True, capture_output=True)
    known_issues = Path(known_issues_path).read_text(encoding="utf-8") if known_issues_path and Path(known_issues_path).is_file() else "# Known issues\n\n(see decision memo)\n"
    kdir = Path(kickoff_dir) if kickoff_dir else None
    results = []
    try:
        for ptype, dest in (("THIN", exchange / "to_review" / "thin"), ("FULL", exchange / "to_review" / "full")):
            results.append(_build_one(ptype, base, run, repo, storage, staging, dest, bundle, kdir, known_issues))
    except Exception as error:
        failed = exchange / "package_staging" / "failed" / staging.name
        failed.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), failed)
        (failed / "FAILURE_REPORT.txt").write_text(f"{type(error).__name__}: {error}\n")
        raise
    shutil.rmtree(staging)
    manifest_path = run / "results" / "stage1r_run_manifest.json"
    scientific_status = "UNKNOWN"
    if manifest_path.is_file():
        scientific_status = str(json.loads(manifest_path.read_text()).get("decision", "UNKNOWN"))
    _append_package_index(storage, results, milestone, run.name, git_sha, scientific_status, timestamp)
    (run / "manifests" / "REVIEW_PACKAGE_STATUS.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--milestone", default="PILOT")
    parser.add_argument("--kickoff-dir", default=None)
    parser.add_argument("--known-issues", default=None)
    args = parser.parse_args()
    print(json.dumps(build_packages(args.run_root, args.repo_root, args.milestone, args.kickoff_dir, args.known_issues), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
