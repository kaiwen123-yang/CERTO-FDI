"""Build and validate the Stage 2A Thin and Full review packages (contract §12).

Thin is meant to be uploaded straight into a reviewing model; Full carries every raw table,
log, figure, checkpoint index, git bundle, frozen input hash and environment record.

If a package cannot be validated the staging tree is preserved as ``FAILED_REVIEW_PACKAGE``
with the exact blocking reason, and the failure is re-raised -- a failed package is still a
deliverable (contract §12.3).
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

from certo_fdi.packaging.build_review_package import _copy_contents, _copy_file, _git, _write_git_archive, _zip_tree
from certo_fdi.packaging.validate_review_package import sha256_file, validate_zip

DECISIONS = ("GO_JACOBIAN_PATHWAY_HEAD", "PIVOT_CONTACT_GEOMETRY_ONLY", "PIVOT_CALIBRATION_SEQUENTIAL",
             "PIVOT_COARSE_EQUIVALENCE_CLASSES", "NO_GO_JACOBIAN_PATHWAY_HEAD", "BLOCKED")

REQUIRED_FILES = ("00_READ_ME_FIRST.md", "01_INDEPENDENT_REVIEW_PROMPT.md", "02_EXECUTION_SUMMARY.md",
                  "03_DECISION_MEMO.md", "04_KNOWN_ISSUES.md", "05_CLAIMS_LEDGER.csv", "06_FILE_TREE.txt",
                  "07_MANIFEST.json", "08_SHA256SUMS.txt", "15_REPRODUCE_REVIEW.sh", "REVIEW_PACKAGE_STATUS.json")
REQUIRED_DIRECTORIES = ("09_GIT_PROVENANCE", "10_CONFIGS", "11_CODE_SNAPSHOT", "12_TEST_REPORTS",
                        "13_CORE_RESULTS", "14_SELECTED_FIGURES")

CORE_RESULTS = (
    "stage2a_baseline_reproduction.csv", "stage2a_pathway_dictionary_audit.csv", "stage2a_principal_angles.csv",
    "stage2a_contact_observability.csv", "stage2a_geometry_scores.csv", "stage2a_detection_metrics.csv",
    "stage2a_event_metrics.csv", "stage2a_localization_metrics.csv", "stage2a_coarse_attribution_metrics.csv",
    "stage2a_diagnosability_error_correlation.csv", "stage2a_learning_curve.csv", "stage2a_decision_evidence.json",
    "stage2a_decision_memo.md", "stage2a_known_issues.md", "stage2a_run_manifest.json", "stage2a_claim_ledger.csv",
    "stage2a_input_freeze.json", "stage2a_baseline_gate.json", "stage2a_whitening_diagnostics.json",
    "stage2a_feature_block_manifest.json", "stage2a_metrics_summary.json", "stage2a_dictionary_summary.json",
    "stage2a_test_report.json",
)

REPRODUCE_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = "--smoke" ] || { echo 'use --smoke' >&2; exit 2; }
python3 - <<'PY'
import csv, json, pathlib
r = pathlib.Path('.')
core = r / '13_CORE_RESULTS'
required = ['stage2a_baseline_reproduction.csv', 'stage2a_pathway_dictionary_audit.csv',
            'stage2a_detection_metrics.csv', 'stage2a_localization_metrics.csv',
            'stage2a_diagnosability_error_correlation.csv', 'stage2a_decision_evidence.json',
            'stage2a_run_manifest.json']
common = {'run_id', 'git_sha', 'config_sha', 'dataset_manifest_sha', 'controller', 'split', 'seed',
          'model', 'fault_family', 'status', 'provisional', 'strict', 'empirical'}
for name in required:
    p = core / name
    if not p.is_file():
        raise SystemExit(f'missing {name}')
    if p.suffix == '.csv':
        with p.open(newline='', encoding='utf-8') as h:
            reader = csv.DictReader(h)
            fields = set(reader.fieldnames or [])
            if not common <= fields:
                raise SystemExit(f'bad schema {name}: missing {sorted(common - fields)}')
            if name == 'stage2a_detection_metrics.csv':
                for row in reader:
                    a = row.get('auroc', '')
                    if a not in ('', 'nan') and not (0.0 <= float(a) <= 1.0):
                        raise SystemExit('auroc out of range')
ev = json.loads((core / 'stage2a_decision_evidence.json').read_text())
allowed = {'GO_JACOBIAN_PATHWAY_HEAD', 'PIVOT_CONTACT_GEOMETRY_ONLY', 'PIVOT_CALIBRATION_SEQUENTIAL',
           'PIVOT_COARSE_EQUIVALENCE_CLASSES', 'NO_GO_JACOBIAN_PATHWAY_HEAD', 'BLOCKED'}
if ev.get('decision') not in allowed:
    raise SystemExit(f"decision {ev.get('decision')!r} is not in the pre-registered vocabulary")
man = json.loads((core / 'stage2a_run_manifest.json').read_text())
if man.get('decision') != ev.get('decision'):
    raise SystemExit('run manifest and decision evidence disagree')
if man.get('baseline_reproduction_gate') not in ('PASS', 'FAIL', None):
    raise SystemExit('unknown baseline gate state')
json.loads((r / '07_MANIFEST.json').read_text())
print('REVIEW_SMOKE=PASS decision=' + str(ev.get('decision')))
PY
"""

