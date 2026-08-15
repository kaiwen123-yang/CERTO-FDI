"""Build validated Thin and Full Stage 1R-B review packages (09_REVIEW_PACKAGE_CONTRACT.md).

Thin: 00–10 documents, environment, git provenance, code diff from PR #2, configs, test reports,
core results, selected figures, dataset manifests, reproduce script.
Full: Thin + all checkpoints, per-window / per-run results, training logs and curves, dataset
manifests, git bundle, environment, complete PR #2 -> branch diff.
Both are validated: CRC, fresh extraction, SHA256 manifest, topology, smoke reproduction, secret
scan, result schema, git HEAD / manifest alignment. Any failure produces FAILED_REVIEW_PACKAGE.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from certo_fdi.packaging.build_review_package import _append_package_index, _copy_contents, _copy_file, _git, _write_git_archive, _write_manifest, _write_tree, _zip_tree
from certo_fdi.packaging.validate_review_package import sha256_file, validate_zip

PR2_BASE_SHA = "4e94370696c193770c8f270c627e50b07cac13ee"
DECISIONS = ("RESEARCH_GO_LIE_MAIN_CONTRIBUTION", "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE", "PIVOT_CHAIN_ONLY", "FINAL_NO_GO_LIE_MAIN_CONTRIBUTION", "PIVOT_TYPED_CAPACITY_UNRESOLVED", "BLOCKED")
CORE_RESULT_FILES = (
    "stage1rb_basis_rank_condition.csv", "stage1rb_basis_dependencies.json", "stage1rb_oracle_torque_capacity.csv", "stage1rb_oracle_wrench_projection.csv", "stage1rb_basis_audit_memo.md", "stage1rb_basis_audit_evidence.json",
    "stage1rb_equivariance_tests.json", "stage1rb_input_parity.json", "stage1rb_leakage_audit.json", "stage1rb_r0_gate.json", "stage1r_r0_geometry_tests.json", "R0_DECISION.md", "stage1rb_provenance_gate.json",
    "stage1rb_tuning_runs.csv", "stage1rb_tuning_selection.json", "stage1rb_training_runs.csv", "stage1rb_healthy_prediction.csv", "stage1rb_ood_detection.csv", "stage1rb_healthy_ood_alarm_audit.csv", "stage1rb_localization.csv",
    "stage1rb_sample_efficiency.csv", "stage1rb_ablation_summary.csv", "stage1rb_frame_invariance.csv", "stage1rb_latency_and_size.csv", "stage1rb_density_heads.csv", "stage1rb_qdd_diagnostic.csv", "stage1rb_metrics_summary.json",
    "stage1rb_decision_evidence.json", "stage1rb_decision_memo.md", "stage1rb_known_issues.md", "stage1rb_run_manifest.json", "stage1rb_claim_ledger.csv",
)
REQUIRED_FILES = ("00_READ_ME_FIRST.md", "01_INDEPENDENT_REVIEW_PROMPT.md", "02_EXECUTION_SUMMARY.md", "03_DECISION_MEMO.md", "04_KNOWN_ISSUES.md", "05_ARCHITECTURE_CONTRACT.md", "06_DECISION_RULES.md", "07_CLAIMS_LEDGER.csv", "08_FILE_TREE.txt", "09_MANIFEST.json", "10_SHA256SUMS.txt", "19_REPRODUCE_REVIEW.sh", "REVIEW_PACKAGE_STATUS.json")
REQUIRED_DIRS = ("11_ENVIRONMENT", "12_GIT_PROVENANCE", "13_CODE_DIFF_FROM_PR2", "14_CONFIGS", "15_TEST_REPORTS", "16_CORE_RESULTS", "17_SELECTED_FIGURES", "18_DATASET_MANIFESTS")

REPRODUCE_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = "--smoke" ] || { echo 'use --smoke' >&2; exit 2; }
python3 - <<'PY'
import csv, json, pathlib
r = pathlib.Path('.')
core = r / '16_CORE_RESULTS'
required_csv = ['stage1rb_basis_rank_condition.csv', 'stage1rb_oracle_torque_capacity.csv', 'stage1rb_oracle_wrench_projection.csv', 'stage1rb_tuning_runs.csv', 'stage1rb_training_runs.csv', 'stage1rb_healthy_prediction.csv', 'stage1rb_ood_detection.csv', 'stage1rb_localization.csv', 'stage1rb_sample_efficiency.csv', 'stage1rb_ablation_summary.csv']
required_json = ['stage1rb_basis_dependencies.json', 'stage1rb_equivariance_tests.json', 'stage1rb_input_parity.json', 'stage1rb_leakage_audit.json', 'stage1rb_decision_evidence.json', 'stage1rb_run_manifest.json']
common = {'run_id', 'git_sha', 'config_sha256', 'dataset_sha256_or_manifest_sha', 'model', 'seed', 'status', 'provisional', 'strict_claim'}
for name in required_csv:
    p = core / name
    if not p.is_file():
        raise SystemExit(f'missing {name}')
    with p.open(newline='', encoding='utf-8') as h:
        reader = csv.DictReader(h)
        fields = set(reader.fieldnames or [])
        if not common <= fields:
            raise SystemExit(f'bad schema {name}: missing {common - fields}')
        if name == 'stage1rb_ood_detection.csv':
            for row in reader:
                a = row.get('auroc', '')
                if a not in ('', 'nan') and not (0.0 <= float(a) <= 1.0):
                    raise SystemExit('auroc out of range')
for name in required_json:
    if not (core / name).is_file():
        raise SystemExit(f'missing {name}')
    json.loads((core / name).read_text())
gate = json.loads((core / 'stage1rb_r0_gate.json').read_text())
if gate.get('decision') != 'PASS':
    raise SystemExit('R0 gate did not pass')
ev = json.loads((core / 'stage1rb_decision_evidence.json').read_text())
assert ev.get('decision') in ('RESEARCH_GO_LIE_MAIN_CONTRIBUTION', 'PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE', 'PIVOT_CHAIN_ONLY', 'FINAL_NO_GO_LIE_MAIN_CONTRIBUTION', 'PIVOT_TYPED_CAPACITY_UNRESOLVED', 'BLOCKED')
assert ev.get('decision_reported', '').startswith('NO_GO_CURRENT_LIGRA_V1 + ')
man = json.loads((core / 'stage1rb_run_manifest.json').read_text())
manifest = json.loads((r / '09_MANIFEST.json').read_text())
if man.get('git_sha') != json.loads((r / '02_EXECUTION_SUMMARY.md').read_text().split('```json')[1].split('```')[0]).get('git_sha'):
    raise SystemExit('git HEAD / manifest misalignment')
print('REVIEW_SMOKE=PASS')
PY
"""


