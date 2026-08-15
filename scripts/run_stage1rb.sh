#!/usr/bin/env bash
# Stage 1R-B phase runner. Usage: scripts/run_stage1rb.sh <phase> <config> <run_id> [extra args...]
#   phases: audit | r0 | tune | train | evaluate | decide | finalize
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PHASE="${1:?phase}"; CONFIG="${2:?config}"; RUN_ID="${3:?run id}"; shift 3 || shift $#
STORAGE_ROOT="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}" OMP_WAIT_POLICY=PASSIVE
unset PYTHONPATH
case "$PHASE" in
  audit) MOD=certo_fdi.experiments.run_stage1rb_basis_audit ;;
  r0) MOD=certo_fdi.experiments.run_stage1rb_r0 ;;
  tune) MOD=certo_fdi.experiments.run_stage1rb_tuning ;;
  train) MOD=certo_fdi.experiments.run_stage1rb_training ;;
  evaluate) MOD=certo_fdi.experiments.run_stage1rb_evaluation ;;
  decide) MOD=certo_fdi.experiments.decision_stage1rb ;;
  finalize) MOD=certo_fdi.experiments.run_stage1rb_finalize ;;
  *) echo "unknown phase $PHASE" >&2; exit 2 ;;
esac
exec "$REPO_ROOT/.venv/bin/python" -m "$MOD" --config "$CONFIG" --storage-root "$STORAGE_ROOT" --run-id "$RUN_ID" --repo-root "$REPO_ROOT" "$@"
