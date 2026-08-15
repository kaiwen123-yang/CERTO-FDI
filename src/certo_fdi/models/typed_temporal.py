"""Causal typed recurrent chain encoder for LiGRA-v2 (contract 04 §4–§5).

Two sweeps per window, mirroring RNEA:

* **forward twist pass** (root -> leaf): a scalar GRU per link consumes standardized invariants of
  the link's typed inputs, joint/context scalars, the parent's scalar hidden sequence and the
  pairings of the parent's *transported* twist channels ``X_{i<-p} h_p^(V)`` with the link's
  input wrenches; it emits invariant gates and mixing coefficients that drive the typed twist
  recurrence ``h_t^(V) = z_t h_{t-1}^(V) + (1 - z_t) sum_l c_l(t) src_l(t)`` over
  ``src = [m_in, I^{-1} f_in, X_{i<-p} h_p^(V)]``;
* **backward wrench pass** (leaf -> root): a second scalar GRU consumes the forward scalar hidden,
  pairings of the link's own twist hidden with its input wrenches, the Gram of the twist hidden,
  and pairings of the children's *transported* wrench channels ``sum_c X_{c<-i}^T h_c^(F)`` with
  the input twists and the twist hidden; it drives the typed wrench recurrence over
  ``src = [f_in, I m_in, sum_c X_{c<-i}^T h_c^(F), I h^(V)]``.

All gates and coefficients are invariant scalars; typed states are only ever formed by invariant
linear combinations of typed sources, type conversions through ``I``/``I^{-1}`` and exact chain
transport, so the encoder is exactly equivariant (tested).
"""

from __future__ import annotations

import torch
from torch import nn

from certo_fdi.models.common import Standardizer
from certo_fdi.models.typed_channels import affine_scan, apply_I, gram_I, pair_mf, transport_twists, transport_wrenches, upper
from certo_fdi.models.typed_equivariant_layers import InputInvariants, InvariantGate, TypedMixer, twist_sources, wrench_sources


class TypedChainRecurrentEncoder(nn.Module):
    def __init__(self, n_twist_in: int, n_wrench_in: int, scalar_in_dim: int, phys_dim: int, ctx_dim: int, *, d_s: int = 48, d_v: int = 5, d_f: int = 5):
        super().__init__()
        self.kv, self.kf, self.d_s, self.d_v, self.d_f = n_twist_in, n_wrench_in, d_s, d_v, d_f
        self.inv_in = InputInvariants(n_twist_in, n_wrench_in)
        self.inv_std = Standardizer(self.inv_in.dim + scalar_in_dim)  # invariant scalars only
        self.phys_std = Standardizer(phys_dim)
        d1 = self.inv_in.dim + scalar_in_dim + phys_dim + ctx_dim + d_s + d_v * n_wrench_in
        self.gru1 = nn.GRU(d1, d_s, batch_first=True)
        self.gate_v = InvariantGate(d_s, d_v)
        self.mix_v = TypedMixer(d_s, n_twist_in + n_wrench_in + d_v, d_v)
        d2 = d_s + d_v * n_wrench_in + d_v * (d_v + 1) // 2 + n_twist_in * d_f + d_v * d_f
        self.gru2 = nn.GRU(d2, d_s, batch_first=True)
        self.gate_f = InvariantGate(d_s, d_f)
        self.mix_f = TypedMixer(d_s, n_wrench_in + n_twist_in + d_f + d_v, d_f)
        self.d1, self.d2 = d1, d2

    # ------------------------------------------------------------------ helpers
    def input_invariants(self, m_in: torch.Tensor, f_in: torch.Tensor, scalars: torch.Tensor, I: torch.Tensor, I_inv: torch.Tensor) -> torch.Tensor:
        """(..., dim_inv + scalar_in) raw (unstandardized) invariant vector for one link."""
        return torch.cat([self.inv_in(m_in, f_in, I, I_inv), scalars], -1)

    def forward(self, m_in: torch.Tensor, f_in: torch.Tensor, scalars: torch.Tensor, phys: torch.Tensor, ctx: torch.Tensor, I: torch.Tensor, I_inv: torch.Tensor, X: torch.Tensor, parents: list[int], children: list[list[int]]) -> dict[str, torch.Tensor]:
        """m_in (B,T,n,kv,6), f_in (B,T,n,kf,6), scalars (B,T,n,s), phys (n,P), ctx (B,C),
        I/I_inv (B,n,6,6) (constant over the window), X (B,T,n,6,6) = X_{i<-p}(t)."""
        B, T, n = m_in.shape[:3]
        ctx_t = ctx[:, None, :].expand(B, T, ctx.shape[-1])
        physn = self.phys_std(phys)
        I_t = I[:, None].expand(B, T, n, 6, 6)
        Ii_t = I_inv[:, None].expand(B, T, n, 6, 6)
        h1: list[torch.Tensor] = [None] * n
        hV: list[torch.Tensor] = [None] * n
        # ---- forward twist pass (root -> leaf)
        for i in range(n):
            p = parents[i]
            inv = self.inv_std(self.input_invariants(m_in[:, :, i], f_in[:, :, i], scalars[:, :, i], I_t[:, :, i], Ii_t[:, :, i]))
            if p < 0:
                hp0 = torch.zeros(B, T, self.d_s, dtype=m_in.dtype, device=m_in.device)
                mp = torch.zeros(B, T, self.d_v, 6, dtype=m_in.dtype, device=m_in.device)
            else:
                hp0 = h1[p]
                mp = transport_twists(X[:, :, i], hV[p])
            inp = torch.cat([inv, physn[i][None, None, :].expand(B, T, -1), ctx_t, hp0, pair_mf(mp, f_in[:, :, i]).reshape(B, T, -1)], -1)
            h, _ = self.gru1(inp)
            z = self.gate_v(h)
            u = self.mix_v(h, twist_sources(m_in[:, :, i], f_in[:, :, i], Ii_t[:, :, i], mp))
            h1[i] = h
            hV[i] = affine_scan(z, (1.0 - z)[..., None] * u)
        # ---- backward wrench pass (leaf -> root)
        h2: list[torch.Tensor] = [None] * n
        hF: list[torch.Tensor] = [None] * n
        for i in range(n - 1, -1, -1):
            kids = children[i]
            if kids:
                fc = sum(transport_wrenches(X[:, :, c], hF[c]) for c in kids)
            else:
                fc = torch.zeros(B, T, self.d_f, 6, dtype=m_in.dtype, device=m_in.device)
            inv2 = torch.cat([
                h1[i],
                pair_mf(hV[i], f_in[:, :, i]).reshape(B, T, -1),
                upper(gram_I(hV[i], I_t[:, :, i])),
                pair_mf(m_in[:, :, i], fc).reshape(B, T, -1),
                pair_mf(hV[i], fc).reshape(B, T, -1),
            ], -1)
            h, _ = self.gru2(inv2)
            z = self.gate_f(h)
            src = wrench_sources(m_in[:, :, i], f_in[:, :, i], I_t[:, :, i], torch.cat([fc, apply_I(I_t[:, :, i], hV[i])], -2))
            u = self.mix_f(h, src)
            h2[i] = h
            hF[i] = affine_scan(z, (1.0 - z)[..., None] * u)
        return {"h1": torch.stack(h1, 2), "hV": torch.stack(hV, 2), "h2": torch.stack(h2, 2), "hF": torch.stack(hF, 2)}


__all__ = ["TypedChainRecurrentEncoder"]
