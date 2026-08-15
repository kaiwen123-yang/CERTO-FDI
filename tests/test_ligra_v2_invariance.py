"""R0 items 6–12 at model level: final delta_tau invariance, residual-only anomaly-score invariance,
counterfactual localization-score invariance, chain-GNN drift under the same protocol, healthy and
fault-like windows under the same law, float64/float32 tolerances, gradient finite-difference check,
parameter-count parity."""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"
V2_SMALL = {"ligra_v2": {"scalar_hidden": 16, "twist_channels": 3, "wrench_channels": 3}}


def _fault_like(batch, rng, dtype):
    """A 'faulty' window: large residual on one joint and an added measured-torque offset — the
    covariance law must hold identically for such windows."""
    import torch

    b = dict(batch)
    tm = batch["tau_meas"].clone()
    tm[..., 3] += torch.as_tensor(rng.normal(size=tm.shape[:2]) * 8 + 5, dtype=dtype)
    b["tau_meas"] = tm
    b["active"] = torch.ones_like(batch["q"][..., 0])
    return b


@requires_sim
@requires_torch
@pytest.mark.parametrize("dtype_name,tol", [("float64", 1e-9), ("float32", 2e-4)])
def test_ligra_v2_T1_T2_T3_and_counterfactual_invariance(dtype_name, tol, rng):
    import torch

    from certo_fdi.anomaly.gaussian_head import ConditionalGaussian
    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.geometry.spatial_types import SpatialType, transform_typed
    from certo_fdi.localization.counterfactual import counterfactual_contributions, pooled_residual_block
    from certo_fdi.models.ligra_chain import build_model, run_front_end
    from tests.test_models_and_heads import _synthetic_batch

    dtype = getattr(torch, dtype_name)
    chain = reference_chain(XML)
    chain.damping[:] = 0.5
    chain.coulomb[:] = 0.3
    payload = chain.with_payload(0.5, np.array([0.0, 0.0, 0.1]))
    for ch in (chain, payload):
        tc0 = TorchChain.from_chain(ch, dtype=dtype)
        healthy = _synthetic_batch(ch, rng, B=4, T=16, dtype=dtype)
        healthy["inertia"] = tc0.inertia[None].expand(4, -1, -1, -1)
        faulty = _fault_like(healthy, rng, dtype)
        m = build_model("ligra_v2_typed", tc0, 6, V2_SMALL).to(dtype)
        m.fit_normalizers(tc0, [healthy])
        # a residual-only head fitted on healthy pooled residuals (tiny, in-sample; protocol shape only)
        with torch.no_grad():
            o_h = m(healthy, tc0)
        z_h = pooled_residual_block(healthy["tau_meas"] - healthy["tau_nom"] - o_h.delta_tau)
        head = ConditionalGaussian(conditional=False, covariance="diag", rank=0).fit(z_h, healthy["ctx"].numpy(), {f"link{i}": slice(i * 3, (i + 1) * 3) for i in range(ch.n_links)})
        for batch in (healthy, faulty):
            frames = sample_link_frames(ch, rng)
            new, adjoints = ch.reparameterize(frames)
            tc1 = TorchChain.from_chain(new, dtype=dtype)
            b1 = dict(batch)
            b1["inertia"] = tc1.inertia[None].expand(4, -1, -1, -1)
            with torch.no_grad():
                o0, o1 = m(batch, tc0), m(b1, tc1)
            m0, m1 = o0.messages.numpy(), o1.messages.numpy()
            for i in range(ch.n_links):  # T1: transmitted messages are wrench-covariant
                pred = transform_typed(SpatialType.FORCE, m0[..., i, :], adjoints[i])
                assert np.abs(m1[..., i, :] - pred).max() < tol * max(np.abs(m0).max(), 1e-9)
                pred_l = transform_typed(SpatialType.FORCE, o0.local.numpy()[..., i, :], adjoints[i])
                assert np.abs(o1.local.numpy()[..., i, :] - pred_l).max() < tol * max(np.abs(o0.local.numpy()).max(), 1e-9)
            # T2: delta_tau invariant; T3: per-link features invariant
            assert np.abs(o1.delta_tau.numpy() - o0.delta_tau.numpy()).max() < tol * max(np.abs(o0.delta_tau.numpy()).max(), 1e-9)
            assert np.abs(o1.link_features.numpy() - o0.link_features.numpy()).max() < tol * max(np.abs(o0.link_features.numpy()).max(), 1e-9)
            # residual-only anomaly score and counterfactual contributions invariant
            tb0, tb1 = run_front_end(tc0, batch), run_front_end(tc1, b1)
            s0, c0 = counterfactual_contributions(head, o0, tc0, tb0.X, batch["tau_meas"], batch["tau_nom"], batch["ctx"].numpy())
            s1, c1 = counterfactual_contributions(head, o1, tc1, tb1.X, batch["tau_meas"], batch["tau_nom"], batch["ctx"].numpy())
            assert np.abs(s1 - s0).max() < 10 * tol * max(np.abs(s0).max(), 1e-9)
            assert np.abs(c1 - c0).max() < 10 * tol * max(np.abs(c0).max(), 1e-9)
        # the non-equivariant chain GNN drifts O(1) under the identical protocol (R0 item 9)
        g = build_model("chain_gnn_aug", tc0, 6, {"scalar_hidden_dim": 32, "scalar_layers": 2}).to(dtype)
        g.fit_normalizers(tc0, [healthy])
        frames = sample_link_frames(ch, rng)
        new, _ = ch.reparameterize(frames)
        tc1 = TorchChain.from_chain(new, dtype=dtype)
        b1 = dict(healthy)
        b1["inertia"] = tc1.inertia[None].expand(4, -1, -1, -1)
        with torch.no_grad():
            g0, g1 = g(healthy, tc0), g(b1, tc1)
        assert np.abs(g1.delta_tau.numpy() - g0.delta_tau.numpy()).max() > 1e-3 * max(np.abs(g0.delta_tau.numpy()).max(), 1e-9)


