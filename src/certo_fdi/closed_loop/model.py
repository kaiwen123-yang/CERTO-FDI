from __future__ import annotations

import jax
from jax import config
import jax.numpy as jnp
import numpy as np

from certo_fdi.actuators.delay_buffer import delayed_command
from certo_fdi.actuators.static import apply_efficiency
from certo_fdi.control.computed_torque import computed_torque_command, reference_trajectory
from certo_fdi.control.pd_gravity import pd_gravity_command
from certo_fdi.dynamics.two_link import mass_matrix, plant_acceleration
from certo_fdi.faults.layout import (
    ACTUATOR_GAIN,
    COMMAND_DELAY,
    CONTACT_FORCE,
    COULOMB_FRICTION,
    ENCODER_BIAS,
    FAULT_DIM,
    FRICTION_SHAPE,
    LINK1_CONTACT_FORCE,
    PAYLOAD_MASS,
    VISCOUS_FRICTION,
)
from certo_fdi.observers.momentum import momentum_estimate_derivative, momentum_residual
from certo_fdi.sensing.encoder import measured_state
from certo_fdi.types import ClosedLoopParams

config.update("jax_enable_x64", True)

NQ = 2
NX_PHYSICAL = 6
NX = 10
NY = 2
HEALTHY_DIM = 3


def split_state(
    x: jnp.ndarray,
) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    return x[0:2], x[2:4], x[4:6], x[6:8], x[8:10]


def pack_state(
    q: jnp.ndarray,
    velocity: jnp.ndarray,
    momentum_estimate: jnp.ndarray,
    previous_command_1: jnp.ndarray | None = None,
    previous_command_2: jnp.ndarray | None = None,
) -> jnp.ndarray:
    if previous_command_1 is None:
        previous_command_1 = jnp.zeros(2, dtype=q.dtype)
    if previous_command_2 is None:
        previous_command_2 = jnp.zeros(2, dtype=q.dtype)
    return jnp.concatenate(
        [q, velocity, momentum_estimate, previous_command_1, previous_command_2]
    )


