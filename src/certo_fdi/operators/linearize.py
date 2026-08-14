from __future__ import annotations

from dataclasses import dataclass

import jax
from jax import config
import jax.numpy as jnp
import numpy as np

from certo_fdi.closed_loop.model import NX, NY, combined_step_output
from certo_fdi.faults.layout import FAULT_DIM, zeros
from certo_fdi.types import ClosedLoopParams

config.update("jax_enable_x64", True)


@dataclass(frozen=True)
class StepLinearization:
    a: np.ndarray
    e: np.ndarray
    c_bar: np.ndarray
    d_bar: np.ndarray


def linearize_step(
    x_nominal: np.ndarray | jnp.ndarray,
    t: float,
    params: ClosedLoopParams,
) -> StepLinearization:
    x = jnp.asarray(x_nominal, dtype=jnp.float64)
    theta0 = zeros()
    t_jax = jnp.asarray(t, dtype=jnp.float64)

    fn = lambda state, fault: combined_step_output(state, t_jax, fault, params)
    jac_x, jac_theta = jax.jacfwd(fn, argnums=(0, 1))(x, theta0)

    jac_x_np = np.asarray(jac_x)
    jac_theta_np = np.asarray(jac_theta)
    if jac_x_np.shape != (NX + NY, NX):
        raise RuntimeError(f"unexpected state Jacobian shape {jac_x_np.shape}")
    if jac_theta_np.shape != (NX + NY, FAULT_DIM):
        raise RuntimeError(f"unexpected fault Jacobian shape {jac_theta_np.shape}")

    return StepLinearization(
        a=jac_x_np[:NX, :],
        e=jac_theta_np[:NX, :],
        c_bar=jac_x_np[NX:, :],
        d_bar=jac_theta_np[NX:, :],
    )


def linearize_nominal_trajectory(
    states: np.ndarray,
    times: np.ndarray,
    params: ClosedLoopParams,
) -> list[StepLinearization]:
    if len(states) != len(times):
        raise ValueError("states and times must have identical lengths")
    if len(states) < 2:
        raise ValueError("at least two states are required")

    def fn(state, time, fault):
        return combined_step_output(state, time, fault, params)

    jacobian_fn = jax.jit(jax.jacfwd(fn, argnums=(0, 2)))
    theta0 = zeros()
    output: list[StepLinearization] = []
    for k in range(len(states) - 1):
        jac_x, jac_theta = jacobian_fn(
            jnp.asarray(states[k], dtype=jnp.float64),
            jnp.asarray(times[k], dtype=jnp.float64),
            theta0,
        )
        jac_x_np = np.asarray(jac_x)
        jac_theta_np = np.asarray(jac_theta)
        output.append(
            StepLinearization(
                a=jac_x_np[:NX, :],
                e=jac_theta_np[:NX, :],
                c_bar=jac_x_np[NX:, :],
                d_bar=jac_theta_np[NX:, :],
            )
        )
    return output
