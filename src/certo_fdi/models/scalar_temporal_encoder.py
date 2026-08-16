"""Shared chain-recursive temporal encoder over per-link scalar sequences (Block B).

One GRU (weights shared across links) processes each link's input sequence together with
the *invariant* hidden state of its parent link at the same time step. Link identity is
represented by physical link descriptors (mass, principal inertias, ...), never a free
one-hot. When the per-link inputs are invariant scalars, all hidden states are invariant.
"""

from __future__ import annotations

import torch
from torch import nn


class ChainGRUEncoder(nn.Module):
    def __init__(self, in_dim: int, phys_dim: int, ctx_dim: int, hidden: int = 64, layers: int = 2, parent_message: bool = True, shared: bool = True, n_links: int = 7):
        super().__init__()
        self.hidden = hidden
        self.parent_message = parent_message
        self.shared = shared
        d = in_dim + phys_dim + ctx_dim + (hidden if parent_message else 0)
        if shared:
            self.gru = nn.GRU(d, hidden, num_layers=layers, batch_first=True)
        else:
            self.grus = nn.ModuleList([nn.GRU(d, hidden, num_layers=layers, batch_first=True) for _ in range(n_links)])

    def forward(self, x: torch.Tensor, phys: torch.Tensor, ctx: torch.Tensor, parents: list[int]) -> torch.Tensor:
        """x (B,T,n,D), phys (n,P), ctx (B,C) -> hidden (B,T,n,H)."""
        b, t, n, _ = x.shape
        ctx_t = ctx[:, None, :].expand(b, t, ctx.shape[-1])
        hs: list[torch.Tensor] = []
        for i in range(n):
            parts = [x[:, :, i], phys[i][None, None, :].expand(b, t, phys.shape[-1]), ctx_t]
            if self.parent_message:
                p = parents[i]
                parts.append(torch.zeros(b, t, self.hidden, dtype=x.dtype, device=x.device) if p < 0 else hs[p])
            inp = torch.cat(parts, -1)
            gru = self.gru if self.shared else self.grus[i]
            h, _ = gru(inp)
            hs.append(h)
        return torch.stack(hs, 2)


class PerStepMLPEncoder(nn.Module):
    """Ablation: no temporal encoder — per-step MLP with the same chain parent message."""

    def __init__(self, in_dim: int, phys_dim: int, ctx_dim: int, hidden: int = 64, layers: int = 2, parent_message: bool = True):
        super().__init__()
        from certo_fdi.models.common import mlp

        self.hidden = hidden
        self.parent_message = parent_message
        d = in_dim + phys_dim + ctx_dim + (hidden if parent_message else 0)
        self.net = mlp(d, hidden, hidden, layers=layers)

    def forward(self, x, phys, ctx, parents):
        b, t, n, _ = x.shape
        ctx_t = ctx[:, None, :].expand(b, t, ctx.shape[-1])
        hs = []
        for i in range(n):
            parts = [x[:, :, i], phys[i][None, None, :].expand(b, t, phys.shape[-1]), ctx_t]
            if self.parent_message:
                p = parents[i]
                parts.append(torch.zeros(b, t, self.hidden, dtype=x.dtype, device=x.device) if p < 0 else hs[p])
            hs.append(self.net(torch.cat(parts, -1)))
        return torch.stack(hs, 2)
