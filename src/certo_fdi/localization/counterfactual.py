"""Unified counterfactual link masking (contract 04 §9, master B4).

For every link ``j`` the model's *local* correction message of that link is masked
(``dF_j^local := 0`` for chain models with wrench-like messages; the joint-``j`` torque
correction for joint-space models), the torque correction and the residual-only window
anomaly score are recomputed with the *same* fitted head, and the change of the score is the
link's contribution. Identical algorithm for every model. Internal message energy is never used
here; nothing is interpreted as a physical wrench.
"""

from __future__ import annotations

import numpy as np
import torch

from certo_fdi.dynamics.rnea_torch import TorchChain
from certo_fdi.models.ligra_chain import ModelOutput, backward_recursion


@torch.no_grad()
def masked_delta_taus(out: ModelOutput, tc: TorchChain, X: torch.Tensor) -> torch.Tensor:
    """(n_links, B, T, n) torque corrections with link ``j``'s local message masked, for every ``j``.

    ``X`` (B*T, n, 6, 6) motion transforms of the batch (chain models); joint-space models
    (``out.local is None``) mask the joint-``j`` correction instead."""
    B, T, n = out.delta_tau.shape
    res = []
    if out.local is not None:
        local = out.local.reshape(B * T, n, 6)
        gain = None if out.child_gain is None else out.child_gain.reshape(B * T, n)
        S = tc.S.to(local.dtype).expand(B * T, n, 6)
        for j in range(n):
            loc = local.clone()
            loc[:, j] = 0.0
            dF = backward_recursion(tc, X, loc, gain)
            res.append((S * dF).sum(-1).reshape(B, T, n))
    else:
        for j in range(n):
            d = out.delta_tau.clone()
            d[..., j] = 0.0
            res.append(d)
    return torch.stack(res, 0)


def pooled_residual_block(resid: torch.Tensor) -> np.ndarray:
    """(B,T,n) residual -> (B, n*3) per-link [mean, std, absmax] blocks (same layout as the
    residual-only density input of the pipeline)."""
    b, t, n = resid.shape
    z = torch.cat([resid.mean(1), resid.std(1), resid.abs().amax(1)], 1)  # (B, 3n) layout [stat][link]
    z = z.reshape(b, 3, n).transpose(1, 2).reshape(b, n * 3)  # -> [link][stat]
    return np.nan_to_num(z.cpu().numpy().astype(np.float64), nan=0.0, posinf=1e15, neginf=-1e15).clip(-1e15, 1e15)


@torch.no_grad()
def counterfactual_contributions(head, out: ModelOutput, tc: TorchChain, X: torch.Tensor, tau_meas: torch.Tensor, tau_nom: torch.Tensor, ctx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (score_full (B,), contributions (B, n)) where contribution_j = score(mask j) - score(full).

    ``head`` is the fitted residual-only conditional Gaussian (``head.nll(z, ctx)``)."""
    resid_full = tau_meas - tau_nom - out.delta_tau
    s_full = head.nll(pooled_residual_block(resid_full), ctx)
    masked = masked_delta_taus(out, tc, X)
    contrib = np.zeros((out.delta_tau.shape[0], out.delta_tau.shape[-1]))
    for j in range(masked.shape[0]):
        r = tau_meas - tau_nom - masked[j]
        contrib[:, j] = head.nll(pooled_residual_block(r), ctx) - s_full
    return s_full, contrib


def rank_by_contribution(contrib: np.ndarray) -> np.ndarray:
    """Descending ranking of links by |contribution| (rows: episodes/windows)."""
    return np.argsort(-np.abs(np.asarray(contrib)), axis=-1)


__all__ = ["masked_delta_taus", "pooled_residual_block", "counterfactual_contributions", "rank_by_contribution"]
