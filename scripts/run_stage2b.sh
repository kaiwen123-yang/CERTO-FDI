#!/usr/bin/env bash
# Stage 2B phase runner.
#   scripts/run_stage2b.sh <phase> <config> <run_id> [extra args...]
# phases: freeze | loadpath | localization | calibration | healthy | literature | tests | decide | finalize | package
set -euo pipefail

PHASE="${1:?phase required}"
CONFIG="${2:?config required}"
RUN_ID="${3:?run id required}"
shift 3 || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
STORAGE="${CERTO_STORAGE_ROOT:-/mnt/g/CERTO-FDI}"

case "${PHASE}" in
  freeze)       MOD="certo_fdi.experiments.run_stage2b_freeze" ;;
  loadpath)     MOD="certo_fdi.experiments.run_stage2b_loadpath" ;;
  localization) MOD="certo_fdi.experiments.run_stage2b_localization" ;;
  calibration)  MOD="certo_fdi.experiments.run_stage2b_calibration" ;;
  healthy)      MOD="certo_fdi.experiments.run_stage2b_healthy" ;;
  literature)   MOD="certo_fdi.experiments.run_stage2b_literature" ;;
  tests)        MOD="certo_fdi.experiments.run_stage2b_tests" ;;
  decide)       MOD="certo_fdi.experiments.run_stage2b_decide" ;;
  finalize)     MOD="certo_fdi.experiments.run_stage2b_finalize" ;;
  package)      MOD="certo_fdi.packaging.build_review_package_stage2b" ;;
  *) echo "unknown phase: ${PHASE}" >&2; exit 64 ;;
esac

# ROS Humble is on the system PYTHONPATH and breaks pytest plugin autoload; drop it.
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
