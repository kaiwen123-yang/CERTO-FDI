from __future__ import annotations

import jax.numpy as jnp
import numpy as np

from certo_fdi.closed_loop.model import (
    combined_step_output,
    nominal_initial_state,
    simulate_constant_fault,
)
from certo_fdi.faults.layout import zeros
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
    dx = rng.normal(size=6)
    dx /= np.linalg.norm(dx)
    dtheta = rng.normal(size=10)
    dtheta /= np.linalg.norm(dtheta)

    fd_x = centered_difference_state(x, t, theta, params, jnp.asarray(dx))
    fd_theta = centered_difference_fault(x, t, theta, params, jnp.asarray(dtheta))
    np.testing.assert_allclose(jac_x @ dx, fd_x, rtol=3e-5, atol=3e-7)
    np.testing.assert_allclose(jac_theta @ dtheta, fd_theta, rtol=5e-5, atol=5e-7)


def test_encoder_bias_has_state_and_direct_residual_paths(params):
    x = nominal_initial_state(params)
    linear = linearize_step(x, 0.2, params)
    encoder_columns = [7, 8]
    assert np.linalg.norm(linear.e[:, encoder_columns]) > 1e-8
    assert np.linalg.norm(linear.d_bar[:, encoder_columns]) > 1e-8
