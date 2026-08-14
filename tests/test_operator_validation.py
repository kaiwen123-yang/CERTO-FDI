from __future__ import annotations

import numpy as np

from certo_fdi.closed_loop.model import nominal_initial_state, simulate_constant_fault, simulate_fault_sequence
from certo_fdi.faults.layout import FAULT_DIM, zeros
from certo_fdi.operators.brute_force import brute_force_linear_recursion
from certo_fdi.operators.hessian_bounds import (
    constant_fault_window_response,
    window_response_derivatives,
)
from certo_fdi.operators.direct_signature import direct_filtered_signature
from certo_fdi.operators.linearize import linearize_nominal_trajectory
from certo_fdi.operators.window import (
    assemble_healthy_window_operator,
    assemble_window_operator,
)


def _nominal_linearizations(params, steps=5):
    times, states, _ = simulate_constant_fault(params, np.asarray(zeros()), steps)
    return times, states, linearize_nominal_trajectory(states, times, params)


def test_fault_window_operator_matches_independent_recursion(params):
    _, _, linearizations = _nominal_linearizations(params)
    rng = np.random.default_rng(19)
    input_sequence = rng.normal(scale=1e-5, size=(len(linearizations), 2))
    columns = [0, 1]
    operator = assemble_window_operator(linearizations, columns)
    expected = brute_force_linear_recursion(
        linearizations, input_sequence, column_indices=columns
    ).reshape(-1)
    np.testing.assert_allclose(operator @ input_sequence.reshape(-1), expected, atol=1e-14)


def test_healthy_window_operator_matches_centered_nonlinear_difference(params):
    times, states, linearizations = _nominal_linearizations(params)
    operator = assemble_healthy_window_operator(linearizations, [0])
    profile = np.ones(len(linearizations))
    predicted = operator @ profile
    h = 1e-5
    healthy_plus = np.array([h, 0.0, 0.0])
    healthy_minus = np.array([-h, 0.0, 0.0])
    _, _, plus = simulate_constant_fault(params, np.asarray(zeros()), len(linearizations), healthy=healthy_plus)
    _, _, minus = simulate_constant_fault(params, np.asarray(zeros()), len(linearizations), healthy=healthy_minus)
    finite_difference = ((plus - minus) / (2.0 * h)).reshape(-1)
    np.testing.assert_allclose(predicted, finite_difference, rtol=2e-4, atol=2e-6)


def test_operator_predicts_small_time_varying_fault_response(params):
    _, states, linearizations = _nominal_linearizations(params, steps=6)
    rng = np.random.default_rng(23)
    values = rng.normal(scale=2e-6, size=6)
    sequence = np.zeros((6, FAULT_DIM))
    sequence[:, 0] = values
    _, _, actual = simulate_fault_sequence(params, sequence, x0=states[0])
    _, _, nominal = simulate_fault_sequence(params, np.zeros_like(sequence), x0=states[0])
    operator = assemble_window_operator(linearizations, [0])
    predicted = operator @ values
    np.testing.assert_allclose(predicted, (actual - nominal).reshape(-1), rtol=2e-4, atol=2e-8)


def test_hessian_matches_second_centered_difference(params):
    state = nominal_initial_state(params)
    jacobian, hessian = window_response_derivatives(state, 0.0, 0, params, steps=3)
    h = 2e-4
    zero = np.asarray(constant_fault_window_response(state, 0.0, 0, 0.0, params, 3))
    plus = np.asarray(constant_fault_window_response(state, 0.0, 0, h, params, 3))
    minus = np.asarray(constant_fault_window_response(state, 0.0, 0, -h, params, 3))
    first_fd = (plus - minus) / (2.0 * h)
    second_fd = (plus - 2.0 * zero + minus) / h**2
    np.testing.assert_allclose(jacobian, first_fd, rtol=2e-5, atol=2e-7)
    np.testing.assert_allclose(hessian, second_fd, rtol=2e-3, atol=2e-5)


def test_interval_end_operator_has_direct_diagonal_and_zero_upper_triangle(params):
    _, _, linearizations = _nominal_linearizations(params, steps=4)
    operator = assemble_window_operator(linearizations, [0])
    for row in range(4):
        np.testing.assert_allclose(
            operator[2 * row : 2 * row + 2, row : row + 1],
            linearizations[row].d_bar[:, [0]],
        )
        if row + 1 < 4:
            np.testing.assert_allclose(operator[2 * row : 2 * row + 2, row + 1 :], 0.0)


def test_archived_delay_comparator_dispatches_both_controllers_without_lax_loop(params):
    for kind in (0, 1):
        configured = params._replace(controller=params.controller._replace(kind=kind))
        times, states, _ = simulate_constant_fault(configured, np.asarray(zeros()), 5)
        signature = direct_filtered_signature(
            "command_delay", states[:-1], times[:-1], configured
        )
        assert signature is not None
        assert signature.shape == (10,)
        assert np.isfinite(signature).all()
