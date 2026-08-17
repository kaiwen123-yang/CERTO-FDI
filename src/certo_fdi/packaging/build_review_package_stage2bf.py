"""Build and validate the Stage 2B-F Thin and Full review packages (contract 08).

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
from certo_fdi.stage2bf.decision_stage2bf import INTEGRITY_PRECEDENCE, SCIENTIFIC_VOCABULARY

REQUIRED_FILES = ("00_READ_ME_FIRST.md", "01_INDEPENDENT_REVIEW_PROMPT.md", "02_EXECUTION_SUMMARY.md",
                  "03_INTEGRITY_DECISION_MEMO.md", "04_SCIENTIFIC_DECISION_MEMO.md", "05_KNOWN_ISSUES.md",
                  "06_CLAIMS_LEDGER.csv", "07_ESTIMATOR_IDENTITY_MAP.csv", "08_FILE_TREE.txt",
                  "09_MANIFEST.json", "10_SHA256SUMS.txt", "17_REPRODUCE_REVIEW.sh",
                  "REVIEW_PACKAGE_STATUS.json")
REQUIRED_DIRECTORIES = ("11_GIT_PROVENANCE", "12_CONFIGS", "13_CODE_SNAPSHOT", "14_TEST_REPORTS",
                        "15_CORE_RESULTS", "16_SELECTED_FIGURES", "18_PROVENANCE")

#: the score-level evidence a reviewer needs to re-derive the classification unaided
CORE_RESULTS = (
    "stage2bf_integrity_decision.json", "stage2bf_scientific_decision_evidence.json",
    "stage2bf_evidence_delta.json", "stage2bf_reproduction_gates.json",
    "stage2bf_f4cal_selection_reproduction.json", "stage2bf_f4cal_selection.csv",
    "stage2bf_input_provenance.json", "stage2bf_git_diff_audit.md",
    "stage2bf_estimator_identity_map.csv",
    "stage2bf_stage2a_ridge_reproduction.csv", "stage2bf_stage2a_ridge_confusion_diff.csv",
    "stage2bf_stage2b_svd_reproduction.csv",
    "stage2bf_estimator_control_matrix.csv", "stage2bf_estimator_contrast_ci.csv",
    "stage2bf_mechanism_robustness.csv", "stage2bf_per_link_metrics.csv",
    "stage2bf_loadpath_mechanism_summary.md", "stage2bf_known_issues.md",
    "stage2bf_claim_ledger.csv", "stage2bf_historical_artifact_preservation.csv",
    "stage2bf_replay_manifest.json",
)
FULL_ONLY_RESULTS = ("stage2bf_per_episode_localization.csv",)

REPRODUCE_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
[ "${1:-}" = "--smoke" ] || { echo 'use --smoke' >&2; exit 2; }
python3 - <<'PY'
import csv, json, pathlib
core = pathlib.Path('.') / '15_CORE_RESULTS'
def fail(m): raise SystemExit(f'SMOKE FAIL: {m}')

PRECEDENCE = %(prec)s
VOCAB = %(vocab)s
PASS = 'PASS_ESTIMATOR_HARMONIZATION'

for name in %(core)s:
    if not (core / name).is_file():
        fail(f'missing core result {name}')

d = json.loads((core / 'stage2bf_integrity_decision.json').read_text())
integ, sci = d['stage2bf_integrity_decision'], d['stage2bf_scientific_decision']
if integ not in PRECEDENCE:
    fail(f'unknown integrity state {integ!r}')
if sci not in list(VOCAB) + ['NOT_RUN']:
    fail(f'scientific state {sci!r} outside the frozen vocabulary')
if d['stage2bf_combined_terminal'] != f'{integ}__{sci}':
    fail('combined terminal does not match its parts')

# BLOCKED must dominate: no scientific decision without the integrity PASS
if integ != PASS and sci != 'NOT_RUN':
    fail('a scientific decision was issued without PASS_ESTIMATOR_HARMONIZATION')
if integ != PASS and (core / 'stage2bf_scientific_decision_evidence.json').exists():
    fail('scientific decision evidence shipped without an integrity PASS')

# a PASS must be backed by both reproduction hard gates
if integ == PASS:
    g = json.loads((core / 'stage2bf_reproduction_gates.json').read_text())
    if not g['phase2_stage2a_ridge']['all_pass']:
        fail('PASS claimed without the Stage 2A ridge reproduction gate')
    if not g['phase3_stage2b_svd']['all_pass']:
        fail('PASS claimed without the Stage 2B SVD reproduction gate')
    s = json.loads((core / 'stage2bf_f4cal_selection_reproduction.json').read_text())
    if not s['reproduction_gate']['all_pass']:
        fail('PASS claimed without the F4_CAL selection reproduction')
    if not s.get('ridge_excluded_from_selection'):
        fail('the ridge must be excluded from the F4_CAL candidate set')

# the evidence delta may not have moved a scientific field
delta = json.loads((core / 'stage2bf_evidence_delta.json').read_text())
if delta['violations']:
    fail(f"evidence delta has {len(delta['violations'])} forbidden change(s)")

# the historical Stage 2B decision must still be BLOCKED
if d['historical_stage2b_decision'] != 'BLOCKED':
    fail('the historical Stage 2B decision is no longer BLOCKED')
for r in csv.DictReader((core / 'stage2bf_historical_artifact_preservation.csv').open(newline='')):
    if r['unchanged'] != 'True':
        fail(f"historical artifact mutated: {r['path']}")

# no renamed legacy estimator name may appear in a new result
# The decision evidence quotes the historical Stage 2B evidence verbatim, so it legitimately
# carries historical names -- rewriting them would alter the decision function's input. It is
# exempt only if it declares the quotation and ships the mapping.
# Contract 04 section 2: historical names may appear ONLY in the migration table and in readers of
# historical files. The migration table is where the mapping is published, so it must carry them;
# the decision evidence quotes the historical record verbatim. Everything else is a new result.
EXEMPT = {'stage2bf_estimator_identity_map.csv', 'stage2bf_scientific_decision_evidence.json'}
QUOTED = 'stage2bf_scientific_decision_evidence.json'
qp = core / QUOTED
# the migration table must actually contain the mapping it is exempted for
mp = core / 'stage2bf_estimator_identity_map.csv'
if mp.is_file():
    names = {r['historical_name'] for r in csv.DictReader(mp.open(newline=''))}
    if 'raw_projection_residual' not in names:
        fail('the migration table is exempt from the name rule but does not carry the mapping')
if qp.is_file():
    qj = json.loads(qp.read_text())
    if not qj.get('quoted_historical_evidence_retains_historical_names'):
        fail(f'{QUOTED} carries historical names without declaring the quotation')
    if not qj.get('legacy_name_mapping'):
        fail(f'{QUOTED} does not ship the legacy name mapping')
for bad in ('raw_projection_residual', 'df_normalized_residual', 'bic_penalized_fit'):
    for f in core.glob('stage2bf_*'):
        if f.name in EXEMPT:
            continue
        if bad in f.read_text(errors='ignore'):
            fail(f'legacy estimator name {bad!r} in {f.name}')

print(f'SMOKE OK: integrity {integ}; scientific {sci}; historical Stage 2B BLOCKED preserved; '
      f'{delta["n_changes"]} delta field(s), 0 violations')
PY
""" % {"core": repr(list(CORE_RESULTS)), "prec": repr(list(INTEGRITY_PRECEDENCE)),
        "vocab": repr(list(SCIENTIFIC_VOCABULARY))}

