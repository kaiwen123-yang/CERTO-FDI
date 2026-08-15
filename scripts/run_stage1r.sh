#!/usr/bin/env bash
# Usage: scripts/run_stage1r.sh <config> <run_id> [smoke|pilot] [extra args...]
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:?config}"; RUN_ID="${2:?run id}"; PROFILE="${3:-pilot}"; shift 3 || shift $#
STORAGE_ROOT="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; unset PYTHONPATH
exec "$REPO_ROOT/.venv/bin/python" -m certo_fdi.experiments.run_stage1r --config "$CONFIG" --profile "$PROFILE" --storage-root "$STORAGE_ROOT" --run-id "$RUN_ID" --repo-root "$REPO_ROOT" "$@"
