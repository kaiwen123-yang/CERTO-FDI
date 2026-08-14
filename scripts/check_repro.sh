#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
"$REPO_ROOT/.venv/bin/python" -m pytest -q -m "not slow"
printf 'REPRO_TESTS=PASS\n'
