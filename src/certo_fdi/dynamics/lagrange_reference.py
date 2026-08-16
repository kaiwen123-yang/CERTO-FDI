"""Independent planar-2R torque oracle from a symbolic Lagrangian.

Ported from Stage 1 (`stage/stage1-closedloop-certificate`, file
``src/certo_fdi/dynamics/lagrange_reference.py``) with the JAX ``TwoLinkParams`` type
replaced by explicit scalar arguments; see docs_pointer/PORT_PROVENANCE.md.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import sympy as sp


@lru_cache(maxsize=1)
def _symbolic_torque_function():
    q1, q2, dq1, dq2, ddq1, ddq2 = sp.symbols("q1 q2 dq1 dq2 ddq1 ddq2", real=True)
    m1, m2, l1, lc1, lc2, i1, i2, gravity = sp.symbols(
        "m1 m2 l1 lc1 lc2 i1 i2 gravity", positive=True, real=True
    )
    q = sp.Matrix([q1, q2])
    dq = sp.Matrix([dq1, dq2])
    ddq = sp.Matrix([ddq1, ddq2])
    p1 = sp.Matrix([lc1 * sp.cos(q1), lc1 * sp.sin(q1)])
    p2 = sp.Matrix(
        [
            l1 * sp.cos(q1) + lc2 * sp.cos(q1 + q2),
            l1 * sp.sin(q1) + lc2 * sp.sin(q1 + q2),
        ]
    )
    v1 = p1.jacobian(q) * dq
    v2 = p2.jacobian(q) * dq
    kinetic = (
        sp.Rational(1, 2) * m1 * v1.dot(v1)
        + sp.Rational(1, 2) * i1 * dq1**2
        + sp.Rational(1, 2) * m2 * v2.dot(v2)
        + sp.Rational(1, 2) * i2 * (dq1 + dq2) ** 2
    )
    potential = gravity * (m1 * p1[1] + m2 * p2[1])
    lagrangian = kinetic - potential
    torque = []
    for idx in range(2):
        momentum = sp.diff(lagrangian, dq[idx])
        time_derivative = sum(
            sp.diff(momentum, q[j]) * dq[j] + sp.diff(momentum, dq[j]) * ddq[j]
            for j in range(2)
        )
        torque.append(sp.simplify(time_derivative - sp.diff(lagrangian, q[idx])))
    arguments = (q1, q2, dq1, dq2, ddq1, ddq2, m1, m2, l1, lc1, lc2, i1, i2, gravity)
    return sp.lambdify(arguments, sp.Matrix(torque), modules="numpy")


def sympy_lagrange_torque(
    q: np.ndarray,
    qd: np.ndarray,
    qdd: np.ndarray,
    *,
    m1: float,
    m2: float,
    l1: float,
    lc1: float,
    lc2: float,
    I1: float,
    I2: float,
    gravity: float,
) -> np.ndarray:
    """Independent torque oracle derived from symbolic kinetic/potential energy."""
    values = (
        *np.asarray(q, dtype=float),
        *np.asarray(qd, dtype=float),
        *np.asarray(qdd, dtype=float),
        m1, m2, l1, lc1, lc2, I1, I2, gravity,
    )
    return np.asarray(_symbolic_torque_function()(*values), dtype=float).reshape(2)
