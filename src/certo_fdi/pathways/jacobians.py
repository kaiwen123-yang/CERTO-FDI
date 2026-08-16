"""Per-link and per-point Jacobians of the frozen serial chain, in the base (world) frame.

Conventions (identical to the rest of the repository, see
``dynamics/mujoco_backend.model_parameter_audit``):

* motion vectors are ``[omega; v]``, wrenches are ``[n; f]`` (torque first);
* ``J_ell(q) in R^{6 x n}`` maps ``qdot`` to the spatial velocity ``[omega_ell; v_ell]`` of the
  **body-frame origin** of link ``ell``, expressed in the base frame;
* consequently an external wrench ``w = [n; f]`` applied at that origin and expressed in the
  base frame produces the joint torque ``tau_ext = J_ell(q)^T w`` (virtual work);
* for a **point force** ``f`` applied at a material point ``x`` of link ``ell``,
  ``tau_ext = J_point(q, x)^T f`` with ``J_point = J_v - skew(x - o_ell) J_omega``.

The frozen simulator injects contact faults as a pure force at a point offset from the body
origin (``data.xfrc_applied`` with ``torque = r x force``), i.e. exactly the point-force case;
Stage 2A therefore uses the **3-D point-force Jacobian** for the candidate-point dictionaries
and the 6-D body-origin Jacobian for the point-agnostic per-link dictionary. The two forms
are never mixed inside one dictionary (contract §3.3 F4).

Everything is vectorised over a leading time axis; the reference implementation is checked
against MuJoCo ``mj_jac`` / ``mj_applyFT`` and against finite differences of forward
kinematics in ``tests/test_stage2a_jacobians.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel


def _rot_axis(axis: np.ndarray, q: np.ndarray) -> np.ndarray:
    """(T,3,3) rotation matrices about a fixed unit ``axis`` by angles ``q`` (T,)."""
    k = np.asarray(axis, dtype=float)
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    c = np.cos(q)[:, None, None]
    s = np.sin(q)[:, None, None]
    return np.eye(3)[None] + s * K[None] + (1.0 - c) * (K @ K)[None]


def skew(v: np.ndarray) -> np.ndarray:
    """(...,3) -> (...,3,3) skew-symmetric matrices."""
    v = np.asarray(v, dtype=float)
    z = np.zeros(v.shape[:-1] + (3, 3))
    z[..., 0, 1] = -v[..., 2]
    z[..., 0, 2] = v[..., 1]
    z[..., 1, 0] = v[..., 2]
    z[..., 1, 2] = -v[..., 0]
    z[..., 2, 0] = -v[..., 1]
    z[..., 2, 1] = v[..., 0]
    return z


@dataclass(frozen=True)
class ChainKinematics:
    """Forward kinematics and Jacobians of one chain evaluated on a batch of configurations."""

    R_link: np.ndarray  # (T, n, 3, 3) link-frame orientation in base
    p_link: np.ndarray  # (T, n, 3) link-frame origin in base
    z_joint: np.ndarray  # (T, n, 3) joint axis direction in base
    o_joint: np.ndarray  # (T, n, 3) joint origin in base
    ancestor: np.ndarray  # (n, n) bool, ancestor[l, k] = joint k moves link l

    @property
    def n_time(self) -> int:
        return int(self.R_link.shape[0])

    @property
    def n_links(self) -> int:
        return int(self.R_link.shape[1])


def ancestor_mask(chain: ChainModel) -> np.ndarray:
    """(n,n) bool: ``mask[l, k]`` is True when joint ``k`` lies on the path base -> link ``l``."""
    n = chain.n_links
    mask = np.zeros((n, n), dtype=bool)
    for l in range(n):
        i = l
        while i >= 0:
            mask[l, i] = True
            i = int(chain.parent[i])
    return mask


def forward_kinematics(chain: ChainModel, q: np.ndarray) -> ChainKinematics:
    """Batched forward kinematics. ``q`` is (T, n); the base frame is the MuJoCo world frame."""
    q = np.atleast_2d(np.asarray(q, dtype=float))
    T, n = q.shape
    if n != chain.n_links:
        raise ValueError(f"q has {n} columns, chain has {chain.n_links} links")
    R_link = np.zeros((T, n, 3, 3))
    p_link = np.zeros((T, n, 3))
    z_joint = np.zeros((T, n, 3))
    o_joint = np.zeros((T, n, 3))
    for i in range(n):
        p = int(chain.parent[i])
        if p < 0:
            R_par = np.broadcast_to(np.eye(3), (T, 3, 3))
            p_par = np.zeros((T, 3))
        else:
            R_par, p_par = R_link[:, p], p_link[:, p]
        Tpj = chain.T_parent_joint[i]
        R_j = R_par @ Tpj[:3, :3][None]  # joint frame orientation (before the joint rotation)
        o_j = p_par + (R_par @ Tpj[:3, 3][None, :, None])[..., 0]
        z_joint[:, i] = (R_j @ chain.joint_axis[i][None, :, None])[..., 0]
        o_joint[:, i] = o_j
        Rq = _rot_axis(chain.joint_axis[i], q[:, i])
        Tjl = chain.T_joint_link[i]
        R_l = R_j @ Rq @ Tjl[:3, :3][None]
        p_l = o_j + (R_j @ Rq @ Tjl[:3, 3][None, :, None])[..., 0]
        R_link[:, i] = R_l
        p_link[:, i] = p_l
    return ChainKinematics(R_link, p_link, z_joint, o_joint, ancestor_mask(chain))


def link_spatial_jacobians(kin: ChainKinematics) -> np.ndarray:
    """(T, n_links, 6, n) spatial Jacobians ``[omega; v]`` at each link's body-frame origin."""
    T, n = kin.n_time, kin.n_links
    J = np.zeros((T, n, 6, n))
    for l in range(n):
        for k in range(n):
            if not kin.ancestor[l, k]:
                continue
            z = kin.z_joint[:, k]  # (T,3)
            r = kin.p_link[:, l] - kin.o_joint[:, k]  # (T,3)
            J[:, l, :3, k] = z
            J[:, l, 3:, k] = np.cross(z, r)
    return J