def controller_command(
    q_measured: jnp.ndarray,
    velocity_measured: jnp.ndarray,
    t: float | jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    computed = lambda _: computed_torque_command(
        q_measured, velocity_measured, t, params.plant, params.controller
    )
    pd_gravity = lambda _: pd_gravity_command(
        q_measured, velocity_measured, t, params.plant, params.controller
    )
    return jax.lax.cond(jnp.asarray(params.controller.kind) == 0, computed, pd_gravity, None)


def residual(x: jnp.ndarray, fault: jnp.ndarray, params: ClosedLoopParams) -> jnp.ndarray:
    q, velocity, momentum_estimate, _, _ = split_state(x)
    q_measured, velocity_measured = measured_state(q, velocity, fault[ENCODER_BIAS])
    return momentum_residual(q_measured, velocity_measured, momentum_estimate, params)


def rhs(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
    healthy: jnp.ndarray | None = None,
) -> jnp.ndarray:
    q, velocity, momentum_estimate, previous_1, previous_2 = split_state(x)
    if healthy is None:
        healthy = jnp.zeros(HEALTHY_DIM, dtype=x.dtype)
    q_measured, velocity_measured = measured_state(q, velocity, fault[ENCODER_BIAS])
    command = controller_command(q_measured, velocity_measured, t, params)
    command_delayed = delayed_command(
        command, previous_1, previous_2, fault[COMMAND_DELAY], params.dt
    )
    applied = apply_efficiency(command_delayed, fault[ACTUATOR_GAIN])
    acceleration = plant_acceleration(
        q,
        velocity,
        applied,
        params.plant,
        payload_mass=healthy[2] + fault[PAYLOAD_MASS][0],
        viscous_delta=healthy[0:2] + fault[VISCOUS_FRICTION],
        coulomb_delta=fault[COULOMB_FRICTION],
        shape_delta=fault[FRICTION_SHAPE],
        link1_contact_force=fault[LINK1_CONTACT_FORCE],
        contact_force=fault[CONTACT_FORCE],
    )
    momentum_dot = momentum_estimate_derivative(
        q_measured, velocity_measured, momentum_estimate, command, params
    )
    return pack_state(
        velocity,
        acceleration,
        momentum_dot,
        jnp.zeros(2, dtype=x.dtype),
        jnp.zeros(2, dtype=x.dtype),
    )


def rk4_step(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
    healthy: jnp.ndarray | None = None,
) -> jnp.ndarray:
    dt = params.dt
    k1 = rhs(x, t, fault, params, healthy)
    k2 = rhs(x + 0.5 * dt * k1, t + 0.5 * dt, fault, params, healthy)
    k3 = rhs(x + 0.5 * dt * k2, t + 0.5 * dt, fault, params, healthy)
    k4 = rhs(x + dt * k3, t + dt, fault, params, healthy)
    integrated = x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    q, velocity, _, previous_1, _ = split_state(x)
    q_measured, velocity_measured = measured_state(q, velocity, fault[ENCODER_BIAS])
    current_command = controller_command(q_measured, velocity_measured, t, params)
    return integrated.at[6:8].set(current_command).at[8:10].set(previous_1)


def step_with_output(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
    healthy: jnp.ndarray | None = None,
) -> tuple[jnp.ndarray, jnp.ndarray]:
    x_next = rk4_step(x, t, fault, params, healthy)
    return x_next, residual(x_next, fault, params)


def closed_loop_step(
    x: jnp.ndarray,
    reference: float | jnp.ndarray,
    healthy_parameters: jnp.ndarray,
    fault_parameters: jnp.ndarray,
    config: ClosedLoopParams,
) -> tuple[jnp.ndarray, jnp.ndarray, dict[str, jnp.ndarray]]:
    """Unique public single-step interface required by the Stage 1 contract."""

    x_next, residual_next = step_with_output(
        x, reference, fault_parameters, config, healthy_parameters
    )
    q, velocity, _, previous_1, previous_2 = split_state(x)
    q_measured, velocity_measured = measured_state(q, velocity, fault_parameters[ENCODER_BIAS])
    command = controller_command(q_measured, velocity_measured, reference, config)
    applied = apply_efficiency(
        delayed_command(
            command,
            previous_1,
            previous_2,
            fault_parameters[COMMAND_DELAY],
            config.dt,
        ),
        fault_parameters[ACTUATOR_GAIN],
    )
    return x_next, residual_next, {"command": command, "applied_command": applied}


def combined_step_output(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    x_next, residual_next = step_with_output(x, t, fault, params)
    return jnp.concatenate([x_next, residual_next])


def combined_step_output_with_healthy(
    x: jnp.ndarray,
    t: float | jnp.ndarray,
    fault: jnp.ndarray,
    healthy: jnp.ndarray,
    params: ClosedLoopParams,
) -> jnp.ndarray:
    x_next, residual_next = step_with_output(x, t, fault, params, healthy)
    return jnp.concatenate([x_next, residual_next])


def nominal_initial_state(params: ClosedLoopParams) -> jnp.ndarray:
    q0, velocity0, _ = reference_trajectory(0.0)
    momentum0 = mass_matrix(q0, params.plant, payload_mass=0.0) @ velocity0
    command0 = controller_command(q0, velocity0, 0.0, params)
    return pack_state(q0, velocity0, momentum0, command0, command0)


_STEP_WITH_OUTPUT_JIT = jax.jit(step_with_output)


def simulate_constant_fault(
    params: ClosedLoopParams,
    fault: np.ndarray | jnp.ndarray,
    steps: int,
    x0: np.ndarray | jnp.ndarray | None = None,
    start_time: float = 0.0,
    healthy: np.ndarray | jnp.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    state = nominal_initial_state(params) if x0 is None else jnp.asarray(x0, dtype=jnp.float64)
    fault_jax = jnp.asarray(fault, dtype=jnp.float64)
    healthy_jax = (
        jnp.zeros(HEALTHY_DIM, dtype=jnp.float64)
        if healthy is None
        else jnp.asarray(healthy, dtype=jnp.float64)
    )
    if fault_jax.shape != (FAULT_DIM,):
        raise ValueError(f"fault must have shape ({FAULT_DIM},), got {fault_jax.shape}")
    if healthy_jax.shape != (HEALTHY_DIM,):
        raise ValueError(f"healthy must have shape ({HEALTHY_DIM},), got {healthy_jax.shape}")
    states = [np.asarray(state)]
    residuals = []
    times = [float(start_time)]
    t = float(start_time)
    for _ in range(steps):
        state, residual_next = _STEP_WITH_OUTPUT_JIT(
            state, jnp.asarray(t, dtype=jnp.float64), fault_jax, params, healthy_jax
        )
        t += params.dt
        states.append(np.asarray(state))
        residuals.append(np.asarray(residual_next))
        times.append(t)
    return np.asarray(times), np.asarray(states), np.asarray(residuals)