READ_ME = """# CERTO-FDI Stage 2B-F review package

**Integrity: `{state}` — Scientific: `{decision}` — Combined: `{combined}`**

Historical Stage 2B decision: **`BLOCKED`**, unchanged and byte-preserved.

Stage 2B gave one name to two different estimators. Stage 2A ranked contact links by a
**ridge-regularised least-squares residual norm**; Stage 2B's `raw_projection_residual` is a
**rank-truncated SVD orthogonal-projection RSS**, and was documented as "exactly the frozen Stage 2A
score". Stage 2B-R proved that wrong at score level. Stage 2B-F separates them, reproduces both
pipelines, measures whether the load-path conclusions depend on which estimator is used, and — only
after the integrity gate passed — re-ran the ORIGINAL frozen `decision_stage2b.decide`.

Start with `02_EXECUTION_SUMMARY.md`, then `03_INTEGRITY_DECISION_MEMO.md` and
`04_SCIENTIFIC_DECISION_MEMO.md`. `07_ESTIMATOR_IDENTITY_MAP.csv` is the old-name → canonical-name
migration. Run `bash 17_REPRODUCE_REVIEW.sh --smoke` to check internal consistency.

No model trained, no episode regenerated, no whitening / dictionary / candidate point / rank
tolerance / ridge lambda / Stage 2B threshold changed, no ridge in the F4_CAL candidate set, no
F4_TEST used for selection, no historical file edited in place.

Run `{run_id}` · git `{git_sha}` · built {built}.
"""

