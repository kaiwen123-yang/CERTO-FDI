from __future__ import annotations

from pathlib import Path

import numpy as np

from certo_fdi.closed_loop.model import simulate_constant_fault
from certo_fdi.config import build_closed_loop_params, load_yaml
from certo_fdi.faults.layout import zeros
from certo_fdi.operators.linearize import linearize_nominal_trajectory
from certo_fdi.operators.window import assemble_window_operator


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    params = build_closed_loop_params(load_yaml(root / "configs/experiments/smoke.yaml"))
    times, states, residuals = simulate_constant_fault(params, np.asarray(zeros()), 3)
    linearizations = linearize_nominal_trajectory(states, times, params)
    operator = assemble_window_operator(linearizations, [0])
    if operator.shape != (6, 3) or not np.isfinite(operator).all():
        raise SystemExit("closed-loop CPU smoke failed")
    if np.max(np.abs(residuals)) >= 1e-5:
        raise SystemExit("nominal residual smoke failed")
    print("CI_SMOKE=PASS")


if __name__ == "__main__":
    main()
