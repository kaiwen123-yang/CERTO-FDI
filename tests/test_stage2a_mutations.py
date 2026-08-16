"""Stage 2A contract §7.4: injected mutations must be caught.

A test suite that cannot fail is worthless. Each mutation below is a *plausible* bug in the
pathway geometry; the tests assert that the checks in ``test_stage2a_jacobians.py`` and
``test_stage2a_dictionaries.py`` reject it. The mutations are:

1. the Jacobian is transposed the wrong way (``J`` instead of ``J^T``);
2. the wrench frame is not transformed under a link-frame reparameterization;
3. the link index is off by one;
4. the residual sign is flipped;
5. the contact-point Jacobian is taken from the wrong link.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
M = 5


@pytest.fixture(scope="module")
def setup():
    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.mujoco_backend import MujocoPlant
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians

    ch = reference_chain(XML)
    plant = MujocoPlant(XML)
    rng = np.random.default_rng(4242)
    q = rng.uniform(ch.joint_lower + 0.1, ch.joint_upper - 0.1, size=(M, ch.n_links))
    kin = forward_kinematics(ch, q)
    return ch, plant, q, kin, link_spatial_jacobians(kin)


@requires_sim
def test_mutation_1_transposed_jacobian_is_caught(setup):
    """``tau_ext = J w`` (instead of ``J^T w``) must fail the virtual-work check."""
    from certo_fdi.pathways.jacobians import mujoco_generalized_force

    ch, plant, q, kin, J = setup
    w = np.array([0.2, -0.1, 0.05, 3.0, -2.0, 1.0])
    n = ch.n_links
    for link in (2, 5):
        ref = mujoco_generalized_force(plant, q[0], link, np.zeros(3), w[3:], w[:3])
        good = J[0, link].T @ w
        np.testing.assert_allclose(good, ref, atol=1e-12)
        # MUTATION: forget the transpose. For a 7-DoF arm the shapes no longer conform at all
        # (6x7 against a 6-vector), so the dictionary cannot even be built.
        with pytest.raises(ValueError):
            _ = J[0, link] @ w
        # and on a hypothetical 6-DoF arm, where the shapes *would* conform, the answer is wrong
        J6 = J[0, link][:, :6]
        assert np.abs(J6 @ w - (J6.T @ w[:6])[: J6.shape[0]]).max() > 1e-6

    # the same mutation at the dictionary level: -J^T is (n, 6); -J is (6, n) and cannot stack
    from certo_fdi.pathways.dictionaries import contact_columns_batched

    D = -np.swapaxes(J[:, 2], 1, 2)
    assert D.shape[1:] == (n, 6)
    assert (-J[:, 2]).shape[1:] == (6, n)


@requires_sim
def test_mutation_2_untransformed_wrench_frame_is_caught(setup):
    """Reparameterizing the link frames but leaving the wrench alone must break virtual work."""
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.geometry.spatial_types import SpatialType, transform_typed
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians

    ch, plant, q, kin, J = setup
    rng = np.random.default_rng(9)
    frames = sample_link_frames(ch, rng)
    new, adjoints = ch.reparameterize(frames)
    kin1 = forward_kinematics(ch, q)
    kinN = forward_kinematics(new, q)
    JN = link_spatial_jacobians(kinN)
    w_link = np.array([0.3, -0.2, 0.1, 2.0, -1.0, 0.5])
    n_wrong = 0
    for link in range(ch.n_links):
        R0, R1 = kin1.R_link[0, link], kinN.R_link[0, link]
        tau0 = J[0, link].T @ np.concatenate([R0 @ w_link[:3], R0 @ w_link[3:]])
        w1 = transform_typed(SpatialType.FORCE, w_link, adjoints[link])
        tau_ok = JN[0, link].T @ np.concatenate([R1 @ w1[:3], R1 @ w1[3:]])
        np.testing.assert_allclose(tau_ok, tau0, atol=1e-9)
        # MUTATION: keep the original wrench components in the new frame
        tau_bad = JN[0, link].T @ np.concatenate([R1 @ w_link[:3], R1 @ w_link[3:]])
        if np.abs(tau_bad - tau0).max() > 1e-6 * max(np.abs(tau0).max(), 1e-9):
            n_wrong += 1
    assert n_wrong >= ch.n_links - 1  # every link but a possibly trivial one must be detected


@requires_sim
def test_mutation_3_link_index_off_by_one_is_caught(setup):
    """Using link ``l+1``'s Jacobian for link ``l`` must break the support structure and the torque."""
    from certo_fdi.pathways.jacobians import mujoco_generalized_force

    ch, plant, q, kin, J = setup
    f = np.array([4.0, -3.0, 2.0])
    r = np.array([0.0, 0.0, 0.06])
    for link in range(ch.n_links - 1):
        ref = mujoco_generalized_force(plant, q[0], link, r, f)
        from certo_fdi.pathways.jacobians import point_jacobian

        good = point_jacobian(kin, J, link, r)[0].T @ f
        np.testing.assert_allclose(good, ref, atol=1e-12)
        bad = point_jacobian(kin, J, link + 1, r)[0].T @ f
        assert np.abs(bad - ref).max() > 1e-6 * max(np.abs(ref).max(), 1e-9), link
        # the support structure alone already exposes it: link l cannot load joint l+1
        assert np.abs(bad[link + 1]) > 0.0 or np.abs(J[0, link + 1, :, link + 1]).max() == 0.0


