"""Reference (NumPy, float64) recursive Newton-Euler algorithm returning typed quantities.

This is the analytic front end of LiGRA (Block A) in its reference form. It exposes every
intermediate spatial quantity with its :class:`SpatialType`, so that the frame
covariance tests can compare two runs of the *same physical system* described in
different link frames.

Conventions: ``[omega; v]`` motion vectors, ``[n; f]`` wrenches, ``ad*_V = -ad_V^T``,
Featherstone RNEA (RBDA Table 5.1) with gravity applied through the base acceleration
``a_0 = -g``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.geometry.se3 import ad, ad_star
from certo_fdi.geometry.spatial_types import SpatialType


@dataclass
class TypedRNEAState:
    """All typed intermediate quantities of one RNEA evaluation."""

    X: np.ndarray  # (n,6,6) TRANSFORM  X_{i<-p}
    S: np.ndarray  # (n,6)   MOTION
    V: np.ndarray  # (n,6)   MOTION
    A: np.ndarray  # (n,6)   MOTION (spatial acceleration incl. gravity offset)
    inertia: np.ndarray  # (n,6,6) INERTIA
    momentum: np.ndarray  # (n,6) FORCE  I_i V_i
    F_body: np.ndarray  # (n,6) FORCE  I a + ad* I v - f_ext (before children)
    F: np.ndarray  # (n,6)   FORCE  net wrench through joint i (after backward pass)
    tau_rb: np.ndarray  # (n,) SCALAR rigid-body torque S^T F
    tau: np.ndarray  # (n,)   SCALAR nominal torque incl. armature/damping/coulomb
    f_ext: np.ndarray  # (n,6) FORCE  external wrench in link coordinates

    TYPES = {
        "X": SpatialType.TRANSFORM,
        "S": SpatialType.MOTION,
        "V": SpatialType.MOTION,
        "A": SpatialType.MOTION,
        "inertia": SpatialType.INERTIA,
        "momentum": SpatialType.FORCE,
        "F_body": SpatialType.FORCE,
        "F": SpatialType.FORCE,
        "f_ext": SpatialType.FORCE,
        "tau_rb": SpatialType.SCALAR,
        "tau": SpatialType.SCALAR,
    }


def joint_friction_torque(chain: ChainModel, qd: np.ndarray) -> np.ndarray:
    qd = np.asarray(qd, dtype=float)
    return chain.damping * qd + chain.coulomb * np.tanh(qd / chain.coulomb_eps)


def rnea(
    chain: ChainModel,
    q: np.ndarray,
    qd: np.ndarray,
    qdd: np.ndarray,
    f_ext: np.ndarray | None = None,
    *,
    mutate_ad_star_sign: bool = False,
    include_joint_terms: bool = True,
    gravity: np.ndarray | None = None,
) -> TypedRNEAState:
    """Evaluate the RNEA and return all typed intermediates.

    ``f_ext`` (n,6) are wrenches *applied to* each link, expressed in link coordinates
    ([n; f]). ``mutate_ad_star_sign`` is for mutation tests only.
    """
    n = chain.n_links
    q = np.asarray(q, dtype=float).reshape(n)
    qd = np.asarray(qd, dtype=float).reshape(n)
    qdd = np.asarray(qdd, dtype=float).reshape(n)
    g = chain.gravity if gravity is None else np.asarray(gravity, dtype=float)
    fx = np.zeros((n, 6)) if f_ext is None else np.asarray(f_ext, dtype=float).reshape(n, 6)

    X = np.zeros((n, 6, 6))
    S = chain.motion_subspaces()
    V = np.zeros((n, 6))
    A = np.zeros((n, 6))
    inertia = chain.spatial_inertias()
    momentum = np.zeros((n, 6))
    F_body = np.zeros((n, 6))

    a_base = np.concatenate([np.zeros(3), -g])
    for i in range(n):
        X[i] = chain.motion_transform(i, q[i])
        p = chain.parent[i]
        v_parent = np.zeros(6) if p < 0 else V[p]
        a_parent = a_base if p < 0 else A[p]
        v_joint = S[i] * qd[i]
        V[i] = X[i] @ v_parent + v_joint
        A[i] = X[i] @ a_parent + S[i] * qdd[i] + ad(V[i]) @ v_joint
        momentum[i] = inertia[i] @ V[i]
        F_body[i] = inertia[i] @ A[i] + ad_star(V[i], mutate_sign=mutate_ad_star_sign) @ momentum[i] - fx[i]

    F = F_body.copy()
    tau_rb = np.zeros(n)
    for i in range(n - 1, -1, -1):
        tau_rb[i] = S[i] @ F[i]
        p = chain.parent[i]
        if p >= 0:
            F[p] = F[p] + X[i].T @ F[i]

    tau = tau_rb.copy()
    if include_joint_terms:
        tau = tau + chain.armature * qdd + joint_friction_torque(chain, qd)
    return TypedRNEAState(
        X=X, S=S, V=V, A=A, inertia=inertia, momentum=momentum, F_body=F_body, F=F,
        tau_rb=tau_rb, tau=tau, f_ext=fx,
    )


def mass_matrix(chain: ChainModel, q: np.ndarray, *, include_armature: bool = True) -> np.ndarray:
    """Joint-space mass matrix from unit-acceleration RNEA columns (test helper)."""
    n = chain.n_links
    zero = np.zeros(n)
    m = np.zeros((n, n))
    for j in range(n):
        e = np.zeros(n)
        e[j] = 1.0
        col = rnea(chain, q, zero, e, include_joint_terms=False, gravity=np.zeros(3)).tau_rb
        m[:, j] = col
    if include_armature:
        m = m + np.diag(chain.armature)
    return m


def bias_torque(chain: ChainModel, q: np.ndarray, qd: np.ndarray, *, include_friction: bool = False) -> np.ndarray:
    """``C(q,qd) qd + g(q)`` (+ friction if requested)."""
    n = chain.n_links
    state = rnea(chain, q, qd, np.zeros(n), include_joint_terms=False)
    tau = state.tau_rb
    if include_friction:
        tau = tau + joint_friction_torque(chain, qd)
    return tau


def generalized_momentum(chain: ChainModel, q: np.ndarray, qd: np.ndarray) -> np.ndarray:
    return mass_matrix(chain, q) @ np.asarray(qd, dtype=float)
