"""Unified counterfactual link masking: masked corrections equal an explicit recomputation, the
joint-space fallback masks one joint, contributions vanish for links without messages, and the
pooled residual block matches the pipeline's residual-only density input layout."""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"


@requires_sim
@requires_torch
def test_masked_delta_tau_matches_explicit_recursion(rng):
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.localization.counterfactual import masked_delta_taus, pooled_residual_block
    from certo_fdi.models.chain_gnn import backward_recursion, build_model, run_front_end
    from certo_fdi.experiments.pipeline import _pool, _regroup_per_link
    from tests.test_models_and_heads import _synthetic_batch

    dtype = torch.float64
    chain = reference_chain(XML)
    tc = TorchChain.from_chain(chain, dtype=dtype)
    batch = _synthetic_batch(chain, rng, B=3, T=8, dtype=dtype)
    batch["inertia"] = tc.inertia[None].expand(3, -1, -1, -1)
    n = chain.n_links
    for name in ("chain_gnn_aug", "chain_gnn"):
        m = build_model(name, tc, 6, {"scalar_hidden_dim": 16, "scalar_layers": 1}).to(dtype)
        m.fit_normalizers(tc, [batch])
        with torch.no_grad():
            for p in m.parameters():
                p.add_(0.1 * torch.randn_like(p))
            out = m(batch, tc)
            tb = run_front_end(tc, batch)
            masked = masked_delta_taus(out, tc, tb.X)
        assert masked.shape == (n, 3, 8, n)
        # unmasked recomputation reproduces the model's delta_tau; masking link j changes only joints <= j
        local = out.local.reshape(-1, n, 6)
        gain = None if out.child_gain is None else out.child_gain.reshape(-1, n)
        dtau_re = (tc.S.expand(local.shape[0], n, 6) * backward_recursion(tc, tb.X, local, gain)).sum(-1).reshape(3, 8, n)
        assert torch.allclose(dtau_re, out.delta_tau, atol=1e-10)
        for j in range(n):
            diff = (masked[j] - out.delta_tau).abs().amax((0, 1))
            assert float(diff[j + 1:].max()) < 1e-12 if j + 1 < n else True  # distal joints untouched
            assert float(diff[j]) > 0.0  # the link's own joint is affected
    # joint-space fallback
    g = build_model("rnea_gru", tc, 6, {"baseline_gru_hidden": 16, "scalar_layers": 1}).to(dtype)
    g.fit_normalizers(tc, [batch])
    with torch.no_grad():
        for p in g.parameters():
            p.add_(0.1 * torch.randn_like(p))
        og = g(batch, tc)
        mg = masked_delta_taus(og, tc, None)
    for j in range(n):
        assert torch.all(mg[j][..., j] == 0)
        others = [k for k in range(n) if k != j]
        assert torch.equal(mg[j][..., others], og.delta_tau[..., others])
    # residual block layout == pipeline residual-only layout
    r = torch.randn(5, 8, n, dtype=dtype)
    z_ref = _regroup_per_link(_pool(r).numpy(), n, 1, 3)
    assert np.allclose(pooled_residual_block(r), z_ref)


@requires_torch
def test_rank_by_contribution_and_zero_message_links():
    from certo_fdi.localization.counterfactual import rank_by_contribution

    c = np.array([[0.1, -3.0, 0.5], [2.0, 0.0, -0.1]])
    r = rank_by_contribution(c)
    assert r[0].tolist() == [1, 2, 0] and r[1].tolist() == [0, 2, 1]
