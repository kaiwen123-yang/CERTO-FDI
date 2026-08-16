"""Chain-structured healthy-residual models: the frozen Stage 2A main baseline and its ablations.

Ported from ``src/certo_fdi/models/ligra_chain.py`` on
``stage/stage1r-b-equivariant-capacity-audit`` @ 11134fb (see
``docs_pointer/STAGE2A_PORT_PROVENANCE.md``). The analytic front end (Block A), the
chain-recursive encoder (Block B) and the exact backward coadjoint recursion (Block D) are
copied **verbatim** so that the frozen ``chain_gnn_aug`` checkpoints and their parameter
count (63,047) reproduce bit-for-bit.

Deliberately **not** ported (Stage 2A contract §1.3): the LiGRA-v1 basis-coefficient model,
LiGRA-v2-Typed, the covariant wrench basis and any decision logic that reads
network-internal wrench-like messages as physical wrenches.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from certo_fdi.dynamics.rnea_torch import TorchChain, TypedBatch, rnea_batch
from certo_fdi.models.common import Standardizer, count_parameters, mlp
from certo_fdi.models.features import RAW_FEATURE_DIM, link_physical_features, raw_features
from certo_fdi.models.scalar_temporal_encoder import ChainGRUEncoder


@dataclass
class ModelOutput:
    delta_tau: torch.Tensor  # (B,T,n)
    link_features: torch.Tensor  # (B,T,n,k) per-link anomaly features
    link_feature_names: list[str]
    messages: torch.Tensor | None = None  # (B,T,n,6) wrench-like messages (NOT physical wrenches)
    coeffs: torch.Tensor | None = None  # kept for checkpoint/API compatibility; always None here
    hidden: torch.Tensor | None = None  # (B,T,n,H)
    local: torch.Tensor | None = None  # (B,T,n,6) local (pre-aggregation) messages, for counterfactual masking
    child_gain: torch.Tensor | None = None  # (B,T,n) learned child-message gain


def run_front_end(tc: TorchChain, batch: dict) -> TypedBatch:
    """Batched typed RNEA on (B,T,n) joint signals with per-episode inertia override."""
    q, qd, qdd = batch["q"], batch["qd"], batch["qdd"]
    b, t, n = q.shape
    inertia = batch.get("inertia")
    if inertia is not None:
        inertia = inertia[:, None].expand(b, t, n, 6, 6).reshape(b * t, n, 6, 6)
    tb = rnea_batch(tc, q.reshape(b * t, n), qd.reshape(b * t, n), qdd.reshape(b * t, n), inertia=inertia)
    return tb


def backward_recursion(tc: TorchChain, X: torch.Tensor, local: torch.Tensor, child_gain: torch.Tensor | None = None) -> torch.Tensor:
    """dF_i = local_i + (1 + child_gain_i) * sum_c X_{c<-i}^T dF_c  (exact coadjoint transport).

    ``X`` (B,n,6,6) are the parent-to-child motion transforms ``X_{i<-p}``; the transport of a
    child message into the parent frame is ``X_{c<-p}^T dF_c``. Shapes: local (B,n,6).
    """
    n = X.shape[1]
    out: list[torch.Tensor | None] = [None] * n
    for i in range(n - 1, -1, -1):
        acc = local[:, i]
        kids = tc.children[i]
        if kids:
            transported = sum((X[:, c].transpose(-1, -2) @ out[c][..., None])[..., 0] for c in kids)
            gain = 1.0 if child_gain is None else (1.0 + child_gain[:, i, None])
            acc = acc + gain * transported
        out[i] = acc
    return torch.stack(out, 1)


def _quad(v, m, w):
    return (v[..., None, :] @ m @ w[..., :, None])[..., 0, 0]


def typed_link_features(tb: TypedBatch, dF: torch.Tensor, dF_local: torch.Tensor, tau_meas: torch.Tensor, tau_nom: torch.Tensor) -> tuple[torch.Tensor, list[str]]:
    """Per-link features (identical for every chain model): invariants of the transmitted
    and local wrench-like messages -- ``S^T dF``, ``V^T dF``, ``dF^T I^{-1} dF``, ``S^T dF_local``,
    ``V^T dF_local``, ``dF_local^T I^{-1} dF_local`` -- and the post-correction residual.
    The primary anomaly head uses the residual only; the message invariants form the secondary
    "representation" variant and are never read as physical wrenches."""
    I_inv = torch.linalg.inv(tb.inertia)
    a1 = (tb.S * dF).sum(-1)
    a2 = (tb.V * dF).sum(-1)
    a3 = _quad(dF, I_inv, dF)
    a5 = (tb.S * dF_local).sum(-1)
    a7 = (tb.V * dF_local).sum(-1)
    a6 = _quad(dF_local, I_inv, dF_local)
    resid = tau_meas - tau_nom - a1
    return torch.stack([a1, a2, a3, a5, a7, a6, resid], -1), ["a1_S_dF", "a2_V_dF", "a3_dF_Iinv_dF", "a5_S_dFlocal", "a7_V_dFlocal", "a6_dFlocal_Iinv_dFlocal", "post_residual"]


class ChainGNN(nn.Module):
    """Non-equivariant chain GNN: raw typed components in, free 6-D wrench-like message out.

    Its outputs are *not* frame covariant; the trainer may apply random legal frame
    reparameterizations as data augmentation (``chain_gnn_aug``, the Stage 2A main baseline).
    """

    name = "chain_gnn"
    exact_covariant = False

    def __init__(self, tc: TorchChain, ctx_dim: int, hidden: int = 64, layers: int = 2, *, augmented: bool = False):
        super().__init__()
        self.tc = tc
        self.n = tc.n
        self.in_std = Standardizer(RAW_FEATURE_DIM)
        self.phys_std = Standardizer(8)
        self.register_buffer("tau_scale", torch.ones(self.n))
        self.encoder = ChainGRUEncoder(RAW_FEATURE_DIM, 8, ctx_dim, hidden, layers)
        self.head = nn.Linear(hidden, 6 + 1)
        nn.init.zeros_(self.head.bias)
        with torch.no_grad():
            self.head.weight.mul_(0.1)
        self.name = "chain_gnn_aug" if augmented else "chain_gnn"

    def features(self, tc: TorchChain, batch: dict, tb: TypedBatch) -> torch.Tensor:
        b, t, n = batch["q"].shape
        return raw_features(tc, tb, batch["tau_nom"].reshape(b * t, n)).reshape(b, t, n, -1)

    @torch.no_grad()
    def fit_normalizers(self, tc: TorchChain, batches: list[dict]) -> None:
        feats, resid = [], []
        for batch in batches:
            tb = run_front_end(tc, batch)
            feats.append(self.features(tc, batch, tb).reshape(-1, RAW_FEATURE_DIM))
            resid.append((batch["tau_meas"] - batch["tau_nom"]).reshape(-1, self.n))
        self.in_std.fit(torch.cat(feats))
        self.phys_std.fit(link_physical_features(tc))
        self.tau_scale.copy_(torch.cat(resid).std(0).clamp_min(1e-3))

    def forward(self, batch: dict, tc: TorchChain | None = None) -> ModelOutput:
        tc = self.tc if tc is None else tc
        b, t, n = batch["q"].shape
        tb = run_front_end(tc, batch)
        x = self.in_std(self.features(tc, batch, tb))
        phys = self.phys_std(link_physical_features(tc))
        h = self.encoder(x, phys, batch["ctx"], tc.parent)
        out = self.head(h)
        local = out[..., :6].reshape(b * t, n, 6) * self.tau_scale.mean()
        child_gain = out[..., 6].reshape(b * t, n)
        dF = backward_recursion(tc, tb.X, local, child_gain)
        delta_tau = (tb.S * dF).sum(-1)
        feats, names = typed_link_features(tb, dF, local, batch["tau_meas"].reshape(b * t, n), batch["tau_nom"].reshape(b * t, n))
        return ModelOutput(delta_tau.reshape(b, t, n), feats.reshape(b, t, n, -1), names, dF.reshape(b, t, n, 6), None, h, local=local.reshape(b, t, n, 6), child_gain=child_gain.reshape(b, t, n))

    @staticmethod
    def input_field_manifest() -> dict[str, list[str]]:
        from certo_fdi.models.features import raw_input_field_manifest

        return raw_input_field_manifest()


class JointSpaceCorrection(nn.Module):
    """RNEA + MLP / RNEA + GRU / GRU-without-RNEA baselines on joint-space signals."""

    exact_covariant = True

    def __init__(self, tc: TorchChain, ctx_dim: int, hidden: int = 96, layers: int = 2, *, kind: str = "gru", use_rnea: bool = True):
        super().__init__()
        self.tc = tc
        self.n = tc.n
        self.kind = kind
        self.use_rnea = use_rnea
        d = self.n * (4 if use_rnea else 3) + ctx_dim
        self.in_std = Standardizer(d)
        self.register_buffer("tau_scale", torch.ones(self.n))
        if kind == "gru":
            self.core = nn.GRU(d, hidden, num_layers=layers, batch_first=True)
        else:
            self.core = mlp(d, hidden, hidden, layers=layers)
        self.head = nn.Linear(hidden, self.n)
        nn.init.zeros_(self.head.bias)
        with torch.no_grad():
            self.head.weight.mul_(0.1)
        self.name = ("rnea_" if use_rnea else "") + kind + ("" if use_rnea else "_no_rnea")

    def _inputs(self, batch: dict) -> torch.Tensor:
        b, t, n = batch["q"].shape
        parts = [batch["q"], batch["qd"], batch["qdd"]]
        if self.use_rnea:
            parts.append(batch["tau_nom"])
        x = torch.cat(parts, -1)
        return torch.cat([x, batch["ctx"][:, None, :].expand(b, t, -1)], -1)

    @torch.no_grad()
    def fit_normalizers(self, tc: TorchChain, batches: list[dict]) -> None:
        self.in_std.fit(torch.cat([self._inputs(bt).reshape(-1, self.in_std.mean.numel()) for bt in batches]))
        target = torch.cat([(bt["tau_meas"] - (bt["tau_nom"] if self.use_rnea else 0.0)).reshape(-1, self.n) for bt in batches])
        self.tau_scale.copy_(target.std(0).clamp_min(1e-3))

    def forward(self, batch: dict, tc: TorchChain | None = None) -> ModelOutput:
        x = self.in_std(self._inputs(batch))
        if self.kind == "gru":
            h, _ = self.core(x)
        else:
            h = self.core(x)
        delta = self.head(h) * self.tau_scale
        target_ref = batch["tau_nom"] if self.use_rnea else torch.zeros_like(batch["tau_nom"])
        resid = batch["tau_meas"] - target_ref - delta
        feats = torch.stack([delta, resid], -1)
        return ModelOutput(delta, feats, ["delta_tau", "post_residual"], None, None, h[..., None, :].expand(*h.shape[:2], self.n, h.shape[-1]))


class RNEAOnly(nn.Module):
    """``rnea_threshold`` front end: the analytic RNEA residual with no learned correction."""

    name = "rnea_only"
    exact_covariant = True

    def __init__(self, tc: TorchChain, ctx_dim: int):
        super().__init__()
        self.tc = tc
        self.n = tc.n
        self._dummy = nn.Parameter(torch.zeros(0))

    def fit_normalizers(self, tc, batches):
        return None

    def forward(self, batch: dict, tc: TorchChain | None = None) -> ModelOutput:
        z = torch.zeros_like(batch["tau_meas"])
        resid = batch["tau_meas"] - batch["tau_nom"]
        return ModelOutput(z, torch.stack([z, resid], -1), ["delta_tau", "post_residual"], None, None, None)


def build_model(name: str, tc: TorchChain, ctx_dim: int, cfg_model: dict) -> nn.Module:
    hidden = int(cfg_model.get("scalar_hidden_dim", 64))
    layers = int(cfg_model.get("scalar_layers", 2))
    if name == "chain_gnn":
        return ChainGNN(tc, ctx_dim, hidden, layers)
    if name == "chain_gnn_aug":
        return ChainGNN(tc, ctx_dim, hidden, layers, augmented=True)
    if name == "rnea_gru":
        return JointSpaceCorrection(tc, ctx_dim, int(cfg_model.get("baseline_gru_hidden", 80)), layers, kind="gru")
    if name == "rnea_mlp":
        return JointSpaceCorrection(tc, ctx_dim, int(cfg_model.get("baseline_mlp_hidden", 160)), layers + 1, kind="mlp")
    if name == "gru_no_rnea":
        return JointSpaceCorrection(tc, ctx_dim, int(cfg_model.get("baseline_gru_hidden", 80)), layers, kind="gru", use_rnea=False)
    if name in ("rnea_only", "rnea_threshold"):
        return RNEAOnly(tc, ctx_dim)
    raise ValueError(f"unknown model '{name}' (Stage 2A ports only the chain-GNN / joint-space family)")


def parameter_report(models: dict[str, nn.Module]) -> dict[str, int]:
    return {k: count_parameters(m) for k, m in models.items()}
