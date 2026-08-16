"""Stage 2A contract §7.2: window-dictionary correctness.

1. the window stack has no off-by-one in either the time index or the joint index;
2. the constant-profile parameterization is what it claims to be;
3. dimensions and units are complete before and after whitening;
4. the ridge projection agrees with a direct least-squares solve;
5. the principal angles agree with an independent SciPy implementation;
6. the per-link dictionary ordering matches the truth link id.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
M = 5


@pytest.fixture(scope="module")
def synthetic():
    """A small synthetic EpisodePathways with analytically known contents."""
    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.pathways.dictionaries import build_episode_pathways

    ch = reference_chain(XML)
    ch.damping[:] = 0.8
    ch.coulomb[:] = 0.9
    ch.coulomb_eps = 0.05
    n = ch.n_links
    T = 1024
    rng = np.random.default_rng(2026)
    t = np.arange(T) * 0.002
    # configurations must stay INSIDE the joint limits: MuJoCo's inverse dynamics adds joint-limit
    # constraint forces outside them, which would make the payload comparison meaningless.
    lo, hi = ch.joint_lower + 0.15, ch.joint_upper - 0.15
    mid, amp = 0.5 * (lo + hi), 0.45 * (hi - lo)
    q = mid[None, :] + amp[None, :] * np.sin(2 * np.pi * 0.4 * t[:, None] + np.arange(n)[None, :])
    qd = amp[None, :] * 2 * np.pi * 0.4 * np.cos(2 * np.pi * 0.4 * t[:, None] + np.arange(n)[None, :])
    qdd = -amp[None, :] * (2 * np.pi * 0.4) ** 2 * np.sin(2 * np.pi * 0.4 * t[:, None] + np.arange(n)[None, :])
    # commands are smooth in the frozen protocol (a clipped controller output at 500 Hz)
    tau_cmd = 6.0 * np.sin(2 * np.pi * 0.7 * t[:, None] + 0.3 * np.arange(n)[None, :]) + 2.0 * np.cos(2 * np.pi * 0.25 * t[:, None])
    sig = {
        "q_meas": q, "qd_meas": qd, "qdd_est": qdd,
        "tau_cmd": tau_cmd, "tau_meas": tau_cmd + rng.normal(size=(T, n)) * 0.05,
        "tau_nominal": rng.normal(size=(T, n)) * 4.0, "q_ref": q.copy(),
    }
    t_index = np.arange(31, T, 32)
    ep = build_episode_pathways(ch, sig, t_index, episode_id="synthetic", control_dt=0.002)
    return ch, sig, ep, t_index


def test_window_stack_has_no_off_by_one(synthetic):
    """Row ``m*n + j`` of a window dictionary is joint ``j`` at the window's ``m``-th time point."""
    from certo_fdi.pathways.dictionaries import family_dictionaries

    ch, sig, ep, t_index = synthetic
    n = ch.n_links
    rows = np.arange(2, 2 + M)
    D = family_dictionaries(ep, rows)["F1_actuator"]
    assert D.shape == (n * M, n)
    for m in range(M):
        expected = np.diag(sig["tau_cmd"][t_index[rows[m]]])
        np.testing.assert_allclose(D[m * n : (m + 1) * n, :], expected, atol=0)
    # a shifted row selection must give a different dictionary (the test would be vacuous otherwise)
    D2 = family_dictionaries(ep, rows + 1)["F1_actuator"]
    assert np.abs(D - D2).max() > 1e-6


def test_contact_stack_matches_the_jacobian_at_each_time_point(synthetic):
    from certo_fdi.pathways.dictionaries import contact_columns
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians, point_jacobian

    ch, sig, ep, t_index = synthetic
    n = ch.n_links
    rows = np.arange(1, 1 + M)
    for link in (0, 3, 6):
        D6 = contact_columns(ep, rows, link, None)
        assert D6.shape == (n * M, 6)
        kin = forward_kinematics(ch, sig["q_meas"][t_index[rows]])
        J = link_spatial_jacobians(kin)
        for m in range(M):
            np.testing.assert_allclose(D6[m * n : (m + 1) * n, :], -J[m, link].T, atol=1e-10)
        r = np.array([0.0, 0.0, 0.05])
        D3 = contact_columns(ep, rows, link, r)
        assert D3.shape == (n * M, 3)
        Jp = point_jacobian(kin, J, link, r)
        for m in range(M):
            np.testing.assert_allclose(D3[m * n : (m + 1) * n, :], -Jp[m].T, atol=1e-10)


