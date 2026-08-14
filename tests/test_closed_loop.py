from __future__ import annotations

import jax.numpy as jnp
import numpy as np

from certo_fdi.closed_loop.model import (
    HEALTHY_DIM,
    NX,
    closed_loop_step,
    combined_step_output,
    nominal_initial_state,
    simulate_constant_fault,
)
from certo_fdi.faults.layout import (
    ACTUATOR_GAIN,
    COMMAND_DELAY,
    CONTACT_FORCE,
    ENCODER_BIAS,
    FAULT_DIM,
    FRICTION_SHAPE,
    LINK1_CONTACT_FORCE,
    PAYLOAD_MASS,
    VISCOUS_FRICTION,
    zeros,
)
from certo_fdi.operators.linearize import linearize_step


def centered_difference_state(x, t, theta, params, direction, h=1e-6):
    plus = np.asarray(combined_step_output(x + h * direction, t, theta, params))
    minus = np.asarray(combined_step_output(x - h * direction, t, theta, params))
    return (plus - minus) / (2.0 * h)


def centered_difference_fault(x, t, theta, params, direction, h=1e-6):
    plus = np.asarray(combined_step_output(x, t, theta + h * direction, params))
    minus = np.asarray(combined_step_output(x, t, theta - h * direction, params))
    return (plus - minus) / (2.0 * h)


def test_nominal_residual_is_numerically_small(params):
    _, _, residuals = simulate_constant_fault(params, np.asarray(zeros()), 80)
    assert float(np.max(np.abs(residuals))) < 2e-7


def test_ad_jacobians_match_centered_differences(params):
    x = nominal_initial_state(params)
    t = 0.37
    theta = zeros()
    linear = linearize_step(x, t, params)
    jac_x = np.vstack([linear.a, linear.c_bar])
    jac_theta = np.vstack([linear.e, linear.d_bar])

    rng = np.random.default_rng(3)
    dx = rng.normal(size=NX)
    dx /= np.linalg.norm(dx)
    dtheta = rng.normal(size=FAULT_DIM)
    dtheta /= np.linalg.norm(dtheta)

    fd_x = centered_difference_state(x, t, theta, params, jnp.asarray(dx))
    fd_theta = centered_difference_fault(x, t, theta, params, jnp.asarray(dtheta))
    np.testing.assert_allclose(jac_x @ dx, fd_x, rtol=3e-5, atol=3e-7)
    np.testing.assert_allclose(jac_theta @ dtheta, fd_theta, rtol=5e-5, atol=5e-7)


def test_encoder_bias_has_state_and_direct_residual_paths(params):
    x = nominal_initial_state(params)
    linear = linearize_step(x, 0.2, params)
    encoder_columns = list(range(ENCODER_BIAS.start, ENCODER_BIAS.stop))
    assert np.linalg.norm(linear.e[:, encoder_columns]) > 1e-8
    assert np.linalg.norm(linear.d_bar[:, encoder_columns]) > 1e-8


def test_explicit_delay_buffer_matches_command_history(params):
    from certo_fdi.actuators.delay_buffer import delayed_command

    current = jnp.array([3.0, -2.0])
    previous_1 = jnp.array([1.0, 4.0])
    previous_2 = jnp.array([-5.0, 2.0])
    np.testing.assert_allclose(
        delayed_command(current, previous_1, previous_2, params.dt, params.dt),
        previous_1,
    )
    np.testing.assert_allclose(
        delayed_command(current, previous_1, previous_2, 2.0 * params.dt, params.dt),
        previous_2,
    )


def test_public_closed_loop_step_returns_diagnostics(params):
    state = nominal_initial_state(params)
    next_state, next_residual, diagnostics = closed_loop_step(
        state,
        0.0,
        jnp.zeros(HEALTHY_DIM),
        zeros(),
        params,
    )
    assert next_state.shape == (NX,)
    assert next_residual.shape == (2,)
    assert diagnostics["command"].shape == (2,)
    assert diagnostics["applied_command"].shape == (2,)


def test_both_controller_families_execute(params):
    for kind in (0, 1):
        controller = params.controller._replace(kind=kind)
        configured = params._replace(controller=controller)
        _, states, residuals = simulate_constant_fault(configured, np.asarray(zeros()), 20)
        assert np.isfinite(states).all()
        assert np.isfinite(residuals).all()
        assert np.max(np.abs(residuals)) < 3e-6


def test_all_six_fault_families_perturb_closed_loop_residual(params):
    family_examples = [
        (ACTUATOR_GAIN.start, 0.05),
        (VISCOUS_FRICTION.start, 0.1),
        (FRICTION_SHAPE.start, 0.01),
        (PAYLOAD_MASS.start, 0.2),
        (LINK1_CONTACT_FORCE.start + 1, 1.0),
        (CONTACT_FORCE.start + 1, 1.0),
        (ENCODER_BIAS.start, 0.005),
        (COMMAND_DELAY.start, params.dt),
    ]
    _, _, healthy_residual = simulate_constant_fault(params, np.asarray(zeros()), 180)
    for index, severity in family_examples:
        fault = np.asarray(zeros()).copy()
        fault[index] = severity
        _, _, faulty_residual = simulate_constant_fault(params, fault, 180)
        assert np.linalg.norm(faulty_residual - healthy_residual) > 1e-7
