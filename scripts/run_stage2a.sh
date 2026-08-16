#!/usr/bin/env bash
# Stage 2A phase runner.
#   scripts/run_stage2a.sh <phase> <config> <run_id> [extra args...]
# phases: freeze | baseline | dictionaries | ablations | metrics | decide | finalize | package
set -euo pipefail

PHASE="${1:?phase required}"
CONFIG="${2:?config required}"
RUN_ID="${3:?run id required}"
shift 3 || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
STORAGE="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"

case "${PHASE}" in
  freeze)       MOD="certo_fdi.experiments.run_stage2a_freeze" ;;
  baseline)     MOD="certo_fdi.experiments.run_stage2a_baseline" ;;
  dictionaries) MOD="certo_fdi.experiments.run_stage2a_dictionaries" ;;
  ablations)    MOD="certo_fdi.experiments.run_stage2a_ablations" ;;
  metrics)      MOD="certo_fdi.experiments.run_stage2a_metrics" ;;
  decide)       MOD="certo_fdi.experiments.run_stage2a_decide" ;;
  finalize)     MOD="certo_fdi.experiments.run_stage2a_finalize" ;;
  package)      MOD="certo_fdi.packaging.build_review_package_stage2a" ;;
  *) echo "unknown phase: ${PHASE}" >&2; exit 64 ;;
esac

# ROS Humble is on the system PYTHONPATH and breaks pytest/plugin autoload; drop it.
# Cap BLAS threads: the host is shared with another long-running session.
exec env -u PYTHONPATH \
  OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" \
  MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}" \
  OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}" \
  OMP_WAIT_POLICY=PASSIVE \
  "${PY}" -m "${MOD}" \
    --config "${ROOT}/${CONFIG#"${ROOT}/"}" \
    --storage-root "${STORAGE}" \
    --run-id "${RUN_ID}" \
    --repo-root "${ROOT}" \
    "$@"
