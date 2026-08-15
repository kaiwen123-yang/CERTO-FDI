"""Invariant scalar features (LiGRA input) and raw typed features (chain-GNN input).

Every invariant feature is documented with its unit and its transformation type
(all SCALAR under link-frame reparameterization). Raw features carry their spatial type
and are *not* invariant — they exist only for the non-equivariant baselines.
"""

from __future__ import annotations

import torch

from certo_fdi.dynamics.rnea_torch import TorchChain, TypedBatch
from certo_fdi.geometry import torch_ops as T

# NOTE: measured/commanded torque is deliberately NOT an input of the healthy correction
# (its target is tau_meas - tau_nom; including tau_meas would let the network copy the
# residual and explain faults away). Torque measurements enter only the anomaly stage.
INVARIANT_FEATURES: list[tuple[str, str]] = [
    # (name, unit) — all transform as SCALAR
    ("q", "rad"),
    ("qd", "rad/s"),
    ("qdd_est", "rad/s^2"),
    ("tau_nom", "N m"),
    ("V_I_V", "J (2x kinetic energy)"),
    ("A_I_A", "kg m^2/s^4"),
    ("V_I_A", "W"),
    ("S_I_S", "kg m^2"),
    ("S_Fbody", "N m"),
    ("S_F", "N m"),
    ("V_F", "W"),
    ("F_Iinv_F", "kg m^2/s^4"),
    ("omega_sq", "rad^2/s^2"),
    ("omegadot_sq", "rad^2/s^4"),
    ("f_sq", "N^2"),
    ("fbody_sq", "N^2"),
    ("Vp_I_Vp", "J (parent twist transported)"),
    ("g_I_g", "kg m^2/s^4 (gravity twist energy)"),
]
LINK_PHYSICAL_FEATURES: list[tuple[str, str]] = [
    ("mass", "kg"),
    ("principal_inertia_1", "kg m^2"),
    ("principal_inertia_2", "kg m^2"),
    ("principal_inertia_3", "kg m^2"),
    ("axis_inertia_S_I_S", "kg m^2"),
    ("com_to_axis_distance", "m"),
    ("armature", "kg m^2"),
    ("link_length", "m"),
]