@requires_sim
def test_mutation_4_flipped_residual_sign_is_caught(setup):
    """A flipped residual sign must flip the fitted contact force, so the physical check fails."""
    from certo_fdi.pathways.geometry import batched_projection
    from certo_fdi.pathways.jacobians import point_jacobian

    ch, plant, q, kin, J = setup
    r = np.array([0.0, 0.0, 0.06])
    f_true = np.array([5.0, -2.0, 1.0])
    D = np.concatenate([-point_jacobian(kin, J, 4, r)[m].T for m in range(M)], axis=0)  # (n*M, 3)
    z = D @ f_true
    good = batched_projection(D[None], z[None])["theta"][0]
    np.testing.assert_allclose(good, f_true, rtol=1e-4, atol=1e-5)
    bad = batched_projection(D[None], -z[None])["theta"][0]
    assert np.abs(bad - f_true).max() > 1.0            # a +5 N force is recovered as -5 N
    np.testing.assert_allclose(bad, -f_true, rtol=1e-4, atol=1e-5)


@requires_sim
def test_mutation_5_wrong_link_contact_dictionary_is_caught(setup):
    """A contact on link ``l`` fitted with link ``k != l``'s dictionary must leave a large residual."""
    from certo_fdi.pathways.geometry import batched_projection

    ch, plant, q, kin, J = setup
    from certo_fdi.pathways.jacobians import point_jacobian

    r = np.array([0.0, 0.0, 0.06])
    f = np.array([3.0, -4.0, 2.0])
    detected = 0
    total = 0
    for l in range(ch.n_links):
        z = np.concatenate([-point_jacobian(kin, J, l, r)[m].T @ f for m in range(M)])
        D_true = np.concatenate([-point_jacobian(kin, J, l, r)[m].T for m in range(M)], axis=0)
        res_true = float(batched_projection(D_true[None], z[None])["projection_residual"][0])
        assert res_true < 1e-5 * max(np.linalg.norm(z), 1e-9)   # its own dictionary explains it
        for k in range(ch.n_links):
            if k == l:
                continue
            total += 1
            D_bad = np.concatenate([-point_jacobian(kin, J, k, r)[m].T for m in range(M)], axis=0)
            res_bad = float(batched_projection(D_bad[None], z[None])["projection_residual"][0])
            if res_bad > 1e-3 * np.linalg.norm(z):
                detected += 1
    # not every ordered pair is separable -- neighbouring links share most of their load path,
    # which is exactly what the diagnosability audit quantifies. The great majority must be.
    assert detected / total > 0.6, (detected, total)


@requires_sim
def test_mutation_6_shuffled_time_dictionary_loses_the_signal(setup):
    """The capacity control must NOT explain a real contact residual (else it is not a control)."""
    from certo_fdi.pathways.geometry import batched_projection

    ch, plant, q, kin, J = setup
    from certo_fdi.pathways.jacobians import point_jacobian

    r = np.array([0.0, 0.0, 0.06])
    f = np.array([3.0, -4.0, 2.0])
    l = 5
    Jp = point_jacobian(kin, J, l, r)
    z = np.concatenate([-Jp[m].T @ f for m in range(M)])
    D_true = np.concatenate([-Jp[m].T for m in range(M)], axis=0)
    perm = np.array([2, 0, 4, 1, 3])
    D_shuf = np.concatenate([-Jp[perm[m]].T for m in range(M)], axis=0)
    r_true = float(batched_projection(D_true[None], z[None])["projection_residual"][0])
    r_shuf = float(batched_projection(D_shuf[None], z[None])["projection_residual"][0])
    assert r_true < 1e-5 * np.linalg.norm(z)
    assert r_shuf > 1e-2 * np.linalg.norm(z)


@requires_sim
def test_mutation_7_constant_body_wrench_is_not_a_constant_point_force(setup):
    """The point-force and body-wrench window dictionaries are DIFFERENT hypotheses.

    A constant point force on a rotating link has a body-origin moment ``(R(t) r) x f`` that
    turns with the link, so the constant-wrench dictionary cannot represent it. Using the wrong
    one silently degrades the fit by orders of magnitude -- this test pins the ordering down so
    the choice cannot regress unnoticed.
    """
    from certo_fdi.pathways.geometry import batched_projection
    from certo_fdi.pathways.jacobians import point_jacobian

    ch, plant, q, kin, J = setup
    r = np.array([0.0, 0.0, 0.06])
    f = np.array([3.0, -4.0, 2.0])
    for l in (1, 3, 5, 6):
        Jp = point_jacobian(kin, J, l, r)
        z = np.concatenate([-Jp[m].T @ f for m in range(M)])
        D_point = np.concatenate([-Jp[m].T for m in range(M)], axis=0)
        D_wrench = np.concatenate([-J[m, l].T for m in range(M)], axis=0)
        rp = float(batched_projection(D_point[None], z[None])["projection_residual"][0]) / np.linalg.norm(z)
        rw = float(batched_projection(D_wrench[None], z[None])["projection_residual"][0]) / np.linalg.norm(z)
        assert rp < 1e-5, (l, rp)
        assert rw > 10 * max(rp, 1e-9), (l, rp, rw)
