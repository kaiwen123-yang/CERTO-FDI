"""R0 (model level): T1–T3 network covariance/invariance tests before any training.

For random legal per-link frame reparameterizations ``H_i`` the *same* physical windows are
pushed through the model with the canonical chain and with the reparameterized chain:

* T1: internal wrench-like messages transform as ``dF' = A^{-T} dF``;
* T2: torque correction ``d tau`` is invariant;
* T3: per-link invariant anomaly features (hence any score computed from them) are invariant.

The non-equivariant chain GNN is evaluated under the identical protocol to quantify its
drift. Healthy and faulty windows are both included.
"""

from __future__ import annotations

import numpy as np
import torch

from certo_fdi.data.windows import WindowSet
from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.dynamics.rnea_torch import TorchChain
from certo_fdi.geometry.frame_reparameterization import sample_link_frames
from certo_fdi.geometry.spatial_types import SpatialType, transform_typed


def tool_chain(base: ChainModel, tool_id: int) -> ChainModel:
    from certo_fdi.data.schema import TOOLS

    tool = TOOLS[int(tool_id)]
    if tool["mass_kg"] > 0:
        return base.with_payload(tool["mass_kg"], np.asarray(tool["com"]), np.diag(tool["inertia_diag"]))
    return base.copy()


@torch.no_grad()
def model_covariance_trial(model, base_chain: ChainModel, ws: WindowSet, window_ids: list[int], rng: np.random.Generator, cfg_ft: dict, dtype=torch.float32, device: str = "cpu") -> dict:
    """One trial: one H set, a few windows (all from episodes with the same declared tool)."""
    model = model.to(device=device, dtype=dtype)
    batch = ws.batch(window_ids, device)
    batch = {k: (v.to(dtype) if torch.is_floating_point(v) else v) for k, v in batch.items()}
    tool_ids = {int(ws.episodes[int(e)].tool_id) for e in batch["episode_index"]}
    assert len(tool_ids) == 1, "trial windows must share the declared tool"
    chain = tool_chain(base_chain, tool_ids.pop())
    frames = sample_link_frames(chain, rng, rotation_angle_max_deg=float(cfg_ft["rotation_angle_max_deg"]), translation_fraction_of_link_length=float(cfg_ft["translation_fraction_of_link_length"]))
    new_chain, adjoints = chain.reparameterize(frames)
    tc0 = TorchChain.from_chain(chain, dtype=dtype, device=device)
    tc1 = TorchChain.from_chain(new_chain, dtype=dtype, device=device)
    b0 = dict(batch)
    b1 = dict(batch)
    nb = batch["q"].shape[0]
    b0["inertia"] = tc0.inertia[None].expand(nb, -1, -1, -1)
    b1["inertia"] = tc1.inertia[None].expand(nb, -1, -1, -1)
    out0 = model(b0, tc0)
    out1 = model(b1, tc1)
    res: dict = {}
    dt0, dt1 = out0.delta_tau.double().cpu().numpy(), out1.delta_tau.double().cpu().numpy()
    scale_tau = max(float(np.abs(dt0).max()), 1e-12)
    res["T2_delta_tau_max_abs"] = float(np.abs(dt1 - dt0).max())
    res["T2_delta_tau_relative"] = res["T2_delta_tau_max_abs"] / scale_tau
    if out0.messages is not None:
        m0 = out0.messages.double().cpu().numpy()
        m1 = out1.messages.double().cpu().numpy()
        worst = 0.0
        scale = max(float(np.abs(m0).max()), 1e-12)
        for i in range(chain.n_links):
            pred = transform_typed(SpatialType.FORCE, m0[..., i, :], adjoints[i])
            worst = max(worst, float(np.abs(m1[..., i, :] - pred).max()))
        res["T1_message_max_abs"] = worst
        res["T1_message_relative"] = worst / scale
    f0 = out0.link_features.double().cpu().numpy()
    f1 = out1.link_features.double().cpu().numpy()
    scale_f = np.maximum(np.abs(f0).reshape(-1, f0.shape[-1]).max(0), 1e-12)
    rel = np.abs(f1 - f0).reshape(-1, f0.shape[-1]).max(0) / scale_f
    res["T3_link_features_relative_by_feature"] = {n: float(r) for n, r in zip(out0.link_feature_names, rel)}
    res["T3_link_features_relative_max"] = float(rel.max())
    if out0.hidden is not None:
        h0 = out0.hidden.double().cpu().numpy()
        h1 = out1.hidden.double().cpu().numpy()
        res["hidden_state_relative"] = float(np.abs(h1 - h0).max() / max(np.abs(h0).max(), 1e-12))
    return res
