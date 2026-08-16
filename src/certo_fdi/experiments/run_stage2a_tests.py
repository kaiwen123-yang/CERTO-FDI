"""Run the offline test suite into the run root and record a machine-readable report.

The decide phase treats a non-zero exit code as a hard block, so the correctness tests are part
of the decision, not a side activity.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from certo_fdi.experiments.common import utc_now, write_json
from certo_fdi.experiments.stage2a_common import Stage, common_parser


def main() -> int:
    ap = common_parser("Stage 2A: run the offline test suite and record the report")
    args = ap.parse_args()
    st = Stage(args, "tests")
    out = st.layout.sub("tests")
    junit = out / "pytest_junit.xml"
    env = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "OMP_NUM_THREADS": "8", "MKL_NUM_THREADS": "8", "OPENBLAS_NUM_THREADS": "8"}
    import os

    e = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    e.update(env)
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
        counts["passed"] = counts.get("tests", 0) - counts.get("errors", 0) - counts.get("failures", 0) - counts.get("skipped", 0)

    report = {
        "timestamp_utc": utc_now(), "command": " ".join(cmd), "cwd": str(st.repo_root),
        "exit_code": proc.returncode, "elapsed_s": elapsed, "counts": counts,
        "tail": proc.stdout.strip().splitlines()[-15:],
        "suites": sorted(p.name for p in (st.repo_root / "tests").glob("test_*.py")),
        "note": "offline suite: dynamics/Jacobian correctness, window dictionaries, injected mutations, "
                "no-leakage AST scan, pre-registered decision rules, packaging validator",
    }
    write_json(st.layout.results / "stage2a_test_report.json", report)
    st.log(f"tests exit={proc.returncode} counts={counts} ({elapsed:.0f}s)")
    st.finish({"exit_code": proc.returncode})
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