def test_constant_profile_parameterization(synthetic):
    """``D theta`` is the residual a *constant* fault parameter produces over the window."""
    from certo_fdi.pathways.dictionaries import contact_columns, family_dictionaries
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians

    ch, sig, ep, t_index = synthetic
    n = ch.n_links
    rows = np.arange(0, M)
    # F1: a constant efficiency loss s on joint 2 produces s * tau_cmd_2(t) at joint 2, at every t
    theta = np.zeros(n)
    theta[2] = 0.13
    r = family_dictionaries(ep, rows)["F1_actuator"] @ theta
    for m in range(M):
        expected = np.zeros(n)
        expected[2] = 0.13 * sig["tau_cmd"][t_index[rows[m]], 2]
        np.testing.assert_allclose(r[m * n : (m + 1) * n], expected, atol=1e-12)
    # F4: a constant wrench on link 4 produces -J_4(q(t))^T w at every t
    w = np.array([0.2, -0.1, 0.05, 3.0, -2.0, 1.0])
    r4 = contact_columns(ep, rows, 4, None) @ w
    kin = forward_kinematics(ch, sig["q_meas"][t_index[rows]])
    J = link_spatial_jacobians(kin)
    for m in range(M):
        np.testing.assert_allclose(r4[m * n : (m + 1) * n], -J[m, 4].T @ w, atol=1e-10)


def test_units_and_dimensions_are_recorded(synthetic):
    from certo_fdi.pathways.dictionaries import dictionary_column_units, family_dictionaries
    from certo_fdi.pathways.whitening import ConditionalWhitener

    ch, sig, ep, t_index = synthetic
    n = ch.n_links
    rows = np.arange(0, M)
    fam = family_dictionaries(ep, rows)
    units = dictionary_column_units()
    for key, D in fam.items():
        assert key in units, key
        assert D.shape[1] == len(units[key]), key
        assert D.shape[0] == n * M
    rng = np.random.default_rng(0)
    E = rng.normal(size=(400, n * M))
    C = rng.normal(size=(400, 6))
    wh = ConditionalWhitener().fit(E, C)
    for key, D in fam.items():
        Dw = wh.whiten_dictionary(D)
        assert Dw.shape == D.shape                     # whitening never changes the dimensions
    d = wh.to_dict()
    for k in ("dimension", "condition_number", "effective_rank_numeric", "shrinkage_absolute", "ridge_mean"):
        assert k in d


def test_ridge_projection_matches_direct_least_squares(synthetic):
    from certo_fdi.pathways.dictionaries import contact_columns
    from certo_fdi.pathways.geometry import batched_projection, exact_projection_energy, ridge_lambda

    ch, sig, ep, t_index = synthetic
    rows = np.arange(0, M)
    D = contact_columns(ep, rows, 5, None)
    rng = np.random.default_rng(3)
    z = rng.normal(size=(7, D.shape[0]))
    out = batched_projection(np.broadcast_to(D, (7,) + D.shape), z)
    lam = float(np.atleast_1d(ridge_lambda(D))[0])
    for i in range(7):
        theta_ref = np.linalg.solve(D.T @ D + lam * np.eye(D.shape[1]), D.T @ z[i])
        np.testing.assert_allclose(out["theta"][i], theta_ref, rtol=1e-9, atol=1e-12)
        np.testing.assert_allclose(out["projection_residual"][i], np.linalg.norm(z[i] - D @ theta_ref), rtol=1e-7)
        np.testing.assert_allclose(out["explained_energy"][i], float(np.linalg.norm(D @ theta_ref) ** 2), rtol=1e-7)
    # the ridge shrinks every singular direction, so it can never explain MORE than the exact
    # projector; on a well-conditioned dictionary the two agree to the ridge's relative size
    ex = exact_projection_energy(np.broadcast_to(D, (7,) + D.shape), z)
    assert np.all(out["explained_energy"] <= ex * (1 + 1e-9) + 1e-9)
    cond = float(np.linalg.cond(D))
    tol = max(1e-3, 20.0 / cond**2 + 1e-3)
    assert np.allclose(out["explained_energy"], ex, rtol=tol), (cond, out["explained_energy"], ex)


def test_principal_angles_match_scipy(synthetic):
    from scipy.linalg import subspace_angles

    from certo_fdi.pathways.dictionaries import contact_columns
    from certo_fdi.pathways.geometry import principal_angles

    ch, sig, ep, t_index = synthetic
    rows = np.arange(0, M)
    for a, b in ((1, 3), (3, 6), (0, 6)):
        A = contact_columns(ep, rows, a, None)
        B = contact_columns(ep, rows, b, None)
        mine = np.sort(principal_angles(A, B))
        ref = np.sort(subspace_angles(A, B))
        assert mine.shape == ref.shape, (a, b, mine.shape, ref.shape)
        np.testing.assert_allclose(mine, ref, atol=1e-8)
    # a link's dictionary is at zero angle to itself and generically not to another link's
    A = contact_columns(ep, rows, 3, None)
    assert principal_angles(A, A).max() < 1e-6  # arccos near 1 amplifies float64 error as sqrt
    assert principal_angles(A, contact_columns(ep, rows, 6, None)).max() > 1e-3


