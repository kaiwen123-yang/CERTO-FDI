from __future__ import annotations

import numpy as np

from certo_fdi.dynamics.spatial_rnea import ad_force, ad_motion, rnea_2r
from certo_fdi.dynamics.two_link import rigid_body_torque, skew_symmetry_residual


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


def test_mdot_minus_2c_is_skew_symmetric(params):
    rng = np.random.default_rng(17)
    for _ in range(30):
        q = rng.normal(size=2)
        qd = rng.normal(size=2)
        residual = np.asarray(skew_symmetry_residual(q, qd, params.plant))
        np.testing.assert_allclose(residual, np.zeros((2, 2)), atol=1e-12, rtol=0.0)
