from __future__ import annotations

from functools import partial

import jax
from jax import config
import jax.numpy as jnp

from certo_fdi.types import TwoLinkParams

config.update("jax_enable_x64", True)


def _skew3(v: jnp.ndarray) -> jnp.ndarray:
    x, y, z = v
    return jnp.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def ee_position(q: jnp.ndarray, p: TwoLinkParams) -> jnp.ndarray:
    q1, q2 = q
    return jnp.array(
        [
            p.l1 * jnp.cos(q1) + p.l2 * jnp.cos(q1 + q2),
            p.l1 * jnp.sin(q1) + p.l2 * jnp.sin(q1 + q2),
        ]
    )


def ee_jacobian(q: jnp.ndarray, p: TwoLinkParams) -> jnp.ndarray:
    q1, q2 = q
    return jnp.array(
        [
            [
                -p.l1 * jnp.sin(q1) - p.l2 * jnp.sin(q1 + q2),
                -p.l2 * jnp.sin(q1 + q2),
            ],
            [
                p.l1 * jnp.cos(q1) + p.l2 * jnp.cos(q1 + q2),
                p.l2 * jnp.cos(q1 + q2),
            ],
        ]
    )


def link1_jacobian(q: jnp.ndarray, p: TwoLinkParams) -> jnp.ndarray:
    q1 = q[0]
    return jnp.array(
        [[-p.l1 * jnp.sin(q1), 0.0], [p.l1 * jnp.cos(q1), 0.0]]
    )


def ee_jacobian_dot(q: jnp.ndarray, v: jnp.ndarray, p: TwoLinkParams) -> jnp.ndarray:
    q1, q2 = q
    v1, v2 = v
    w12 = v1 + v2
    return jnp.array(
        [
            [
                -p.l1 * jnp.cos(q1) * v1 - p.l2 * jnp.cos(q1 + q2) * w12,
                -p.l2 * jnp.cos(q1 + q2) * w12,
            ],
            [
                -p.l1 * jnp.sin(q1) * v1 - p.l2 * jnp.sin(q1 + q2) * w12,
                -p.l2 * jnp.sin(q1 + q2) * w12,
            ],
        ]
    )


def _base_coefficients(p: TwoLinkParams) -> tuple[float, float, float]:
    a = p.I1 + p.I2 + p.m1 * p.lc1**2 + p.m2 * (p.l1**2 + p.lc2**2)
    b = p.m2 * p.l1 * p.lc2
    d = p.I2 + p.m2 * p.lc2**2
    return a, b, d


def mass_matrix(q: jnp.ndarray, p: TwoLinkParams, payload_mass: float = 0.0) -> jnp.ndarray:
    _, q2 = q
    a, b, d = _base_coefficients(p)
    c2 = jnp.cos(q2)
    base = jnp.array(
        [
            [a + 2.0 * b * c2, d + b * c2],
            [d + b * c2, d],
        ]
    )
    j = ee_jacobian(q, p)
    return base + payload_mass * (j.T @ j)


def coriolis_matrix(
    q: jnp.ndarray,
    v: jnp.ndarray,
    p: TwoLinkParams,
    payload_mass: float = 0.0,
) -> jnp.ndarray:
    _, q2 = q
    v1, v2 = v
    _, b, _ = _base_coefficients(p)
    b_total = b + payload_mass * p.l1 * p.l2
    h = b_total * jnp.sin(q2)
    return jnp.array(
        [
            [-h * v2, -h * (v1 + v2)],
            [h * v1, 0.0],
        ]
    )


def gravity_vector(q: jnp.ndarray, p: TwoLinkParams, payload_mass: float = 0.0) -> jnp.ndarray:
    q1, q2 = q
    c1 = jnp.cos(q1)
    c12 = jnp.cos(q1 + q2)
    g1 = (
        p.m1 * p.lc1 + p.m2 * p.l1 + payload_mass * p.l1
    ) * p.gravity * c1 + (
        p.m2 * p.lc2 + payload_mass * p.l2
    ) * p.gravity * c12
    g2 = (p.m2 * p.lc2 + payload_mass * p.l2) * p.gravity * c12
    return jnp.array([g1, g2])


