from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np

from certo_fdi.closed_loop.model import step_with_output
from certo_fdi.faults.layout import zeros
from certo_fdi.types import ClosedLoopParams


def constant_fault_window_response(
    initial_state: jnp.ndarray,
    start_time: float,
    mode_index: int,
    severity: float | jnp.ndarray,
    params: ClosedLoopParams,
    steps: int,
) -> jnp.ndarray:
    fault = zeros().at[mode_index].set(severity)

    def advance(state, offset):
        time = jnp.asarray(start_time, dtype=jnp.float64) + offset * params.dt
        next_state, next_residual = step_with_output(state, time, fault, params)
        return next_state, next_residual

    _, residuals = jax.lax.scan(advance, initial_state, jnp.arange(steps))
    return residuals.reshape(-1)


def window_response_derivatives(
    initial_state: np.ndarray,
    start_time: float,
    mode_index: int,
    params: ClosedLoopParams,
    steps: int,
    expansion_point: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    function = lambda value: constant_fault_window_response(
        jnp.asarray(initial_state, dtype=jnp.float64),
        start_time,
        mode_index,
        value,
        params,
        steps,
    )
    point = jnp.asarray(expansion_point, dtype=jnp.float64)
    jacobian = jax.jacfwd(function)(point)
    hessian = jax.jacfwd(jax.jacfwd(function))(point)
    return np.asarray(jacobian), np.asarray(hessian)
