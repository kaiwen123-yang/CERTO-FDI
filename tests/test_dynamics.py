from __future__ import annotations

import numpy as np

from certo_fdi.dynamics.spatial_rnea import ad_force, ad_motion, rnea_2r
from certo_fdi.dynamics.lagrange_reference import sympy_lagrange_torque
from certo_fdi.dynamics.two_link import (
    payload_torque_per_kg,
    rigid_body_torque,
    skew_symmetry_residual,
)


def test_ad_star_sign_is_frozen():
    v = np.array([0.2, -0.3, 0.4, 1.0, -0.7, 0.5])
    np.testing.assert_allclose(ad_force(v), -ad_motion(v).T, atol=0.0, rtol=0.0)


def test_spatial_rnea_matches_closed_form(params):
    rng = np.random.default_rng(20260814)
    for _ in range(50):
        q = rng.uniform(low=-1.5, high=1.5, size=2)
        qd = rng.normal(scale=1.0, size=2)
        qdd = rng.normal(scale=2.0, size=2)
        tau_rnea = rnea_2r(q, qd, qdd, params.plant)
        tau_closed = np.asarray(rigid_body_torque(q, qd, qdd, params.plant))
        np.testing.assert_allclose(tau_rnea, tau_closed, rtol=1e-11, atol=1e-11)


def test_closed_form_matches_independent_sympy_lagrange(params):
    rng = np.random.default_rng(11)
    for _ in range(12):
        q = rng.uniform(-1.4, 1.4, size=2)
        qd = rng.normal(size=2)
        qdd = rng.normal(scale=2.0, size=2)
        expected = sympy_lagrange_torque(q, qd, qdd, params.plant)
        actual = np.asarray(rigid_body_torque(q, qd, qdd, params.plant))
        np.testing.assert_allclose(actual, expected, rtol=2e-12, atol=2e-12)


def test_wrong_ad_star_mutation_is_caught_by_dynamics_oracle(params):
    q = np.array([0.7, -0.9])
    qd = np.array([1.2, -0.8])
    qdd = np.array([0.4, 1.1])
    expected = np.asarray(rigid_body_torque(q, qd, qdd, params.plant))
    mutated = rnea_2r(q, qd, qdd, params.plant, mutate_ad_star_sign=True)
    assert np.linalg.norm(mutated - expected) > 1e-2

    spatial_velocity = np.array([0.2, -0.3, 0.7, 1.0, -0.5, 0.4])
    momentum = np.array([0.9, 0.1, -0.2, 0.3, -0.8, 1.1])
    correct_power = spatial_velocity @ (ad_force(spatial_velocity) @ momentum)
    wrong_power = spatial_velocity @ (ad_motion(spatial_velocity).T @ momentum)
    assert abs(correct_power) < 1e-14
    assert abs(wrong_power) < 1e-14


def test_payload_regressor_and_right_hand_disturbance_sign(params):
    q = np.array([0.4, -0.7])
    qd = np.array([0.3, -0.2])
    qdd = np.array([0.8, -0.1])
    delta = 0.25
    nominal = np.asarray(rigid_body_torque(q, qd, qdd, params.plant, payload_mass=0.0))
    loaded = np.asarray(rigid_body_torque(q, qd, qdd, params.plant, payload_mass=delta))
    regressor = np.asarray(payload_torque_per_kg(q, qd, qdd, params.plant))
    np.testing.assert_allclose(loaded - nominal, delta * regressor, rtol=2e-12, atol=2e-12)
    right_hand_disturbance = nominal - loaded
    np.testing.assert_allclose(right_hand_disturbance, -delta * regressor, rtol=2e-12, atol=2e-12)


def test_mdot_minus_2c_is_skew_symmetric(params):
    rng = np.random.default_rng(17)
    for _ in range(30):
        q = rng.normal(size=2)
        qd = rng.normal(size=2)
        residual = np.asarray(skew_symmetry_residual(q, qd, params.plant))
        np.testing.assert_allclose(residual, np.zeros((2, 2)), atol=1e-12, rtol=0.0)
