"""Exactly equivariant typed layers for LiGRA-v2 (contract 04 §3).

Allowed operations only:

* type-internal linear mixing with *invariant* scalar coefficients,
* type conversion through the spatial inertia ``I`` (twist -> wrench) and ``I^{-1}`` (wrench -> twist),
* invariant scalars: ``m^T f``, ``m^T I m'``, ``f^T I^{-1} f'`` and joint/context scalars,
* chain transport ``X_{i<-p}`` (twists, forward) and ``X_{c<-i}^T`` (wrenches, backward).

No component-wise activation or normalization ever touches a 6-D typed component; every
non-linearity lives in scalar networks that consume invariants and emit invariant coefficients.
"""

from __future__ import annotations

import torch
from torch import nn

from certo_fdi.models.typed_channels import apply_I, apply_Iinv, gram_I, gram_Iinv, pair_mf, upper


class InputInvariants(nn.Module):
    """All pairwise invariants of the typed *inputs* of one link at one time:
    ``upper(m I m^T)`` (k_v(k_v+1)/2), ``upper(f I^{-1} f^T)`` (k_f(k_f+1)/2), ``m f^T`` (k_v k_f)."""

    def __init__(self, n_twist: int, n_wrench: int):
        super().__init__()
        self.n_twist, self.n_wrench = n_twist, n_wrench
        self.dim = n_twist * (n_twist + 1) // 2 + n_wrench * (n_wrench + 1) // 2 + n_twist * n_wrench

    def forward(self, m: torch.Tensor, f: torch.Tensor, I: torch.Tensor, I_inv: torch.Tensor) -> torch.Tensor:
        b = m.shape[:-2]
        return torch.cat([upper(gram_I(m, I)), upper(gram_Iinv(f, I_inv)), pair_mf(m, f).reshape(*b, -1)], -1)


class TypedMixer(nn.Module):
    """Emit invariant mixing coefficients from a scalar hidden state and apply them to a stack of
    same-type source channels: ``u_k = sum_l c_kl(h) src_l`` (k = 1..out_channels).

    ``coeff_scale`` bounds nothing; the coefficients are plain linear read-outs (as in LiGRA-v1)."""

    def __init__(self, scalar_dim: int, n_sources: int, out_channels: int):
        super().__init__()
        self.n_sources, self.out_channels = n_sources, out_channels
        self.coeff = nn.Linear(scalar_dim, out_channels * n_sources)
        nn.init.zeros_(self.coeff.bias)
        with torch.no_grad():
            self.coeff.weight.mul_(0.1)

    def forward(self, h: torch.Tensor, sources: torch.Tensor) -> torch.Tensor:
        """h (..., D), sources (..., n_sources, 6) -> (..., out_channels, 6)."""
        c = self.coeff(h).reshape(*h.shape[:-1], self.out_channels, self.n_sources)
        return torch.einsum("...kl,...li->...ki", c, sources)


def twist_sources(m_in: torch.Tensor, f_in: torch.Tensor, I_inv: torch.Tensor, extra: torch.Tensor | None = None) -> torch.Tensor:
    """Stack of twist-type sources: input twists, converted input wrenches ``I^{-1} f``, and extra twists."""
    parts = [m_in, apply_Iinv(I_inv, f_in)]
    if extra is not None:
        parts.append(extra)
    return torch.cat(parts, -2)


def wrench_sources(m_in: torch.Tensor, f_in: torch.Tensor, I: torch.Tensor, extra: torch.Tensor | None = None) -> torch.Tensor:
    """Stack of wrench-type sources: input wrenches, converted input twists ``I m``, and extra wrenches."""
    parts = [f_in, apply_I(I, m_in)]
    if extra is not None:
        parts.append(extra)
    return torch.cat(parts, -2)


class InvariantGate(nn.Module):
    """Sigmoid gates (one invariant scalar per typed channel) from the scalar hidden state."""

    def __init__(self, scalar_dim: int, channels: int, bias_init: float = 1.0):
        super().__init__()
        self.lin = nn.Linear(scalar_dim, channels)
        nn.init.constant_(self.lin.bias, bias_init)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.lin(h))


__all__ = ["InputInvariants", "TypedMixer", "InvariantGate", "twist_sources", "wrench_sources"]