REVIEW_PROMPT = """# Independent adversarial review prompt — CERTO-FDI Stage 2A

You are reviewing an audit, not a paper. Assume nothing in it is correct or novel.

## What was claimed

With `chain_gnn_aug` frozen as the healthy-residual front end, does an explicitly constructed
joint-Cartesian fault-pathway geometry (per-link `J^T` contact dictionaries plus actuator /
friction / load / sensor / delay sensitivity dictionaries) improve fault detection, coarse
attribution, link localization, rejection and trajectory-conditioned interpretability?

## What to attack, in order

1. **The decision rules.** They are in `11_CODE_SNAPSHOT/src/certo_fdi/experiments/decision_stage2a.py`
   and `10_CONFIGS/`, committed in the first commit of the branch, before any result existed. Check
   the git history in `09_GIT_PROVENANCE/`. Did any threshold move afterwards? Is the evaluation order
   defensible, in particular the split of the §8.5 triggers into integrity and performance?
2. **The dictionaries.** Are the columns really `d E_W / d theta`? The audit compares every deployed
   column against symmetric finite differences through the frozen truth simulator. Two of them do not
   agree (F6 at all; F5 only in its steady-state form). Are the reported agreements enough to license
   the conclusions drawn from F1-F5?
3. **The contact model.** A constant point force on a rotating link is not a constant body-origin
   wrench. Check that the primary dictionary is the point-force form and that the candidate-point set
   is derived from link geometry only, never from the fault protocol.
4. **The controls.** `chain_plus_shuffled_jacobian_control` has the identical feature count but takes
   the Jacobians at permuted time indices. Where it reproduces a gain, the gain is not
   configuration-dependent Cartesian geometry. Is that control too weak, or too strong?
5. **Leakage.** No encoder or fuser input may contain `tau_meas`, the raw residual, a fault label,
   severity, fault link id or a truth-only state. The scan is an AST scan; is it complete?
6. **The baseline.** The frozen Stage 1R-B `chain_gnn_aug` must reproduce within 2 %. Check
   `stage2a_baseline_reproduction.csv` against the Stage 1R-B numbers in Draft PR #3.

## Hard rules that were meant to hold

- Healthy and faulty samples obey the same link-frame covariance law; frame drift is never a
  detection-value axis.
- Network-internal wrench-like messages are never read as physical wrenches.
- Primary detection is healthy-only: no fault window, label, severity or location enters it.
- The truth contact point is an oracle statistic, never a deployed input.
- PR #1/#2/#3 are historical negative results: Draft, never merged, never rewritten.

Report anything that would change the decision, and anything that is stated more strongly than the
evidence supports.
"""


def _read_me(decision: str, run_id: str) -> str:
    return (
        "# CERTO-FDI Stage 2A review package\n\n"
        f"**Decision: `{decision}`** · run `{run_id}`\n\n"
        "This package is evidence for independent adversarial review. It is not authorization to merge, to claim\n"
        "novelty, or to proceed. Start with `01_INDEPENDENT_REVIEW_PROMPT.md`, then `03_DECISION_MEMO.md`,\n"
        "`04_KNOWN_ISSUES.md` and `13_CORE_RESULTS/`.\n\n"
        "Hard rules that constrain every claim inside:\n\n"
        "- healthy and faulty samples obey the same link-frame covariance law; frame drift is never a detection-value axis;\n"
        "- network-internal 6-D messages are latent wrench-like messages, not identified physical wrenches;\n"
        "- primary detection is healthy-only; the truth contact point is an oracle statistic, never a deployed input;\n"
        "- the Stage 1 strict-certificate NO-GO and `FINAL_NO_GO_LIE_MAIN_CONTRIBUTION` are frozen and are not\n"
        "  evidence for or against anything in this stage;\n"
        "- the pre-registered decision rules were committed before any result existed and were not changed afterwards.\n"
    )


