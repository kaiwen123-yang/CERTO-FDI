"""Typed spatial quantities and their exact link-frame transformation laws.

Every quantity handled by the LiGRA front end carries a :class:`SpatialType`. Under a
legal reparameterization of link ``i`` by ``H_i in SE(3)`` with ``A_i = Ad_{H_i}`` (and
``A_p`` for the parent), the frozen laws (02_MATHEMATICAL_CONTRACT.md §2) are::

    MOTION    V'  = A_i V              (twists, spatial accelerations, joint subspaces)
    FORCE     F'  = A_i^{-T} F         (wrenches, momenta, wrench-like messages)
    INERTIA   I'  = A_i^{-T} I A_i^{-1}
    TRANSFORM X'  = A_i X A_p^{-1}     (X = X_{i<-p}, parent-to-child motion transform)
    SCALAR    s'  = s                  (joint scalars, torques, invariants)

These laws hold for healthy and faulty samples alike; nothing in this module refers to
faults.
"""

from __future__ import annotations

from enum import Enum

import numpy as np


class SpatialType(str, Enum):
    MOTION = "motion"
    FORCE = "force"
    INERTIA = "inertia"
    TRANSFORM = "transform"
    SCALAR = "scalar"


def transform_typed(
    kind: SpatialType,
    value: np.ndarray,
    a_self: np.ndarray,
    a_parent: np.ndarray | None = None,
) -> np.ndarray:
    """Apply the exact transformation law of ``kind`` to ``value``.

    ``a_self`` is the motion adjoint of the link's own reparameterization and
    ``a_parent`` the parent's (needed only for TRANSFORM). ``value`` may carry leading
    batch dimensions; the last one or two axes are the spatial axes.
    """
    value = np.asarray(value, dtype=float)
    a_self = np.asarray(a_self, dtype=float)
    if kind == SpatialType.SCALAR:
        return value.copy()
    if kind == SpatialType.MOTION:
        return np.einsum("ij,...j->...i", a_self, value)
    a_inv_t = np.linalg.inv(a_self).T
    if kind == SpatialType.FORCE:
        return np.einsum("ij,...j->...i", a_inv_t, value)
    if kind == SpatialType.INERTIA:
        a_inv = np.linalg.inv(a_self)
        return np.einsum("ij,...jk,kl->...il", a_inv_t, value, a_inv)
    if kind == SpatialType.TRANSFORM:
        if a_parent is None:
            raise ValueError("TRANSFORM law needs the parent adjoint")
        a_parent_inv = np.linalg.inv(np.asarray(a_parent, dtype=float))
        return np.einsum("ij,...jk,kl->...il", a_self, value, a_parent_inv)
    raise ValueError(f"unknown spatial type {kind}")


def covariance_residual(
    kind: SpatialType,
    value_before: np.ndarray,
    value_after: np.ndarray,
    a_self: np.ndarray,
    a_parent: np.ndarray | None = None,
) -> float:
    """Max-abs residual between ``value_after`` and the law applied to ``value_before``."""
    predicted = transform_typed(kind, value_before, a_self, a_parent)
    return float(np.max(np.abs(np.asarray(value_after, dtype=float) - predicted)))


def spatial_inertia(mass: float, com: np.ndarray, inertia_com: np.ndarray) -> np.ndarray:
    """6x6 spatial inertia in link coordinates for ``[omega; v]`` motion vectors.

    ``I = [[I_c + m c^ c^T, m c^], [m c^T^, m 1]]`` with ``c^ = skew(com)``.
    """
    from certo_fdi.geometry.se3 import skew

    c = skew(np.asarray(com, dtype=float))
    inertia_com = np.asarray(inertia_com, dtype=float)
    return np.block(
        [
            [inertia_com + mass * c @ c.T, mass * c],
            [mass * c.T, mass * np.eye(3)],
        ]
    )


def decompose_spatial_inertia(inertia: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Recover ``(mass, com, inertia_com)`` from a 6x6 spatial inertia."""
    from certo_fdi.geometry.se3 import skew, unskew

    inertia = np.asarray(inertia, dtype=float)
    mass = float(np.trace(inertia[3:, 3:]) / 3.0)
    if mass <= 0.0:
        raise ValueError("non-positive mass")
    com = unskew(inertia[:3, 3:] / mass)
    c = skew(com)
    inertia_com = inertia[:3, :3] - mass * c @ c.T
    return mass, com, inertia_com


def is_physical_spatial_inertia(inertia: np.ndarray, atol: float = 1e-9) -> bool:
    """Symmetry, positive mass, and positive semidefinite rotational part about the CoM."""
    inertia = np.asarray(inertia, dtype=float)
    if inertia.shape != (6, 6) or not np.allclose(inertia, inertia.T, atol=atol):
        return False
    try:
        mass, _, inertia_com = decompose_spatial_inertia(inertia)
    except ValueError:
        return False
    eig = np.linalg.eigvalsh((inertia_com + inertia_com.T) / 2.0)
    return mass > 0.0 and bool(np.all(eig >= -atol))
