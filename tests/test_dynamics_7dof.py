"""7-DoF R0 gate as unit tests (skipped when mujoco/pinocchio/torch are unavailable)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tests.conftest import HAS_TORCH, requires_sim, requires_torch

XML = Path("/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml")

pytestmark = pytest.mark.skipif(not XML.is_file(), reason="frozen menagerie model not present")


@pytest.fixture(scope="module")
def plant():
    from certo_fdi.dynamics.mujoco_backend import MujocoPlant

    return MujocoPlant(XML)


def _states(chain, rng, k):
    for _ in range(k):
        yield rng.uniform(chain.joint_lower, chain.joint_upper), rng.normal(size=7), rng.normal(size=7) * 3


@requires_sim
def test_chain_extraction_and_audit(plant):
    from certo_fdi.dynamics.mujoco_backend import model_parameter_audit

    ch = plant.chain
    assert ch.n_links == 7 and list(ch.parent) == [-1, 0, 1, 2, 3, 4, 5]
    assert abs(ch.mass.sum() - 16.062132) < 1e-6
    audit = model_parameter_audit(plant.model, ch, XML)
    assert audit["actuators_removed"] and audit["collisions_disabled"] and audit["mjcf_damping_removed_from_model"]
    assert audit["joint_order_matches_mujoco_dof_order"]


@requires_sim
def test_rnea_matches_mujoco_and_pinocchio(plant, rng):
    from certo_fdi.dynamics.pinocchio_backend import build_pinocchio_model, pin_crba, pin_rnea, pin_rnea_includes_armature
    from certo_fdi.dynamics.rnea import mass_matrix, rnea

    ch = plant.chain
    pm = build_pinocchio_model(ch)
    inc = pin_rnea_includes_armature(pm)
    for q, qd, qdd in _states(ch, rng, 30):
        ours = rnea(ch, q, qd, qdd).tau
        np.testing.assert_allclose(ours, plant.inverse_dynamics(q, qd, qdd), atol=1e-9)
        ref = pin_rnea(pm, q, qd, qdd) + (0 if inc else ch.armature * qdd)
        np.testing.assert_allclose(ours, ref, atol=1e-9)
        wrong = rnea(ch, q, qd, qdd, mutate_ad_star_sign=True).tau
        assert np.max(np.abs(wrong - ref)) > 1e-3 or np.max(np.abs(qd)) < 1e-6
    q = next(_states(ch, rng, 1))[0]
    m_pin = pin_crba(pm, q) + (0 if inc else np.diag(ch.armature))
    np.testing.assert_allclose(mass_matrix(ch, q), plant.mass_matrix(q), atol=1e-9)
    np.testing.assert_allclose(mass_matrix(ch, q), m_pin, atol=1e-9)


@requires_sim
def test_7dof_frame_reparameterization_covariance(plant, rng):
    from certo_fdi.dynamics.rnea import rnea
    from certo_fdi.geometry.frame_reparameterization import compare_typed_states, sample_link_frames

    ch = plant.chain.copy()
    ch.damping[:] = 0.5
    ch.coulomb[:] = 0.3
    payload = ch.with_payload(0.5, np.array([0.0, 0.0, 0.1]))
    for chain in (ch, payload):
        for _ in range(3):
            frames = sample_link_frames(chain, rng)
            new, adjoints = chain.reparameterize(frames)
            for q, qd, qdd in _states(chain, rng, 3):
                f_ext = rng.normal(size=(7, 6))
                f_ext_new = np.stack([np.linalg.inv(adjoints[i]).T @ f_ext[i] for i in range(7)])
                before = rnea(chain, q, qd, qdd, f_ext=f_ext)
                after = rnea(new, q, qd, qdd, f_ext=f_ext_new)
                rep = compare_typed_states(chain, before, after, adjoints)
                assert rep.max_residual < 1e-8, rep.residuals


@requires_sim
@requires_torch
def test_torch_frontend_matches_numpy_and_is_covariant(plant, rng):
    import torch

    from certo_fdi.dynamics.rnea import rnea
    from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.geometry.spatial_types import SpatialType, transform_typed

    ch = plant.chain.copy()
    ch.damping[:] = 0.4
    ch.coulomb[:] = 0.2
    states = list(_states(ch, rng, 16))
    tc = TorchChain.from_chain(ch, dtype=torch.float64)
    q = torch.as_tensor(np.stack([s[0] for s in states]))
    qd = torch.as_tensor(np.stack([s[1] for s in states]))
    qdd = torch.as_tensor(np.stack([s[2] for s in states]))
    out = rnea_batch(tc, q, qd, qdd)
    ref = np.stack([rnea(ch, *s).tau for s in states])
    np.testing.assert_allclose(out.tau.numpy(), ref, atol=1e-10)
    # covariance in torch
    frames = sample_link_frames(ch, rng)
    new, adjoints = ch.reparameterize(frames)
    out2 = rnea_batch(TorchChain.from_chain(new, dtype=torch.float64), q, qd, qdd)
    for i in range(7):
        p = ch.parent[i]
        ap = np.eye(6) if p < 0 else adjoints[p]
        np.testing.assert_allclose(out2.V[:, i].numpy(), transform_typed(SpatialType.MOTION, out.V[:, i].numpy(), adjoints[i]), atol=1e-10)
        np.testing.assert_allclose(out2.F[:, i].numpy(), transform_typed(SpatialType.FORCE, out.F[:, i].numpy(), adjoints[i]), atol=1e-10)
        np.testing.assert_allclose(out2.X[:, i].numpy(), transform_typed(SpatialType.TRANSFORM, out.X[:, i].numpy(), adjoints[i], ap), atol=1e-10)
    np.testing.assert_allclose(out2.tau.numpy(), out.tau.numpy(), atol=1e-10)
    # gradient flows
    q.requires_grad_(True)
    loss = rnea_batch(tc, q, qd, qdd).tau.pow(2).sum()
    loss.backward()
    assert torch.isfinite(q.grad).all()
