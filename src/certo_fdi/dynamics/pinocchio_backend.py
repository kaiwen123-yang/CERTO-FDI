"""Pinocchio analytic backend used as the *independent* RNEA cross-check.

Two construction paths are provided:

* :func:`build_pinocchio_model` — programmatic construction from a
  :class:`~certo_fdi.dynamics.chain_model.ChainModel` (parameters that were read from the
  MuJoCo model), so that Pinocchio's RNEA/CRBA can be compared with the reference
  implementation on *identical* parameters;
* :func:`build_pinocchio_model_from_mjcf` — Pinocchio's own MJCF parser (when available),
  used only for the parameter-parsing audit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.geometry.se3 import SE3


def build_pinocchio_model(chain: ChainModel):
    import pinocchio as pin

    model = pin.Model()
    model.name = chain.name
    model.gravity.linear = np.asarray(chain.gravity, dtype=float)
    joint_ids: list[int] = []
    for i in range(chain.n_links):
        p = chain.parent[i]
        parent_joint = 0 if p < 0 else joint_ids[p]
        # placement of joint i frame in the parent's pinocchio joint frame
        if p < 0:
            placement_matrix = chain.T_parent_joint[i]
        else:
            placement_matrix = (SE3.from_matrix(chain.T_joint_link[p]) @ SE3.from_matrix(chain.T_parent_joint[i])).matrix()
        placement = pin.SE3(np.ascontiguousarray(placement_matrix[:3, :3]), np.ascontiguousarray(placement_matrix[:3, 3]))
        joint_model = pin.JointModelRevoluteUnaligned(np.asarray(chain.joint_axis[i], dtype=float))
        name = chain.joint_names[i] if chain.joint_names else f"joint{i + 1}"
        jid = model.addJoint(parent_joint, joint_model, placement, name)
        joint_ids.append(jid)
        body_placement_matrix = chain.T_joint_link[i]
        body_placement = pin.SE3(
            np.ascontiguousarray(body_placement_matrix[:3, :3]),
            np.ascontiguousarray(body_placement_matrix[:3, 3]),
        )
        inertia = pin.Inertia(float(chain.mass[i]), np.asarray(chain.com[i], dtype=float), np.asarray(chain.inertia_com[i], dtype=float))
        model.appendBodyToJoint(jid, inertia, body_placement)
    if hasattr(model, "armature"):
        model.armature = np.asarray(chain.armature, dtype=float)
    return model


def pin_rnea(model, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> np.ndarray:
    import pinocchio as pin

    data = model.createData()
    tau = pin.rnea(model, data, np.asarray(q, dtype=float), np.asarray(qd, dtype=float), np.asarray(qdd, dtype=float))
    return np.array(tau, dtype=float)


def pin_crba(model, q: np.ndarray) -> np.ndarray:
    import pinocchio as pin

    data = model.createData()
    m = pin.crba(model, data, np.asarray(q, dtype=float))
    m = np.array(m, dtype=float)
    return np.triu(m) + np.triu(m, 1).T


def pin_rnea_includes_armature(model) -> bool:
    """Empirically determine whether this Pinocchio build adds ``armature * qdd`` in rnea."""
    import pinocchio as pin

    if not hasattr(model, "armature"):
        return False
    q = pin.neutral(model)
    n = model.nv
    a = np.zeros(n)
    a[0] = 1.0
    data = model.createData()
    saved = np.array(model.armature, dtype=float)
    model.armature = np.zeros(n)
    tau0 = np.array(pin.rnea(model, data, q, np.zeros(n), a), dtype=float)
    model.armature = np.ones(n)
    tau1 = np.array(pin.rnea(model, data, q, np.zeros(n), a), dtype=float)
    model.armature = saved
    return bool(abs((tau1 - tau0)[0] - 1.0) < 1e-9)


def build_pinocchio_model_from_mjcf(xml_path: str | Path):
    import pinocchio as pin

    return pin.buildModelFromMJCF(str(xml_path))


def pinocchio_version() -> str:
    try:
        import pinocchio as pin

        return str(pin.__version__)
    except Exception:  # pragma: no cover
        return "NOT_INSTALLED"
