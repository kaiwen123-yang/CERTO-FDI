"""Build and validate the Stage 2B Thin and Full review packages (kickoff §10).

Thin is meant to be uploaded straight into a reviewing model; Full carries every raw table, log,
figure, checkpoint index, episode manifest, generated-partition manifest, environment record and
a git bundle.

If a package cannot be validated the staging tree is preserved as ``FAILED_REVIEW_PACKAGE`` with
the exact blocking reason and the failure is re-raised. A failed package is still a deliverable.
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
from certo_fdi.stage2b.decision_stage2b import DECISION_VOCABULARY

REQUIRED_FILES = ("00_READ_ME_FIRST.md", "01_INDEPENDENT_REVIEW_PROMPT.md", "02_EXECUTION_SUMMARY.md",
                  "03_DECISION_MEMO.md", "04_KNOWN_ISSUES.md", "05_CLAIMS_LEDGER.csv", "06_FILE_TREE.txt",
                  "07_MANIFEST.json", "08_SHA256SUMS.txt", "15_REPRODUCE_REVIEW.sh", "REVIEW_PACKAGE_STATUS.json")
REQUIRED_DIRECTORIES = ("09_GIT_PROVENANCE", "10_CONFIGS", "11_CODE_SNAPSHOT", "12_TEST_REPORTS",
                        "13_CORE_RESULTS", "14_SELECTED_FIGURES")

#: the kickoff §13 hard result files, plus the tables the decision reads
CORE_RESULTS = (
    "stage2b_input_freeze.json", "stage2b_baseline_reproduction.csv", "stage2b_reproduction_gate.json",
    "stage2b_contact_calibration_manifest.csv", "stage2b_loadpath_controls.csv", "stage2b_rank_audit.csv",
    "stage2b_localizer_selection.csv", "stage2b_localizer_selection.json", "stage2b_localization_metrics.csv",
    "stage2b_selective_risk.csv", "stage2b_context_calibration.csv", "stage2b_sequential_metrics.csv",
    "stage2b_event_metrics.csv", "stage2b_event_accounting.json", "stage2b_healthy_learning_curve.csv",
    "stage2b_healthy_expansion_manifest.json", "stage2b_episode_bootstrap.csv", "stage2b_gain_decomposition.json",
    "stage2b_literature_verification.md", "stage2b_literature_probe.json", "stage2b_literature_claims.csv",
    "stage2b_literature_sources.csv", "NOT_PERFORMED.md", "stage2b_claim_ledger.csv",
    "stage2b_decision_evidence.json", "stage2b_decision_conditions.csv", "stage2b_decision_memo.md",
    "stage2b_known_issues.md", "stage2b_run_manifest.json", "stage2b_test_report.json",
)

#: §10.3 -- the six things the review smoke must verify
REPRODUCE_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = "--smoke" ] || { echo 'use --smoke' >&2; exit 2; }
python3 - <<'PY'
import csv, json, pathlib
r = pathlib.Path('.')
core = r / '13_CORE_RESULTS'
fail = lambda m: (_ for _ in ()).throw(SystemExit(m))

# ---- 1. all hard result files exist
required = ['stage2b_input_freeze.json', 'stage2b_baseline_reproduction.csv',
            'stage2b_contact_calibration_manifest.csv', 'stage2b_loadpath_controls.csv',
            'stage2b_rank_audit.csv', 'stage2b_localizer_selection.csv',
            'stage2b_localization_metrics.csv', 'stage2b_selective_risk.csv',
            'stage2b_context_calibration.csv', 'stage2b_sequential_metrics.csv',
            'stage2b_event_metrics.csv', 'stage2b_healthy_learning_curve.csv',
            'stage2b_episode_bootstrap.csv', 'stage2b_literature_verification.md',
            'stage2b_claim_ledger.csv', 'stage2b_decision_evidence.json',
            'stage2b_decision_memo.md', 'stage2b_known_issues.md', 'stage2b_run_manifest.json']
common = {'run_id', 'git_sha', 'config_sha', 'dataset_manifest_sha', 'partition', 'split', 'seed',
          'method', 'fault_family', 'status', 'provisional', 'strict', 'empirical'}
for name in required:
    p = core / name
    if not p.is_file():
        fail(f'missing hard result file: {name}')
    if p.suffix == '.csv':
        with p.open(newline='', encoding='utf-8') as h:
            rd = csv.DictReader(h)
            fields = set(rd.fieldnames or [])
            if not common <= fields:
                fail(f'bad schema {name}: missing {sorted(common - fields)}')

# ---- 2. input hashes
fr = json.loads((core / 'stage2b_input_freeze.json').read_text())
if fr.get('gate') != 'PASS':
    fail(f"input freeze gate is {fr.get('gate')!r}")
for key in ('stage2a_git_sha', 'dataset_content_manifest_sha256'):
    if not fr.get(key):
        fail(f'input freeze is missing {key}')
if fr.get('dataset_content_manifest_sha256') != fr.get('dataset_content_manifest_expected'):
    fail('dataset content manifest does not match the frozen expectation')

# ---- 3. baseline reproduction gate
rg = core / 'stage2b_reproduction_gate.json'
if rg.is_file():
    g = json.loads(rg.read_text())
    if g.get('gate') != 'PASS':
        fail(f"baseline reproduction gate is {g.get('gate')!r}")

# ---- 4. selection happened on the declared partitions only
with (core / 'stage2b_localizer_selection.csv').open(newline='', encoding='utf-8') as h:
    parts = {row['partition'] for row in csv.DictReader(h)}
if not parts <= {'F4_CAL', 'healthy_val', 'healthy_train'}:
    fail(f'localizer selection touched a forbidden partition: {sorted(parts)}')
with (core / 'stage2b_sequential_metrics.csv').open(newline='', encoding='utf-8') as h:
    tune = {row['partition'] for row in csv.DictReader(h)}
if not tune <= {'healthy_val'}:
    fail(f'sequential tuning touched a forbidden partition: {sorted(tune)}')

# ---- 5. decision JSON agrees with the memo and the manifest
ev = json.loads((core / 'stage2b_decision_evidence.json').read_text())
allowed = {'GO_CONTACT_LOADPATH_MONITOR', 'PIVOT_SUPPORT_ONLY_LOCALIZER',
           'PIVOT_LOADPATH_LOCALIZATION_ONLY', 'PIVOT_SEQUENTIAL_DETECTION_ONLY',
           'PIVOT_CONTEXT_CALIBRATION_ONLY', 'NO_GO_CONTACT_PRODUCT', 'BLOCKED'}
if ev.get('decision') not in allowed:
    fail(f"decision {ev.get('decision')!r} is not in the pre-registered vocabulary")
memo = (core / 'stage2b_decision_memo.md').read_text()
if ev['decision'] not in memo.splitlines()[0]:
    fail('the decision memo headline does not name the decision in the evidence JSON')
man = json.loads((core / 'stage2b_run_manifest.json').read_text())
if man.get('decision') != ev.get('decision'):
    fail('run manifest and decision evidence disagree')

# ---- 6. historical PR heads were not changed
for h_ in fr.get('historical_branch_heads', []):
    if h_.get('unchanged') is False:
        fail(f"historical branch {h_.get('branch')} was rewritten")

json.loads((r / '07_MANIFEST.json').read_text())
print('REVIEW_SMOKE=PASS decision=' + str(ev.get('decision')))
PY
"""

