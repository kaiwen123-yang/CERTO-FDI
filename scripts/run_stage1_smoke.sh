#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
pytest -q
python -m certo_fdi.experiments.run_closedloop_operators --config configs/experiments/smoke.yaml
python -m certo_fdi.experiments.run_epsA_sweep --config configs/experiments/smoke.yaml
python -m certo_fdi.experiments.run_certificates --config configs/experiments/smoke.yaml