def point_jacobian(kin: ChainKinematics, J_link: np.ndarray, link: int, r_link: np.ndarray) -> np.ndarray:
    """(T, 3, n) translational Jacobian of the material point ``r_link`` (link-frame offset).

    ``J_point = J_v - skew(R r) J_omega`` where ``R r`` is the offset in base-frame components.
    """
    r_world = (kin.R_link[:, link] @ np.asarray(r_link, dtype=float)[None, :, None])[..., 0]  # (T,3)
    return J_link[:, link, 3:, :] - skew(r_world) @ J_link[:, link, :3, :]


def point_position(kin: ChainKinematics, link: int, r_link: np.ndarray) -> np.ndarray:
    """(T,3) base-frame position of the material point ``r_link`` of ``link``."""
    return kin.p_link[:, link] + (kin.R_link[:, link] @ np.asarray(r_link, dtype=float)[None, :, None])[..., 0]


# --------------------------------------------------------------------------- candidate points
def candidate_points(chain: ChainModel) -> dict[int, list[tuple[str, np.ndarray]]]:
    """Deployment candidate contact points per link, in that link's own frame.

    Purely geometric and derived from the link alone -- **never** from the fault protocol:

    * ``proximal``  the link's own body-frame origin;
    * ``com``       its centre of mass;
    * ``distal``    the origin of its child joint (for the last link: the CoM direction scaled
                    to the link length);
    * ``mid``       the midpoint of proximal and distal;
    * ``+x/-x/+y/-y/+z/-z``  a fixed offset grid at half the link's characteristic length along
                    the link-frame axes, so that links whose child joint sits at their own
                    origin (links 0 and 4 of the Panda) still have off-axis candidates.

    The last point matters: a force applied exactly **on** a joint axis exerts no moment about
    it, so a candidate set collapsed onto the body origin makes that link unobservable by
    construction. The truth contact point of the frozen protocol (a random offset along the
    link ``z`` axis in ``[0.03, 0.10] m``) is deliberately *not* a member of this set; it is
    only used for the oracle upper bound.
    """
    n = chain.n_links
    out: dict[int, list[tuple[str, np.ndarray]]] = {}
    for l in range(n):
        kids = chain.children(l)
        if kids:
            distal = np.asarray(chain.T_parent_joint[kids[0]][:3, 3], dtype=float)
        else:
            com = np.asarray(chain.com[l], dtype=float)
            nrm = float(np.linalg.norm(com))
            distal = com / nrm * float(chain.link_length[l]) if nrm > 1e-9 else np.array([0.0, 0.0, float(chain.link_length[l])])
        d = 0.5 * max(float(chain.link_length[l]), 0.05)
        pts: list[tuple[str, np.ndarray]] = [
            ("proximal", np.zeros(3)),
            ("com", np.asarray(chain.com[l], dtype=float).copy()),
            ("mid", 0.5 * distal),
            ("distal", distal.copy()),
        ]
        for axis, name in enumerate("xyz"):
            e = np.zeros(3)
            e[axis] = d
            pts.append((f"+{name}", e.copy()))
            pts.append((f"-{name}", -e))
        out[l] = pts
    return out


def end_effector_point(chain: ChainModel) -> np.ndarray:
    """Link-frame offset of the declared end-effector point (distal point of the last link)."""
    return dict(candidate_points(chain)[chain.n_links - 1])["distal"]


# --------------------------------------------------------------------------- cross-checks
def mujoco_point_jacobian(plant, q: np.ndarray, link: int, r_link: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reference ``(jacp, jacr)`` from MuJoCo at one configuration (independent implementation)."""
    import mujoco

    plant.data.qpos[:] = np.asarray(q, dtype=float)
    plant.data.qvel[:] = 0.0
    mujoco.mj_forward(plant.model, plant.data)
    b = plant.link_body_ids[link]
    R = np.array(plant.data.xmat[b]).reshape(3, 3)
    point = np.array(plant.data.xpos[b]) + R @ np.asarray(r_link, dtype=float)
    jacp = np.zeros((3, plant.model.nv))
    jacr = np.zeros((3, plant.model.nv))
    mujoco.mj_jac(plant.model, plant.data, jacp, jacr, point, b)
    return jacp, jacr


def mujoco_generalized_force(plant, q: np.ndarray, link: int, r_link: np.ndarray, force: np.ndarray, torque: np.ndarray | None = None) -> np.ndarray:
    """Reference ``tau_ext`` from MuJoCo ``mj_applyFT`` (virtual-work ground truth)."""
    import mujoco

    plant.data.qpos[:] = np.asarray(q, dtype=float)
    plant.data.qvel[:] = 0.0
    mujoco.mj_forward(plant.model, plant.data)
    b = plant.link_body_ids[link]
    R = np.array(plant.data.xmat[b]).reshape(3, 3)
    point = np.array(plant.data.xpos[b]) + R @ np.asarray(r_link, dtype=float)
    out = np.zeros(plant.model.nv)
    mujoco.mj_applyFT(
        plant.model, plant.data,
        np.ascontiguousarray(np.asarray(force, dtype=float)),
        np.ascontiguousarray(np.zeros(3) if torque is None else np.asarray(torque, dtype=float)),
        np.ascontiguousarray(point), b, out,
    )
    return out