REVIEW_PROMPT = """# Independent adversarial review prompt — CERTO-FDI Stage 2B

You are reviewing an audit, not a paper. Assume nothing in it is correct or novel. This stage
**overturns a conclusion of the previous stage**, so the bar for its own controls is higher, not
lower.

## What was asked

With `chain_gnn_aug` frozen and no new network anywhere: how much of the contact-link localization
signal is serial-chain load-path *support* and how much is Cartesian subspace geometry; does
rank-aware subspace scoring help; does an ambiguity-aware accept/defer rule reduce error; can
healthy-only context calibration plus sequential monitoring reach 50 event false alarms per hour;
and does scaling the healthy set from 40 to 160 episodes change any of it?

## What to attack, in order

1. **The control that overturns Stage 2A.** Stage 2A concluded "load-path structure, not Cartesian
   geometry" because a shuffled-time control reproduced most of the gain. Stage 2B argues that
   control was not geometry-free — shuffling time keeps the real per-window Jacobians. Is the new
   `support_prefix_rankmatched` control genuinely geometry-free? Check
   `11_CODE_SNAPSHOT/src/certo_fdi/stage2b/loadpath_controls.py`. Does it preserve the support mask
   and the numerical rank *exactly* (`13_CORE_RESULTS/stage2b_rank_audit.csv`)? If the ranks differ,
   the whole decomposition is void.
2. **Rank matching.** Higher rank must never confer an automatic advantage. The mutation test
   (`12_TEST_REPORTS`, `tests/test_stage2b_rank_mutations.py`) adds orthogonal, uninformative
   dimensions and asserts the raw residual degrades while BIC and the GLRT do not. Is the mutation
   really uninformative? Is the positive control strong enough to be meaningful?
3. **Selection hygiene.** One localization score out of five and an accept/defer threshold were
   selected. They must have been selected on `F4_CAL`, a separately generated contact partition with
   provably disjoint seeds, and never on the final F4 test set. Check the seed disjointness in
   `stage2b_contact_calibration_manifest.csv`, and check `tests/test_stage2b_no_leakage.py` — it
   parses the runners and asserts no test-set symbol reaches a fit or a selector.
4. **The detector's operating point.** The memo reports each detection condition at its *most
   favourable* value over all validation-admissible operating points, because healthy validation
   resolves the false-alarm rate too coarsely to break ties. Is that oracle framing honest, or does
   it hide a selection? Note that it can only make the GO decision easier. Compare it against the
   pre-registered conservative rule reported next to it.
5. **The zero-denominator ratio.** The healthy-ID false-alarm rate is exactly zero at the best
   operating points, so the OOD/ID ratio is reported as non-estimable and the condition is failed
   conservatively. Is failing it the right call, or should the arm have been declared void?
6. **Statistical units.** Every interval must be an episode-cluster bootstrap. A window-level IID
   bootstrap anywhere is an integrity failure, not a nitpick — the windows overlap.
7. **The literature record.** Claim N1 was *retired* because the bounded search found the
   serial-chain prefix-support isolation rule and Jacobian-transpose projection are standard prior
   art. Check that no text in this package claims either as new, and that nothing was upgraded on
   the basis of an abstract-level search.

## Hard rules that were meant to hold

- the final F4 test set selected nothing — not the localizer, not a threshold, not a wrapper;
- calibration and sequential parameters were tuned on healthy validation episodes only;
- the episode, never the window, is the unit of statistical independence;
- no exact conditional CFAR claim; coverage is marginal or grouped empirical only;
- network-internal messages are never called physical wrenches;
- PR #1–#4 stay Draft, unmerged, and their heads unchanged;
- no new encoder, no architecture search, no F6 delay dictionary, no instantaneous F5 dictionary.

Report anything that would change the decision, and anything stated more strongly than the
evidence supports. A finding that the overturning control is itself flawed is the most valuable
thing you can produce.
"""


