"""SE(3) / se(3) primitives with the frozen CERTO-FDI spatial-vector conventions.

Conventions (frozen by 02_MATHEMATICAL_CONTRACT.md):

* motion vectors are ordered ``V = [omega; v]`` (angular first);
* wrench vectors are ordered ``F = [n; f]`` (moment first);
* the force cross product is ``ad*_V = -ad_V^T``;
* a homogeneous transform ``T = (R, p)`` maps coordinates from frame B to frame A
  (``x_A = R x_B + p``) and its motion adjoint ``Ad_T = [[R, 0], [skew(p) R, R]]``
  maps motion vectors expressed in B to motion vectors expressed in A;
* wrenches transform contragrediently: ``F_A = Ad_T^{-T} F_B``.

All functions here are float64 NumPy and are the reference implementation against
which the batched torch versions in :mod:`certo_fdi.geometry.torch_ops` are tested.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def skew(v: np.ndarray) -> np.ndarray:
    """Return the 3x3 skew-symmetric matrix such that ``skew(a) @ b == cross(a, b)``."""
    x, y, z = np.asarray(v, dtype=float)
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def unskew(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=float)
    return np.array([m[2, 1], m[0, 2], m[1, 0]])


def so3_exp(w: np.ndarray) -> np.ndarray:
    """Rodrigues formula for the rotation matrix ``exp(skew(w))``."""
    w = np.asarray(w, dtype=float)
    theta = float(np.linalg.norm(w))
    k = skew(w)
    if theta < 1e-12:
        return np.eye(3) + k + 0.5 * k @ k
    a = np.sin(theta) / theta
    b = (1.0 - np.cos(theta)) / theta**2
    return np.eye(3) + a * k + b * k @ k


def so3_log(r: np.ndarray) -> np.ndarray:
    r = np.asarray(r, dtype=float)
    cos_theta = np.clip((np.trace(r) - 1.0) / 2.0, -1.0, 1.0)
    theta = float(np.arccos(cos_theta))
    if theta < 1e-12:
        return unskew(r - r.T) / 2.0
    if abs(np.pi - theta) < 1e-9:
        # Near pi: use the symmetric part.
        m = (r + np.eye(3)) / 2.0
        axis = np.sqrt(np.clip(np.diag(m), 0.0, None))
        # fix signs
        i = int(np.argmax(axis))
        axis = m[:, i] / axis[i]
        axis /= np.linalg.norm(axis)
        return theta * axis
    return theta / (2.0 * np.sin(theta)) * unskew(r - r.T)


def is_rotation(r: np.ndarray, atol: float = 1e-9) -> bool:
    r = np.asarray(r, dtype=float)
    return (
        r.shape == (3, 3)
        and np.allclose(r.T @ r, np.eye(3), atol=atol)
        and abs(np.linalg.det(r) - 1.0) < atol
    )


def quat_to_rot(q_wxyz: np.ndarray) -> np.ndarray:
    """MuJoCo-style (w, x, y, z) unit quaternion to rotation matrix."""
    w, x, y, z = np.asarray(q_wxyz, dtype=float)
    n = w * w + x * x + y * y + z * z
    if n < 1e-15:
        return np.eye(3)
    s = 2.0 / n
    return np.array(
        [
            [1.0 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w)],
            [s * (x * y + z * w), 1.0 - s * (x * x + z * z), s * (y * z - x * w)],
            [s * (x * z - y * w), s * (y * z + x * w), 1.0 - s * (x * x + y * y)],
        ]
    )


@dataclass(frozen=True)
class SE3:
    """Rigid transform ``T = (R, p)``; ``x_A = R x_B + p``."""

    R: np.ndarray
    p: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "R", np.array(self.R, dtype=float).reshape(3, 3))
        object.__setattr__(self, "p", np.array(self.p, dtype=float).reshape(3))

    @staticmethod
    def identity() -> "SE3":
        return SE3(np.eye(3), np.zeros(3))

    @staticmethod
    def from_matrix(m: np.ndarray) -> "SE3":
        m = np.asarray(m, dtype=float)
        return SE3(m[:3, :3], m[:3, 3])

    @staticmethod
    def from_rot_trans(r: np.ndarray, p: np.ndarray) -> "SE3":
        return SE3(r, p)

    @staticmethod
    def from_quat_pos(q_wxyz: np.ndarray, pos: np.ndarray) -> "SE3":
        return SE3(quat_to_rot(q_wxyz), pos)

    @staticmethod
    def exp(xi: np.ndarray) -> "SE3":
        """Exponential of a twist ``xi = [omega; v]`` (rotation applied about origin)."""
        xi = np.asarray(xi, dtype=float)
        w, v = xi[:3], xi[3:]
        theta = float(np.linalg.norm(w))
        k = skew(w)
        if theta < 1e-12:
            vmat = np.eye(3) + 0.5 * k + k @ k / 6.0
        else:
            vmat = (
                np.eye(3)
                + (1.0 - np.cos(theta)) / theta**2 * k
                + (theta - np.sin(theta)) / theta**3 * k @ k
            )
        return SE3(so3_exp(w), vmat @ v)

    def matrix(self) -> np.ndarray:
        m = np.eye(4)
        m[:3, :3] = self.R
        m[:3, 3] = self.p
        return m

    def inverse(self) -> "SE3":
        return SE3(self.R.T, -self.R.T @ self.p)

    def __matmul__(self, other: "SE3") -> "SE3":
        return SE3(self.R @ other.R, self.R @ other.p + self.p)

    def act_point(self, x: np.ndarray) -> np.ndarray:
        return self.R @ np.asarray(x, dtype=float) + self.p

    def adjoint(self) -> np.ndarray:
        """Motion adjoint ``Ad_T`` (6x6): maps ``[omega; v]`` in B to A coordinates."""
        z = np.zeros((3, 3))
        return np.block([[self.R, z], [skew(self.p) @ self.R, self.R]])

    def adjoint_inv(self) -> np.ndarray:
        return self.inverse().adjoint()

    def coadjoint(self) -> np.ndarray:
        """Wrench transform ``Ad_T^{-T}`` (6x6): maps ``[n; f]`` in B to A coordinates."""
        z = np.zeros((3, 3))
        # Ad_T^{-T} = [[R, skew(p) R], [0, R]]
        return np.block([[self.R, skew(self.p) @ self.R], [z, self.R]])

    def is_valid(self, atol: float = 1e-9) -> bool:
        return is_rotation(self.R, atol=atol) and np.all(np.isfinite(self.p))


def ad(v: np.ndarray) -> np.ndarray:
    """Motion cross-product matrix ``ad_V`` for ``V = [omega; v]``."""
    v = np.asarray(v, dtype=float)
    z = np.zeros((3, 3))
    return np.block([[skew(v[:3]), z], [skew(v[3:]), skew(v[:3])]])


def ad_star(v: np.ndarray, *, mutate_sign: bool = False) -> np.ndarray:
    """Force cross-product matrix ``ad*_V = -ad_V^T`` (frozen convention).

    ``mutate_sign=True`` returns the deliberately wrong ``+ad_V^T`` used only by
    mutation tests; it must never be used in production code paths.
    """
    a = ad(v).T
    return a if mutate_sign else -a


def adjoint_transpose_inverse(adjoint_matrix: np.ndarray) -> np.ndarray:
    """Return ``A^{-T}`` for a motion adjoint ``A`` computed with linear algebra (test helper)."""
    return np.linalg.inv(np.asarray(adjoint_matrix, dtype=float)).T


def random_rotation(rng: np.random.Generator, max_angle_rad: float = np.pi) -> np.ndarray:
    """Random rotation with uniformly random axis and angle uniform in [0, max_angle]."""
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    angle = rng.uniform(0.0, max_angle_rad)
    return so3_exp(axis * angle)


def random_se3(
    rng: np.random.Generator,
    max_angle_rad: float = np.pi,
    max_translation: float = 0.25,
) -> SE3:
    """Random legal rigid transform (member of SE(3), never a general GL(6) element)."""
    r = random_rotation(rng, max_angle_rad)
    p = rng.uniform(-max_translation, max_translation, size=3)
    return SE3(r, p)


def is_legal_motion_adjoint(a: np.ndarray, atol: float = 1e-9) -> bool:
    """Check that a 6x6 matrix is the adjoint of some SE(3) element (structure test).

    A legal motion adjoint has the block form ``[[R, 0], [skew(p) R, R]]`` with ``R`` a
    rotation. This distinguishes legal frame changes from arbitrary ``GL(6)`` matrices.
    """
    a = np.asarray(a, dtype=float)
    if a.shape != (6, 6):
        return False
    r = a[:3, :3]
    if not is_rotation(r, atol=atol):
        return False
    if not np.allclose(a[:3, 3:], 0.0, atol=atol):
        return False
    if not np.allclose(a[3:, 3:], r, atol=atol):
        return False
    m = a[3:, :3] @ r.T  # should be skew(p)
    return np.allclose(m, -m.T, atol=atol)
