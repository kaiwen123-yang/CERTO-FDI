"""Batched, differentiable typed RNEA front end (Block A of LiGRA) in torch.

Given a :class:`ChainModel` and batched joint states, returns every typed intermediate
quantity with the same conventions as :mod:`certo_fdi.dynamics.rnea`. Numerical agreement
with the NumPy reference (float64) and Pinocchio is part of the R0 gate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.geometry import torch_ops as T


@dataclass
class TorchChain:
    """Tensor view of a ChainModel (constant per model; batch-broadcastable)."""

    n: int
    parent: list[int]
    children: list[list[int]]
    T_pj_R: torch.Tensor  # (n,3,3)
    T_pj_p: torch.Tensor  # (n,3)
    axis: torch.Tensor  # (n,3)
    T_jl_R: torch.Tensor  # (n,3,3)
    T_jl_p: torch.Tensor  # (n,3)
    inertia: torch.Tensor  # (n,6,6)
    S: torch.Tensor  # (n,6)
    armature: torch.Tensor  # (n,)
    damping: torch.Tensor  # (n,)
    coulomb: torch.Tensor  # (n,)
    coulomb_eps: float
    gravity: torch.Tensor  # (3,)
    link_length: torch.Tensor  # (n,)

    @staticmethod
    def from_chain(chain: ChainModel, dtype=torch.float64, device="cpu") -> "TorchChain":
        def t(x):
            return torch.as_tensor(np.asarray(x, dtype=float), dtype=dtype, device=device)

        n = chain.n_links
        return TorchChain(
            n=n,
            parent=[int(p) for p in chain.parent],
            children=[chain.children(i) for i in range(n)],
            T_pj_R=t(chain.T_parent_joint[:, :3, :3]),
            T_pj_p=t(chain.T_parent_joint[:, :3, 3]),
            axis=t(chain.joint_axis),
            T_jl_R=t(chain.T_joint_link[:, :3, :3]),
            T_jl_p=t(chain.T_joint_link[:, :3, 3]),
            inertia=t(chain.spatial_inertias()),
            S=t(chain.motion_subspaces()),
            armature=t(chain.armature),
            damping=t(chain.damping),
            coulomb=t(chain.coulomb),
            coulomb_eps=float(chain.coulomb_eps),
            gravity=t(chain.gravity),
            link_length=t(chain.link_length),
        )

    def to(self, dtype=None, device=None) -> "TorchChain":
        kw = {}
        if dtype is not None:
            kw["dtype"] = dtype
        if device is not None:
            kw["device"] = device
        fields = {}
        for name in ("T_pj_R", "T_pj_p", "axis", "T_jl_R", "T_jl_p", "inertia", "S", "armature", "damping", "coulomb", "gravity", "link_length"):
            fields[name] = getattr(self, name).to(**kw)
        return TorchChain(n=self.n, parent=self.parent, children=self.children, coulomb_eps=self.coulomb_eps, **fields)


@dataclass
class TypedBatch:
    """Batched typed quantities; leading batch shape ``(B,)`` then link axis ``n``."""

    X: torch.Tensor  # (B,n,6,6)
    S: torch.Tensor  # (B,n,6)
    V: torch.Tensor  # (B,n,6)
    A: torch.Tensor  # (B,n,6)
    inertia: torch.Tensor  # (B,n,6,6)
    momentum: torch.Tensor  # (B,n,6)
    F_body: torch.Tensor  # (B,n,6)
    F: torch.Tensor  # (B,n,6)
    tau_rb: torch.Tensor  # (B,n)
    tau: torch.Tensor  # (B,n)
    Xp: torch.Tensor  # (B,n,6,6) X_{i<-p} of link i's parent-side transport helper (identity for base) — same as X
    q: torch.Tensor
    qd: torch.Tensor
    qdd: torch.Tensor


def motion_transforms(tc: TorchChain, q: torch.Tensor) -> torch.Tensor:
    """X_{i<-p}(q) for all links: q (B,n) -> (B,n,6,6)."""
    b = q.shape[0]
    axis = tc.axis.expand(b, tc.n, 3)
    r_joint = T.rot_axis_angle(axis, q)  # (B,n,3,3)
    r_pj = tc.T_pj_R.expand(b, tc.n, 3, 3)
    p_pj = tc.T_pj_p.expand(b, tc.n, 3)
    r_jl = tc.T_jl_R.expand(b, tc.n, 3, 3)
    p_jl = tc.T_jl_p.expand(b, tc.n, 3)
    zero3 = torch.zeros_like(p_pj)
    r1, p1 = T.compose(r_pj, p_pj, r_joint, zero3)
    r_pi, p_pi = T.compose(r1, p1, r_jl, p_jl)  # T_{p,i}(q)
    r_ip, p_ip = T.inverse(r_pi, p_pi)
    return T.adjoint(r_ip, p_ip)


def rnea_batch(
    tc: TorchChain,
    q: torch.Tensor,
    qd: torch.Tensor,
    qdd: torch.Tensor,
    f_ext: torch.Tensor | None = None,
    *,
    mutate_ad_star_sign: bool = False,
    include_joint_terms: bool = True,
) -> TypedBatch:
    b, n = q.shape
    dtype, device = q.dtype, q.device
    X = motion_transforms(tc, q)
    S = tc.S.to(dtype).expand(b, n, 6)
    inertia = tc.inertia.to(dtype).expand(b, n, 6, 6)
    a_base = torch.cat([torch.zeros(3, dtype=dtype, device=device), -tc.gravity.to(dtype)]).expand(b, 6)
    v_list, a_list, h_list, fb_list = [], [], [], []
    for i in range(n):
        p = tc.parent[i]
        v_parent = torch.zeros(b, 6, dtype=dtype, device=device) if p < 0 else v_list[p]
        a_parent = a_base if p < 0 else a_list[p]
        v_joint = S[:, i] * qd[:, i : i + 1]
        v_i = (X[:, i] @ v_parent[..., None])[..., 0] + v_joint
        a_i = (X[:, i] @ a_parent[..., None])[..., 0] + S[:, i] * qdd[:, i : i + 1] + (T.ad(v_i) @ v_joint[..., None])[..., 0]
        h_i = (inertia[:, i] @ v_i[..., None])[..., 0]
        fb_i = (inertia[:, i] @ a_i[..., None])[..., 0] + (T.ad_star(v_i, mutate_sign=mutate_ad_star_sign) @ h_i[..., None])[..., 0]
        if f_ext is not None:
            fb_i = fb_i - f_ext[:, i]
        v_list.append(v_i)
        a_list.append(a_i)
        h_list.append(h_i)
        fb_list.append(fb_i)
    f_list = list(fb_list)
    tau_rb = [None] * n
    for i in range(n - 1, -1, -1):
        tau_rb[i] = (S[:, i] * f_list[i]).sum(-1)
        p = tc.parent[i]
        if p >= 0:
            f_list[p] = f_list[p] + (X[:, i].transpose(-1, -2) @ f_list[i][..., None])[..., 0]
    tau_rb_t = torch.stack(tau_rb, dim=1)
    tau = tau_rb_t
    if include_joint_terms:
        tau = tau + tc.armature.to(dtype) * qdd + tc.damping.to(dtype) * qd + tc.coulomb.to(dtype) * torch.tanh(qd / tc.coulomb_eps)
    return TypedBatch(
        X=X, S=S, V=torch.stack(v_list, 1), A=torch.stack(a_list, 1), inertia=inertia,
        momentum=torch.stack(h_list, 1), F_body=torch.stack(fb_list, 1), F=torch.stack(f_list, 1),
        tau_rb=tau_rb_t, tau=tau, Xp=X, q=q, qd=qd, qdd=qdd,
    )


def transport_child_wrench(X_child: torch.Tensor, F_child: torch.Tensor) -> torch.Tensor:
    """Exact coadjoint transport of a child wrench-type message into the parent frame.

    ``X_child = X_{c<-i}`` (B,6,6); returns ``X_{c<-i}^T F_c`` (B,6) — the contract's
    ``X_{i<-c}^{-T} F_c``.
    """
    return (X_child.transpose(-1, -2) @ F_child[..., None])[..., 0]