def _read_me(decision: str, run_id: str) -> str:
    return (
        "# CERTO-FDI Stage 2B review package\n\n"
        f"**Decision: `{decision}`** · run `{run_id}`\n\n"
        "This package is evidence for independent adversarial review. It is not authorization to merge, to claim\n"
        "novelty, or to proceed to hardware. Start with `01_INDEPENDENT_REVIEW_PROMPT.md`, then\n"
        "`03_DECISION_MEMO.md`, `04_KNOWN_ISSUES.md` and `13_CORE_RESULTS/`.\n\n"
        "What this stage concluded, in one line: a genuinely geometry-free, rank-matched support control does\n"
        "**not** reproduce the contact-localization gain, which overturns the Stage 2A attribution — and every\n"
        "product threshold is still missed, so the terminal state is the pre-registered default rather than a pivot.\n\n"
        "Hard rules that constrain every claim inside:\n\n"
        "- the final F4 test set selected nothing; the localizer score and the accept/defer threshold were chosen\n"
        "  on a separately generated `F4_CAL` partition with provably disjoint seeds;\n"
        "- calibration and sequential parameters were tuned on healthy validation episodes only;\n"
        "- the episode is the unit of statistical independence everywhere; no window-level IID bootstrap is used;\n"
        "- coverage claims are marginal or grouped empirical only — never exact conditional CFAR;\n"
        "- the serial-chain prefix-support rule and Jacobian-transpose projection are **prior art**, not findings\n"
        "  of this stage; the bounded literature search retired that novelty claim;\n"
        "- the pre-registered decision rules were committed before any Stage 2B metric existed.\n"
    )


