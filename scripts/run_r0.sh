#!/usr/bin/env bash
# R0 geometry gate. Usage: scripts/run_r0.sh <config> <run_id>
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:?config path required}"
RUN_ID="${2:?run id required}"
STORAGE_ROOT="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
unset PYTHONPATH
exec "$REPO_ROOT/.venv/bin/python" -m certo_fdi.experiments.run_r0_geometry \
  --config "$CONFIG" --storage-root "$STORAGE_ROOT" --run-id "$RUN_ID" --repo-root "$REPO_ROOT"
