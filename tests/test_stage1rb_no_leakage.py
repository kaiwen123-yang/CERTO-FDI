"""R0 items 13–14 (dynamic part): the encoders of every Stage 1R-B model are blind to measured
torque, raw residual, fault labels/targets/severity, GMO residual and truth-only state — perturbing
those batch fields leaves the torque correction bit-identical (they enter only the anomaly stage)."""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
MODELS = ("chain_gnn_aug", "ligra_v2_typed", "rnea_gru", "ligra_free_output", "chain_gnn")
CFG = {"scalar_hidden_dim": 32, "scalar_layers": 2, "baseline_gru_hidden": 32, "ligra_v2": {"scalar_hidden": 16, "twist_channels": 3, "wrench_channels": 3}}


def perturb_forbidden(batch, rng, dtype):
    """Randomize every field an encoder must not see; keep the allowed inputs identical."""
    import torch

    b = dict(batch)
    b["tau_meas"] = batch["tau_meas"] + torch.as_tensor(rng.normal(size=batch["tau_meas"].shape) * 20, dtype=dtype)
    b["r_gmo"] = torch.as_tensor(rng.normal(size=batch["q"].shape), dtype=dtype)
    b["active"] = torch.as_tensor(rng.integers(0, 2, size=batch["q"].shape[:2]), dtype=dtype)
    b["target"] = torch.as_tensor(rng.integers(-1, 7, size=batch["q"].shape[:2]))
    b["family"] = torch.as_tensor(rng.integers(0, 7, size=(batch["q"].shape[0],)))
    b["qdd_true"] = torch.as_tensor(rng.normal(size=batch["q"].shape), dtype=dtype)
    b["q_true"] = torch.as_tensor(rng.normal(size=batch["q"].shape), dtype=dtype)
    b["severity"] = torch.as_tensor(rng.normal(size=batch["q"].shape[:2]), dtype=dtype)
    return b


@requires_sim
@requires_torch
@pytest.mark.parametrize("name", MODELS)
def test_encoder_blind_to_forbidden_fields(name, rng):
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.models.ligra_chain import build_model
    from tests.test_models_and_heads import _synthetic_batch

    dtype = torch.float64
    chain = reference_chain(XML)
    tc = TorchChain.from_chain(chain, dtype=dtype)
    batch = _synthetic_batch(chain, rng, B=3, T=10, dtype=dtype)
    batch["inertia"] = tc.inertia[None].expand(3, -1, -1, -1)
    m = build_model(name, tc, 6, CFG).to(dtype)
    m.fit_normalizers(tc, [batch])
    with torch.no_grad():
        o0 = m(batch, tc)
        o1 = m(perturb_forbidden(batch, rng, dtype), tc)
    assert torch.equal(o0.delta_tau, o1.delta_tau), name
    if o0.messages is not None:
        assert torch.equal(o0.messages, o1.messages)
    # normalizer fitting must not depend on forbidden fields either (except tau_scale which uses the
    # residual *target* scale, a training-target statistic, not an encoder input)
    m2 = build_model(name, tc, 6, CFG).to(dtype)
    torch.manual_seed(0)
    m2.load_state_dict(m.state_dict())
    m2.fit_normalizers(tc, [perturb_forbidden(batch, rng, dtype)])
    for k, v in m.state_dict().items():
        if k.endswith("tau_scale"):
            continue
        assert torch.equal(v, m2.state_dict()[k]), (name, k)


@requires_sim
@requires_torch
def test_allowed_inputs_do_change_the_output(rng):
    """Sanity: the encoders are not constant — perturbing an allowed input changes the correction."""
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.models.ligra_chain import build_model
    from tests.test_models_and_heads import _synthetic_batch

    dtype = torch.float64
    chain = reference_chain(XML)
    tc = TorchChain.from_chain(chain, dtype=dtype)
    batch = _synthetic_batch(chain, rng, B=3, T=10, dtype=dtype)
    batch["inertia"] = tc.inertia[None].expand(3, -1, -1, -1)
    for name in ("chain_gnn_aug", "ligra_v2_typed"):
        m = build_model(name, tc, 6, CFG).to(dtype)
        m.fit_normalizers(tc, [batch])
        with torch.no_grad():
            for p in m.parameters():
                p.add_(0.1 * torch.randn_like(p))
            o0 = m(batch, tc)
            b1 = dict(batch)
            b1["qd"] = batch["qd"] + 0.5
            o1 = m(b1, tc)
        assert not torch.allclose(o0.delta_tau, o1.delta_tau)
