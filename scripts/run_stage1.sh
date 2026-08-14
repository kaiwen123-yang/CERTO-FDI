#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
STORAGE_ROOT="${CERTO_STORAGE_ROOT:-}"
CLEAN=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --clean) CLEAN=1 ;;
    --storage-root)
      shift
      STORAGE_ROOT="${1:?--storage-root requires a path}"
      ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done
if [ "$CLEAN" -ne 1 ]; then
  printf 'ERROR: --clean is required; every execution creates a new immutable run\n' >&2
  exit 2
fi
if [ -z "$STORAGE_ROOT" ]; then
  printf 'ERROR: CERTO_STORAGE_ROOT or --storage-root is required\n' >&2
  exit 2
fi
bash "$REPO_ROOT/scripts/bootstrap_storage.sh" "$STORAGE_ROOT"
RUN_ROOT=$("$REPO_ROOT/.venv/bin/python" -m certo_fdi.paths \
  --create-run --storage-root "$STORAGE_ROOT" --repo-root "$REPO_ROOT")
export CERTO_STORAGE_ROOT="$STORAGE_ROOT"
export CERTO_RUN_ROOT="$RUN_ROOT"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
printf 'CERTO_RUN_ROOT=%s\n' "$CERTO_RUN_ROOT"
CONFIG_FILE="$REPO_ROOT/configs/experiments/smoke.yaml"
cp "$CONFIG_FILE" "$CERTO_RUN_ROOT/config/smoke.yaml"
capture_environment() {
  "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/capture_environment.py" \
    --run-root "$CERTO_RUN_ROOT" --storage-root "$CERTO_STORAGE_ROOT" \
    --repo-root "$REPO_ROOT" --seed 260809 --phase "$1"
}
capture_environment start
trap 'capture_environment final' EXIT
"$REPO_ROOT/.venv/bin/python" -m pytest -q -m "not slow" \
  | tee "$CERTO_RUN_ROOT/tests/pytest.txt"
"$REPO_ROOT/.venv/bin/python" -m certo_fdi.experiments.run_stage1 \
  --config "$CONFIG_FILE" | tee "$CERTO_RUN_ROOT/logs/stage1_pipeline.log"
trap - EXIT
capture_environment final
