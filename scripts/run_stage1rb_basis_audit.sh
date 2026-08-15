#!/usr/bin/env bash
# Usage: scripts/run_stage1rb_basis_audit.sh <config> <run_id> [extra args...]
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:?config}"; RUN_ID="${2:?run id}"; shift 2 || shift $#
STORAGE_ROOT="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}" OMP_WAIT_POLICY=PASSIVE
unset PYTHONPATH
exec "$REPO_ROOT/.venv/bin/python" -m certo_fdi.experiments.run_stage1rb_basis_audit --config "$CONFIG" --storage-root "$STORAGE_ROOT" --run-id "$RUN_ID" --repo-root "$REPO_ROOT" "$@"