def test_link_dictionary_order_matches_truth_link_id(synthetic):
    """Link ``l``'s dictionary loads joints ``0..l`` only -- so the index really is the link id."""
    from certo_fdi.pathways.dictionaries import contact_columns

    ch, sig, ep, t_index = synthetic
    n = ch.n_links
    rows = np.arange(0, M)
    for l in range(n):
        D = contact_columns(ep, rows, l, None).reshape(M, n, 6)
        loaded = np.abs(D).max(axis=(0, 2)) > 1e-12
        assert loaded[: l + 1].all(), l
        assert not loaded[l + 1 :].any(), l


def test_payload_regressor_is_linear_and_matches_rnea(synthetic):
    """``Y_load phi`` equals the RNEA torque difference of attaching that payload."""
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch
    from certo_fdi.geometry.spatial_types import spatial_inertia
    from certo_fdi.pathways.dictionaries import payload_inertia_basis, payload_regressor

    ch, sig, ep, t_index = synthetic
    q, qd, qdd = sig["q_meas"][t_index], sig["qd_meas"][t_index], sig["qdd_est"][t_index]
    Y = payload_regressor(ch, q, qd, qdd)
    assert Y.shape == (len(t_index), ch.n_links, 10)
    mass, com, icom = 0.37, np.array([0.01, -0.02, 0.11]), np.diag([7e-4, 6e-4, 3e-4])
    # phi = [m, m c, I_o] with I_o = I_c + m skew(c) skew(c)^T
    from certo_fdi.geometry.se3 import skew

    Io = icom + mass * skew(com) @ skew(com).T
    phi = np.array([mass, *(mass * com), Io[0, 0], Io[0, 1], Io[0, 2], Io[1, 1], Io[1, 2], Io[2, 2]])
    np.testing.assert_allclose(sum(phi[k] * payload_inertia_basis()[k] for k in range(10)), spatial_inertia(mass, com, icom), atol=1e-12)
    heavy = ch.with_payload(mass, com, icom)
    tc0 = TorchChain.from_chain(ch, dtype=torch.float64)
    tc1 = TorchChain.from_chain(heavy, dtype=torch.float64)
    qt, qdt, qddt = (torch.as_tensor(a) for a in (q, qd, qdd))
    d_tau = (rnea_batch(tc1, qt, qdt, qddt).tau - rnea_batch(tc0, qt, qdt, qddt).tau).numpy()
    np.testing.assert_allclose(Y @ phi, d_tau, atol=1e-9)


@requires_sim
def test_payload_regressor_matches_mujoco_nonlinear_replay(synthetic):
    """First-order check against the frozen truth backend (contract §7.1 item 6)."""
    from certo_fdi.dynamics.mujoco_backend import MujocoPlant
    from certo_fdi.pathways.dictionaries import payload_regressor

    ch, sig, ep, t_index = synthetic
    # in-limit configurations only (see the fixture): mj_inverse would otherwise add joint-limit
    # constraint forces that differ between the two models and swamp the payload term.
    q, qd, qdd = sig["q_meas"][t_index][:6], sig["qd_meas"][t_index][:6], sig["qdd_est"][t_index][:6]
    assert np.all(q >= ch.joint_lower) and np.all(q <= ch.joint_upper)
    Y = payload_regressor(ch, q, qd, qdd)
    mass, com, icom = 0.25, np.array([0.0, 0.0, 0.11]), np.diag([5e-4, 5e-4, 2e-4]) * 0.25
    from certo_fdi.geometry.se3 import skew

    Io = icom + mass * skew(com) @ skew(com).T
    phi = np.array([mass, *(mass * com), Io[0, 0], Io[0, 1], Io[0, 2], Io[1, 1], Io[1, 2], Io[2, 2]])
    p0, p1 = MujocoPlant(XML), MujocoPlant(XML)
    p1.payload_variant(mass, com, icom)
    for i in range(len(q)):
        d_mj = p1.inverse_dynamics(q[i], qd[i], qdd[i]) - p0.inverse_dynamics(q[i], qd[i], qdd[i])
        np.testing.assert_allclose(Y[i] @ phi, d_mj, rtol=1e-6, atol=1e-8)


def test_command_delay_buffer_difference_matches_the_analytic_control(synthetic):
    """The explicit command-buffer finite difference agrees with ``d tau_cmd/dt``."""
    ch, sig, ep, t_index = synthetic
    a = ep.d_delay            # analytic control: d tau_cmd / dt (centred, +-1 sample)
    b = ep.d_delay_buffer     # deployed causal command-buffer difference over dd = 2 dt
    # a backward difference over dd is first order, so it lags the centred derivative by
    # O(omega * dd / 2); at 0.7 Hz with dd = 4 ms that is under 1 %.
    assert np.abs(a - b).max() < 0.03 * np.abs(a).max()
    cos = float((a.ravel() @ b.ravel()) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert cos > 0.999