def friction_torque(
    v: jnp.ndarray,
    p: TwoLinkParams,
    viscous_delta: jnp.ndarray | None = None,
    coulomb_delta: jnp.ndarray | None = None,
    shape_delta: jnp.ndarray | None = None,
) -> jnp.ndarray:
    if viscous_delta is None:
        viscous_delta = jnp.zeros(2, dtype=v.dtype)
    if coulomb_delta is None:
        coulomb_delta = jnp.zeros(2, dtype=v.dtype)
    if shape_delta is None:
        shape_delta = jnp.zeros(2, dtype=v.dtype)
    smoothing = jnp.maximum(p.friction_eps + shape_delta, 0.005)
    return (p.viscous + viscous_delta) * v + (p.coulomb + coulomb_delta) * jnp.tanh(
        v / smoothing
    )


def mass_matrix_dot(
    q: jnp.ndarray,
    v: jnp.ndarray,
    p: TwoLinkParams,
    payload_mass: float = 0.0,
) -> jnp.ndarray:
    _, q2 = q
    _, v2 = v
    _, b, _ = _base_coefficients(p)
    b_total = b + payload_mass * p.l1 * p.l2
    s = -b_total * jnp.sin(q2) * v2
    return jnp.array([[2.0 * s, s], [s, 0.0]])


def rigid_body_torque(
    q: jnp.ndarray,
    v: jnp.ndarray,
    a: jnp.ndarray,
    p: TwoLinkParams,
    payload_mass: float = 0.0,
) -> jnp.ndarray:
    return (
        mass_matrix(q, p, payload_mass) @ a
        + coriolis_matrix(q, v, p, payload_mass) @ v
        + gravity_vector(q, p, payload_mass)
    )


def payload_torque_per_kg(
    q: jnp.ndarray,
    v: jnp.ndarray,
    a: jnp.ndarray,
    p: TwoLinkParams,
) -> jnp.ndarray:
    j = ee_jacobian(q, p)
    jd = ee_jacobian_dot(q, v, p)
    cartesian_acc = j @ a + jd @ v
    return j.T @ (cartesian_acc + jnp.array([0.0, p.gravity]))


def plant_acceleration(
    q: jnp.ndarray,
    v: jnp.ndarray,
    tau_applied: jnp.ndarray,
    p: TwoLinkParams,
    payload_mass: float = 0.0,
    viscous_delta: jnp.ndarray | None = None,
    coulomb_delta: jnp.ndarray | None = None,
    shape_delta: jnp.ndarray | None = None,
    link1_contact_force: jnp.ndarray | None = None,
    contact_force: jnp.ndarray | None = None,
) -> jnp.ndarray:
    if contact_force is None:
        contact_force = jnp.zeros(2, dtype=q.dtype)
    if link1_contact_force is None:
        link1_contact_force = jnp.zeros(2, dtype=q.dtype)
    tau_ext = (
        ee_jacobian(q, p).T @ contact_force
        + link1_jacobian(q, p).T @ link1_contact_force
    )
    m = mass_matrix(q, p, payload_mass)
    h = (
        coriolis_matrix(q, v, p, payload_mass) @ v
        + gravity_vector(q, p, payload_mass)
        + friction_torque(v, p, viscous_delta, coulomb_delta, shape_delta)
    )
    return jnp.linalg.solve(m, tau_applied + tau_ext - h)


def skew_symmetry_residual(
    q: jnp.ndarray,
    v: jnp.ndarray,
    p: TwoLinkParams,
    payload_mass: float = 0.0,
) -> jnp.ndarray:
    s = mass_matrix_dot(q, v, p, payload_mass) - 2.0 * coriolis_matrix(
        q, v, p, payload_mass
    )
    return s + s.T