def _populate_common(root: Path, run_root: Path, repo: Path, kickoff_dir: Path | None) -> None:
    results = run_root / "results"
    root.mkdir(parents=True, exist_ok=False)
    ev = json.loads((results / "stage1rb_decision_evidence.json").read_text()) if (results / "stage1rb_decision_evidence.json").is_file() else {}
    manifest = json.loads((results / "stage1rb_run_manifest.json").read_text()) if (results / "stage1rb_run_manifest.json").is_file() else {}
    (root / "00_READ_ME_FIRST.md").write_text(
        "# CERTO-FDI Stage 1R-B review package (LiGRA-v2-Typed vs chain_gnn_aug)\n\n"
        "Evidence for independent adversarial review of a stacked incremental audit on the Stage 1R pilot data. It is not authorization to merge, to claim novelty, or to proceed. "
        "Start with 01_INDEPENDENT_REVIEW_PROMPT.md, then 03_DECISION_MEMO.md, 04_KNOWN_ISSUES.md and 16_CORE_RESULTS/.\n\n"
        f"Reported decision: **{ev.get('decision_reported', 'n/a')}**. The LiGRA-v1 pilot result of PR #2 (NO_GO_LIE_MAIN_CONTRIBUTION) is unchanged.\n\n"
        "Hard rules kept: healthy and faulty samples obey the same link-frame covariance law; gauge-equivariance error / frame drift is never a fault score or a value axis; "
        "internal wrench-like messages are not identified physical wrenches; qdd_true numbers are an oracle diagnostic only; no fault data was used for any tuning, head selection or threshold.\n",
        encoding="utf-8",
    )
    if kickoff_dir and (kickoff_dir / "10_INDEPENDENT_REVIEW_PROMPT.md").is_file():
        _copy_file(kickoff_dir / "10_INDEPENDENT_REVIEW_PROMPT.md", root / "01_INDEPENDENT_REVIEW_PROMPT.md")
    else:
        (root / "01_INDEPENDENT_REVIEW_PROMPT.md").write_text("# Independent review prompt\n\nDo not trust the executor. Re-derive covariance tests, input-field audit and the four-axis decision.\n", encoding="utf-8")
    summary = {"run_root": str(run_root), "run_id": run_root.name, "repo_root": str(repo), "git_sha": _git(repo, "rev-parse", "HEAD").strip(), "branch": _git(repo, "branch", "--show-current").strip(), "dirty": bool(_git(repo, "status", "--porcelain").strip()), "pr2_base_sha": PR2_BASE_SHA, "decision": ev.get("decision"), "decision_reported": ev.get("decision_reported"), "basis_audit_verdict": ev.get("basis_audit_verdict"), "axes_won": ev.get("axes_won"), "manifest": manifest}
    (root / "02_EXECUTION_SUMMARY.md").write_text("# Execution summary\n\n```json\n" + json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n```\n", encoding="utf-8")
    _copy_file(results / "stage1rb_decision_memo.md", root / "03_DECISION_MEMO.md")
    _copy_file(results / "stage1rb_known_issues.md", root / "04_KNOWN_ISSUES.md")
    for src, dst in (("04_TYPED_EQUIVARIANT_ARCHITECTURE_CONTRACT.md", "05_ARCHITECTURE_CONTRACT.md"), ("07_DECISION_RULES.md", "06_DECISION_RULES.md")):
        if kickoff_dir and (kickoff_dir / src).is_file():
            _copy_file(kickoff_dir / src, root / dst)
        else:
            (root / dst).write_text(f"({src} not found on storage root)\n", encoding="utf-8")
    _copy_file(results / "stage1rb_claim_ledger.csv", root / "07_CLAIMS_LEDGER.csv")
    for directory in REQUIRED_DIRS:
        (root / directory).mkdir()
    _copy_contents(run_root / "environment", root / "11_ENVIRONMENT")
    prov = root / "12_GIT_PROVENANCE"
    (prov / "git_status.txt").write_text(_git(repo, "status", "--short", "--branch"))
    (prov / "git_log.txt").write_text(_git(repo, "log", "--oneline", "--decorate", "-40"))
    (prov / "git_remote.txt").write_text(_git(repo, "remote", "-v"))
    (prov / "working_tree.patch").write_text(_git(repo, "diff", "--binary"))
    (prov / "head_sha.txt").write_text(_git(repo, "rev-parse", "HEAD"))
    diff_dir = root / "13_CODE_DIFF_FROM_PR2"
    (diff_dir / "pr2_base_sha.txt").write_text(PR2_BASE_SHA + "\n")
    (diff_dir / "diff_stat.txt").write_text(_git(repo, "diff", "--stat", f"{PR2_BASE_SHA}..HEAD"))
    (diff_dir / "diff_from_pr2.patch").write_text(_git(repo, "diff", f"{PR2_BASE_SHA}..HEAD"))
    (diff_dir / "commits_since_pr2.txt").write_text(_git(repo, "log", "--oneline", f"{PR2_BASE_SHA}..HEAD"))
    _copy_contents(repo / "configs", root / "14_CONFIGS" / "repository_configs")
    _copy_contents(run_root / "config", root / "14_CONFIGS" / "run_config")
    _copy_contents(run_root / "tests", root / "15_TEST_REPORTS")
    for name in CORE_RESULT_FILES:
        if (results / name).is_file():
            _copy_file(results / name, root / "16_CORE_RESULTS" / name)
    _copy_contents(run_root / "figures", root / "17_SELECTED_FIGURES")
    _copy_contents(run_root / "provenance", root / "18_DATASET_MANIFESTS")
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
        pass


def _populate_full(root: Path, run_root: Path, storage_root: Path, bundle: Path, repo: Path) -> None:
    for directory in ("20_FULL_RESULTS", "21_RUN_LOGS", "22_CHECKPOINTS", "23_GIT_BUNDLE", "25_R0_GEOMETRY_AND_AUDIT", "26_PER_RUN_RESULTS", "27_TRAINING_CURVES", "28_CODE_SNAPSHOT"):
        (root / directory).mkdir(exist_ok=True)
    _copy_contents(run_root / "results", root / "20_FULL_RESULTS")
    _copy_contents(run_root / "logs", root / "21_RUN_LOGS")
    _copy_contents(run_root / "checkpoints", root / "22_CHECKPOINTS")
    _copy_contents(run_root / "r0_geometry", root / "25_R0_GEOMETRY_AND_AUDIT")
    _copy_contents(run_root / "c2_tuning", root / "26_PER_RUN_RESULTS" / "c2_tuning")
    _copy_contents(run_root / "c3_final", root / "26_PER_RUN_RESULTS" / "c3_final")
    _copy_file(bundle, root / "23_GIT_BUNDLE" / bundle.name)
    _write_git_archive(repo, root / "28_CODE_SNAPSHOT")
    # training curves (per-epoch train/val loss and lr) exported from the per-run JSONs
    rows = []
    for p in sorted((run_root / "c3_final" / "runs").glob("*.json")) + sorted((run_root / "c2_tuning" / "runs").glob("*.json")):
        if p.name.endswith(".FAILED.json"):
            continue
        try:
            res = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for ti in res.get("train_info", []):
            for h in ti.get("history", []):
                rows.append({"job": p.stem, "model": ti.get("name"), "seed": ti.get("seed"), "training_fraction": ti.get("training_fraction"), "config_tag": ti.get("tag"), **h})
    with (root / "27_TRAINING_CURVES" / "training_curves.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["job", "model", "seed", "training_fraction", "config_tag", "epoch", "train_loss", "val_loss", "elapsed_s", "lr"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    frozen = storage_root / "01_frozen_sources"
    for name in ("source_index.csv", "SHA256SUMS.txt"):
        if (frozen / name).is_file():
            _copy_file(frozen / name, root / "22_CHECKPOINTS" / f"frozen_{name}")
    lrows = []
    for path in sorted(run_root.rglob("*")):
        if path.is_file():
            lrows.append([str(path), path.stat().st_size, sha256_file(path)])
    with (root / "24_LARGE_FILE_MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["absolute_path", "size_bytes", "sha256"])
        writer.writerows(lrows)


def _validate(path: Path) -> dict[str, object]:
    return validate_zip(path, REQUIRED_FILES, REQUIRED_DIRS)


def _build_one(package_type: str, base_name: str, run_root: Path, repo: Path, storage_root: Path, staging_root: Path, destination_root: Path, bundle: Path, kickoff_dir: Path | None) -> dict[str, object]:
    tree = staging_root / f"{base_name}_{package_type}"
    _populate_common(tree, run_root, repo, kickoff_dir)
    if package_type == "FULL":
        _populate_full(tree, run_root, storage_root, bundle, repo)
    status_path = tree / "REVIEW_PACKAGE_STATUS.json"
    status_path.write_text(json.dumps({"validation_status": "PENDING_SECOND_PASS"}, indent=2), encoding="utf-8")
    _write_tree(tree)
    _write_manifest(tree)
    temporary_zip = staging_root / f"{base_name}_{package_type}.zip"
    _zip_tree(tree, temporary_zip)
    _validate(temporary_zip)
    status_path.write_text(json.dumps({"validation_status": "PASS", "checks": ["zip_crc", "fresh_extract", "sha256_manifest", "required_topology", "reproduce_smoke", "secret_scan", "result_schema", "git_head_manifest_alignment"]}, indent=2, sort_keys=True), encoding="utf-8")
    _write_tree(tree)
    _write_manifest(tree)
    temporary_zip.unlink()
    _zip_tree(tree, temporary_zip)
    result = _validate(temporary_zip)
    destination = destination_root / temporary_zip.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary_zip, destination)
    result["archive"] = str(destination)
    result["checks"] = result["checks"] + ["result_schema", "git_head_manifest_alignment"]
    return result


def build_packages(run_root: str | Path, repo_root: str | Path, milestone: str, kickoff_dir: str | Path | None) -> list[dict[str, object]]:
    run = Path(run_root).resolve()
    repo = Path(repo_root).resolve()
    storage = run.parents[2]
    git_sha = _git(repo, "rev-parse", "HEAD").strip()
    short_sha = git_sha[:7]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"CERTO_FDI_stage1rb_typed_capacity_{milestone}_{timestamp}_{short_sha}"
    exchange = storage / "06_review_exchange"
    staging_parent = exchange / "package_staging" / "working"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{base}_", dir=staging_parent))
    bundle_dir = storage / "07_backups" / "git_bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = bundle_dir / f"CERTO-FDI_{run.name}_{short_sha}.bundle"
    subprocess.run(["git", "-C", str(repo), "bundle", "create", str(bundle), "--all"], check=True, capture_output=True)
    kdir = Path(kickoff_dir) if kickoff_dir else None
    results = []
    try:
        for ptype, dest in (("THIN", exchange / "to_review" / "thin"), ("FULL", exchange / "to_review" / "full")):
            results.append(_build_one(ptype, base, run, repo, storage, staging, dest, bundle, kdir))
    except Exception as error:
        failed = exchange / "package_staging" / "failed" / staging.name
        failed.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), failed)
        (failed / "FAILURE_REPORT.txt").write_text(f"FAILED_REVIEW_PACKAGE: {type(error).__name__}: {error}\n")
        (run / "manifests").mkdir(exist_ok=True)
        (run / "manifests" / "REVIEW_PACKAGE_STATUS.json").write_text(json.dumps({"validation_status": "FAILED_REVIEW_PACKAGE", "error": f"{type(error).__name__}: {error}"}, indent=2), encoding="utf-8")
        raise
    shutil.rmtree(staging)
    ev_path = run / "results" / "stage1rb_decision_evidence.json"
    scientific_status = str(json.loads(ev_path.read_text()).get("decision_reported", "UNKNOWN")) if ev_path.is_file() else "UNKNOWN"
    _append_package_index(storage, results, milestone, run.name, git_sha, scientific_status, timestamp)
    (run / "manifests").mkdir(exist_ok=True)
    (run / "manifests" / "REVIEW_PACKAGE_STATUS.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--milestone", default="AUDIT")
    parser.add_argument("--kickoff-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(build_packages(args.run_root, args.repo_root, args.milestone, args.kickoff_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
