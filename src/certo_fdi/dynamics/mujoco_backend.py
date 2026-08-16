"""MuJoCo truth-simulator backend and machine-readable model audit for the 7-DoF arm.

The MJCF from MuJoCo Menagerie (``franka_emika_panda/panda_nohand.xml``) is loaded through
``mujoco.MjSpec`` and *derived* deterministically:

* all built-in position actuators are removed (torques are applied directly to
  ``data.qfrc_applied``);
* all geoms are made non-colliding (free-space protocol; contact faults are injected as
  explicit external wrenches through ``data.xfrc_applied``);
* joint damping is moved out of the MJCF and applied explicitly by the friction model of
  the plant so that every friction term is visible, loggable and faultable.

``chain_from_mujoco`` extracts the kinematic/inertial parameters into a
:class:`~certo_fdi.dynamics.chain_model.ChainModel` for the analytic RNEA branch.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.geometry.se3 import SE3, quat_to_rot

PANDA_TORQUE_LIMITS = np.array([87.0, 87.0, 87.0, 87.0, 12.0, 12.0, 12.0])
PANDA_VELOCITY_LIMITS = np.array([2.175, 2.175, 2.175, 2.175, 2.61, 2.61, 2.61])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_derived_spec(xml_path: str | Path, *, keep_damping: bool = False):
    """Load the Menagerie MJCF and derive the free-space torque-controlled variant."""
    import mujoco

    spec = mujoco.MjSpec.from_file(str(xml_path))
    for actuator in list(spec.actuators):
        spec.delete(actuator)
    for geom in spec.geoms:
        geom.contype = 0
        geom.conaffinity = 0
    # Joint damping is zeroed on the compiled model (see compile_model); the MjSpec joint
    # damping attribute is class-inherited and not reliably writable across versions.
    # No keyframes referencing ctrl (actuators removed).
    for key in list(spec.keys):
        spec.delete(key)
    return spec


def compile_model(xml_path: str | Path, *, keep_damping: bool = False):
    spec = load_derived_spec(xml_path, keep_damping=keep_damping)
    model = spec.compile()
    if not keep_damping:
        model.dof_damping[:] = 0.0
    return model


def _fixed_body_merge(model, body_id: int, joint_body_ids: set[int]) -> list[int]:
    """Return the ids of fixed (jointless) descendant bodies welded to ``body_id``."""
    merged = []
    stack = [body_id]
    while stack:
        b = stack.pop()
        for c in range(model.nbody):
            if model.body_parentid[c] == c:
                continue
            if model.body_parentid[c] == b and c != b:
                if c in joint_body_ids:
                    continue
                if model.body_jntnum[c] == 0:
                    merged.append(c)
                    stack.append(c)
    return merged


def chain_from_mujoco(model, name: str = "franka_emika_panda", *, torque_limits: np.ndarray | None = None) -> ChainModel:
    """Extract a ChainModel (canonical link frames = MuJoCo body frames) from an MjModel."""
    import mujoco

    joint_ids = [j for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE]
    if len(joint_ids) != model.njnt:
        raise ValueError("only hinge joints are supported")
    joint_body = [int(model.jnt_bodyid[j]) for j in joint_ids]
    joint_body_set = set(joint_body)
    body_to_link = {b: k for k, b in enumerate(joint_body)}
    n = len(joint_ids)

    parent = np.full(n, -1)
    t_pj = np.zeros((n, 4, 4))
    axes = np.zeros((n, 3))
    t_jl = np.zeros((n, 4, 4))
    mass = np.zeros(n)
    com = np.zeros((n, 3))
    inertia_com = np.zeros((n, 3, 3))
    link_names = []
    joint_names = []
    lower = np.zeros(n)
    upper = np.zeros(n)

    for k, (j, b) in enumerate(zip(joint_ids, joint_body)):
        # walk up through fixed bodies to the nearest jointed ancestor
        pb = int(model.body_parentid[b])
        t_chain = SE3.from_quat_pos(model.body_quat[b], model.body_pos[b])
        while pb != 0 and pb not in joint_body_set:
            t_chain = SE3.from_quat_pos(model.body_quat[pb], model.body_pos[pb]) @ t_chain
            pb = int(model.body_parentid[pb])
        parent[k] = -1 if pb == 0 else body_to_link[pb]
        jpos = np.array(model.jnt_pos[j], dtype=float)
        jaxis = np.array(model.jnt_axis[j], dtype=float)
        jaxis /= np.linalg.norm(jaxis)
        t_pj[k] = (t_chain @ SE3(np.eye(3), jpos)).matrix()
        axes[k] = jaxis
        t_jl[k] = SE3(np.eye(3), -jpos).matrix()
        # inertial parameters: body plus welded fixed descendants
        m_total = float(model.body_mass[b])
        c_total = m_total * np.array(model.body_ipos[b], dtype=float)
        parts = [(b, SE3.identity())]
        for fb in _fixed_body_merge(model, b, joint_body_set):
            # pose of fixed body fb in body b
            chain_ids = []
            x = fb
            while x != b:
                chain_ids.append(x)
                x = int(model.body_parentid[x])
            t = SE3.identity()
            for x in reversed(chain_ids):
                t = t @ SE3.from_quat_pos(model.body_quat[x], model.body_pos[x])
            parts.append((fb, t))
            m_total += float(model.body_mass[fb])
            c_total += float(model.body_mass[fb]) * t.act_point(model.body_ipos[fb])
        c_total = c_total / m_total if m_total > 0 else np.zeros(3)
        ic = np.zeros((3, 3))
        from certo_fdi.geometry.se3 import skew

        for pid, t in parts:
            m_p = float(model.body_mass[pid])
            r_i = quat_to_rot(model.body_iquat[pid])
            i_p = r_i @ np.diag(model.body_inertia[pid]) @ r_i.T
            i_p = t.R @ i_p @ t.R.T
            d = t.act_point(model.body_ipos[pid]) - c_total
            ic += i_p + m_p * (skew(d) @ skew(d).T)
        mass[k] = m_total
        com[k] = c_total
        inertia_com[k] = ic
        link_names.append(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, b))
        joint_names.append(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j))
        if model.jnt_limited[j]:
            lower[k], upper[k] = model.jnt_range[j]
        else:
            lower[k], upper[k] = -np.pi, np.pi

    dof_of_joint = [int(model.jnt_dofadr[j]) for j in joint_ids]
    armature = np.array([model.dof_armature[d] for d in dof_of_joint], dtype=float)
    damping = np.array([model.dof_damping[d] for d in dof_of_joint], dtype=float)
    return ChainModel(
        name=name,
        parent=parent,
        T_parent_joint=t_pj,
        joint_axis=axes,
        T_joint_link=t_jl,
        mass=mass,
        com=com,
        inertia_com=inertia_com,
        armature=armature,
        damping=damping,
        coulomb=np.zeros(n),
        gravity=np.array(model.opt.gravity, dtype=float),
        joint_names=tuple(joint_names),
        link_names=tuple(link_names),
        joint_lower=lower,
        joint_upper=upper,
        velocity_limit=PANDA_VELOCITY_LIMITS[:n] if n == 7 else None,
        torque_limit=(PANDA_TORQUE_LIMITS if torque_limits is None else np.asarray(torque_limits)) if n == 7 else None,
        provenance={"source": "mujoco", "nbody": int(model.nbody), "njnt": int(model.njnt)},
    )


def model_parameter_audit(model, chain: ChainModel, xml_path: str | Path) -> dict:
    """Machine-readable audit of joint ordering, gravity, inertias, and conventions."""
    import mujoco

    audit = {
        "mjcf_path": str(xml_path),
        "mjcf_sha256": sha256_file(Path(xml_path)),
        "mujoco_version": mujoco.__version__,
        "gravity": chain.gravity.tolist(),
        "timestep_default": float(model.opt.timestep),
        "integrator": int(model.opt.integrator),
        "n_links": chain.n_links,
        "joint_names": list(chain.joint_names),
        "link_names": list(chain.link_names),
        "joint_order_matches_mujoco_dof_order": bool(
            all(model.jnt_dofadr[j] == j for j in range(model.njnt))
        ),
        "joint_axes_in_joint_frame": chain.joint_axis.tolist(),
        "joint_lower": chain.joint_lower.tolist(),
        "joint_upper": chain.joint_upper.tolist(),
        "armature": chain.armature.tolist(),
        "mjcf_damping_removed_from_model": bool(np.allclose(model.dof_damping, 0.0)),
        "actuators_removed": int(model.nu) == 0,
        "collisions_disabled": bool(np.all(model.geom_contype == 0) and np.all(model.geom_conaffinity == 0)),
        "mass_kg": chain.mass.tolist(),
        "total_mass_kg": float(chain.mass.sum()),
        "com_link_frame_m": chain.com.tolist(),
        "inertia_com_link_frame_kgm2": chain.inertia_com.tolist(),
        "spatial_convention": "motion=[omega;v], wrench=[n;f], ad*=-ad^T, X_{i<-p}=Ad(T_{p,i})^{-1}",
        "torque_limits_nm": None if chain.torque_limit is None else chain.torque_limit.tolist(),
        "velocity_limits_rad_s": None if chain.velocity_limit is None else chain.velocity_limit.tolist(),
    }
    return audit


@dataclass
class PlantParams:
    """Truth-plant parameters that may differ from the nominal analytic model."""

    viscous: np.ndarray  # (n,) N m s/rad
    coulomb: np.ndarray  # (n,) N m
    stribeck: np.ndarray  # (n,) additional static friction N m (truth only)
    stribeck_velocity: float = 0.1  # rad/s
    coulomb_eps: float = 0.02  # rad/s tanh smoothing
    actuator_gain: np.ndarray | None = None  # (n,) multiplicative torque efficiency

    def friction_torque(self, qd: np.ndarray) -> np.ndarray:
        qd = np.asarray(qd, dtype=float)
        sgn = np.tanh(qd / self.coulomb_eps)
        stribeck = self.stribeck * np.exp(-((qd / self.stribeck_velocity) ** 2)) * sgn
        return self.viscous * qd + self.coulomb * sgn + stribeck


class MujocoPlant:
    """Torque-controlled fixed-base arm truth simulator."""

    def __init__(self, xml_path: str | Path, *, timestep: float = 0.001):
        import mujoco

        self.xml_path = Path(xml_path)
        self.model = compile_model(self.xml_path)
        self.model.opt.timestep = timestep
        self.data = mujoco.MjData(self.model)
        self.n = self.model.nv
        self.chain = chain_from_mujoco(self.model)
        self._mujoco = mujoco
        self.link_body_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, name) for name in self.chain.link_names
        ]

    # -------------------------------------------------------------- state access
    def reset(self, q: np.ndarray, qd: np.ndarray | None = None) -> None:
        self._mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = np.asarray(q, dtype=float)
        self.data.qvel[:] = 0.0 if qd is None else np.asarray(qd, dtype=float)
        self.data.qacc[:] = 0.0
        self._mujoco.mj_forward(self.model, self.data)

    @property
    def q(self) -> np.ndarray:
        return np.array(self.data.qpos, dtype=float)

    @property
    def qd(self) -> np.ndarray:
        return np.array(self.data.qvel, dtype=float)

    @property
    def qdd(self) -> np.ndarray:
        return np.array(self.data.qacc, dtype=float)

    # -------------------------------------------------------------- dynamics
    def inverse_dynamics(self, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> np.ndarray:
        """Rigid-body inverse dynamics (with armature) from MuJoCo ``mj_inverse``."""
        self.data.qpos[:] = q
        self.data.qvel[:] = qd
        self.data.qacc[:] = qdd
        self.data.qfrc_applied[:] = 0.0
        self.data.xfrc_applied[:] = 0.0
        self._mujoco.mj_inverse(self.model, self.data)
        return np.array(self.data.qfrc_inverse, dtype=float)

    def mass_matrix(self, q: np.ndarray) -> np.ndarray:
        self.data.qpos[:] = q
        self._mujoco.mj_forward(self.model, self.data)
        m = np.zeros((self.n, self.n))
        try:
            self._mujoco.mj_fullM(self.model, self.data, m)  # mujoco >= 3.4 signature
        except TypeError:  # pragma: no cover - older bindings
            self._mujoco.mj_fullM(self.model, m, self.data.qM)
        return m

    def link_pose_world(self, link_index: int) -> SE3:
        b = self.link_body_ids[link_index]
        return SE3(np.array(self.data.xmat[b]).reshape(3, 3), np.array(self.data.xpos[b]))

    def step(
        self,
        tau_applied: np.ndarray,
        *,
        link_wrench_world: dict[int, np.ndarray] | None = None,
    ) -> None:
        """Advance one physics step with joint torques and optional world-frame link wrenches.

        ``link_wrench_world[i]`` is a 6-vector ``[force(3); torque(3)]`` (MuJoCo xfrc order)
        applied at the body frame origin of link ``i`` and expressed in the world frame.
        """
        self.data.qfrc_applied[:] = np.asarray(tau_applied, dtype=float)
        self.data.xfrc_applied[:] = 0.0
        if link_wrench_world:
            for i, w in link_wrench_world.items():
                self.data.xfrc_applied[self.link_body_ids[i]] = np.asarray(w, dtype=float)
        self._mujoco.mj_step(self.model, self.data)

    def payload_variant(self, mass: float, com: np.ndarray, inertia_com: np.ndarray | None = None) -> None:
        """Attach a rigid payload to the last link (modifies the truth model in place)."""
        import mujoco

        b = self.link_body_ids[-1]
        m0 = float(self.model.body_mass[b])
        c0 = np.array(self.model.body_ipos[b], dtype=float)
        r0 = quat_to_rot(self.model.body_iquat[b])
        i0 = r0 @ np.diag(self.model.body_inertia[b]) @ r0.T
        m1 = float(mass)
        c1 = np.asarray(com, dtype=float)
        i1 = np.zeros((3, 3)) if inertia_com is None else np.asarray(inertia_com, dtype=float)
        m = m0 + m1
        c = (m0 * c0 + m1 * c1) / m
        from certo_fdi.geometry.se3 import skew

        d0, d1 = c0 - c, c1 - c
        ic = i0 + m0 * skew(d0) @ skew(d0).T + i1 + m1 * skew(d1) @ skew(d1).T
        w, v = np.linalg.eigh(ic)
        if np.linalg.det(v) < 0:
            v[:, 0] *= -1
        quat = np.zeros(4)
        mujoco.mju_mat2Quat(quat, v.reshape(-1))
        self.model.body_mass[b] = m
        self.model.body_ipos[b] = c
        self.model.body_inertia[b] = w
        self.model.body_iquat[b] = quat
        self.recompute_constants()
        self.chain = chain_from_mujoco(self.model)

    def recompute_constants(self) -> None:
        """Recompute derived model constants without disturbing the simulation state.

        ``mj_setConst`` evaluates the model at ``qpos0`` using ``data`` as scratch space and
        would otherwise reset the state mid-episode.
        """
        d = self.data
        saved = (d.time, d.qpos.copy(), d.qvel.copy(), d.qacc.copy(), d.qfrc_applied.copy(), d.xfrc_applied.copy(), d.act.copy() if d.act.size else None)
        self._mujoco.mj_setConst(self.model, d)
        d.time = saved[0]
        d.qpos[:] = saved[1]
        d.qvel[:] = saved[2]
        d.qacc[:] = saved[3]
        d.qfrc_applied[:] = saved[4]
        d.xfrc_applied[:] = saved[5]
        if saved[6] is not None:
            d.act[:] = saved[6]
        self._mujoco.mj_forward(self.model, d)


def write_audit(audit: dict, path: Path) -> None:
    Path(path).write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
