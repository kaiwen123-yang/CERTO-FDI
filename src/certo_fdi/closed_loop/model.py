from __future__ import annotations

import jax
from jax import config
import jax.numpy as jnp
import numpy as np

from certo_fdi.control.computed_torque import (
    computed_torque_command,
    nominal_command_derivative,
    reference_trajectory,
)
from certo_fdi.dynamics.two_link import (
    coriolis_matrix,
    friction_torque,
    gravity_vector,
    mass_matrix,
    plant_acceleration,
)
from certo_fdi.faults.layout import (
    ACTUATOR_GAIN,
    COMMAND_DELAY,
    CONTACT_FORCE,
    ENCODER_BIAS,
    FAULT_DIM,
    PAYLOAD_MASS,
    VISCOUS_FRICTION,
)
from certo_fdi.types import ClosedLoopParams

config.update("jax_enable_x64", True)

NQ = 2
NX = 6
NY = 2


def split_state(x: jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    return x[0:2], x[2:4], x[4:6]


def pack_state(q: jnp.ndarray, v: jnp.ndarray, p_hat: jnp.ndarray) -> jnp.ndarray:
    return jnp.concatenate([q, v, p_hat])


def measured_state(
    q: jnp.ndarray,
    v: jnp.ndarray,
    fault: jnp.ndarray,
) -> tuple[jnp.ndarray, jnp.ndarray]:
    # Stage-one minimum sensor model: encoder position bias, ideal velocity.
    # A derived-velocity chain will be added only after this path is verified.
    q_measured = q + fault[ENCODER_BIAS]
    v_measured = v
    return q_measured, v_measured


def residual(
    x: jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    q, v, p_hat = split_state(x)
    q_m, v_m = measured_state(q, v, fault)
    p_measured = mass_matrix(q_m, params.plant, payload_mass=0.0) @ v_m
    return params.observer.ko * (p_measured - p_hat)


def rhs(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    q, v, p_hat = split_state(x)
    q_m, v_m = measured_state(q, v, fault)

    tau_command = computed_torque_command(q_m, v_m, t, params.plant, params.controller)

    actuator_gain = fault[ACTUATOR_GAIN]
    viscous_delta = fault[VISCOUS_FRICTION]
    payload_mass = fault[PAYLOAD_MASS][0]
    contact_force = fault[CONTACT_FORCE]
    small_delay = fault[COMMAND_DELAY][0]

    # First-order local delay model. This channel is marked provisional until an
    # explicit command-buffer state is added.
    tau_delay_direction = nominal_command_derivative(t, params.plant, params.controller)
    tau_applied = (1.0 - actuator_gain) * tau_command - small_delay * tau_delay_direction

    qdd = plant_acceleration(
        q,
        v,
        tau_applied,
        params.plant,
        payload_mass=payload_mass,
        viscous_delta=viscous_delta,
        contact_force=contact_force,
    )

    r = params.observer.ko * (
        mass_matrix(q_m, params.plant, payload_mass=0.0) @ v_m - p_hat
    )
    p_hat_dot = (
        tau_command
        + coriolis_matrix(q_m, v_m, params.plant, payload_mass=0.0).T @ v_m
        - gravity_vector(q_m, params.plant, payload_mass=0.0)
        - friction_torque(v_m, params.plant)
        + r
    )

    return pack_state(v, qdd, p_hat_dot)


def rk4_step(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    dt = params.dt
    k1 = rhs(x, t, fault, params)
    k2 = rhs(x + 0.5 * dt * k1, t + 0.5 * dt, fault, params)
    k3 = rhs(x + 0.5 * dt * k2, t + 0.5 * dt, fault, params)
    k4 = rhs(x + dt * k3, t + dt, fault, params)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def step_with_output(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
) -> tuple[jnp.ndarray, jnp.ndarray]:
    x_next = rk4_step(x, t, fault, params)
    r_next = residual(x_next, fault, params)
    return x_next, r_next


def combined_step_output(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    x_next, r_next = step_with_output(x, t, fault, params)
    return jnp.concatenate([x_next, r_next])


def nominal_initial_state(params: ClosedLoopParams) -> jnp.ndarray:
    q0, v0, _ = reference_trajectory(0.0)
    p0 = mass_matrix(q0, params.plant, payload_mass=0.0) @ v0
    return pack_state(q0, v0, p0)


_STEP_WITH_OUTPUT_JIT = jax.jit(step_with_output)


def simulate_constant_fault(
    params: ClosedLoopParams,
    fault: np.ndarray | jnp.ndarray,
    steps: int,
    x0: np.ndarray | jnp.ndarray | None = None,
    start_time: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if x0 is None:
        state = nominal_initial_state(params)
    else:
        state = jnp.asarray(x0, dtype=jnp.float64)
    fault_jax = jnp.asarray(fault, dtype=jnp.float64)
    if fault_jax.shape != (FAULT_DIM,):
        raise ValueError(f"fault must have shape ({FAULT_DIM},), got {fault_jax.shape}")

    states = [np.asarray(state)]
    residuals = []
    times = [float(start_time)]
    t = float(start_time)
    for _ in range(steps):
        state, r = _STEP_WITH_OUTPUT_JIT(
            state, jnp.asarray(t, dtype=jnp.float64), fault_jax, params
        )
        t += params.dt
        states.append(np.asarray(state))
        residuals.append(np.asarray(r))
        times.append(t)
    return np.asarray(times), np.asarray(states), np.asarray(residuals)
