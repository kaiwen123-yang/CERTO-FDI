"""Batched torch versions of the spatial-algebra primitives (tested against se3.py)."""

from __future__ import annotations

import torch


def skew(v: torch.Tensor) -> torch.Tensor:
    """(..., 3) -> (..., 3, 3)."""
    x, y, z = v[..., 0], v[..., 1], v[..., 2]
    o = torch.zeros_like(x)
    return torch.stack(
        [
            torch.stack([o, -z, y], dim=-1),
            torch.stack([z, o, -x], dim=-1),
            torch.stack([-y, x, o], dim=-1),
        ],
        dim=-2,
    )


def ad(v: torch.Tensor) -> torch.Tensor:
    """Motion cross product ad_V for V=[omega; v] : (..., 6) -> (..., 6, 6)."""
    w = skew(v[..., :3])
    u = skew(v[..., 3:])
    z = torch.zeros_like(w)
    top = torch.cat([w, z], dim=-1)
    bottom = torch.cat([u, w], dim=-1)
    return torch.cat([top, bottom], dim=-2)


def ad_star(v: torch.Tensor, *, mutate_sign: bool = False) -> torch.Tensor:
    """Force cross product ad*_V = -ad_V^T (frozen convention)."""
    a = ad(v).transpose(-1, -2)
    return a if mutate_sign else -a


def rot_axis_angle(axis: torch.Tensor, angle: torch.Tensor) -> torch.Tensor:
    """Rodrigues: axis (..., 3) unit, angle (...) -> (..., 3, 3)."""
    k = skew(axis)
    s = torch.sin(angle)[..., None, None]
    c = torch.cos(angle)[..., None, None]
    eye = torch.eye(3, dtype=axis.dtype, device=axis.device).expand(k.shape)
    return eye + s * k + (1.0 - c) * (k @ k)


def adjoint(r: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
    """Motion adjoint of T=(R,p): (...,3,3),(...,3) -> (...,6,6)."""
    z = torch.zeros_like(r)
    top = torch.cat([r, z], dim=-1)
    bottom = torch.cat([skew(p) @ r, r], dim=-1)
    return torch.cat([top, bottom], dim=-2)


def coadjoint(r: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
    """Wrench transform Ad_T^{-T} = [[R, skew(p) R], [0, R]]."""
    z = torch.zeros_like(r)
    top = torch.cat([r, skew(p) @ r], dim=-1)
    bottom = torch.cat([z, r], dim=-1)
    return torch.cat([top, bottom], dim=-2)


def compose(r1, p1, r2, p2):
    return r1 @ r2, (r1 @ p2[..., None])[..., 0] + p1


def inverse(r, p):
    rt = r.transpose(-1, -2)
    return rt, -(rt @ p[..., None])[..., 0]
