"""Serial-chain rigid-body model description with explicit, reparameterizable link frames.

A link ``i`` (0-based; parent ``-1`` is the fixed base) is described by

* ``T_parent_joint[i]`` — pose of joint frame ``j_i`` in the parent link frame,
* ``joint_axis[i]``    — unit revolute axis expressed in the joint frame,
* ``T_joint_link[i]``  — pose of the link frame ``i`` in the joint frame (identity for
  canonical MJCF/URDF models; non-identity after a legal reparameterization),
* ``mass, com, inertia_com`` — inertial parameters in the link frame,
* ``armature, damping, coulomb`` — joint-scalar nominal actuator/friction terms.

The parent-to-child pose at joint angle ``q`` is::

    T_{p,i}(q) = T_parent_joint[i] @ Rot(axis, q) @ T_joint_link[i]

and the motion transform used by RNEA is ``X_{i<-p} = Ad(T_{p,i}(q))^{-1}``.

Reparameterizing link ``i`` by ``H_i`` (pose of the *old* frame in the *new* frame,
``A_i = Ad_{H_i}``) is an exact operation on this description; see
:meth:`ChainModel.reparameterize`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Sequence

import numpy as np

from certo_fdi.geometry.se3 import SE3, so3_exp
from certo_fdi.geometry.spatial_types import spatial_inertia


@dataclass
class ChainModel:
    name: str
    parent: np.ndarray  # (n,) int
    T_parent_joint: np.ndarray  # (n, 4, 4)
    joint_axis: np.ndarray  # (n, 3)
    T_joint_link: np.ndarray  # (n, 4, 4)
    mass: np.ndarray  # (n,)
    com: np.ndarray  # (n, 3)
    inertia_com: np.ndarray  # (n, 3, 3)
    armature: np.ndarray  # (n,)
    damping: np.ndarray  # (n,)
    coulomb: np.ndarray  # (n,)
    gravity: np.ndarray  # (3,) in base frame
    coulomb_eps: float = 0.05  # rad/s smoothing width of tanh(qd/eps)
    link_length: np.ndarray | None = None  # (n,) characteristic length for frame sampling
    joint_names: tuple[str, ...] = field(default_factory=tuple)
    link_names: tuple[str, ...] = field(default_factory=tuple)
    joint_lower: np.ndarray | None = None
    joint_upper: np.ndarray | None = None
    velocity_limit: np.ndarray | None = None
    torque_limit: np.ndarray | None = None
    provenance: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = self.n_links
        self.parent = np.asarray(self.parent, dtype=int).reshape(n)
        self.T_parent_joint = np.asarray(self.T_parent_joint, dtype=float).reshape(n, 4, 4)
        self.joint_axis = np.asarray(self.joint_axis, dtype=float).reshape(n, 3)
        self.T_joint_link = np.asarray(self.T_joint_link, dtype=float).reshape(n, 4, 4)
        self.mass = np.asarray(self.mass, dtype=float).reshape(n)
        self.com = np.asarray(self.com, dtype=float).reshape(n, 3)
        self.inertia_com = np.asarray(self.inertia_com, dtype=float).reshape(n, 3, 3)
        self.armature = np.asarray(self.armature, dtype=float).reshape(n)
        self.damping = np.asarray(self.damping, dtype=float).reshape(n)
        self.coulomb = np.asarray(self.coulomb, dtype=float).reshape(n)
        self.gravity = np.asarray(self.gravity, dtype=float).reshape(3)
        if self.link_length is None:
            self.link_length = self._default_link_length()
        self.link_length = np.asarray(self.link_length, dtype=float).reshape(n)
        for i in range(n):
            if self.parent[i] >= i:
                raise ValueError("links must be topologically ordered (parent index < child)")
            nrm = np.linalg.norm(self.joint_axis[i])
            if abs(nrm - 1.0) > 1e-9:
                raise ValueError(f"joint axis {i} is not unit length")

    # ------------------------------------------------------------------ properties
    @property
    def n_links(self) -> int:
        return int(np.asarray(self.parent).size)

    def children(self, i: int) -> list[int]:
        return [c for c in range(self.n_links) if self.parent[c] == i]

    def _default_link_length(self) -> np.ndarray:
        n = self.n_links
        lengths = np.zeros(n)
        for i in range(n):
            kids = self.children(i)
            if kids:
                lengths[i] = max(
                    float(np.linalg.norm(self.T_parent_joint[c][:3, 3])) for c in kids
                )
            if lengths[i] < 1e-6:
                lengths[i] = max(float(np.linalg.norm(self.com[i])), 0.05)
        return lengths

    # ------------------------------------------------------------------ geometry
    def spatial_inertia(self, i: int) -> np.ndarray:
        return spatial_inertia(self.mass[i], self.com[i], self.inertia_com[i])

    def spatial_inertias(self) -> np.ndarray:
        return np.stack([self.spatial_inertia(i) for i in range(self.n_links)])

    def motion_subspace(self, i: int) -> np.ndarray:
        """Joint motion subspace ``S_i`` (6,) expressed in link frame ``i``."""
        t_link_joint = SE3.from_matrix(self.T_joint_link[i]).inverse()
        axis6 = np.concatenate([self.joint_axis[i], np.zeros(3)])
        return t_link_joint.adjoint() @ axis6

    def motion_subspaces(self) -> np.ndarray:
        return np.stack([self.motion_subspace(i) for i in range(self.n_links)])

    def joint_rotation(self, i: int, q_i: float) -> SE3:
        return SE3(so3_exp(self.joint_axis[i] * float(q_i)), np.zeros(3))

    def parent_to_link_pose(self, i: int, q_i: float) -> SE3:
        """``T_{p,i}(q)``: pose of link frame ``i`` in the parent link frame."""
        return (
            SE3.from_matrix(self.T_parent_joint[i])
            @ self.joint_rotation(i, q_i)
            @ SE3.from_matrix(self.T_joint_link[i])
        )

    def motion_transform(self, i: int, q_i: float) -> np.ndarray:
        """``X_{i<-p}(q)`` (6x6): parent-frame motion vectors to link-``i`` frame."""
        return self.parent_to_link_pose(i, q_i).inverse().adjoint()

    def link_poses_in_base(self, q: Sequence[float]) -> list[SE3]:
        poses: list[SE3] = []
        for i in range(self.n_links):
            local = self.parent_to_link_pose(i, q[i])
            if self.parent[i] < 0:
                poses.append(local)
            else:
                poses.append(poses[self.parent[i]] @ local)
        return poses

    # ------------------------------------------------------------------ mutation
    def copy(self) -> "ChainModel":
        return replace(
            self,
            parent=self.parent.copy(),
            T_parent_joint=self.T_parent_joint.copy(),
            joint_axis=self.joint_axis.copy(),
            T_joint_link=self.T_joint_link.copy(),
            mass=self.mass.copy(),
            com=self.com.copy(),
            inertia_com=self.inertia_com.copy(),
            armature=self.armature.copy(),
            damping=self.damping.copy(),
            coulomb=self.coulomb.copy(),
            gravity=self.gravity.copy(),
            link_length=None if self.link_length is None else self.link_length.copy(),
            provenance=dict(self.provenance),
        )

    def reparameterize(self, H: Sequence[SE3]) -> tuple["ChainModel", np.ndarray]:
        """Return the same physical chain described in new link frames.

        ``H[i]`` is the pose of the *old* frame ``i`` expressed in the *new* frame
        (contract notation); ``A_i = Ad_{H_i}`` maps old-frame motion vectors to
        new-frame motion vectors. Returns the new model and the stacked adjoints
        ``A`` of shape ``(n, 6, 6)``. The base frame (parent ``-1``) is never changed.
        """
        n = self.n_links
        if len(H) != n:
            raise ValueError("need one H per link")
        new = self.copy()
        adjoints = np.zeros((n, 6, 6))
        for i in range(n):
            h = H[i]
            if not h.is_valid():
                raise ValueError(f"H[{i}] is not a legal SE(3) element")
            adjoints[i] = h.adjoint()
            h_inv = h.inverse()  # pose of new frame in old frame
            # link frame relative to its joint frame
            new.T_joint_link[i] = (SE3.from_matrix(self.T_joint_link[i]) @ h_inv).matrix()
            # inertial parameters expressed in the new frame
            new.com[i] = h.act_point(self.com[i])
            new.inertia_com[i] = h.R @ self.inertia_com[i] @ h.R.T
            # children joints are located relative to the new frame
            for c in self.children(i):
                new.T_parent_joint[c] = (h @ SE3.from_matrix(self.T_parent_joint[c])).matrix()
        new.provenance = dict(self.provenance, reparameterized=True)
        return new, adjoints

    def with_payload(self, mass: float, com_in_last_link: np.ndarray, inertia_com: np.ndarray | None = None) -> "ChainModel":
        """Return a model whose last link carries an additional rigid payload."""
        new = self.copy()
        i = self.n_links - 1
        m0, c0, i0 = self.mass[i], self.com[i], self.inertia_com[i]
        m1 = float(mass)
        c1 = np.asarray(com_in_last_link, dtype=float)
        i1 = np.zeros((3, 3)) if inertia_com is None else np.asarray(inertia_com, dtype=float)
        m = m0 + m1
        c = (m0 * c0 + m1 * c1) / m
        from certo_fdi.geometry.se3 import skew

        d0 = c0 - c
        d1 = c1 - c
        new.mass[i] = m
        new.com[i] = c
        new.inertia_com[i] = (
            i0 + m0 * (skew(d0) @ skew(d0).T) + i1 + m1 * (skew(d1) @ skew(d1).T)
        )
        return new


def make_planar_2r(
    m1: float = 1.2,
    m2: float = 0.8,
    l1: float = 0.5,
    l2: float = 0.4,
    lc1: float = 0.25,
    lc2: float = 0.2,
    I1: float = 0.03,
    I2: float = 0.015,
    gravity: float = 9.81,
    damping: Sequence[float] = (0.0, 0.0),
    coulomb: Sequence[float] = (0.0, 0.0),
    armature: Sequence[float] = (0.0, 0.0),
) -> ChainModel:
    """Planar 2R arm in the x-y plane (gravity along -y), z revolute axes.

    Matches the closed-form Lagrangian oracle ported from Stage 1
    (:mod:`certo_fdi.dynamics.lagrange_reference`).
    """
    eye = np.eye(4)
    t_pj = np.stack([eye, eye.copy()])
    t_pj[1][:3, 3] = [l1, 0.0, 0.0]
    inertia1 = np.diag([1e-12, I1, I1])
    inertia2 = np.diag([1e-12, I2, I2])
    return ChainModel(
        name="planar_2r",
        parent=np.array([-1, 0]),
        T_parent_joint=t_pj,
        joint_axis=np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]),
        T_joint_link=np.stack([eye, eye]),
        mass=np.array([m1, m2]),
        com=np.array([[lc1, 0.0, 0.0], [lc2, 0.0, 0.0]]),
        inertia_com=np.stack([inertia1, inertia2]),
        armature=np.asarray(armature, dtype=float),
        damping=np.asarray(damping, dtype=float),
        coulomb=np.asarray(coulomb, dtype=float),
        gravity=np.array([0.0, -gravity, 0.0]),
        link_length=np.array([l1, l2]),
        joint_names=("j1", "j2"),
        link_names=("link1", "link2"),
    )