def _populate_common(root: Path, run_root: Path, repo: Path, decision: str) -> None:
    results = run_root / "results"
    root.mkdir(parents=True, exist_ok=False)
    (root / "00_READ_ME_FIRST.md").write_text(_read_me(decision, run_root.name), encoding="utf-8")
    (root / "01_INDEPENDENT_REVIEW_PROMPT.md").write_text(REVIEW_PROMPT, encoding="utf-8")
    manifest = json.loads((results / "stage2a_run_manifest.json").read_text()) if (results / "stage2a_run_manifest.json").is_file() else {}
    summary = {
        "run_root": str(run_root), "repo_root": str(repo),
        "git_sha": _git(repo, "rev-parse", "HEAD").strip(), "branch": _git(repo, "branch", "--show-current").strip(),
        "dirty": bool(_git(repo, "status", "--porcelain").strip()),
        "decision": manifest.get("decision"), "decision_reasons": manifest.get("decision_reasons"),
        "input_freeze_gate": manifest.get("input_freeze_gate"),
        "baseline_reproduction_gate": manifest.get("baseline_reproduction_gate"),
        "seeds": manifest.get("seeds"), "ablations": manifest.get("ablations"),
        "dataset_manifest_sha256": manifest.get("dataset_manifest_sha256"),
        "config_sha256": manifest.get("config_sha256"),
        "result_tables": manifest.get("result_tables"), "figures": manifest.get("figures"),
        "test_report": manifest.get("test_report"),
    }
    (root / "02_EXECUTION_SUMMARY.md").write_text(
        "# Execution summary\n\n```json\n" + json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n```\n", encoding="utf-8")
    for src, dst in ((results / "stage2a_decision_memo.md", "03_DECISION_MEMO.md"),
                     (results / "stage2a_known_issues.md", "04_KNOWN_ISSUES.md"),
                     (results / "stage2a_claim_ledger.csv", "05_CLAIMS_LEDGER.csv")):
        if src.is_file():
            _copy_file(src, root / dst)
        else:
            (root / dst).write_text("(not produced by this run)\n", encoding="utf-8")
    for d in REQUIRED_DIRECTORIES:
        (root / d).mkdir()
    prov = root / "09_GIT_PROVENANCE"
    (prov / "git_status.txt").write_text(_git(repo, "status", "--short", "--branch"))
    (prov / "git_log.txt").write_text(_git(repo, "log", "--stat", "--decorate", "-40"))
    (prov / "git_log_oneline.txt").write_text(_git(repo, "log", "--oneline", "--decorate", "-60"))
    (prov / "git_remote.txt").write_text(_git(repo, "remote", "-v"))
    (prov / "working_tree.patch").write_text(_git(repo, "diff", "--binary"))
    (prov / "decision_rules_first_commit.txt").write_text(
        _git(repo, "log", "--follow", "--oneline", "--", "src/certo_fdi/experiments/decision_stage2a.py"))
    _write_git_archive(repo, root / "11_CODE_SNAPSHOT")
    _copy_contents(repo / "configs", root / "10_CONFIGS" / "repository_configs")
    _copy_contents(run_root / "config", root / "10_CONFIGS" / "run_config")
    _copy_contents(run_root / "tests", root / "12_TEST_REPORTS")
    for name in ("stage2a_test_report.json",):
        if (results / name).is_file():
            _copy_file(results / name, root / "12_TEST_REPORTS" / name)
    for name in CORE_RESULTS:
        if (results / name).is_file():
            _copy_file(results / name, root / "13_CORE_RESULTS" / name)
    _copy_contents(run_root / "figures", root / "14_SELECTED_FIGURES")
    rp = root / "15_REPRODUCE_REVIEW.sh"
    rp.write_text(REPRODUCE_SCRIPT, encoding="utf-8")
    try:
        rp.chmod(rp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except PermissionError:
        pass  # drvfs; the zip entry mode is set explicitly


def _populate_full(root: Path, run_root: Path, storage: Path, bundle: Path) -> None:
    for d in ("16_FULL_RESULTS", "17_RUN_LOGS", "18_PROVENANCE", "19_GIT_BUNDLE", "20_PHASE_ARTEFACTS",
              "21_ENVIRONMENT", "22_FROZEN_INPUT_HASHES", "23_LITERATURE"):
        (root / d).mkdir(exist_ok=True)
    _copy_contents(run_root / "results", root / "16_FULL_RESULTS")
    _copy_contents(run_root / "logs", root / "17_RUN_LOGS")
    _copy_contents(run_root / "provenance", root / "18_PROVENANCE")
    _copy_contents(run_root / "environment", root / "21_ENVIRONMENT")
    for phase in ("p2_baseline", "p3_dictionaries", "p4_tests", "p5_ablations", "p6_metrics", "p7_decision"):
        src = run_root / phase
        if src.is_dir():
            _copy_contents(src, root / "20_PHASE_ARTEFACTS" / phase, exclude_suffixes=(".npz",) if phase == "p3_dictionaries" else ())
    if bundle.is_file():
        _copy_file(bundle, root / "19_GIT_BUNDLE" / bundle.name)
    # checkpoint index (never the weights themselves)
    rows = []
    for p in sorted((run_root / "checkpoints").glob("*.pt")):
        rows.append({"checkpoint": p.name, "size_bytes": p.stat().st_size, "sha256": sha256_file(p), "absolute_path": str(p)})
    with (root / "16_FULL_RESULTS" / "checkpoint_index.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["checkpoint", "size_bytes", "sha256", "absolute_path"])
        w.writeheader()
        w.writerows(rows)
    # frozen input hashes
    freeze = run_root / "results" / "stage2a_input_freeze.json"
    if freeze.is_file():
        _copy_file(freeze, root / "22_FROZEN_INPUT_HASHES" / "stage2a_input_freeze.json")
    for name in ("episode_sha256_manifest.csv", "replay_fidelity.csv"):
        p = run_root / "provenance" / name
        if p.is_file():
            _copy_file(p, root / "22_FROZEN_INPUT_HASHES" / name)
    lit = run_root / "results" / "stage2a_literature_check.json"
    if lit.is_file():
        _copy_file(lit, root / "23_LITERATURE" / "stage2a_literature_check.json")
    else:
        (root / "23_LITERATURE" / "NOT_PERFORMED.md").write_text(
            "# Literature verification\n\nNo bounded literature verification was performed in this run "
            "(the host is offline). The candidate-novelty status therefore stays "
            "`PLAUSIBLY_OPEN / NOT_ESTABLISHED`, and the forbidden-claim list in the config was honoured "
            "throughout: nothing in this package claims priority for Jacobian-based collision isolation, "
            "GNN-based manipulator anomaly detection, trajectory-conditioned diagnosability, strict global "
            "identifiability, exact conditional CFAR, or physical-wrench recovery from internal messages.\n",
            encoding="utf-8")
    # large-file manifest
    with (root / "16_FULL_RESULTS" / "large_file_manifest.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["absolute_path", "size_bytes", "sha256"])
        for p in sorted(run_root.rglob("*")):
            if p.is_file() and p.stat().st_size > 1_000_000:
                w.writerow([str(p), p.stat().st_size, sha256_file(p)])


def _write_tree(root: Path) -> None:
    skip = {"06_FILE_TREE.txt", "07_MANIFEST.json", "08_SHA256SUMS.txt"}
    lines = [f"{p.relative_to(root).as_posix()}{'/' if p.is_dir() else ''}" for p in sorted(root.rglob("*")) if p.name not in skip]
    (root / "06_FILE_TREE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(root: Path) -> None:
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name not in {"07_MANIFEST.json", "08_SHA256SUMS.txt"}:
            files[p.relative_to(root).as_posix()] = {"sha256": sha256_file(p), "size_bytes": p.stat().st_size}
    (root / "07_MANIFEST.json").write_text(json.dumps({"files": files, "file_count": len(files)}, indent=2, sort_keys=True), encoding="utf-8")
    lines = [f"{sha256_file(p)}  {p.relative_to(root).as_posix()}" for p in sorted(root.rglob("*")) if p.is_file() and p.name != "08_SHA256SUMS.txt"]
    (root / "08_SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate(zpath: Path) -> dict:
    """Stage 2A topology: the manifest, checksum and reproduce-script names are renumbered (§12.1)."""
    return validate_zip(zpath, REQUIRED_FILES, REQUIRED_DIRECTORIES,
                        sha_file="08_SHA256SUMS.txt", manifest_file="07_MANIFEST.json",
                        reproduce_script="15_REPRODUCE_REVIEW.sh")


def _build_one(kind: str, base: str, run_root: Path, repo: Path, storage: Path, staging: Path, dest_root: Path, bundle: Path, decision: str) -> dict:
    tree = staging / f"{base}_{kind}"
    _populate_common(tree, run_root, repo, decision)
    if kind == "FULL":
        _populate_full(tree, run_root, storage, bundle)
    status = tree / "REVIEW_PACKAGE_STATUS.json"
    status.write_text(json.dumps({"validation_status": "PENDING_SECOND_PASS"}, indent=2), encoding="utf-8")
    _write_tree(tree)
    _write_manifest(tree)
    zpath = staging / f"{base}_{kind}.zip"
    _zip_tree(tree, zpath)
    _validate(zpath)
    status.write_text(json.dumps({"validation_status": "PASS", "decision": decision,
                                  "checks": ["zip_crc", "fresh_extract", "sha256_manifest", "required_topology", "reproduce_smoke", "secret_scan"]},
                                 indent=2, sort_keys=True), encoding="utf-8")
    _write_tree(tree)
    _write_manifest(tree)
    zpath.unlink()
    _zip_tree(tree, zpath)
    result = _validate(zpath)
    dest = dest_root / zpath.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(zpath, dest)
    result["archive"] = str(dest)
    return result


def build(run_root: str | Path, repo_root: str | Path, milestone: str = "AUDIT") -> list[dict]:
    run = Path(run_root).resolve()
    repo = Path(repo_root).resolve()
    storage = run.parents[2]
    git = _git(repo, "rev-parse", "HEAD").strip()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"CERTO_FDI_stage2a_chain_jacobian_pathway_{milestone}_{ts}_{git[:7]}"
    manifest = run / "results" / "stage2a_run_manifest.json"
    decision = json.loads(manifest.read_text()).get("decision", "BLOCKED") if manifest.is_file() else "BLOCKED"
    exchange = storage / "06_review_exchange"
    staging_parent = exchange / "package_staging" / "working"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{base}_", dir=staging_parent))
    bundle_dir = storage / "07_backups" / "git_bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = bundle_dir / f"CERTO-FDI_{run.name}_{git[:7]}.bundle"
    subprocess.run(["git", "-C", str(repo), "bundle", "create", str(bundle), "--all"], check=True, capture_output=True)
    results = []
    try:
        for kind, dest in (("THIN", exchange / "to_review" / "thin"), ("FULL", exchange / "to_review" / "full")):
            results.append(_build_one(kind, base, run, repo, storage, staging, dest, bundle, decision))
    except Exception as error:
        failed = exchange / "package_staging" / "FAILED_REVIEW_PACKAGE" / staging.name
        failed.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), failed)
        (failed / "FAILURE_REPORT.txt").write_text(
            f"{type(error).__name__}: {error}\n\nrun_root={run}\nrepo={repo}\ngit={git}\ndecision={decision}\n"
            "The failing staging tree is preserved here so the blocking reason is auditable.\n")
        raise
    shutil.rmtree(staging, ignore_errors=True)
    idx = exchange / "package_index.csv"
    fields = ["package_name", "type", "milestone", "run_id", "git_sha", "sha256", "size_bytes", "created_at_utc",
              "validation_status", "scientific_status", "absolute_path"]
    write_header = not idx.exists() or idx.stat().st_size == 0
    with idx.open("a", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields)
        if write_header:
            w.writeheader()
        for r in results:
            p = Path(str(r["archive"]))
            kind = "THIN" if p.name.endswith("_THIN.zip") else "FULL"
            w.writerow({"package_name": p.name, "type": kind, "milestone": milestone, "run_id": run.name,
                        "git_sha": git, "sha256": r["sha256"], "size_bytes": r["size_bytes"], "created_at_utc": ts,
                        "validation_status": r["validation_status"], "scientific_status": decision, "absolute_path": p})
            (exchange / f"LATEST_{kind}_PACKAGE.txt").write_text(f"{p}\n", encoding="utf-8")
    (run / "manifests" / "REVIEW_PACKAGE_STATUS.json").parent.mkdir(parents=True, exist_ok=True)
    (run / "manifests" / "REVIEW_PACKAGE_STATUS.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--storage-root", default=os.environ.get("CERTO_STORAGE_ROOT", ""), required=not os.environ.get("CERTO_STORAGE_ROOT"))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--milestone", default="AUDIT")
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()
    run_root = Path(a.storage_root) / "04_runs" / "stage2a_chain_jacobian_pathway" / a.run_id
    print(json.dumps(build(run_root, a.repo_root, a.milestone), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
