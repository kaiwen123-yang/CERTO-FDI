"""Shared building blocks: MLPs, parameter counting, feature normalization."""

from __future__ import annotations

import torch
from torch import nn


def mlp(in_dim: int, hidden: int, out_dim: int, layers: int = 2, act=nn.SiLU) -> nn.Sequential:
    mods: list[nn.Module] = []
    d = in_dim
    for _ in range(layers):
        mods += [nn.Linear(d, hidden), act()]
        d = hidden
    mods.append(nn.Linear(d, out_dim))
    return nn.Sequential(*mods)


def count_parameters(module: nn.Module) -> int:
    return int(sum(p.numel() for p in module.parameters() if p.requires_grad))


class Standardizer(nn.Module):
    """Per-feature affine standardization with statistics fitted on healthy training data.

    Applying an affine map to *invariant scalars* preserves invariance exactly.
    """

    def __init__(self, dim: int):
        super().__init__()
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("std", torch.ones(dim))
        self.fitted = False

    @torch.no_grad()
    def fit(self, x: torch.Tensor) -> None:
        flat = x.reshape(-1, x.shape[-1]).double()
        self.mean.copy_(flat.mean(0).to(self.mean.dtype))
        std = flat.std(0)
        std = torch.where(std < 1e-8, torch.ones_like(std), std)
        self.std.copy_(std.to(self.std.dtype))
        self.fitted = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std
