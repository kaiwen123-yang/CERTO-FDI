from __future__ import annotations

import jax.numpy as jnp

from certo_fdi.control.computed_torque import reference_trajectory
from certo_fdi.dynamics.two_link import gravity_vector
from certo_fdi.types import ControllerParams, TwoLinkParams


def pd_gravity_command(
    q_measured: jnp.ndarray,
    v_measured: jnp.ndarray,
    t: float | jnp.ndarray,
    plant: TwoLinkParams,
    controller: ControllerParams,
) -> jnp.ndarray:
    qd, vd, _ = reference_trajectory(t)
    return (
        controller.kp * (qd - q_measured)
        + controller.kd * (vd - v_measured)
        + gravity_vector(q_measured, plant, payload_mass=0.0)
    )
