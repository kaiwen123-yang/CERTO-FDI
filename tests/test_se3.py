from __future__ import annotations

import numpy as np
import pytest

from certo_fdi.geometry.se3 import (
    SE3,
    ad,
    ad_star,
    is_legal_motion_adjoint,
    random_se3,
    skew,
    so3_exp,
    so3_log,
)
from certo_fdi.geometry.spatial_types import (
    SpatialType,
    decompose_spatial_inertia,
    is_physical_spatial_inertia,
    spatial_inertia,
    transform_typed,
)


def test_skew_matches_cross(rng):
    a, b = rng.normal(size=3), rng.normal(size=3)
    np.testing.assert_allclose(skew(a) @ b, np.cross(a, b), atol=1e-14)


def test_so3_exp_log_roundtrip(rng):
    for _ in range(50):
        w = rng.normal(size=3)
        w *= rng.uniform(0.0, 3.0) / np.linalg.norm(w)
        r = so3_exp(w)
        assert np.allclose(r.T @ r, np.eye(3), atol=1e-12)
        assert abs(np.linalg.det(r) - 1.0) < 1e-12
        np.testing.assert_allclose(so3_log(r), w, atol=1e-9)


def test_ad_star_is_minus_ad_transpose(rng):
    v = rng.normal(size=6)
    np.testing.assert_allclose(ad_star(v), -ad(v).T, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(ad_star(v, mutate_sign=True), ad(v).T, atol=0.0)


def test_adjoint_is_homomorphism(rng):
    t1, t2 = random_se3(rng), random_se3(rng)
    np.testing.assert_allclose((t1 @ t2).adjoint(), t1.adjoint() @ t2.adjoint(), atol=1e-12)
    np.testing.assert_allclose(t1.inverse().adjoint(), np.linalg.inv(t1.adjoint()), atol=1e-12)
    np.testing.assert_allclose(t1.coadjoint(), np.linalg.inv(t1.adjoint()).T, atol=1e-12)


def test_adjoint_transforms_twists_like_point_velocities(rng):
    """Motion adjoint must agree with the kinematic definition of a twist transform."""
    t = random_se3(rng)
    omega_b, v_b = rng.normal(size=3), rng.normal(size=3)
    # velocity of the point currently at the B origin, expressed in A: R v_b ; angular: R omega_b
    # velocity of the point at the A origin: R v_b + skew(p) R omega_b ... i.e. v_A = R v_B + p x (R omega_B)
    v_a_expected = t.R @ v_b + np.cross(t.p, t.R @ omega_b)
    out = t.adjoint() @ np.concatenate([omega_b, v_b])
    np.testing.assert_allclose(out[:3], t.R @ omega_b, atol=1e-12)
    np.testing.assert_allclose(out[3:], v_a_expected, atol=1e-12)


def test_ad_is_lie_bracket_and_transforms_covariantly(rng):
    """Ad_T ad_V Ad_T^{-1} = ad_{Ad_T V} (adjoint equivariance of the bracket)."""
    t = random_se3(rng)
    v = rng.normal(size=6)
    a = t.adjoint()
    np.testing.assert_allclose(a @ ad(v) @ np.linalg.inv(a), ad(a @ v), atol=1e-11)
    # dual statement for ad*
    a_it = np.linalg.inv(a).T
    np.testing.assert_allclose(a_it @ ad_star(v) @ a.T, ad_star(a @ v), atol=1e-11)


def test_power_pairing_is_invariant(rng):
    t = random_se3(rng)
    v, f = rng.normal(size=6), rng.normal(size=6)
    a = t.adjoint()
    v2 = transform_typed(SpatialType.MOTION, v, a)
    f2 = transform_typed(SpatialType.FORCE, f, a)
    assert abs(v2 @ f2 - v @ f) < 1e-12


def test_inertia_transform_preserves_kinetic_energy_and_physicality(rng):
    t = random_se3(rng)
    a = t.adjoint()
    inertia = spatial_inertia(2.3, rng.normal(size=3) * 0.1, np.diag([0.02, 0.03, 0.04]))
    assert is_physical_spatial_inertia(inertia)
    v = rng.normal(size=6)
    inertia2 = transform_typed(SpatialType.INERTIA, inertia, a)
    v2 = transform_typed(SpatialType.MOTION, v, a)
    assert abs(v2 @ inertia2 @ v2 - v @ inertia @ v) < 1e-10
    assert is_physical_spatial_inertia(inertia2)
    m, c, ic = decompose_spatial_inertia(inertia2)
    assert abs(m - 2.3) < 1e-12
    np.testing.assert_allclose(c, t.act_point(decompose_spatial_inertia(inertia)[1]), atol=1e-12)
    np.testing.assert_allclose(ic, t.R @ np.diag([0.02, 0.03, 0.04]) @ t.R.T, atol=1e-11)


def test_legal_adjoint_detector_rejects_gl6(rng):
    t = random_se3(rng)
    assert is_legal_motion_adjoint(t.adjoint())
    g = rng.normal(size=(6, 6))
    assert not is_legal_motion_adjoint(g)
    scaled = t.adjoint().copy()
    scaled[:3, :3] *= 1.01
    assert not is_legal_motion_adjoint(scaled)


def test_se3_exp_matches_matrix_exponential(rng):
    from scipy.linalg import expm

    xi = rng.normal(size=6)
    m = np.zeros((4, 4))
    m[:3, :3] = skew(xi[:3])
    m[:3, 3] = xi[3:]
    np.testing.assert_allclose(SE3.exp(xi).matrix(), expm(m), atol=1e-11)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_transform_law_composition(seed):
    """Applying H1 then H2 equals applying H2 @ H1 for every type."""
    rng = np.random.default_rng(seed)
    h1, h2 = random_se3(rng), random_se3(rng)
    a1, a2 = h1.adjoint(), h2.adjoint()
    a12 = (h2 @ h1).adjoint()
    ap1, ap2 = random_se3(rng).adjoint(), random_se3(rng).adjoint()
    v = rng.normal(size=6)
    f = rng.normal(size=6)
    inertia = spatial_inertia(1.0, rng.normal(size=3), np.eye(3) * 0.1)
    x = random_se3(rng).adjoint()
    for kind, val in ((SpatialType.MOTION, v), (SpatialType.FORCE, f), (SpatialType.INERTIA, inertia)):
        seq = transform_typed(kind, transform_typed(kind, val, a1), a2)
        np.testing.assert_allclose(seq, transform_typed(kind, val, a12), atol=1e-10)
    seq = transform_typed(SpatialType.TRANSFORM, transform_typed(SpatialType.TRANSFORM, x, a1, ap1), a2, ap2)
    np.testing.assert_allclose(seq, transform_typed(SpatialType.TRANSFORM, x, a12, ap2 @ ap1), atol=1e-10)
