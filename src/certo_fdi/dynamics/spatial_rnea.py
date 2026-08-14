from __future__ import annotations

import numpy as np

from certo_fdi.types import TwoLinkParams


def skew(v: np.ndarray) -> np.ndarray:
    x, y, z = np.asarray(v, dtype=float)
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def ad_motion(v: np.ndarray) -> np.ndarray:
    """Spatial motion cross-product matrix for [omega; linear]."""
    omega = np.asarray(v[:3], dtype=float)
    linear = np.asarray(v[3:], dtype=float)
    z = np.zeros((3, 3))
    return np.block([[skew(omega), z], [skew(linear), skew(omega)]])


def ad_force(v: np.ndarray) -> np.ndarray:
    """Spatial force cross-product matrix: ad*_v = -ad_v^T."""
    return -ad_motion(v).T


def rotz(angle: float) -> np.ndarray:
    c = np.cos(angle)
    s = np.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def motion_rotation(e: np.ndarray) -> np.ndarray:
    z = np.zeros((3, 3))
    return np.block([[e, z], [z, e]])


def motion_translation(r_parent_to_child: np.ndarray) -> np.ndarray:
    z = np.zeros((3, 3))
    return np.block(
        [[np.eye(3), z], [-skew(np.asarray(r_parent_to_child, dtype=float)), np.eye(3)]]
    )


def spatial_inertia(mass: float, com: np.ndarray, inertia_com: np.ndarray) -> np.ndarray:
    c = skew(np.asarray(com, dtype=float))
    return np.block(
        [
            [inertia_com + mass * c @ c.T, mass * c],
            [mass * c.T, mass * np.eye(3)],
        ]
    )


def rnea_2r(
    q: np.ndarray,
    qd: np.ndarray,
    qdd: np.ndarray,
    p: TwoLinkParams,
) -> np.ndarray:
    """Full 6D spatial RNEA for the planar 2R robot.

    Frames are attached at the joints with x axes along each link. Motion vectors
    use [omega; v]. The implementation intentionally uses ad_force=-ad_motion.T;
    tests cross-check against the independent closed-form M/C/g equations.
    """

    q = np.asarray(q, dtype=float)
    qd = np.asarray(qd, dtype=float)
    qdd = np.asarray(qdd, dtype=float)

    i1 = np.diag([1e-12, p.I1, p.I1])
    i2 = np.diag([1e-12, p.I2, p.I2])
    inertias = [
        spatial_inertia(p.m1, np.array([p.lc1, 0.0, 0.0]), i1),
        spatial_inertia(p.m2, np.array([p.lc2, 0.0, 0.0]), i2),
    ]

    xup = [
        motion_rotation(rotz(q[0]).T),
        motion_rotation(rotz(q[1]).T)
        @ motion_translation(np.array([p.l1, 0.0, 0.0])),
    ]
    s = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0])

    v_parent = np.zeros(6)
    # World gravity is [0,-g,0]; Featherstone base acceleration is -gravity.
    a_parent = np.array([0.0, 0.0, 0.0, 0.0, p.gravity, 0.0])

    velocities: list[np.ndarray] = []
    accelerations: list[np.ndarray] = []
    forces: list[np.ndarray] = []

    for i in range(2):
        vj = s * qd[i]
        vi = xup[i] @ v_parent + vj
        ai = xup[i] @ a_parent + s * qdd[i] + ad_motion(vi) @ vj
        fi = inertias[i] @ ai + ad_force(vi) @ (inertias[i] @ vi)
        velocities.append(vi)
        accelerations.append(ai)
        forces.append(fi)
        v_parent = vi
        a_parent = ai

    tau = np.zeros(2)
    for i in (1, 0):
        tau[i] = s @ forces[i]
        if i > 0:
            forces[i - 1] = forces[i - 1] + xup[i].T @ forces[i]
    return tau
