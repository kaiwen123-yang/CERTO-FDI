"""LiGRA-v2-Typed: exactly link-frame-equivariant typed recurrent chain model (contract 04).

Inputs per link (identical physical information to ``chain_gnn_aug``, see
:func:`input_field_manifest`): scalars ``q, qd, qdd_est, tau_nom``; twists ``V, A, S, g``;
wrenches ``F_body, F, I V, I A``; declared context; invariant link descriptors. The typed
inputs are processed by type (never compressed to a few hand-picked scalars): the encoder keeps
twist- and wrench-typed hidden channels; the head emits an invariant coefficient per hidden
wrench channel, ``dF_local = sum_k alpha_k h_k^(F)``, followed by the backward recursion
``dF_i = dF_i^local + (1 + g_i) sum_c X_{c<-i}^T dF_c`` (exact coadjoint transport; ``g_i`` is an
invariant child-message gain — the same head freedom the PR #2 chain models have) and
``d tau_i = S_i^T dF_i``. The gain was added as the single pre-registered numerical/optimization fix
of Stage 1R-B after healthy-validation-only diagnostics (see the known-issues document); it does not
change any typed transformation law.

Anomaly representation: primary = residual only (identical head to the baseline); the reported
per-link features are invariants of the messages (no coefficient energy). Internal messages are
wrench-*like*; no physical-wrench identification is claimed.
"""

from __future__ import annotations

import torch
from torch import nn

from certo_fdi.data.windows import MODEL_CONTEXT_NAMES
from certo_fdi.dynamics.rnea_torch import TorchChain, TypedBatch
from certo_fdi.models.common import Standardizer, count_parameters
from certo_fdi.models.features import LINK_PHYSICAL_FEATURES, base_gravity_twist, link_physical_features
from certo_fdi.models.ligra_chain import ModelOutput, backward_recursion, run_front_end, typed_link_features
from certo_fdi.models.typed_channels import SCALAR_INPUTS, TWIST_INPUTS, WRENCH_INPUTS, TypedScale
from certo_fdi.models.typed_temporal import TypedChainRecurrentEncoder


