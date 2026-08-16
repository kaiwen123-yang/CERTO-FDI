"""Stage 2A contract §7.1: Jacobians, virtual work, frame changes, link support, singularities.

Every claim about the contact pathway rests on these; MuJoCo (``mj_jac`` / ``mj_applyFT``) and
finite differences of forward kinematics are the independent references.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
OFFSETS = (np.zeros(3), np.array([0.02, -0.03, 0.07]), np.array([0.0, 0.0, 0.06]))


@pytest.fixture(scope="module")
def chain_and_plant():
    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.mujoco_backend import MujocoPlant

    return reference_chain(XML), MujocoPlant(XML)


@pytest.fixture(scope="module")
def configs(chain_and_plant):
    ch, _ = chain_and_plant
    rng = np.random.default_rng(20260816)
    return rng.uniform(ch.joint_lower, ch.joint_upper, size=(6, ch.n_links))


@requires_sim
def test_forward_kinematics_matches_mujoco(chain_and_plant, configs):
    import mujoco

    from certo_fdi.pathways.jacobians import forward_kinematics

    ch, plant = chain_and_plant
    kin = forward_kinematics(ch, configs)
    for t in range(configs.shape[0]):
        plant.data.qpos[:] = configs[t]
        plant.data.qvel[:] = 0.0
        mujoco.mj_forward(plant.model, plant.data)
        for l in range(ch.n_links):
            b = plant.link_body_ids[l]
            np.testing.assert_allclose(kin.p_link[t, l], np.array(plant.data.xpos[b]), atol=1e-12)
            np.testing.assert_allclose(kin.R_link[t, l], np.array(plant.data.xmat[b]).reshape(3, 3), atol=1e-12)


@requires_sim
def test_point_and_angular_jacobians_match_mujoco(chain_and_plant, configs):
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians, mujoco_point_jacobian, point_jacobian

    ch, plant = chain_and_plant
    kin = forward_kinematics(ch, configs)
    J = link_spatial_jacobians(kin)
    for t in range(configs.shape[0]):
        for l in range(ch.n_links):
            for r in OFFSETS:
                jacp, jacr = mujoco_point_jacobian(plant, configs[t], l, r)
                np.testing.assert_allclose(point_jacobian(kin, J, l, r)[t], jacp, atol=1e-12)
                np.testing.assert_allclose(J[t, l, :3, :], jacr, atol=1e-12)


@requires_sim
def test_point_jacobian_matches_finite_differences(chain_and_plant, configs):
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians, point_jacobian, point_position

    ch, _ = chain_and_plant
    kin = forward_kinematics(ch, configs)
    J = link_spatial_jacobians(kin)
    h = 1e-6
    q0 = configs[0]
    for l in (0, 3, 6):
        r = np.array([0.01, 0.0, 0.05])
        Jp = point_jacobian(kin, J, l, r)[0]
        for k in range(ch.n_links):
            qp, qm = q0.copy(), q0.copy()
            qp[k] += h
            qm[k] -= h
            fd = (point_position(forward_kinematics(ch, qp[None]), l, r)[0] - point_position(forward_kinematics(ch, qm[None]), l, r)[0]) / (2 * h)
            np.testing.assert_allclose(Jp[:, k], fd, atol=1e-8)


@requires_sim
def test_virtual_work_matches_mujoco_apply_ft(chain_and_plant, configs):
    """``tau_ext = J_p^T f`` and ``tau_ext = J^T [n; f]`` against ``mj_applyFT``."""
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians, mujoco_generalized_force, point_jacobian

    ch, plant = chain_and_plant
    kin = forward_kinematics(ch, configs)
    J = link_spatial_jacobians(kin)
    rng = np.random.default_rng(7)
    for t in range(configs.shape[0]):
        for l in range(ch.n_links):
            f = rng.normal(size=3) * 5.0
            r = np.array([0.0, 0.0, 0.06])
            np.testing.assert_allclose(point_jacobian(kin, J, l, r)[t].T @ f, mujoco_generalized_force(plant, configs[t], l, r, f), atol=1e-12)
            tq = rng.normal(size=3) * 0.7
            np.testing.assert_allclose(J[t, l].T @ np.concatenate([tq, f]), mujoco_generalized_force(plant, configs[t], l, np.zeros(3), f, tq), atol=1e-12)


@requires_sim
def test_simulator_contact_wrench_equals_point_force_dictionary(chain_and_plant, configs):
    """The frozen F4 hook applies ``xfrc = [f; r x f]`` at the body origin: exactly a point force.

    This is why the deployed contact dictionary uses the 3-D point-force Jacobian.
    """
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians, point_jacobian

    ch, _ = chain_and_plant
    kin = forward_kinematics(ch, configs)
    J = link_spatial_jacobians(kin)
    rng = np.random.default_rng(11)
    for t in range(configs.shape[0]):
        for l in (1, 3, 5, 6):  # the frozen protocol's contact links
            r = np.array([0.0, 0.0, float(rng.uniform(0.03, 0.10))])
            f = rng.normal(size=3)
            f = f / np.linalg.norm(f) * 5.0
            r_world = kin.R_link[t, l] @ r
            tau_body = J[t, l].T @ np.concatenate([np.cross(r_world, f), f])
            np.testing.assert_allclose(tau_body, point_jacobian(kin, J, l, r)[t].T @ f, atol=1e-12)


@requires_sim
def test_link_column_support_is_the_ancestor_set(chain_and_plant, configs):
    """A wrench on link ``l`` can only load joints on the path base -> ``l``."""
    from certo_fdi.pathways.jacobians import ancestor_mask, forward_kinematics, link_spatial_jacobians

    ch, _ = chain_and_plant
    kin = forward_kinematics(ch, configs)
    J = link_spatial_jacobians(kin)
    anc = ancestor_mask(ch)
    for l in range(ch.n_links):
        for k in range(ch.n_links):
            if anc[l, k]:
                assert np.abs(J[:, l, :, k]).max() > 0.0
            else:
                assert np.abs(J[:, l, :, k]).max() == 0.0
        # serial chain: the ancestors of link l are exactly 0..l
        assert anc[l].tolist() == [k <= l for k in range(ch.n_links)]


@requires_sim
def test_frame_reparameterization_preserves_virtual_work(chain_and_plant, configs):
    """``J'^T w' = J^T w`` for ``w' = Ad_H^{-T} w`` -- the physical torque is frame independent."""
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.geometry.spatial_types import SpatialType, transform_typed
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians

    ch, _ = chain_and_plant
    rng = np.random.default_rng(3)
    frames = sample_link_frames(ch, rng)
    new, adjoints = ch.reparameterize(frames)
    kin0, kin1 = forward_kinematics(ch, configs), forward_kinematics(new, configs)
    J0, J1 = link_spatial_jacobians(kin0), link_spatial_jacobians(kin1)
    for l in range(ch.n_links):
        # the Jacobian is expressed at the link's own origin, in base-frame components:
        # a wrench given in the *link* frame transforms as FORCE under H_l.
        w_link = rng.normal(size=6)
        # express the same physical wrench in base components before and after
        R0, p0 = kin0.R_link[:, l], kin0.p_link[:, l]
        R1, p1 = kin1.R_link[:, l], kin1.p_link[:, l]
        w1_link = transform_typed(SpatialType.FORCE, w_link, adjoints[l])
        for t in range(configs.shape[0]):
            tau0 = J0[t, l].T @ _link_wrench_to_base(w_link, R0[t], p0[t])
            tau1 = J1[t, l].T @ _link_wrench_to_base(w1_link, R1[t], p1[t])
            np.testing.assert_allclose(tau1, tau0, atol=1e-9, err_msg=f"link {l}")


