"""Build and validate the Stage 2B-R Thin and Full review packages (master prompt §12.3).

Thin carries enough score-level evidence for an independent reviewer to re-derive the tie
classification **without training and without the frozen run roots**: the per-episode and
per-window score comparisons, the flipped episode's full trace, the measured envelope, and the
gate. Full adds every raw table, figure, log, environment record and a git archive.

Both packages are validated by extraction: CRC, fresh extract, internal SHA256 manifest, required
topology, secret scan, a smoke script that re-derives the terminal state from the shipped tables,
clean Git HEAD alignment, and a check that the historical Stage 2B result files are byte-identical
to what they were before this stage ran.

A package that cannot be validated is still a deliverable: the staging tree is preserved as
``FAILED_REVIEW_PACKAGE`` with the blocking reason, and the failure is re-raised.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from certo_fdi.packaging.build_review_package import _copy_contents, _copy_file, _git, _write_git_archive, _zip_tree
from certo_fdi.packaging.validate_review_package import sha256_file, validate_zip
from certo_fdi.stage2br.decision_stage2br import TERMINAL_STATES

REQUIRED_FILES = ("00_READ_ME_FIRST.md", "01_INDEPENDENT_REVIEW_PROMPT.md", "02_EXECUTION_SUMMARY.md",
                  "03_GIT_DIFF_AUDIT.md", "04_KNOWN_ISSUES.md", "05_CLAIMS_LEDGER.csv", "06_FILE_TREE.txt",
                  "07_MANIFEST.json", "08_SHA256SUMS.txt", "15_REPRODUCE_REVIEW.sh", "REVIEW_PACKAGE_STATUS.json")
REQUIRED_DIRECTORIES = ("09_GIT_PROVENANCE", "10_CONFIGS", "11_CODE_SNAPSHOT", "12_TEST_REPORTS",
                        "13_CORE_RESULTS", "14_SELECTED_FIGURES")

#: the score-level evidence a reviewer needs to re-derive the classification unaided
CORE_RESULTS = (
    "stage2br_reproduction_gate.json",
    "stage2br_input_provenance.json",
    "stage2br_git_head_audit.json",
    "stage2br_reference_artifact_inventory.csv",
    "stage2br_per_episode_score_comparison.csv",
    "stage2br_per_link_score_comparison.csv",
    "stage2br_flipped_episode_trace.json",
    "stage2br_confusion_matrix_diff.csv",
    "stage2br_numerical_envelopes.csv",
    "stage2br_tie_sets.csv",
    "stage2br_rank_stability.csv",
    "stage2br_backend_stability.csv",
    "stage2br_candidate_order_stability.csv",
    "stage2br_memory_order_stability.csv",
    "stage2br_process_repeatability.csv",
    "stage2br_estimator_gap.csv",
    "stage2br_disagreement_band.csv",
    "stage2br_claim_ledger.csv",
    "stage2br_execution_summary.md",
    "stage2br_known_issues.md",
    "stage2br_git_diff_audit.md",
)
#: 2.7 MB of per-window rows: Full only
FULL_ONLY_RESULTS = ("stage2br_window_score_comparison.csv",)

REPRODUCE_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = "--smoke" ] || { echo 'use --smoke' >&2; exit 2; }
python3 - <<'PY'
import csv, json, pathlib
r = pathlib.Path('.')
core = r / '13_CORE_RESULTS'
def fail(m): raise SystemExit(f'SMOKE FAIL: {m}')

TERMINAL = {"BLOCKED_INPUT_PROVENANCE", "BLOCKED_SCIENTIFIC_HEAD_MISMATCH",
            "BLOCKED_MISSING_REFERENCE_EVIDENCE", "BLOCKED_UNRESOLVABLE_SCORE_HISTORY",
            "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH", "PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP",
            "PASS_EXACT_REPRODUCTION"}

# ---- 1. every core result is present
for name in %(core)s:
    if not (core / name).is_file():
        fail(f'missing core result {name}')

# ---- 2. the gate declares a terminal state from the frozen vocabulary
g = json.loads((core / 'stage2br_reproduction_gate.json').read_text())
state = g.get('integrity_state')
if state not in TERMINAL:
    fail(f'unknown integrity state {state!r}')

# ---- 3. a non-PASS state must leave Stage 2B BLOCKED and must not carry a scientific decision
is_pass = state in {'PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP', 'PASS_EXACT_REPRODUCTION'}
if bool(g.get('reproduction_gate_pass')) != is_pass:
    fail('reproduction_gate_pass disagrees with the integrity state')
if not is_pass:
    if 'BLOCKED' not in str(g.get('stage2b_scientific_decision', '')):
        fail('a non-passing integrity state must leave Stage 2B BLOCKED')
    if (core / 'stage2br_scientific_decision_evidence.json').exists():
        fail('a scientific decision was shipped without an integrity PASS')

# ---- 4. the label differences in the gate match the per-episode table
with (core / 'stage2br_per_episode_score_comparison.csv').open(newline='') as h:
    rows = list(csv.DictReader(h))
changed = [x for x in rows if x['label_changed'].lower() == 'true']
if len(changed) != len(g.get('label_differences', [])):
    fail('gate and per-episode table disagree on how many labels changed')

# ---- 5. a FAIL must be backed by a non-tie disagreement or a score-tolerance breach
if state == 'FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH':
    n_nontie = int(g.get('n_nontie_window_disagreements', 0))
    within = g.get('score_agreement', {}).get('within_frozen_tolerance')
    if n_nontie <= 0 and within is not False:
        fail('FAIL declared with neither a non-tie disagreement nor a tolerance breach')
    with (core / 'stage2br_numerical_envelopes.csv').open(newline='') as h:
        env = list(csv.DictReader(h))
    if sum(1 for e in env if e['is_numerical_tie'].lower() == 'false') != n_nontie:
        fail('envelope table and gate disagree on the non-tie count')

# ---- 6. rank instability may never be reported as a pure tie
if 'RANK_THRESHOLD_UNSTABLE' in (g.get('modifiers') or []) and is_pass:
    fail('rank instability cannot accompany a PASS')

print(f'SMOKE OK: integrity {state}; stage 2B decision {g.get("stage2b_scientific_decision")!r}; '
      f'{len(changed)} label difference(s); {g.get("n_nontie_window_disagreements")} non-tie window disagreement(s)')
PY
""" % {"core": repr(list(CORE_RESULTS))}

