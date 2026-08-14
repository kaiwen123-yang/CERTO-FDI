from __future__ import annotations

from jax import config
import jax.numpy as jnp

from certo_fdi.dynamics.two_link import (
    coriolis_matrix,
    friction_torque,
    gravity_vector,
    mass_matrix,
)
from certo_fdi.types import ControllerParams, TwoLinkParams

config.update("jax_enable_x64", True)


def reference_trajectory(t: float | jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    """Smooth, persistently varying 2R reference used by stage-one smoke tests."""
    t = jnp.asarray(t, dtype=jnp.float64)

    q1 = 0.55 * jnp.sin(0.8 * t) + 0.18 * jnp.sin(1.7 * t + 0.2)
    q2 = -0.45 * jnp.cos(0.6 * t + 0.1) + 0.20 * jnp.sin(1.3 * t)

    v1 = 0.55 * 0.8 * jnp.cos(0.8 * t) + 0.18 * 1.7 * jnp.cos(1.7 * t + 0.2)
    v2 = 0.45 * 0.6 * jnp.sin(0.6 * t + 0.1) + 0.20 * 1.3 * jnp.cos(1.3 * t)

    a1 = -0.55 * 0.8**2 * jnp.sin(0.8 * t) - 0.18 * 1.7**2 * jnp.sin(1.7 * t + 0.2)
    a2 = 0.45 * 0.6**2 * jnp.cos(0.6 * t + 0.1) - 0.20 * 1.3**2 * jnp.sin(1.3 * t)

    return jnp.array([q1, q2]), jnp.array([v1, v2]), jnp.array([a1, a2])


def computed_torque_command(
    q_measured: jnp.ndarray,
    v_measured: jnp.ndarray,
    t: float | jnp.ndarray,
    plant: TwoLinkParams,
    controller: ControllerParams,
) -> jnp.ndarray:
    qd, vd, ad = reference_trajectory(t)
    commanded_acceleration = ad + controller.kd * (vd - v_measured) + controller.kp * (
        qd - q_measured
    )
    return (
        mass_matrix(q_measured, plant, payload_mass=0.0) @ commanded_acceleration
        + coriolis_matrix(q_measured, v_measured, plant, payload_mass=0.0) @ v_measured
        + gravity_vector(q_measured, plant, payload_mass=0.0)
        + friction_torque(v_measured, plant)
    )


def nominal_command_on_reference(
    t: float | jnp.ndarray,
    plant: TwoLinkParams,
    controller: ControllerParams,
) -> jnp.ndarray:
    qd, vd, _ = reference_trajectory(t)
    return computed_torque_command(qd, vd, t, plant, controller)


def nominal_command_derivative(
    t: float | jnp.ndarray,
    plant: TwoLinkParams,
    controller: ControllerParams,
) -> jnp.ndarray:
    """Centered time derivative of the perfect-tracking nominal torque.

    The command-delay channel is provisional. A small centered difference keeps
    the outer closed-loop AD graph simple; an exact delay-buffer state is a later
    stage-one item and is not claimed by this implementation.
    """

    t = jnp.asarray(t, dtype=jnp.float64)
    h = jnp.asarray(1e-5, dtype=jnp.float64)
    return (
        nominal_command_on_reference(t + h, plant, controller)
        - nominal_command_on_reference(t - h, plant, controller)
    ) / (2.0 * h)