def _populate_common(root: Path, run_root: Path, repo: Path, decision: str) -> None:
    results = run_root / "results"
    root.mkdir(parents=True, exist_ok=False)
    (root / "00_READ_ME_FIRST.md").write_text(_read_me(decision, run_root.name), encoding="utf-8")
    (root / "01_INDEPENDENT_REVIEW_PROMPT.md").write_text(REVIEW_PROMPT, encoding="utf-8")
    manifest = json.loads((results / "stage2b_run_manifest.json").read_text()) if (results / "stage2b_run_manifest.json").is_file() else {}
    evidence = json.loads((results / "stage2b_decision_evidence.json").read_text()) if (results / "stage2b_decision_evidence.json").is_file() else {}
    ev = evidence.get("evidence", {})
    summary = {
        "run_root": str(run_root), "repo_root": str(repo),
        "git_sha": _git(repo, "rev-parse", "HEAD").strip(), "branch": _git(repo, "branch", "--show-current").strip(),
        "dirty": bool(_git(repo, "status", "--porcelain").strip()),
        "decision": evidence.get("decision"), "decision_reasons": evidence.get("reasons"),
        "evaluation_order": evidence.get("evaluation_order"),
        "stage2a_git_sha": evidence.get("stage2a_git_sha"),
        "reproduction_gate": evidence.get("reproduction_gate"),
        "config_sha256": manifest.get("config_sha256"),
        "dataset_manifest_sha256": manifest.get("dataset_manifest_sha256"),
        "frozen_inputs": manifest.get("frozen_inputs"),
        "go_conditions": evidence.get("go", {}).get("conditions"),
        "n_go_conditions_pass": sum(1 for v in evidence.get("go", {}).get("conditions", {}).values() if v),
        "loadpath_top1_by_method": ev.get("loadpath", {}).get("top1_by_method"),
        "detection_headline": {k: ev.get("detection", {}).get(k) for k in
                               ("false_alarms_per_hour", "event_tpr", "event_f1", "healthy_ood_id_ratio",
                                "median_delay_s", "p95_delay_s", "n_operating_points")},
        "localization_headline": {k: ev.get("localization", {}).get(k) for k in
                                  ("episode_top1", "mean_chain_distance", "n_links_recall_ge_040")},
        "literature_status": ev.get("literature", {}),
        "phases": manifest.get("phases"), "figures": manifest.get("figures"),
        "n_artefacts": manifest.get("n_files"),
    }
    (root / "02_EXECUTION_SUMMARY.md").write_text(
        "# Execution summary\n\n```json\n" + json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n```\n",
        encoding="utf-8")
    for src, dst in ((results / "stage2b_decision_memo.md", "03_DECISION_MEMO.md"),
                     (results / "stage2b_known_issues.md", "04_KNOWN_ISSUES.md"),
                     (results / "stage2b_claim_ledger.csv", "05_CLAIMS_LEDGER.csv")):
        if src.is_file():
            _copy_file(src, root / dst)
        else:
            (root / dst).write_text("(not produced by this run)\n", encoding="utf-8")
    for d in REQUIRED_DIRECTORIES:
        (root / d).mkdir()
    prov = root / "09_GIT_PROVENANCE"
    (prov / "git_status.txt").write_text(_git(repo, "status", "--short", "--branch"))
    (prov / "git_log.txt").write_text(_git(repo, "log", "--stat", "--decorate", "-40"))
    (prov / "git_log_oneline.txt").write_text(_git(repo, "log", "--oneline", "--decorate", "-80"))
    (prov / "git_remote.txt").write_text(_git(repo, "remote", "-v"))
    (prov / "working_tree.patch").write_text(_git(repo, "diff", "--binary"))
    (prov / "decision_rules_first_commit.txt").write_text(
        _git(repo, "log", "--follow", "--oneline", "--", "src/certo_fdi/stage2b/decision_stage2b.py"))
    (prov / "frozen_config_first_commit.txt").write_text(
        _git(repo, "log", "--follow", "--oneline", "--", "configs/stage2b_contact_loadpath.yaml"))
    # the stacked-branch claim, made checkable: what Stage 2B changed relative to Stage 2A
    (prov / "diff_stat_vs_stage2a.txt").write_text(
        _git(repo, "diff", "--stat", "bcf2ad5c978f58dc159636d64d0b5c81efb9e396..HEAD"))
    _write_git_archive(repo, root / "11_CODE_SNAPSHOT")
    _copy_contents(repo / "configs", root / "10_CONFIGS" / "repository_configs")
    _copy_contents(run_root / "config", root / "10_CONFIGS" / "run_config")
    _copy_contents(run_root / "tests", root / "12_TEST_REPORTS")
    for name in ("stage2b_test_report.json",):
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
              "21_ENVIRONMENT", "22_FROZEN_INPUT_HASHES", "23_LITERATURE", "24_GENERATED_PARTITIONS"):
        (root / d).mkdir(exist_ok=True)
    _copy_contents(run_root / "results", root / "16_FULL_RESULTS")
    _copy_contents(run_root / "logs", root / "17_RUN_LOGS")
    _copy_contents(run_root / "provenance", root / "18_PROVENANCE")
    _copy_contents(run_root / "environment", root / "21_ENVIRONMENT")
    for phase in ("p0_freeze", "p1_loadpath", "p2_localization", "p3_calibration", "p4_healthy",
                  "p5_literature", "p6_decision"):
        src = run_root / phase
        if src.is_dir():
            _copy_contents(src, root / "20_PHASE_ARTEFACTS" / phase, exclude_suffixes=(".npz", ".h5"))
    if bundle.is_file():
        _copy_file(bundle, root / "19_GIT_BUNDLE" / bundle.name)

    # checkpoint index (never the weights themselves)
    rows = []
    for p in sorted((run_root / "checkpoints").glob("*.pt")):
        rows.append({"checkpoint": p.name, "size_bytes": p.stat().st_size, "sha256": sha256_file(p),
                     "absolute_path": str(p)})
    with (root / "16_FULL_RESULTS" / "checkpoint_index.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["checkpoint", "size_bytes", "sha256", "absolute_path"])
        w.writeheader()
        w.writerows(rows)

    # frozen input hashes
    for name in ("stage2b_input_freeze.json", "stage2b_reproduction_gate.json"):
        p = run_root / "results" / name
        if p.is_file():
            _copy_file(p, root / "22_FROZEN_INPUT_HASHES" / name)
    for name in ("episode_sha256_manifest.csv", "replay_fidelity.csv"):
        p = run_root / "provenance" / name
        if p.is_file():
            _copy_file(p, root / "22_FROZEN_INPUT_HASHES" / name)

    # the two partitions Stage 2B generated -- manifests and indices only, never the episode files
    for sub, label in (("contact_calibration_F4", "F4_CAL"), ("healthy_expansion", "healthy_expansion")):
        src = storage / "03_data" / "stage2b" / sub
        dst = root / "24_GENERATED_PARTITIONS" / label
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("manifest.json", "episode_index.csv"):
            if (src / name).is_file():
                _copy_file(src / name, dst / name)
        n = len(list((src / "episodes").glob("*.h5"))) if (src / "episodes").is_dir() else 0
        (dst / "README.md").write_text(
            f"# {label}\n\n{n} generated episode files live at `{src / 'episodes'}` and are **not** shipped in\n"
            "this package (size). `manifest.json` carries a sha256 per episode plus a joint content-manifest\n"
            "hash, and every episode is reproducible from its (seed, context, fault spec) triple in the same\n"
            "file, so the partition is verifiable without the binaries.\n", encoding="utf-8")

    for name in ("stage2b_literature_verification.md", "NOT_PERFORMED.md", "stage2b_literature_probe.json",
                 "stage2b_literature_sources.csv", "stage2b_literature_claims.csv"):
        p = run_root / "results" / name
        if p.is_file():
            _copy_file(p, root / "23_LITERATURE" / name)

    with (root / "16_FULL_RESULTS" / "large_file_manifest.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["absolute_path", "size_bytes", "sha256"])
        for p in sorted(run_root.rglob("*")):
            if p.is_file() and p.stat().st_size > 1_000_000:
                w.writerow([str(p), p.stat().st_size, sha256_file(p)])


def _write_tree(root: Path) -> None:
    skip = {"06_FILE_TREE.txt", "07_MANIFEST.json", "08_SHA256SUMS.txt"}
    lines = [f"{p.relative_to(root).as_posix()}{'/' if p.is_dir() else ''}"
             for p in sorted(root.rglob("*")) if p.name not in skip]
    (root / "06_FILE_TREE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(root: Path) -> None:
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name not in {"07_MANIFEST.json", "08_SHA256SUMS.txt"}:
            files[p.relative_to(root).as_posix()] = {"sha256": sha256_file(p), "size_bytes": p.stat().st_size}
    (root / "07_MANIFEST.json").write_text(
        json.dumps({"files": files, "file_count": len(files)}, indent=2, sort_keys=True), encoding="utf-8")
    lines = [f"{sha256_file(p)}  {p.relative_to(root).as_posix()}"
             for p in sorted(root.rglob("*")) if p.is_file() and p.name != "08_SHA256SUMS.txt"]
    (root / "08_SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate(zpath: Path) -> dict:
    return validate_zip(zpath, REQUIRED_FILES, REQUIRED_DIRECTORIES,
                        sha_file="08_SHA256SUMS.txt", manifest_file="07_MANIFEST.json",
                        reproduce_script="15_REPRODUCE_REVIEW.sh")


def _build_one(kind: str, base: str, run_root: Path, repo: Path, storage: Path, staging: Path,
               dest_root: Path, bundle: Path, decision: str) -> dict:
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
    status.write_text(json.dumps(
        {"validation_status": "PASS", "decision": decision,
         "checks": ["zip_crc", "fresh_extract", "sha256_manifest", "required_topology", "reproduce_smoke",
                    "secret_scan"]}, indent=2, sort_keys=True), encoding="utf-8")
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
    base = f"CERTO_FDI_stage2b_contact_loadpath_sequential_{milestone}_{ts}_{git[:7]}"
    manifest = run / "results" / "stage2b_run_manifest.json"
    decision = json.loads(manifest.read_text()).get("decision", "BLOCKED") if manifest.is_file() else "BLOCKED"
    if decision not in DECISION_VOCABULARY:
        raise ValueError(f"decision {decision!r} is not in the pre-registered vocabulary")
    exchange = storage / "06_review_exchange"
    staging_parent = exchange / "package_staging" / "working"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{base}_", dir=staging_parent))
    bundle_dir = storage / "07_backups" / "git_bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = bundle_dir / f"CERTO-FDI_{run.name}_{git[:7]}.bundle"
    subprocess.run(["git", "-C", str(repo), "bundle", "create", str(bundle), "--all"],
                   check=True, capture_output=True)
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
                        "validation_status": r["validation_status"], "scientific_status": decision,
                        "absolute_path": p})
            (exchange / f"LATEST_{kind}_PACKAGE.txt").write_text(f"{p}\n", encoding="utf-8")
    (run / "manifests").mkdir(parents=True, exist_ok=True)
    (run / "manifests" / "REVIEW_PACKAGE_STATUS.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--storage-root", default=os.environ.get("CERTO_STORAGE_ROOT", ""),
                    required=not os.environ.get("CERTO_STORAGE_ROOT"))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--milestone", default="AUDIT")
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--workers", default=None)
    a = ap.parse_args()
    run_root = Path(a.storage_root) / "04_runs" / "stage2b_contact_loadpath_sequential" / a.run_id
    print(json.dumps(build(run_root, a.repo_root, a.milestone), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