def _link_wrench_to_base(w_link: np.ndarray, R: np.ndarray, p: np.ndarray) -> np.ndarray:
    """``[n; f]`` given in link coordinates at the link origin -> base components at the link origin."""
    return np.concatenate([R @ w_link[:3], R @ w_link[3:]])


@requires_sim
def test_end_effector_jacobian_rank_and_singularity(chain_and_plant):
    """The 7-DoF end-effector Jacobian is generically full row rank and degrades near singularities."""
    from certo_fdi.pathways.jacobians import forward_kinematics, link_spatial_jacobians

    ch, _ = chain_and_plant
    rng = np.random.default_rng(5)
    q = rng.uniform(ch.joint_lower, ch.joint_upper, size=(40, ch.n_links))
    kin = forward_kinematics(ch, q)
    J = link_spatial_jacobians(kin)[:, ch.n_links - 1]
    s = np.linalg.svd(J, compute_uv=False)
    assert (s[:, -1] > 1e-6).mean() > 0.9  # generically full row rank
    # a deliberately singular configuration (joint 4 straight) loses rank / conditioning
    q_sing = np.zeros((1, ch.n_links))
    s_sing = np.linalg.svd(link_spatial_jacobians(forward_kinematics(ch, q_sing))[:, ch.n_links - 1], compute_uv=False)
    assert s_sing[0, -1] < np.median(s[:, -1])