def _quad(v: torch.Tensor, m: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
    """v^T M w for (...,6),(...,6,6),(...,6)."""
    return (v[..., None, :] @ m @ w[..., :, None])[..., 0, 0]


def base_gravity_twist(tc: TorchChain, X: torch.Tensor) -> torch.Tensor:
    """Gravity as a motion vector ``[0; g]`` transported from the base into every link frame."""
    b, n = X.shape[0], X.shape[1]
    g6 = torch.cat([torch.zeros(3, dtype=X.dtype, device=X.device), tc.gravity.to(X.dtype)])
    out = []
    for i in range(n):
        p = tc.parent[i]
        parent_g = g6.expand(b, 6) if p < 0 else out[p]
        out.append((X[:, i] @ parent_g[..., None])[..., 0])
    return torch.stack(out, 1)


def parent_twists(tc: TorchChain, tb: TypedBatch) -> torch.Tensor:
    """X_{i<-p} V_p (parent twist expressed in link i), zeros for base children."""
    b, n = tb.V.shape[0], tb.V.shape[1]
    out = []
    for i in range(n):
        p = tc.parent[i]
        vp = torch.zeros(b, 6, dtype=tb.V.dtype, device=tb.V.device) if p < 0 else tb.V[:, p]
        out.append((tb.X[:, i] @ vp[..., None])[..., 0])
    return torch.stack(out, 1)


def link_physical_features(tc: TorchChain) -> torch.Tensor:
    """(n, 8) invariant physical descriptors used instead of a free link one-hot."""
    n = tc.n
    I = tc.inertia  # (n,6,6)
    mass = I[:, 5, 5]
    # rotational inertia about the CoM: I_c = I_rot - m c^ c^T with c^ = I[:3,3:]/m
    c_skew = I[:, :3, 3:] / mass[:, None, None]
    ic = I[:, :3, :3] - mass[:, None, None] * (c_skew @ c_skew.transpose(-1, -2))
    eig = torch.linalg.eigvalsh((ic + ic.transpose(-1, -2)) / 2)
    s_i_s = _quad(tc.S, I, tc.S)
    w = tc.S[:, :3]
    v = tc.S[:, 3:]
    p0 = torch.cross(w, v, dim=-1)  # point on the axis closest to the origin (unit w)
    com = torch.stack([c_skew[:, 2, 1], c_skew[:, 0, 2], c_skew[:, 1, 0]], -1)
    dist = torch.linalg.norm(torch.cross(w, com - p0, dim=-1), dim=-1)
    return torch.stack([mass, eig[:, 0], eig[:, 1], eig[:, 2], s_i_s, dist, tc.armature, tc.link_length], -1)


def invariant_features(tc: TorchChain, tb: TypedBatch, tau_nom: torch.Tensor) -> torch.Tensor:
    """(B, n, len(INVARIANT_FEATURES)) invariant scalars (no measured torque; see note above)."""
    I = tb.inertia
    I_inv = torch.linalg.inv(I)
    Vp = parent_twists(tc, tb)
    g = base_gravity_twist(tc, tb.X)
    feats = [
        tb.q, tb.qd, tb.qdd, tau_nom,
        _quad(tb.V, I, tb.V), _quad(tb.A, I, tb.A), _quad(tb.V, I, tb.A), _quad(tb.S, I, tb.S),
        (tb.S * tb.F_body).sum(-1), (tb.S * tb.F).sum(-1), (tb.V * tb.F).sum(-1), _quad(tb.F, I_inv, tb.F),
        (tb.V[..., :3] ** 2).sum(-1), (tb.A[..., :3] ** 2).sum(-1), (tb.F[..., 3:] ** 2).sum(-1), (tb.F_body[..., 3:] ** 2).sum(-1),
        _quad(Vp, I, Vp), _quad(g, I, g),
    ]
    return torch.stack(feats, -1)


# Stage 1R-B matched-input manifest (contract 04 §1 / master B1): the non-equivariant chain GNN and
# LiGRA-v2 receive exactly the same physical fields — the GNN as raw components, LiGRA-v2 by type.
RAW_TWIST_FIELDS = ("V", "A", "S", "g")
RAW_WRENCH_FIELDS = ("F_body", "F", "I_V", "I_A")
RAW_SCALAR_FIELDS = ("q", "qd", "qdd_est", "tau_nom")
RAW_FEATURE_DIM = 6 * (len(RAW_TWIST_FIELDS) + len(RAW_WRENCH_FIELDS)) + len(RAW_SCALAR_FIELDS)  # 52 (no measured torque)


def raw_features(tc: TorchChain, tb: TypedBatch, tau_nom: torch.Tensor) -> torch.Tensor:
    """(B, n, RAW_FEATURE_DIM) raw components in the current link frames (NOT invariant):
    twists V, A, S, g; wrenches F_body, F, I V, I A; scalars q, qd, qdd_est, tau_nom."""
    g = base_gravity_twist(tc, tb.X)
    IA = (tb.inertia @ tb.A[..., None])[..., 0]
    return torch.cat([tb.V, tb.A, tb.S, g, tb.F_body, tb.F, tb.momentum, IA, tb.q[..., None], tb.qd[..., None], tb.qdd[..., None], tau_nom[..., None]], -1)


def raw_input_field_manifest() -> dict[str, list[str]]:
    from certo_fdi.data.windows import MODEL_CONTEXT_NAMES

    return {"scalars": list(RAW_SCALAR_FIELDS), "twists": list(RAW_TWIST_FIELDS), "wrenches": list(RAW_WRENCH_FIELDS), "context": list(MODEL_CONTEXT_NAMES), "link_descriptors": [n for n, _ in LINK_PHYSICAL_FEATURES], "processing": "raw components in the current link frames (non-equivariant)"}
