"""Typed channels for LiGRA-v2: containers, exact transformation laws, invariant pairings, type
conversions, chain transport and healthy-only invariant normalization.

Types (per link ``i`` with reparameterization ``A_i = Ad_{H_i}``):

* twist channels  ``m in se(3)``:      ``m' = A_i m``
* wrench channels ``f in se(3)^*``:    ``f' = A_i^{-T} f``
* inertia         ``I``:               ``I' = A_i^{-T} I A_i^{-1}``

Everything in this module is exactly covariant/invariant by construction; nothing acts
component-wise on the 6-D vectors.
"""

from __future__ import annotations

import torch
from torch import nn

TWIST_INPUTS: tuple[str, ...] = ("V", "A", "S", "g")  # twists / spatial accelerations / joint subspace / gravity twist
WRENCH_INPUTS: tuple[str, ...] = ("F_body", "F", "I_V", "I_A")  # body wrench, transmitted wrench, momentum, inertial wrench
SCALAR_INPUTS: tuple[str, ...] = ("q", "qd", "qdd_est", "tau_nom")


def sym_upper_indices(k: int, device=None) -> tuple[torch.Tensor, torch.Tensor]:
    iu = torch.triu_indices(k, k, offset=0, device=device)
    return iu[0], iu[1]


def pair_mf(m: torch.Tensor, f: torch.Tensor) -> torch.Tensor:
    """Twist–wrench pairing ``m_a^T f_b``: (..., k, 6) x (..., l, 6) -> (..., k, l). GL(6)-invariant."""
    return torch.einsum("...ki,...li->...kl", m, f)


def gram_I(m: torch.Tensor, I: torch.Tensor, m2: torch.Tensor | None = None) -> torch.Tensor:
    """``m_a^T I m_b`` : (..., k, 6), (..., 6, 6)[, (..., l, 6)] -> (..., k, l)."""
    m2 = m if m2 is None else m2
    return torch.einsum("...ki,...ij,...lj->...kl", m, I, m2)


def gram_Iinv(f: torch.Tensor, I_inv: torch.Tensor, f2: torch.Tensor | None = None) -> torch.Tensor:
    """``f_a^T I^{-1} f_b``."""
    f2 = f if f2 is None else f2
    return torch.einsum("...ki,...ij,...lj->...kl", f, I_inv, f2)


def apply_I(I: torch.Tensor, m: torch.Tensor) -> torch.Tensor:
    """Type conversion twist -> wrench: (..., 6, 6), (..., k, 6) -> (..., k, 6)."""
    return torch.einsum("...ij,...kj->...ki", I, m)


def apply_Iinv(I_inv: torch.Tensor, f: torch.Tensor) -> torch.Tensor:
    """Type conversion wrench -> twist."""
    return torch.einsum("...ij,...kj->...ki", I_inv, f)


def transport_twists(X_i: torch.Tensor, m_parent: torch.Tensor) -> torch.Tensor:
    """Forward motion transport of the parent's twist channels into link ``i``: ``X_{i<-p} m`` (..., k, 6)."""
    return torch.einsum("...ij,...kj->...ki", X_i, m_parent)


def transport_wrenches(X_c: torch.Tensor, f_child: torch.Tensor) -> torch.Tensor:
    """Backward wrench transport of a child's wrench channels into its parent: ``X_{c<-i}^T f`` (..., k, 6)."""
    return torch.einsum("...ji,...kj->...ki", X_c, f_child)


def upper(x: torch.Tensor) -> torch.Tensor:
    """Upper-triangular (incl. diagonal) entries of a symmetric (..., k, k) tensor -> (..., k(k+1)/2)."""
    k = x.shape[-1]
    r, c = sym_upper_indices(k, x.device)
    return x[..., r, c]


class TypedScale(nn.Module):
    """Healthy-only invariant per-channel scales: twists by ``sqrt(E[m^T I m])``, wrenches by
    ``sqrt(E[f^T I^{-1} f])`` (contract 04 §7). Scalars, so covariance is preserved exactly."""

    def __init__(self, n_twist: int, n_wrench: int):
        super().__init__()
        self.register_buffer("twist_scale", torch.ones(n_twist))
        self.register_buffer("wrench_scale", torch.ones(n_wrench))
        self.fitted = False

    @torch.no_grad()
    def fit(self, m: torch.Tensor, f: torch.Tensor, I: torch.Tensor, I_inv: torch.Tensor) -> None:
        """m (N, k_v, 6), f (N, k_f, 6), I/I_inv (N, 6, 6)."""
        tm = torch.einsum("nki,nij,nkj->nk", m.double(), I.double(), m.double()).clamp_min(0).mean(0).sqrt()
        tf = torch.einsum("nki,nij,nkj->nk", f.double(), I_inv.double(), f.double()).clamp_min(0).mean(0).sqrt()
        self.twist_scale.copy_(torch.where(tm < 1e-8, torch.ones_like(tm), tm).to(self.twist_scale.dtype))
        self.wrench_scale.copy_(torch.where(tf < 1e-8, torch.ones_like(tf), tf).to(self.wrench_scale.dtype))
        self.fitted = True

    def forward(self, m: torch.Tensor, f: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return m / self.twist_scale[:, None], f / self.wrench_scale[:, None]


def affine_scan(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Parallel (Hillis–Steele) evaluation of ``h_t = a_t * h_{t-1} + b_t`` with ``h_{-1} = 0`` along axis 1.

    ``a`` (B, T, C) invariant gate scalars, ``b`` (B, T, C, 6) typed candidates. Multiplying a typed
    vector by an invariant scalar and adding typed vectors of the same type are exactly
    equivariant, so the whole recurrence is."""
    T = a.shape[1]
    A = a.unsqueeze(-1)  # (B,T,C,1)
    Bv = b
    d = 1
    while d < T:
        A_shift = torch.cat([torch.ones_like(A[:, :d]), A[:, :-d]], 1)
        B_shift = torch.cat([torch.zeros_like(Bv[:, :d]), Bv[:, :-d]], 1)
        Bv = Bv + A * B_shift
        A = A * A_shift
        d *= 2
    return Bv


__all__ = ["TWIST_INPUTS", "WRENCH_INPUTS", "SCALAR_INPUTS", "pair_mf", "gram_I", "gram_Iinv", "apply_I", "apply_Iinv", "transport_twists", "transport_wrenches", "upper", "TypedScale", "affine_scan"]
