"""Generalized-momentum observer residual (physics baseline; also an invariant input).

    p = M(q) qd,   r_{k+1} = K_O [ p_{k+1} - p_0 - sum_j (tau_j + C_j^T qd_j - g_j - f_j + r_j) dt ]

computed with the nominal model (Pinocchio backend). ``r`` is a joint-space vector and hence
frame-invariant.
"""

from __future__ import annotations

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.dynamics.rnea import joint_friction_torque


def gmo_residual(chain: ChainModel, q: np.ndarray, qd: np.ndarray, tau: np.ndarray, dt: float, gain: float = 20.0) -> np.ndarray:
    import pinocchio as pin

    from certo_fdi.dynamics.pinocchio_backend import build_pinocchio_model, pin_rnea_includes_armature

    model = build_pinocchio_model(chain)
    data = model.createData()
    inc = pin_rnea_includes_armature(model)
    T, n = q.shape
    r = np.zeros((T, n))
    integ = np.zeros(n)
    arm = chain.armature
    def momentum(k):
        m = pin.crba(model, data, q[k])
        m = np.triu(m) + np.triu(m, 1).T
        if not inc:
            m = m + np.diag(arm)
        return m @ qd[k]
    p0 = momentum(0)
    for k in range(1, T):
        qk, vk = q[k - 1], qd[k - 1]
        c = pin.computeCoriolisMatrix(model, data, qk, vk)
        g = pin.computeGeneralizedGravity(model, data, qk)
        fric = joint_friction_torque(chain, vk)
        integ += (tau[k - 1] + np.asarray(c).T @ vk - np.asarray(g) - fric + r[k - 1]) * dt
        r[k] = gain * (momentum(k) - p0 - integ)
    return r
