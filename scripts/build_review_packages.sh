#!/usr/bin/env bash
# Usage: scripts/build_review_packages.sh <run_id> [milestone]
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ID="${1:?run id}"; MILESTONE="${2:-PILOT}"
STORAGE_ROOT="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"
RUN_ROOT="$STORAGE_ROOT/04_runs/stage1r_ligra/$RUN_ID"
KICKOFF="$STORAGE_ROOT/02_research_docs/stage1r/kickoff_package"
unset PYTHONPATH
"$REPO_ROOT/.venv/bin/python" -m certo_fdi.experiments.make_figures --run-root "$RUN_ROOT" >/dev/null
exec "$REPO_ROOT/.venv/bin/python" -m certo_fdi.packaging.build_review_package --run-root "$RUN_ROOT" --repo-root "$REPO_ROOT" --milestone "$MILESTONE" --kickoff-dir "$KICKOFF" --known-issues "$RUN_ROOT/decision/KNOWN_ISSUES.md"
