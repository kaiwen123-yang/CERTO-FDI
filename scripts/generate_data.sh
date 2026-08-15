#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:?config}"; PROFILE="${2:?smoke|pilot}"; shift 2
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; unset PYTHONPATH
exec "$REPO_ROOT/.venv/bin/python" -m certo_fdi.experiments.run_generate_data --config "$CONFIG" --profile "$PROFILE" --repo-root "$REPO_ROOT" "$@"
