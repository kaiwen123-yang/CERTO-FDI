"""R0 covariance gate on the reference RNEA: healthy and faulty chains obey the same law."""

from __future__ import annotations

import numpy as np
import pytest

from certo_fdi.dynamics.chain_model import make_planar_2r
from certo_fdi.dynamics.rnea import rnea
from certo_fdi.geometry.frame_reparameterization import compare_typed_states, sample_link_frames
from certo_fdi.geometry.se3 import SE3, is_legal_motion_adjoint


def _random_state(rng, n):
    return rng.uniform(-1.5, 1.5, size=n), rng.normal(size=n), rng.normal(scale=2.0, size=n)


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_reparameterized_2r_is_same_physical_system(seed):
    rng = np.random.default_rng(seed)
    chain = make_planar_2r(damping=(0.1, 0.1), coulomb=(0.2, 0.1))
    frames = sample_link_frames(chain, rng)
    new, adjoints = chain.reparameterize(frames)
    for a in adjoints:
        assert is_legal_motion_adjoint(a)
    for _ in range(10):
        q, qd, qdd = _random_state(rng, 2)
        f_ext = rng.normal(size=(2, 6))
        before = rnea(chain, q, qd, qdd, f_ext=f_ext)
        f_ext_new = np.stack([np.linalg.inv(adjoints[i]).T @ f_ext[i] for i in range(2)])
        after = rnea(new, q, qd, qdd, f_ext=f_ext_new)
        report = compare_typed_states(chain, before, after, adjoints)
        assert report.max_residual < 1e-9, report.residuals
        np.testing.assert_allclose(after.tau, before.tau, atol=1e-10)


def test_faulty_chain_obeys_same_covariance_law():
    """Payload/inertia, friction and actuator-scale faults transform identically."""
    rng = np.random.default_rng(7)
    healthy = make_planar_2r()
    faulty = healthy.with_payload(0.7, np.array([0.4, 0.02, 0.0]))
    faulty.damping[:] = [0.9, 0.5]
    faulty.coulomb[:] = [1.1, 0.8]
    frames = sample_link_frames(healthy, rng)
    for chain in (healthy, faulty):
        new, adjoints = chain.reparameterize(frames)
        for _ in range(5):
            q, qd, qdd = _random_state(rng, 2)
            before, after = rnea(chain, q, qd, qdd), rnea(new, q, qd, qdd)
            report = compare_typed_states(chain, before, after, adjoints)
            assert report.max_residual < 1e-9
    # actuator gain fault acts on the joint scalar torque: still invariant
    q, qd, qdd = _random_state(rng, 2)
    gain = np.array([0.8, 1.0])
    new, adjoints = faulty.reparameterize(frames)
    np.testing.assert_allclose(gain * rnea(new, q, qd, qdd).tau, gain * rnea(faulty, q, qd, qdd).tau, atol=1e-10)


def test_illegal_gl6_frame_change_is_rejected():
    chain = make_planar_2r()
    bad = SE3(np.eye(3) * 1.1, np.zeros(3))
    with pytest.raises(ValueError):
        chain.reparameterize([bad, SE3.identity()])
