#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export CERTO_STORAGE_ROOT="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"
bash "$SCRIPT_DIR/scripts/bootstrap_host.sh"
bash "$SCRIPT_DIR/scripts/bootstrap_storage.sh" "$CERTO_STORAGE_ROOT"
bash "$SCRIPT_DIR/scripts/bootstrap_github_repo.sh"
WORKTREE_ROOT="${CERTO_WORKTREE_ROOT:-${HOME}/research/CERTO-FDI-WORKTREES/stage1-closedloop-certificate}"
python3 -m venv "$WORKTREE_ROOT/.venv"
"$WORKTREE_ROOT/.venv/bin/python" -m pip install --upgrade pip wheel setuptools
"$WORKTREE_ROOT/.venv/bin/python" -m pip install -e "$WORKTREE_ROOT[dev]"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
"$WORKTREE_ROOT/.venv/bin/python" -m pytest -q -m "not slow" "$WORKTREE_ROOT/tests"
printf 'BOOTSTRAP_STATUS=PASS\n'
