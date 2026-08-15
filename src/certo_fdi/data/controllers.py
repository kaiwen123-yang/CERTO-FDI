"""Joint-space controllers running on the *nominal* model with declared context."""

from __future__ import annotations

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.dynamics.nominal_model import NominalModel

KP_CT = np.array([120.0, 120.0, 100.0, 100.0, 60.0, 40.0, 25.0])
KP_PD = np.array([250.0, 250.0, 200.0, 200.0, 90.0, 60.0, 30.0])
KD_PD = np.array([25.0, 25.0, 20.0, 20.0, 8.0, 5.0, 3.0])


class ComputedTorque:
    name = "computed_torque"

    def __init__(self, chain: ChainModel):
        self.model = NominalModel(chain)
        self.kp = KP_CT[: chain.n_links]
        self.kd = 2.0 * np.sqrt(self.kp)

    def __call__(self, q, qd, q_ref, qd_ref, qdd_ref):
        e = q_ref - q
        ed = qd_ref - qd
        a_cmd = qdd_ref + self.kd * ed + self.kp * e
        return self.model.torque(q, qd, a_cmd)


class PDGravity:
    name = "pd_gravity"

    def __init__(self, chain: ChainModel):
        self.model = NominalModel(chain)
        self.kp = KP_PD[: chain.n_links]
        self.kd = KD_PD[: chain.n_links]

    def __call__(self, q, qd, q_ref, qd_ref, qdd_ref):
        return self.kp * (q_ref - q) + self.kd * (qd_ref - qd) + self.model.gravity(q) + self.model.friction(qd_ref)


def make_controller(name: str, chain: ChainModel):
    if name == "computed_torque":
        return ComputedTorque(chain)
    if name == "pd_gravity":
        return PDGravity(chain)
    raise ValueError(name)
