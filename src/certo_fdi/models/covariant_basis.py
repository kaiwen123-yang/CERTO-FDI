"""Covariant wrench basis ``B_i`` (Block C): every column transforms as ``B' = A^{-T} B``.

Columns (all wrench-type by construction):
 0  I A            inertial wrench
 1  ad*_V I V      gyroscopic wrench
 2  I S            joint-axis inertia wrench
 3  I V            spatial momentum
 4  F_body         nominal net body wrench
 5  F              nominal transmitted wrench
 6  I (X V_p)      inertia applied to the transported parent twist
 7  I (X A_p)      inertia applied to the transported parent acceleration
 8  ad*_V I S
 9  ad*_S I V
10  I ad_V S
11  I (X_{i<-0} g) gravity-direction wrench
(12) sum_c X_{c<-i}^T dF_c  transported learned child messages (added by the chain model)
"""

from __future__ import annotations

import torch

from certo_fdi.dynamics.rnea_torch import TorchChain, TypedBatch
from certo_fdi.geometry import torch_ops as T
from certo_fdi.models.features import base_gravity_twist

BASIS_NAMES = ["I_A", "adstar_V_IV", "I_S", "I_V", "F_body", "F", "I_XVp", "I_XAp", "adstar_V_IS", "adstar_S_IV", "I_adV_S", "I_Xg"]
ANALYTIC_BASIS_DIM = len(BASIS_NAMES)


def covariant_basis(tc: TorchChain, tb: TypedBatch) -> torch.Tensor:
    """(B, n, 6, ANALYTIC_BASIS_DIM) analytic wrench-covariant columns."""
    I = tb.inertia
    b, n = tb.V.shape[0], tb.V.shape[1]
    mv = lambda m, v: (m @ v[..., None])[..., 0]
    g = base_gravity_twist(tc, tb.X)
    Vp = []
    Ap = []
    a_base = torch.cat([torch.zeros(3, dtype=tb.V.dtype, device=tb.V.device), -tc.gravity.to(tb.V.dtype)]).expand(b, 6)
    for i in range(n):
        p = tc.parent[i]
        vp = torch.zeros(b, 6, dtype=tb.V.dtype, device=tb.V.device) if p < 0 else tb.V[:, p]
        ap = a_base if p < 0 else tb.A[:, p]
        Vp.append(mv(tb.X[:, i], vp))
        Ap.append(mv(tb.X[:, i], ap))
    Vp = torch.stack(Vp, 1)
    Ap = torch.stack(Ap, 1)
    ad_v = T.ad(tb.V)
    adstar_v = T.ad_star(tb.V)
    adstar_s = T.ad_star(tb.S)
    cols = [
        mv(I, tb.A),
        mv(adstar_v, tb.momentum),
        mv(I, tb.S),
        tb.momentum,
        tb.F_body,
        tb.F,
        mv(I, Vp),
        mv(I, Ap),
        mv(adstar_v, mv(I, tb.S)),
        mv(adstar_s, tb.momentum),
        mv(I, mv(ad_v, tb.S)),
        mv(I, g),
    ]
    return torch.stack(cols, -1)