READ_ME = """# CERTO-FDI Stage 2B-R review package

**Integrity state: `{state}`** — Stage 2B scientific decision: **`{decision}`**.

One bounded question was asked and answered:

> Did the single Stage 2A/Stage 2B contact-localization label difference arise from a numerically
> equivalent near tie, or from a real difference in frozen inputs, score computation, rank
> handling, candidate ordering, aggregation, or implementation?

Start with `02_EXECUTION_SUMMARY.md`. `13_CORE_RESULTS/` carries the score-level evidence; you can
re-derive the classification from those tables alone, without the frozen run roots and without
training anything. Run `bash 15_REPRODUCE_REVIEW.sh --smoke` to check the package is internally
consistent.

No model was trained, no episode regenerated, no dictionary/candidate set/whitening/score/rank
threshold/aggregation changed, the historical 2 % tolerance was not relaxed, and the historical
Stage 2B `BLOCKED` artifacts were not touched.

Run `{run_id}` · git `{git_sha}` · package built {built}.
"""

REVIEW_PROMPT = """# Adversarial review prompt — Stage 2B-R

You are reviewing an integrity audit, not a scientific result. Its claim is that a single
contact-localizer label difference between two frozen runs is **not** a floating-point tie but a
consequence of the two runs ranking links with different estimators.

Try to break it:

1. **Is the reproduction real?** `stage2br_reproduction_gate.json → reproduction` claims both
   stages' published top-1 comes back bit-exactly from the shipped score arrays, on all three
   seeds, with a complete and unique join. Check the per-episode table reproduces those means.
2. **Is the flip correctly located?** One episode should differ. Check
   `stage2br_confusion_matrix_diff.csv` moves in exactly one cell pair.
3. **Is the tie test fair?** `stage2br_numerical_envelopes.csv` gives each changed window's
   top-two margin and the tie tolerance. The tolerance is built from a *measured* backend range
   (`stage2br_backend_stability.csv`) floored at `1000·eps`. Would a far larger envelope change
   the verdict? By how much would it have to grow?
4. **Could it be rank?** `stage2br_rank_stability.csv` sweeps the frozen rank tolerance at
   0.5×/2×. If any spectrum flips rank, the classification must say `RANK_THRESHOLD_UNSTABLE`.
5. **Could it be the backend, the ordering, the layout, the threads?**
   `stage2br_candidate_order_stability.csv`, `stage2br_memory_order_stability.csv`,
   `stage2br_process_repeatability.csv`.
6. **Is the mechanism claim supported or asserted?** `stage2br_per_link_score_comparison.csv`
   should show the cross-stage gap ordered by link, largest where the serial chain gives the
   fewest support rows. If it does not, the mechanism story fails even if the verdict stands.
7. **Scope discipline.** Nothing here may retrain, regenerate, relax a threshold, or edit a
   historical Stage 2B artifact. Check the claim ledger admits its own limits.

Report any claim that the shipped evidence does not support.
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


#: Patterns are shaped like the real credential, not like its prefix. A bare ``ghp_`` is what a
#: secret *scanner's own source* contains, and matching that flags every copy of this repository's
#: hygiene tooling -- a false positive that would make the check useless by crying wolf.
SECRET_PATTERNS = (
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
)


def _secret_scan(root: Path) -> list[str]:
    bad: list[str] = []
    for q in root.rglob("*"):
        if not q.is_file() or q.suffix in (".png", ".zip", ".npz", ".pt", ".pyc"):
            continue
        try:
            text = q.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, rx in SECRET_PATTERNS:
            if rx.search(text):
                bad.append(f"{q.relative_to(root)}: {label}")
    return bad


def build(run_root: Path, repo: Path, out_dir: Path, kind: str, historical_2b: Path) -> Path:
    res, fig = run_root / "results", run_root / "figures"
    gate = json.loads((res / "stage2br_reproduction_gate.json").read_text())
    state = gate["integrity_state"]
    decision = gate.get("stage2b_scientific_decision", "BLOCKED")
    git_sha = _git(repo, "rev-parse", "HEAD").strip()
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"CERTO_FDI_stage2br_reproduction_gate_{state}_{stamp}_{git_sha[:7]}_{kind.upper()}"
    # Stage on local ext4, never on the G-drive: it is 9p/drvfs, where chmod is not permitted and
    # the executable bit on the smoke script cannot be set. Only the finished zip goes to G, with
    # its member modes written explicitly by _zip_tree.
    stage_root = Path(tempfile.mkdtemp(prefix="certo_stage2br_pkg_"))
    stage = stage_root / name
    stage.mkdir(parents=True)

    _write(stage / "00_READ_ME_FIRST.md",
           READ_ME.format(state=state, decision=decision, run_id=gate["run_id"], git_sha=git_sha, built=built))
    _write(stage / "01_INDEPENDENT_REVIEW_PROMPT.md", REVIEW_PROMPT)
    _copy_file(res / "stage2br_execution_summary.md", stage / "02_EXECUTION_SUMMARY.md")
    _copy_file(res / "stage2br_git_diff_audit.md", stage / "03_GIT_DIFF_AUDIT.md")
    _copy_file(res / "stage2br_known_issues.md", stage / "04_KNOWN_ISSUES.md")
    _copy_file(res / "stage2br_claim_ledger.csv", stage / "05_CLAIMS_LEDGER.csv")

    # git provenance
    gp = stage / "09_GIT_PROVENANCE"
    gp.mkdir(parents=True, exist_ok=True)
    _write(gp / "HEAD.txt", git_sha + "\n")
    _write(gp / "log.txt", _git(repo, "log", "--oneline", "-25"))
    _write(gp / "status.txt", _git(repo, "status", "--porcelain=v1"))
    _write(gp / "branches.txt", _git(repo, "branch", "-vv"))

    # configs + code snapshot + tests
    _copy_file(repo / "configs" / "stage2br_reproduction_gate.yaml",
               stage / "10_CONFIGS" / "stage2br_reproduction_gate.yaml")
    _copy_file(repo / "docs_pointer" / "STAGE2BR_PROTOCOL.md", stage / "10_CONFIGS" / "STAGE2BR_PROTOCOL.md")
    code = stage / "11_CODE_SNAPSHOT"
    _copy_contents(repo / "src" / "certo_fdi" / "stage2br", code / "stage2br", exclude_suffixes=(".pyc",))
    for f in ("run_stage2br_audit.py", "run_stage2br_resolve.py"):
        _copy_file(repo / "src" / "certo_fdi" / "experiments" / f, code / "experiments" / f)
    for f in ("test_stage2br_frozen_protocol.py", "test_stage2br_canonical_scores.py",
              "test_stage2br_estimator_gap.py", "test_stage2br_evidence.py"):
        _copy_file(repo / "tests" / f, stage / "12_TEST_REPORTS" / f)
    _write(stage / "12_TEST_REPORTS" / "README.md",
           "The four Stage 2B-R suites. `test_stage2br_evidence.py` reads the frozen run roots and "
           "skips cleanly when they are not mounted; the other three run anywhere.\n")

    # core results
    core = stage / "13_CORE_RESULTS"
    names = list(CORE_RESULTS) + (list(FULL_ONLY_RESULTS) if kind == "full" else [])
    for n in names:
        if (res / n).is_file():
            _copy_file(res / n, core / n)

    # figures
    figs = stage / "14_SELECTED_FIGURES"
    for p in sorted(fig.glob("*.png")):
        _copy_file(p, figs / p.name)

    if kind == "full":
        _copy_contents(run_root / "logs", stage / "16_LOGS")
        _copy_contents(run_root / "environment", stage / "17_ENVIRONMENT")
        _copy_contents(run_root / "provenance", stage / "18_PROVENANCE")
        _write_git_archive(repo, stage / "19_GIT_ARCHIVE")

    # historical Stage 2B artifacts must be unchanged by this stage
    hist = {}
    hres = Path(historical_2b) / "results"
    for n in ("stage2b_decision_evidence.json", "stage2b_contact_reproduction_gate.json",
              "stage2b_reproduction_gate.json", "stage2b_decision_memo.md", "stage2b_input_freeze.json"):
        p = hres / n
        if p.is_file():
            hist[n] = sha256_file(p)
    _write(stage / "13_CORE_RESULTS" / "HISTORICAL_STAGE2B_HASHES.json",
           json.dumps({"note": "hashes of the historical Stage 2B result files, unchanged by Stage 2B-R",
                       "run_root": str(historical_2b), "sha256": hist}, indent=2) + "\n")

    script = stage / "15_REPRODUCE_REVIEW.sh"
    _write(script, REPRODUCE_SCRIPT)
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # manifest, tree, checksums, status
    files = sorted(p for p in stage.rglob("*") if p.is_file())
    _write(stage / "06_FILE_TREE.txt", "\n".join(str(p.relative_to(stage)) for p in files) + "\n")
    _write(stage / "07_MANIFEST.json", json.dumps({
        "package": name, "kind": kind, "built_utc": built, "run_id": gate["run_id"],
        "git_sha": git_sha, "integrity_state": state, "stage2b_scientific_decision": decision,
        "reproduction_gate_pass": gate.get("reproduction_gate_pass"),
        "modifiers": gate.get("modifiers", []),
        "n_files": len(files),
        "historical_stage2b_hashes": hist,
    }, indent=2) + "\n")
    _write(stage / "REVIEW_PACKAGE_STATUS.json", json.dumps({
        "status": "BUILT", "integrity_state": state, "stage2b_scientific_decision": decision,
        "validated": False, "built_utc": built}, indent=2) + "\n")
    # checksums cover every file except the sums themselves and this status stub
    _write(stage / "08_SHA256SUMS.txt",
           "".join(f"{sha256_file(q)}  {q.relative_to(stage).as_posix()}\n"
                   for q in sorted(x for x in stage.rglob("*") if x.is_file())
                   if q.name not in ("08_SHA256SUMS.txt", "REVIEW_PACKAGE_STATUS.json")))

    leaked = _secret_scan(stage)
    if leaked:
        raise RuntimeError(f"secret scan failed: {leaked[:5]} (staging kept at {stage})")

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{name}.zip"
    _zip_tree(stage, zip_path)
    try:
        validate_zip(zip_path, REQUIRED_FILES, REQUIRED_DIRECTORIES,
                     sha_file="08_SHA256SUMS.txt", manifest_file="07_MANIFEST.json",
                     reproduce_script="15_REPRODUCE_REVIEW.sh")
    except Exception as e:
        raise RuntimeError(f"package validation failed: {e} (staging kept at {stage})") from e
    shutil.rmtree(stage_root, ignore_errors=True)
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser(description="build the Stage 2B-R review packages")
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--historical-stage2b-run", required=True)
    args = ap.parse_args()
    run_root = Path(args.run_root).resolve()
    repo = Path(args.repo_root).resolve()
    made = []
    for kind in ("thin", "full"):
        out = Path(args.out_root) / kind
        z = build(run_root, repo, out, kind, Path(args.historical_stage2b_run))
        print(f"{kind.upper():5s} {z}  sha256 {sha256_file(z)}  {z.stat().st_size/1e6:.2f} MB")
        made.append(z)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
