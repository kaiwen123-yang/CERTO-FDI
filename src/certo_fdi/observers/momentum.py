from __future__ import annotations

import jax.numpy as jnp

from certo_fdi.dynamics.two_link import coriolis_matrix, friction_torque, gravity_vector, mass_matrix
from certo_fdi.types import ClosedLoopParams


def momentum_residual(
    q_measured: jnp.ndarray,
    velocity_measured: jnp.ndarray,
    momentum_estimate: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    measured_momentum = mass_matrix(q_measured, params.plant, payload_mass=0.0) @ velocity_measured
    return params.observer.ko * (measured_momentum - momentum_estimate)


def momentum_estimate_derivative(
    q_measured: jnp.ndarray,
    velocity_measured: jnp.ndarray,
    momentum_estimate: jnp.ndarray,
    nominal_command: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    residual = momentum_residual(q_measured, velocity_measured, momentum_estimate, params)
    return (
        nominal_command
        + coriolis_matrix(q_measured, velocity_measured, params.plant).T @ velocity_measured
        - gravity_vector(q_measured, params.plant)
        - friction_torque(velocity_measured, params.plant)
        + residual
    )
