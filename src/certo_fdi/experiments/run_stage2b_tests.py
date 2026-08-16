"""Run the offline test suite into the run root and record a machine-readable report.

The tests are part of the decision, not a side activity: several of them are the *only* thing
standing between the audit and a silent integrity failure -- the no-leakage AST scan, the rank
mutation tests and the episode-partition disjointness checks all encode contract rules that no
result table could reveal on its own. A non-zero exit code is a blocking condition.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from certo_fdi.experiments.common import utc_now, write_json
from certo_fdi.experiments.stage2b_common import Stage, common_parser

#: the twelve suites the kickoff §13 requires, and what each one defends
REQUIRED_SUITES = {
    "test_stage2b_input_freeze.py": "the three mandatory input hashes and the historical PR heads",
    "test_stage2b_rank_matching.py": "every synthetic control realises the same numerical rank",
    "test_stage2b_support_masks.py": "the serial-chain prefix support is exactly the loaded rows",
    "test_stage2b_rank_mutations.py": "higher rank confers no automatic advantage",
    "test_stage2b_episode_partitions.py": "episode-level splits, seeds and the cluster bootstrap",
    "test_stage2b_no_leakage.py": "the final F4 test set selects nothing, statically and behaviourally",
    "test_stage2b_alarm_accounting.py": "the frozen alarm-event definitions",
    "test_stage2b_calibration.py": "healthy-only calibration and the forbidden CFAR language",
    "test_stage2b_sequential.py": "the wrappers are causal and episode-local",
    "test_stage2b_selective_localization.py": "accept/defer is selected on F4_CAL and reduces error",
    "test_stage2b_decision_rules.py": "the pre-registered terminal states and evaluation order",
    "test_stage2b_review_package.py": "the review package topology and smoke contract",
}


def main() -> int:
    ap = common_parser("Stage 2B: run the offline test suite and record the report")
    args = ap.parse_args()
    st = Stage(args, "tests")
    out = st.layout.sub("tests")
    junit = out / "pytest_junit.xml"
    e = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    e.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "OMP_NUM_THREADS": "8",
              "MKL_NUM_THREADS": "8", "OPENBLAS_NUM_THREADS": "8"})
    t0 = time.time()
    cmd = [sys.executable, "-m", "pytest", "-q", f"--junit-xml={junit}"]
    proc = subprocess.run(cmd, cwd=str(st.repo_root), env=e, text=True, capture_output=True)
    elapsed = time.time() - t0
    (out / "pytest_stdout.txt").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")

    counts = {}
    if junit.exists():
        import xml.etree.ElementTree as ET

        root = ET.parse(junit).getroot()
        suite = root if root.tag == "testsuite" else (root.find("testsuite") or root)
        counts = {k: int(suite.get(k, 0)) for k in ("tests", "errors", "failures", "skipped")}
        counts["passed"] = counts["tests"] - counts["errors"] - counts["failures"] - counts["skipped"]

    present = {p.name for p in (st.repo_root / "tests").glob("test_stage2b_*.py")}
    missing = sorted(set(REQUIRED_SUITES) - present)
    report = {
        "timestamp_utc": utc_now(), "command": " ".join(cmd), "cwd": str(st.repo_root),
        "exit_code": proc.returncode, "elapsed_s": elapsed, "counts": counts,
        "tail": proc.stdout.strip().splitlines()[-15:],
        "all_suites": sorted(p.name for p in (st.repo_root / "tests").glob("test_*.py")),
        "stage2b_suites": sorted(present),
        "required_suites": REQUIRED_SUITES,
        "missing_required_suites": missing,
        "required_suites_complete": not missing,
        "note": ("offline suite; the Stage 2B suites encode contract rules no result table could reveal: "
                 "rank matching, support masks, rank-bias mutations, episode-level partitioning and the "
                 "static no-leakage scan"),
    }
    write_json(st.layout.results / "stage2b_test_report.json", report)
    st.log(f"tests exit={proc.returncode} counts={counts} ({elapsed:.0f}s)")
    if missing:
        st.log(f"BLOCKING: required test suites are missing: {missing}")
    st.finish({"exit_code": proc.returncode, "missing_required_suites": missing})
    return proc.returncode or (7 if missing else 0)


if __name__ == "__main__":
    raise SystemExit(main())
