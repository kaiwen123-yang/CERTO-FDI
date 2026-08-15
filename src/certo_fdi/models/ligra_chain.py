"""LiGRA basis-coefficient model (exact link-frame covariance by construction) and the
structurally matched non-equivariant chain GNN and ablations.

All models share the analytic front end (Block A), the chain-recursive encoder (Block B),
and the exact backward coadjoint recursion (Block D). They differ only in what the encoder
consumes (invariant scalars vs raw components) and what the head emits (scalar coefficients
of a covariant basis vs free 6-D vectors).
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from certo_fdi.dynamics.rnea_torch import TorchChain, TypedBatch, rnea_batch
from certo_fdi.models.common import Standardizer, count_parameters, mlp
from certo_fdi.models.covariant_basis import ANALYTIC_BASIS_DIM, covariant_basis
from certo_fdi.models.features import INVARIANT_FEATURES, RAW_FEATURE_DIM, invariant_features, link_physical_features, raw_features
from certo_fdi.models.scalar_temporal_encoder import ChainGRUEncoder, PerStepMLPEncoder


@dataclass
class ModelOutput:
    delta_tau: torch.Tensor  # (B,T,n)
    link_features: torch.Tensor  # (B,T,n,k) per-link anomaly features (invariant for LiGRA)
    link_feature_names: list[str]
    messages: torch.Tensor | None = None  # (B,T,n,6) wrench-like messages
    coeffs: torch.Tensor | None = None  # (B,T,n,K)
    hidden: torch.Tensor | None = None  # (B,T,n,H)


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


def message_link_features(tb: TypedBatch, dF: torch.Tensor, coeffs: torch.Tensor | None, tau_meas: torch.Tensor, tau_nom: torch.Tensor) -> tuple[torch.Tensor, list[str]]:
    """Per-link anomaly features from a wrench-like message: a1=S^T dF, a2=V^T dF, a3=dF^T I^{-1} dF,
    a4=|coeffs|^2 (or |dF|^2 for free-output models), post-correction residual."""
    I_inv = torch.linalg.inv(tb.inertia)
    a1 = (tb.S * dF).sum(-1)
    a2 = (tb.V * dF).sum(-1)
    a3 = _quad(dF, I_inv, dF)
    a4 = (coeffs**2).sum(-1) if coeffs is not None else (dF**2).sum(-1)
    resid = tau_meas - tau_nom - a1
    return torch.stack([a1, a2, a3, a4, resid], -1), ["a1_S_dF", "a2_V_dF", "a3_dF_Iinv_dF", "a4_coeff_energy", "post_residual"]


class LiGRA(nn.Module):
    """Exact basis-coefficient LiGRA (invariant scalar inputs, covariant wrench basis output)."""

    name = "ligra"
    exact_covariant = True

    def __init__(self, tc: TorchChain, ctx_dim: int, hidden: int = 64, layers: int = 2, *, variant: str = "exact", shared: bool = True):
        super().__init__()
        self.tc = tc
        self.n = tc.n
        self.variant = variant  # exact | free_output | mlp_encoder
        self.in_std = Standardizer(len(INVARIANT_FEATURES))
        self.phys_std = Standardizer(8)
        self.register_buffer("basis_scale", torch.ones(ANALYTIC_BASIS_DIM))
        self.register_buffer("tau_scale", torch.ones(self.n))
        enc_cls = PerStepMLPEncoder if variant == "mlp_encoder" else ChainGRUEncoder
        if variant == "mlp_encoder":
            self.encoder = enc_cls(len(INVARIANT_FEATURES), 8, ctx_dim, hidden, layers)
        else:
            self.encoder = enc_cls(len(INVARIANT_FEATURES), 8, ctx_dim, hidden, layers, shared=shared, n_links=self.n)
        self.K = ANALYTIC_BASIS_DIM + 1
        if variant == "free_output":
            self.head = nn.Linear(hidden, 6 + 1)
            self.exact_covariant = False
            self.name = "ligra_free_output"
        else:
            self.head = nn.Linear(hidden, self.K)
            self.name = "ligra" if variant == "exact" else f"ligra_{variant}"
        if not shared:
            self.name = "ligra_unshared"
        nn.init.zeros_(self.head.bias)
        with torch.no_grad():
            self.head.weight.mul_(0.1)

    def features(self, tc: TorchChain, batch: dict, tb: TypedBatch) -> torch.Tensor:
        b, t, n = batch["q"].shape
        f = invariant_features(tc, tb, batch["tau_meas"].reshape(b * t, n), batch["tau_nom"].reshape(b * t, n))
        return f.reshape(b, t, n, -1)

    @torch.no_grad()
    def fit_normalizers(self, tc: TorchChain, batches: list[dict]) -> None:
        feats, basis_norms, resid = [], [], []
        for batch in batches:
            tb = run_front_end(tc, batch)
            feats.append(self.features(tc, batch, tb).reshape(-1, len(INVARIANT_FEATURES)))
            B = covariant_basis(tc, tb)  # (BT,n,6,K)
            basis_norms.append(B.pow(2).sum(2).sqrt().reshape(-1, ANALYTIC_BASIS_DIM))
            resid.append((batch["tau_meas"] - batch["tau_nom"]).reshape(-1, self.n))
        self.in_std.fit(torch.cat(feats))
        self.phys_std.fit(link_physical_features(tc))
        bn = torch.cat(basis_norms).pow(2).mean(0).sqrt()
        self.basis_scale.copy_(torch.where(bn < 1e-8, torch.ones_like(bn), bn))
        self.tau_scale.copy_(torch.cat(resid).std(0).clamp_min(1e-3))

    def forward(self, batch: dict, tc: TorchChain | None = None) -> ModelOutput:
        tc = self.tc if tc is None else tc
        b, t, n = batch["q"].shape
        tb = run_front_end(tc, batch)
        x = self.in_std(self.features(tc, batch, tb))
        phys = self.phys_std(link_physical_features(tc))
        h = self.encoder(x, phys, batch["ctx"], tc.parent)  # (B,T,n,H)
        out = self.head(h)  # (B,T,n,K)
        if self.variant == "free_output":
            local = out[..., :6].reshape(b * t, n, 6) * self.tau_scale.mean()
            child_gain = out[..., 6].reshape(b * t, n)
            coeffs = None
        else:
            B = covariant_basis(tc, tb) / self.basis_scale  # (BT,n,6,12)
            coeffs = out[..., : ANALYTIC_BASIS_DIM].reshape(b * t, n, ANALYTIC_BASIS_DIM)
            local = (B @ coeffs[..., None])[..., 0] * self.tau_scale.mean()
            child_gain = out[..., ANALYTIC_BASIS_DIM].reshape(b * t, n)
        dF = backward_recursion(tc, tb.X, local, child_gain)
        delta_tau = (tb.S * dF).sum(-1)
        feats, names = message_link_features(tb, dF, coeffs, batch["tau_meas"].reshape(b * t, n), batch["tau_nom"].reshape(b * t, n))
        return ModelOutput(
            delta_tau=delta_tau.reshape(b, t, n),
            link_features=feats.reshape(b, t, n, -1),
            link_feature_names=names,
            messages=dF.reshape(b, t, n, 6),
            coeffs=None if coeffs is None else coeffs.reshape(b, t, n, -1),
            hidden=h,
        )


class ChainGNN(nn.Module):
    """Non-equivariant chain GNN: raw typed components in, free 6-D wrench-like message out.

    Same chain-recursive encoder, same exact backward transport, same parameter budget as
    LiGRA. Its outputs are *not* frame covariant; the trainer may apply random legal frame
    reparameterizations as data augmentation (``chain_gnn_aug``).
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
        return raw_features(tc, tb, batch["tau_meas"].reshape(b * t, n), batch["tau_nom"].reshape(b * t, n)).reshape(b, t, n, -1)

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
        feats, names = message_link_features(tb, dF, None, batch["tau_meas"].reshape(b * t, n), batch["tau_nom"].reshape(b * t, n))
        return ModelOutput(delta_tau.reshape(b, t, n), feats.reshape(b, t, n, -1), names, dF.reshape(b, t, n, 6), None, h)


class JointSpaceCorrection(nn.Module):
    """RNEA + MLP / RNEA + GRU / GRU-without-RNEA baselines on joint-space signals.

    Inputs are joint scalars (frame-invariant by construction, but with no link structure).
    """

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
    if name == "ligra":
        return LiGRA(tc, ctx_dim, hidden, layers)
    if name == "ligra_free_output":
        return LiGRA(tc, ctx_dim, hidden, layers, variant="free_output")
    if name == "ligra_mlp_encoder":
        return LiGRA(tc, ctx_dim, hidden, layers, variant="mlp_encoder")
    if name == "ligra_unshared":
        return LiGRA(tc, ctx_dim, max(24, hidden // 2), layers, shared=False)
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
    if name == "rnea_only":
        return RNEAOnly(tc, ctx_dim)
    raise ValueError(name)


def parameter_report(models: dict[str, nn.Module]) -> dict[str, int]:
    return {k: count_parameters(m) for k, m in models.items()}