@requires_sim
@requires_torch
def test_ligra_v2_gradient_finite_difference(rng):
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.models.ligra_chain import build_model
    from tests.test_models_and_heads import _synthetic_batch

    dtype = torch.float64
    chain = reference_chain(XML)
    tc = TorchChain.from_chain(chain, dtype=dtype)
    batch = _synthetic_batch(chain, rng, B=2, T=6, dtype=dtype)
    batch["inertia"] = tc.inertia[None].expand(2, -1, -1, -1)
    m = build_model("ligra_v2_typed", tc, 6, {"ligra_v2": {"scalar_hidden": 8, "twist_channels": 2, "wrench_channels": 2}}).to(dtype)
    m.fit_normalizers(tc, [batch])
    # perturb the head so that gradients are non-trivial
    with torch.no_grad():
        for p in m.parameters():
            p.add_(0.05 * torch.randn_like(p))
    target = batch["tau_meas"] - batch["tau_nom"]

    def loss_fn():
        return ((m(batch, tc).delta_tau - target) ** 2).mean()

    loss = loss_fn()
    params = [p for p in m.parameters() if p.requires_grad]
    grads = torch.autograd.grad(loss, params)
    checked = 0
    for p, g in zip(params, grads):
        flat = p.data.reshape(-1)
        idx = rng.choice(flat.numel(), size=min(3, flat.numel()), replace=False)
        for k in idx:
            k = int(k)
            old = float(flat[k])
            eps = 1e-6
            flat[k] = old + eps
            lp = float(loss_fn())
            flat[k] = old - eps
            lm = float(loss_fn())
            flat[k] = old
            fd = (lp - lm) / (2 * eps)
            an = float(g.reshape(-1)[k])
            assert abs(fd - an) <= 1e-6 + 1e-4 * max(abs(fd), abs(an)), (fd, an)
            checked += 1
    assert checked > 20


@requires_sim
@requires_torch
def test_parameter_count_parity_primary_models():
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.models.common import count_parameters
    from certo_fdi.models.ligra_chain import build_model

    chain = reference_chain(XML)
    tc = TorchChain.from_chain(chain, dtype=torch.float32)
    cfg = {"scalar_hidden_dim": 64, "scalar_layers": 2, "ligra_v2": {"scalar_hidden": 48, "twist_channels": 6, "wrench_channels": 6}}
    nb = count_parameters(build_model("chain_gnn_aug", tc, 6, cfg))
    nv = count_parameters(build_model("ligra_v2_typed", tc, 6, cfg))
    assert abs(nv - nb) / nb <= 0.10, (nb, nv)