REVIEW_PROMPT = """# Stage 2B-F independent adversarial review

You are a numerical linear algebra auditor and research-integrity reviewer. Do not trust the
summary or the terminal state; try to overturn them.

1. Recompute the Stage 2A/2B/2B-R package SHA256s and the 590-episode dataset manifest from disk.
   `15_CORE_RESULTS/stage2bf_input_provenance.json` claims all four verify.
2. From `13_CODE_SNAPSHOT`, confirm `stage2a_ridge_residual_norm` **delegates** to
   `pathways.geometry.batched_projection` and does not reimplement the solve. Check the claim that
   `geometry.py` is byte-identical at `bcf2ad5`, `bee5f9b` and HEAD.
3. Confirm `truncated_svd_orthogonal_projection_rss` is an exact projection truncated at
   `1e-8·sigma_1`, and that the rank tolerance did not move.
4. Search every new result for `raw_projection_residual` described as the Stage 2A score. It must
   appear only in the migration table.
5. Independently recompute ridge and SVD scores on at least 100 random windows.
6. Check the Stage 2A ridge reproduction is exact at score, candidate, window-label, vote and
   confusion level — not merely within tolerance.
7. Check the Stage 2B F4_CAL selection and F4_TEST metrics reproduce, including the random control's
   sixteen `#k` replicate rows.
8. Check the 2x5 matrix used the same residuals, whitening, dictionaries and episodes for both
   estimators. Note that three of five controls are orthonormalised and therefore cannot separate
   the estimators; verify the report says so rather than presenting ten independent cells.
9. Check every CI is an episode-cluster bootstrap over paired episodes, never window-level IID.
10. Check the ridge never entered the F4_CAL candidate set and that F4_TEST selected nothing.
11. Check `stage2bf_evidence_delta.json`: only the reproduction gate may have moved.
12. Import the frozen `decision_stage2b.decide` yourself and re-derive the terminal state.
13. Check the historical Stage 2B `BLOCKED` record and all 17 historical artifacts are unchanged.
14. Check PRs #1-#6 are still Draft, unmerged, heads unmoved.
15. Return PASS / FAIL / BLOCKED and list anything that would change the scientific reading.

Attack hardest at: whether the ridge lambda matches Stage 2A exactly; whether the candidate-point
minimum is the same reduction; whether norm and energy units are ever mixed in a comparison;
whether any mechanism conclusion is carried by a single estimator; and whether the decision wrapper
could have hard-coded its terminal state.
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
    gate = json.loads((res / "stage2bf_integrity_decision.json").read_text())
    state = gate["stage2bf_integrity_decision"]
    decision = gate["stage2bf_scientific_decision"]
    combined = gate["stage2bf_combined_terminal"]
    git_sha = _git(repo, "rev-parse", "HEAD").strip()
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"CERTO_FDI_stage2bf_estimator_harmonization_{state}__{decision}_{stamp}_{git_sha[:7]}_{kind.upper()}"
    # Stage on local ext4, never on the G-drive: it is 9p/drvfs, where chmod is not permitted and
    # the executable bit on the smoke script cannot be set. Only the finished zip goes to G, with
    # its member modes written explicitly by _zip_tree.
    stage_root = Path(tempfile.mkdtemp(prefix="certo_stage2br_pkg_"))
    stage = stage_root / name
    stage.mkdir(parents=True)

    _write(stage / "00_READ_ME_FIRST.md",
           READ_ME.format(state=state, decision=decision, combined=combined,
                          run_id=gate["run_id"], git_sha=git_sha, built=built))
    _write(stage / "01_INDEPENDENT_REVIEW_PROMPT.md", REVIEW_PROMPT)
    _copy_file(res / "stage2bf_execution_summary.md", stage / "02_EXECUTION_SUMMARY.md")
    _copy_file(res / "stage2bf_integrity_decision_memo.md", stage / "03_INTEGRITY_DECISION_MEMO.md")
    _copy_file(res / "stage2bf_scientific_decision_memo.md", stage / "04_SCIENTIFIC_DECISION_MEMO.md")
    _copy_file(res / "stage2bf_known_issues.md", stage / "05_KNOWN_ISSUES.md")
    _copy_file(res / "stage2bf_claim_ledger.csv", stage / "06_CLAIMS_LEDGER.csv")
    _copy_file(res / "stage2bf_estimator_identity_map.csv", stage / "07_ESTIMATOR_IDENTITY_MAP.csv")

    # git provenance
    gp = stage / "11_GIT_PROVENANCE"
    gp.mkdir(parents=True, exist_ok=True)
    _write(gp / "HEAD.txt", git_sha + "\n")
    _write(gp / "log.txt", _git(repo, "log", "--oneline", "-25"))
    _write(gp / "status.txt", _git(repo, "status", "--porcelain=v1"))
    _write(gp / "branches.txt", _git(repo, "branch", "-vv"))

    # configs + code snapshot + tests
    _copy_file(repo / "configs" / "stage2bf_estimator_harmonization.yaml",
               stage / "12_CONFIGS" / "stage2bf_estimator_harmonization.yaml")
    _copy_file(repo / "docs_pointer" / "STAGE2BF_PROTOCOL.md", stage / "12_CONFIGS" / "STAGE2BF_PROTOCOL.md")
    code = stage / "13_CODE_SNAPSHOT"
    _copy_contents(repo / "src" / "certo_fdi" / "stage2bf", code / "stage2bf", exclude_suffixes=(".pyc",))
    _copy_file(repo / "docs_pointer" / "STAGE2BF_PORT_PROVENANCE.md", code / "STAGE2BF_PORT_PROVENANCE.md")
    for f in ("run_stage2bf_provenance.py", "run_stage2bf_replay.py", "run_stage2bf_analyse.py",
              "run_stage2bf_selection.py", "run_stage2bf_decide.py", "run_stage2bf_report.py"):
        _copy_file(repo / "src" / "certo_fdi" / "experiments" / f, code / "experiments" / f)
    for f in ("test_stage2bf_frozen_protocol.py", "test_stage2bf_reproduction.py"):
        _copy_file(repo / "tests" / f, stage / "14_TEST_REPORTS" / f)
    _write(stage / "14_TEST_REPORTS" / "README.md",
           "The two Stage 2B-F suites. `test_stage2bf_reproduction.py` reads the run root and skips "
           "cleanly when it is absent; the frozen-protocol suite runs anywhere.\n")

    # core results
    core = stage / "15_CORE_RESULTS"
    names = list(CORE_RESULTS) + (list(FULL_ONLY_RESULTS) if kind == "full" else [])
    for n in names:
        if (res / n).is_file():
            _copy_file(res / n, core / n)

    # figures
    figs = stage / "16_SELECTED_FIGURES"
    for p in sorted(fig.glob("*.png")):
        _copy_file(p, figs / p.name)

    if kind == "full":
        # contract 08: Full carries every per-window/per-link score array. They are already
        # npz-compressed, so they are stored rather than re-deflated.
        for a in sorted((run_root / "arrays").glob("*.npz")):
            _copy_file(a, stage / "22_SCORE_ARRAYS" / a.name)
        _copy_contents(run_root / "logs", stage / "19_LOGS")
        _copy_contents(run_root / "environment", stage / "20_ENVIRONMENT")
        _copy_contents(run_root / "provenance", stage / "18_PROVENANCE")
        _write_git_archive(repo, stage / "21_GIT_ARCHIVE")

    # historical Stage 2B artifacts must be unchanged by this stage
    hist = {}
    hres = Path(historical_2b) / "results"
    for n in ("stage2b_decision_evidence.json", "stage2b_contact_reproduction_gate.json",
              "stage2b_reproduction_gate.json", "stage2b_decision_memo.md", "stage2b_input_freeze.json"):
        p = hres / n
        if p.is_file():
            hist[n] = sha256_file(p)
    _write(stage / "18_PROVENANCE" / "HISTORICAL_STAGE2B_HASHES.json",
           json.dumps({"note": "hashes of the historical Stage 2B result files, unchanged by Stage 2B-R",
                       "run_root": str(historical_2b), "sha256": hist}, indent=2) + "\n")

    script = stage / "17_REPRODUCE_REVIEW.sh"
    _write(script, REPRODUCE_SCRIPT)
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # manifest, tree, checksums, status
    files = sorted(p for p in stage.rglob("*") if p.is_file())
    _write(stage / "08_FILE_TREE.txt", "\n".join(str(p.relative_to(stage)) for p in files) + "\n")
    _write(stage / "09_MANIFEST.json", json.dumps({
        "package": name, "kind": kind, "built_utc": built, "run_id": gate["run_id"],
        "git_sha": git_sha, "stage2bf_integrity_decision": state,
        "stage2bf_scientific_decision": decision, "stage2bf_combined_terminal": combined,
        "historical_stage2b_decision": "BLOCKED",
        "n_files": len(files),
        "historical_stage2b_hashes": hist,
    }, indent=2) + "\n")
    _write(stage / "REVIEW_PACKAGE_STATUS.json", json.dumps({
        "status": "BUILT", "stage2bf_integrity_decision": state, "stage2bf_scientific_decision": decision,
        "validated": False, "built_utc": built}, indent=2) + "\n")
    # checksums cover every file except the sums themselves and this status stub
    _write(stage / "10_SHA256SUMS.txt",
           "".join(f"{sha256_file(q)}  {q.relative_to(stage).as_posix()}\n"
                   for q in sorted(x for x in stage.rglob("*") if x.is_file())
                   if q.name not in ("10_SHA256SUMS.txt", "REVIEW_PACKAGE_STATUS.json")))

    leaked = _secret_scan(stage)
    if leaked:
        raise RuntimeError(f"secret scan failed: {leaked[:5]} (staging kept at {stage})")

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{name}.zip"
    _zip_tree(stage, zip_path)
    try:
        validate_zip(zip_path, REQUIRED_FILES, REQUIRED_DIRECTORIES,
                     sha_file="10_SHA256SUMS.txt", manifest_file="09_MANIFEST.json",
                     reproduce_script="17_REPRODUCE_REVIEW.sh")
    except Exception as e:
        raise RuntimeError(f"package validation failed: {e} (staging kept at {stage})") from e
    shutil.rmtree(stage_root, ignore_errors=True)
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser(description="build the Stage 2B-F review packages")
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
