"""Ported Stage 1 dynamics gate: general RNEA vs. independent symbolic Lagrangian (2R)."""

from __future__ import annotations

import numpy as np

from certo_fdi.dynamics.chain_model import make_planar_2r
from certo_fdi.dynamics.lagrange_reference import sympy_lagrange_torque
from certo_fdi.dynamics.rnea import bias_torque, mass_matrix, rnea

P = dict(m1=1.2, m2=0.8, l1=0.5, l2=0.4, lc1=0.25, lc2=0.2, I1=0.03, I2=0.015, gravity=9.81)


def _oracle(q, qd, qdd):
    return sympy_lagrange_torque(
        q, qd, qdd, m1=P["m1"], m2=P["m2"], l1=P["l1"], lc1=P["lc1"], lc2=P["lc2"],
        I1=P["I1"], I2=P["I2"], gravity=P["gravity"],
    )


def test_general_rnea_matches_independent_sympy_lagrange(rng):
    chain = make_planar_2r(**P)
    for _ in range(50):
        q = rng.uniform(-1.5, 1.5, size=2)
        qd = rng.normal(size=2)
        qdd = rng.normal(scale=2.0, size=2)
        tau = rnea(chain, q, qd, qdd).tau
        np.testing.assert_allclose(tau, _oracle(q, qd, qdd), rtol=1e-11, atol=1e-11)


def test_wrong_ad_star_sign_mutation_fails_dynamics_oracle(rng):
    chain = make_planar_2r(**P)
    worst = 0.0
    for _ in range(20):
        q = rng.uniform(-1.5, 1.5, size=2)
        qd = rng.normal(size=2) * 2.0
        qdd = rng.normal(scale=2.0, size=2)
        mutated = rnea(chain, q, qd, qdd, mutate_ad_star_sign=True).tau
        worst = max(worst, float(np.linalg.norm(mutated - _oracle(q, qd, qdd))))
    assert worst > 1e-2, "mutation test must FAIL the oracle; it passed"


def test_mass_matrix_symmetric_positive_definite_and_mdot_2c_skew(rng):
    chain = make_planar_2r(**P)
    for _ in range(10):
        q = rng.uniform(-2, 2, size=2)
        qd = rng.normal(size=2)
        m = mass_matrix(chain, q)
        assert np.allclose(m, m.T, atol=1e-12)
        assert np.all(np.linalg.eigvalsh(m) > 0)
        # numerical Mdot via central difference; C from bias with g removed
        eps = 1e-6
        mdot = (mass_matrix(chain, q + eps * qd) - mass_matrix(chain, q - eps * qd)) / (2 * eps)
        # C(q,qd) qd = bias(q,qd) - g(q); build C via Christoffel from finite differences of M
        n = 2
        dm = np.zeros((n, n, n))
        for k in range(n):
            e = np.zeros(n)
            e[k] = eps
            dm[:, :, k] = (mass_matrix(chain, q + e) - mass_matrix(chain, q - e)) / (2 * eps)
        c = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                c[i, j] = 0.5 * sum((dm[i, j, k] + dm[i, k, j] - dm[j, k, i]) * qd[k] for k in range(n))
        skew_res = mdot - 2 * c
        assert np.allclose(skew_res, -skew_res.T, atol=1e-5)
        g = bias_torque(chain, q, np.zeros(2))
        np.testing.assert_allclose(bias_torque(chain, q, qd) - g, c @ qd, atol=1e-5)


def test_payload_and_friction_terms_enter_torque_linearly(rng):
    chain = make_planar_2r(**P, damping=(0.3, 0.2), coulomb=(0.5, 0.4))
    q, qd, qdd = rng.normal(size=2), rng.normal(size=2), rng.normal(size=2)
    tau_full = rnea(chain, q, qd, qdd).tau
    tau_rb = rnea(chain, q, qd, qdd, include_joint_terms=False).tau
    fric = chain.damping * qd + chain.coulomb * np.tanh(qd / chain.coulomb_eps)
    np.testing.assert_allclose(tau_full - tau_rb, fric, atol=1e-12)
    loaded = chain.with_payload(0.5, np.array([P["l2"], 0.0, 0.0]))
    tau_loaded = rnea(loaded, q, qd, qdd).tau
    # payload point mass at link tip: torque difference equals point-mass Lagrangian contribution
    tip_only = make_planar_2r(**dict(P, m1=1e-12, m2=0.5, lc2=P["l2"], I1=1e-12, I2=1e-12))
    tau_tip = rnea(tip_only, q, qd, qdd).tau
    np.testing.assert_allclose(tau_loaded - tau_full, tau_tip, atol=1e-8)
