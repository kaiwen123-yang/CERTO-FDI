from __future__ import annotations

import argparse
import csv
import hashlib
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


def _copy_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return
    for item in source.rglob("*"):
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
    return subprocess.check_output(
        ["git", "-C", str(repo), *arguments], text=True, stderr=subprocess.STDOUT
    )


def _write_git_archive(repo: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar") as temporary, tempfile.TemporaryDirectory(
        prefix="certo_git_archive_"
    ) as extracted:
        subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar", "HEAD"],
            check=True,
            stdout=temporary,
        )
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
    (root / "09_MANIFEST.json").write_text(
        json.dumps({"files": files, "file_count": len(files)}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    checksum_lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "10_SHA256SUMS.txt":
            checksum_lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "10_SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )


def _write_tree(root: Path) -> None:
    lines = [
        f"{path.relative_to(root).as_posix()}{'/' if path.is_dir() else ''}"
        for path in sorted(root.rglob("*"))
        if path.name not in {"08_FILE_TREE.txt", "09_MANIFEST.json", "10_SHA256SUMS.txt"}
    ]
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
                mode = path.stat().st_mode
                info.external_attr = (mode & 0xFFFF) << 16
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def _populate_common(root: Path, run_root: Path, repo: Path, storage_root: Path) -> None:
    results = run_root / "results"
    decision = run_root / "decision" / "stage1_decision_memo.md"
    root.mkdir(parents=True, exist_ok=False)
    (root / "00_READ_ME_FIRST.md").write_text(
        "# CERTO-FDI review package\n\nThis package is evidence for independent review. "
        "It is not authorization to merge or proceed to 7DoF. Start with the review prompt.\n",
        encoding="utf-8",
    )
    (root / "01_REVIEW_PROMPT.md").write_text(
        "# Independent review prompt\n\n"
        "Do not presume the recorded GO/PIVOT/NO-GO decision is correct. Check formulas, "
        "interval indices, units, signs, code/output consistency, and rerun the smoke script. "
        "Separate strict, empirical, and provisional rows. Verify that every claimed certificate "
        "uses deployment-computable quantities. Check manifest references for G-drive files.\n",
        encoding="utf-8",
    )
    summary = {
        "run_root": str(run_root),
        "repo_root": str(repo),
        "git_sha": _git(repo, "rev-parse", "HEAD").strip(),
        "branch": _git(repo, "branch", "--show-current").strip(),
        "dirty": bool(_git(repo, "status", "--porcelain").strip()),
    }
    (root / "02_EXECUTION_SUMMARY.md").write_text(
        "# Execution summary\n\n```json\n"
        + json.dumps(summary, indent=2, sort_keys=True)
        + "\n```\n",
        encoding="utf-8",
    )
    _copy_file(decision, root / "03_DECISION_MEMO.md")
    (root / "04_KNOWN_ISSUES.md").write_text(
        "# Known issues\n\n- Model and healthy-set remainders are empirical grid maxima.\n"
        "- Heavy-tail calibration is marginal and empirical.\n"
        "- Command-delay AD is piecewise and marked provisional.\n"
        "- Pinocchio was not used; the third dynamics path is SymPy/Lagrange.\n",
        encoding="utf-8",
    )
    (root / "05_OPEN_PROOF_OBLIGATIONS.md").write_text(
        "# Open proof obligations\n\n1. Support-wide closed-loop remainder bound.\n"
        "2. Exact structured e0 constants and a joint probability event.\n"
        "3. Heavy-tail deployment guarantee beyond independent marginal calibration.\n"
        "4. Global fault-manifold equivalence and self-intersection audit.\n",
        encoding="utf-8",
    )
    _copy_file(results / "stage1_claim_ledger.csv", root / "06_CLAIMS_LEDGER.csv")
    _copy_file(results / "stage1_theorem_status.csv", root / "07_THEOREM_STATUS.csv")
    for directory in (
        "11_ENVIRONMENT",
        "12_GIT_PROVENANCE",
        "13_CODE_SNAPSHOT",
        "14_CONFIGS",
        "15_TEST_REPORTS",
        "16_CORE_RESULTS",
        "17_SELECTED_FIGURES",
        "18_DOCUMENT_DIFFS",
    ):
        (root / directory).mkdir()
    _copy_contents(run_root / "environment", root / "11_ENVIRONMENT")
    provenance = root / "12_GIT_PROVENANCE"
    (provenance / "git_status.txt").write_text(_git(repo, "status", "--short", "--branch"))
    (provenance / "git_log.txt").write_text(_git(repo, "log", "--oneline", "--decorate", "-20"))
    (provenance / "git_remote.txt").write_text(_git(repo, "remote", "-v"))
    (provenance / "working_tree.patch").write_text(_git(repo, "diff", "--binary"))
    _write_git_archive(repo, root / "13_CODE_SNAPSHOT")
    _copy_contents(repo / "configs", root / "14_CONFIGS" / "repository_configs")
    _copy_contents(run_root / "config", root / "14_CONFIGS" / "run_config")
    _copy_contents(run_root / "tests", root / "15_TEST_REPORTS")
    for path in sorted(results.iterdir()):
        if path.is_file() and path.suffix in {".csv", ".json", ".md"}:
            _copy_file(path, root / "16_CORE_RESULTS" / path.name)
    _copy_contents(run_root / "figures", root / "17_SELECTED_FIGURES")
    corrections = storage_root / "02_research_docs" / "corrections"
    _copy_contents(corrections, root / "18_DOCUMENT_DIFFS")
    reproduce = root / "19_REPRODUCE_REVIEW.sh"
    reproduce.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "[ \"${1:-}\" = \"--smoke\" ] || { echo 'use --smoke' >&2; exit 2; }\n"
        "python3 - <<'PY'\n"
        "import csv,json,pathlib\n"
        "r=pathlib.Path('.')\n"
        "required=['stage1_closedloop_operators.csv','stage1_epsA_sweep.csv','stage1_certificates.csv','stage1_coverage_t3.csv']\n"
        "common={'run_id','seed','git_sha','config_sha256','strict_certificate','empirical_screening','provisional'}\n"
        "for name in required:\n"
        " p=r/'16_CORE_RESULTS'/name\n"
        " if not p.is_file(): raise SystemExit(f'missing {name}')\n"
        " with p.open(newline='',encoding='utf-8') as h: fields=set(next(csv.reader(h)))\n"
        " if not common <= fields: raise SystemExit(f'bad schema {name}')\n"
        "json.loads((r/'09_MANIFEST.json').read_text())\n"
        "print('REVIEW_SMOKE=PASS')\n"
        "PY\n",
        encoding="utf-8",
    )
    reproduce.chmod(reproduce.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _populate_full(root: Path, run_root: Path, storage_root: Path, bundle: Path) -> None:
    for directory in ("20_FULL_RESULTS", "21_RUN_LOGS", "22_FROZEN_SOURCE_INDEX", "23_GIT_BUNDLE"):
        (root / directory).mkdir(exist_ok=True)
    _copy_contents(run_root / "results", root / "20_FULL_RESULTS")
    _copy_contents(run_root / "logs", root / "21_RUN_LOGS")
    frozen = storage_root / "01_frozen_sources"
    for name in ("source_index.csv", "SHA256SUMS.txt"):
        if (frozen / name).is_file():
            _copy_file(frozen / name, root / "22_FROZEN_SOURCE_INDEX" / name)
    archives = root / "22_FROZEN_SOURCE_INDEX" / "archives"
    _copy_contents(frozen / "archives", archives)
    _copy_file(bundle, root / "23_GIT_BUNDLE" / bundle.name)
    rows = []
    for path in sorted(run_root.rglob("*")):
        if path.is_file():
            rows.append([str(path), path.stat().st_size, sha256_file(path)])
    with (root / "24_LARGE_FILE_MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["absolute_path", "size_bytes", "sha256"])
        writer.writerows(rows)


def _build_one(
    package_type: str,
    base_name: str,
    run_root: Path,
    repo: Path,
    storage_root: Path,
    staging_root: Path,
    destination_root: Path,
    bundle: Path,
) -> dict[str, object]:
    tree = staging_root / f"{base_name}_{package_type}"
    _populate_common(tree, run_root, repo, storage_root)
    if package_type == "FULL":
        _populate_full(tree, run_root, storage_root, bundle)
    status_path = tree / "REVIEW_PACKAGE_STATUS.json"
    status_path.write_text(
        json.dumps({"validation_status": "PENDING_SECOND_PASS"}, indent=2), encoding="utf-8"
    )
    _write_tree(tree)
    _write_manifest(tree)
    temporary_zip = staging_root / f"{base_name}_{package_type}.zip"
    _zip_tree(tree, temporary_zip)
    validate_zip(temporary_zip)
    status_path.write_text(
        json.dumps(
            {
                "validation_status": "PASS",
                "checks": [
                    "zip_crc",
                    "fresh_extract",
                    "sha256_manifest",
                    "required_topology",
                    "reproduce_smoke",
                    "secret_scan",
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
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


def _append_package_index(
    storage_root: Path,
    results: list[dict[str, object]],
    milestone: str,
    run_id: str,
    git_sha: str,
    scientific_status: str,
    created: str,
) -> None:
    index = storage_root / "06_review_exchange" / "package_index.csv"
    fields = [
        "package_name",
        "type",
        "milestone",
        "run_id",
        "git_sha",
        "sha256",
        "size_bytes",
        "created_at_utc",
        "validation_status",
        "scientific_status",
        "absolute_path",
    ]
    write_header = not index.exists() or index.stat().st_size == 0
    with index.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if write_header:
            writer.writeheader()
        for result in results:
            path = Path(str(result["archive"]))
            package_type = "THIN" if path.name.endswith("_THIN.zip") else "FULL"
            writer.writerow(
                {
                    "package_name": path.name,
                    "type": package_type,
                    "milestone": milestone,
                    "run_id": run_id,
                    "git_sha": git_sha,
                    "sha256": result["sha256"],
                    "size_bytes": result["size_bytes"],
                    "created_at_utc": created,
                    "validation_status": result["validation_status"],
                    "scientific_status": scientific_status,
                    "absolute_path": path,
                }
            )
            (storage_root / "06_review_exchange" / f"LATEST_{package_type}_PACKAGE.txt").write_text(
                f"{path}\n", encoding="utf-8"
            )


def build_packages(
    run_root: str | Path,
    repo_root: str | Path,
    milestone: str = "FINAL",
) -> list[dict[str, object]]:
    run = Path(run_root).resolve()
    repo = Path(repo_root).resolve()
    storage = run.parents[2]
    git_sha = _git(repo, "rev-parse", "HEAD").strip()
    short_sha = git_sha[:7]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"CERTO_FDI_stage1_2r_closedloop_certificate_{milestone}_{timestamp}_{short_sha}"
    exchange = storage / "06_review_exchange"
    staging_parent = exchange / "package_staging" / "working"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{base}_", dir=staging_parent))
    bundle = storage / "07_backups" / "git_bundles" / f"CERTO-FDI_{run.name}_{short_sha}.bundle"
    subprocess.run(
        ["git", "-C", str(repo), "bundle", "create", str(bundle), "--all"], check=True
    )
    results = []
    try:
        results.append(
            _build_one(
                "THIN",
                base,
                run,
                repo,
                storage,
                staging,
                exchange / "to_review" / "thin",
                bundle,
            )
        )
        results.append(
            _build_one(
                "FULL",
                base,
                run,
                repo,
                storage,
                staging,
                exchange / "to_review" / "full",
                bundle,
            )
        )
    except Exception as error:
        failed = exchange / "package_staging" / "failed" / staging.name
        failed.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), failed)
        (failed / "FAILURE_REPORT.txt").write_text(f"{type(error).__name__}: {error}\n")
        raise
    shutil.rmtree(staging)
    decision_text = (run / "decision" / "stage1_decision_memo.md").read_text(encoding="utf-8")
    scientific_status = next(
        (value for value in ("GO", "PIVOT", "NO-GO", "BLOCKED") if f"Decision: {value}" in decision_text),
        "UNKNOWN",
    )
    _append_package_index(
        storage,
        results,
        milestone,
        run.name,
        git_sha,
        scientific_status,
        timestamp,
    )
    (run / "manifests" / "REVIEW_PACKAGE_STATUS.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8"
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--milestone", default="FINAL")
    args = parser.parse_args()
    print(
        json.dumps(
            build_packages(args.run_root, args.repo_root, args.milestone),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