def typed_inputs(tc: TorchChain, tb: TypedBatch, tau_nom: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """(m_in (N,n,4,6), f_in (N,n,4,6), scalars (N,n,4)) in the current link frames."""
    g = base_gravity_twist(tc, tb.X)
    m = torch.stack([tb.V, tb.A, tb.S, g], -2)  # TWIST_INPUTS order
    IA = (tb.inertia @ tb.A[..., None])[..., 0]
    f = torch.stack([tb.F_body, tb.F, tb.momentum, IA], -2)  # WRENCH_INPUTS order
    s = torch.stack([tb.q, tb.qd, tb.qdd, tau_nom], -1)  # SCALAR_INPUTS order
    return m, f, s


class LiGRAv2Typed(nn.Module):
    name = "ligra_v2_typed"
    exact_covariant = True

    def __init__(self, tc: TorchChain, ctx_dim: int, *, d_s: int = 48, d_v: int = 5, d_f: int = 5):
        super().__init__()
        self.tc = tc
        self.n = tc.n
        self.d_s, self.d_v, self.d_f = d_s, d_v, d_f
        self.scale = TypedScale(len(TWIST_INPUTS), len(WRENCH_INPUTS))
        self.encoder = TypedChainRecurrentEncoder(len(TWIST_INPUTS), len(WRENCH_INPUTS), len(SCALAR_INPUTS), len(LINK_PHYSICAL_FEATURES), ctx_dim, d_s=d_s, d_v=d_v, d_f=d_f)
        self.head = nn.Linear(d_s, d_f)  # invariant coefficients alpha_k of the hidden wrench channels
        nn.init.zeros_(self.head.bias)
        with torch.no_grad():
            self.head.weight.mul_(0.1)
        self.gain = nn.Linear(d_s, 1)  # invariant child-message gain g_i (as in the PR #2 chain models)
        nn.init.zeros_(self.gain.bias)
        with torch.no_grad():
            self.gain.weight.mul_(0.1)
        self.register_buffer("tau_scale", torch.ones(self.n))

    # ------------------------------------------------------------------ manifest / audit
    @staticmethod
    def input_field_manifest() -> dict[str, list[str]]:
        return {"scalars": list(SCALAR_INPUTS), "twists": list(TWIST_INPUTS), "wrenches": list(WRENCH_INPUTS), "context": list(MODEL_CONTEXT_NAMES), "link_descriptors": [n for n, _ in LINK_PHYSICAL_FEATURES], "processing": "typed (scalar / twist / wrench channels, invariant gates)"}

    # ------------------------------------------------------------------ normalizers
    @torch.no_grad()
    def fit_normalizers(self, tc: TorchChain, batches: list[dict]) -> None:
        ms, fs, Is, invs, resid = [], [], [], [], []
        for batch in batches:
            b, t, n = batch["q"].shape
            tb = run_front_end(tc, batch)
            m, f, s = typed_inputs(tc, tb, batch["tau_nom"].reshape(b * t, n))
            I = tb.inertia
            ms.append(m.reshape(-1, m.shape[-2], 6))
            fs.append(f.reshape(-1, f.shape[-2], 6))
            Is.append(I.reshape(-1, 6, 6))
            resid.append((batch["tau_meas"] - batch["tau_nom"]).reshape(-1, self.n))
        M, F, I = torch.cat(ms), torch.cat(fs), torch.cat(Is)
        self.scale.fit(M, F, I, torch.linalg.inv(I))
        for batch in batches:
            b, t, n = batch["q"].shape
            tb = run_front_end(tc, batch)
            m, f, s = typed_inputs(tc, tb, batch["tau_nom"].reshape(b * t, n))
            m, f = self.scale(m, f)
            I = tb.inertia
            invs.append(self.encoder.input_invariants(m, f, s, I, torch.linalg.inv(I)).reshape(-1, self.encoder.inv_std.mean.numel()))
        self.encoder.inv_std.fit(torch.cat(invs))
        self.encoder.phys_std.fit(link_physical_features(tc))
        self.tau_scale.copy_(torch.cat(resid).std(0).clamp_min(1e-3))

    # ------------------------------------------------------------------ forward
    def encode(self, batch: dict, tc: TorchChain) -> tuple[TypedBatch, dict[str, torch.Tensor]]:
        b, t, n = batch["q"].shape
        tb = run_front_end(tc, batch)
        m, f, s = typed_inputs(tc, tb, batch["tau_nom"].reshape(b * t, n))
        m, f = self.scale(m, f)
        I = tb.inertia.reshape(b, t, n, 6, 6)[:, 0]
        I_inv = torch.linalg.inv(I)
        enc = self.encoder(m.reshape(b, t, n, -1, 6), f.reshape(b, t, n, -1, 6), s.reshape(b, t, n, -1), link_physical_features(tc), batch["ctx"], I, I_inv, tb.X.reshape(b, t, n, 6, 6), tc.parent, tc.children)
        return tb, enc

    def forward(self, batch: dict, tc: TorchChain | None = None) -> ModelOutput:
        tc = self.tc if tc is None else tc
        b, t, n = batch["q"].shape
        tb, enc = self.encode(batch, tc)
        alpha = self.head(enc["h2"])  # (B,T,n,d_f) invariant coefficients
        local = torch.einsum("btnk,btnki->btni", alpha, enc["hF"]).reshape(b * t, n, 6) * self.tau_scale.mean()
        child_gain = self.gain(enc["h2"]).reshape(b * t, n)  # invariant scalar per link
        dF = backward_recursion(tc, tb.X, local, child_gain)  # exact coadjoint transport with invariant child gain
        delta_tau = (tb.S * dF).sum(-1)
        feats, names = typed_link_features(tb, dF, local, batch["tau_meas"].reshape(b * t, n), batch["tau_nom"].reshape(b * t, n))
        return ModelOutput(delta_tau=delta_tau.reshape(b, t, n), link_features=feats.reshape(b, t, n, -1), link_feature_names=names, messages=dF.reshape(b, t, n, 6), coeffs=alpha, hidden=enc["h2"], local=local.reshape(b, t, n, 6), child_gain=child_gain.reshape(b, t, n))


def build_ligra_v2(tc: TorchChain, ctx_dim: int, cfg_model: dict) -> LiGRAv2Typed:
    v2 = cfg_model.get("ligra_v2", {})
    return LiGRAv2Typed(tc, ctx_dim, d_s=int(v2.get("scalar_hidden", 48)), d_v=int(v2.get("twist_channels", 5)), d_f=int(v2.get("wrench_channels", 5)))


__all__ = ["LiGRAv2Typed", "typed_inputs", "build_ligra_v2", "count_parameters"]
