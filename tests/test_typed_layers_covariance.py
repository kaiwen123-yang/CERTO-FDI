"""R0 items 3–5: typed layer transformation laws (scalar/twist/wrench), typed temporal recurrence
covariance, forward/backward chain transport covariance — on random legal SE(3) reparameterizations."""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"


def _random_adjoints(rng, n, dtype):
    import torch

    from certo_fdi.geometry.se3 import random_se3

    A = np.stack([random_se3(rng, max_angle_rad=np.pi, max_translation=0.3).adjoint() for _ in range(n)])
    return torch.as_tensor(A, dtype=dtype)


@requires_torch
def test_typed_primitives_transform_exactly(rng):
    import torch

    from certo_fdi.models.typed_channels import affine_scan, apply_I, apply_Iinv, gram_I, gram_Iinv, pair_mf, transport_twists, transport_wrenches, upper
    from certo_fdi.models.typed_equivariant_layers import InputInvariants, InvariantGate, TypedMixer

    torch.manual_seed(0)
    dt = torch.float64
    N, k, l = 5, 4, 3
    A = _random_adjoints(rng, N, dt)  # one frame change per sample
    A_inv = torch.linalg.inv(A)
    A_invT = A_inv.transpose(-1, -2)
    m = torch.randn(N, k, 6, dtype=dt)
    f = torch.randn(N, l, 6, dtype=dt)
    L = torch.randn(N, 6, 6, dtype=dt)
    I = L @ L.transpose(-1, -2) + torch.eye(6, dtype=dt)  # SPD "inertia"
    I_inv = torch.linalg.inv(I)
    m2 = torch.einsum("nij,nkj->nki", A, m)
    f2 = torch.einsum("nij,nkj->nki", A_invT, f)
    I2 = A_invT @ I @ A_inv
    I2_inv = torch.linalg.inv(I2)
    tol = 1e-10
    # invariants
    assert torch.allclose(pair_mf(m2, f2), pair_mf(m, f), atol=tol, rtol=tol)
    assert torch.allclose(gram_I(m2, I2), gram_I(m, I), atol=tol, rtol=tol)
    assert torch.allclose(gram_Iinv(f2, I2_inv), gram_Iinv(f, I_inv), atol=tol, rtol=tol)
    inv = InputInvariants(k, l)
    assert torch.allclose(inv(m2, f2, I2, I2_inv), inv(m, f, I, I_inv), atol=tol, rtol=tol)
    # type conversions are covariant
    assert torch.allclose(apply_I(I2, m2), torch.einsum("nij,nkj->nki", A_invT, apply_I(I, m)), atol=tol, rtol=tol)
    assert torch.allclose(apply_Iinv(I2_inv, f2), torch.einsum("nij,nkj->nki", A, apply_Iinv(I_inv, f)), atol=tol, rtol=tol)
    # invariant-coefficient mixing is covariant (coefficients from an invariant scalar state)
    h = torch.randn(N, 7, dtype=dt)
    mixer = TypedMixer(7, k, 2).to(dt)
    assert torch.allclose(mixer(h, m2), torch.einsum("nij,nkj->nki", A, mixer(h, m)), atol=tol, rtol=tol)
    mixer_f = TypedMixer(7, l, 2).to(dt)
    assert torch.allclose(mixer_f(h, f2), torch.einsum("nij,nkj->nki", A_invT, mixer_f(h, f)), atol=tol, rtol=tol)
    gate = InvariantGate(7, 2).to(dt)
    assert torch.allclose(gate(h), gate(h))  # scalar
    # chain transport: X' = A_i X A_p^{-1}
    Ap = _random_adjoints(rng, N, dt)
    X = _random_adjoints(rng, N, dt)
    X2 = A @ X @ torch.linalg.inv(Ap)
    mp = torch.randn(N, k, 6, dtype=dt)
    mp2 = torch.einsum("nij,nkj->nki", Ap, mp)  # parent twist in the parent's new frame
    assert torch.allclose(transport_twists(X2, mp2), torch.einsum("nij,nkj->nki", A, transport_twists(X, mp)), atol=tol, rtol=tol)
    # child wrench f_c in child frame with adjoint A (child), parent adjoint Ap: X_{c<-i}' = A_c X A_i^{-1}
    fc = torch.randn(N, l, 6, dtype=dt)
    fc2 = torch.einsum("nij,nkj->nki", A_invT, fc)
    out = transport_wrenches(X, fc)  # in parent frame
    out2 = transport_wrenches(X2, fc2)
    assert torch.allclose(out2, torch.einsum("nij,nkj->nki", torch.linalg.inv(Ap).transpose(-1, -2), out), atol=tol, rtol=tol)
    # typed temporal recurrence: affine scan == sequential loop, and equivariant
    T = 11
    a = torch.rand(N, T, k, dtype=dt)
    b = torch.randn(N, T, k, 6, dtype=dt)
    hs = affine_scan(a, b)
    hprev = torch.zeros(N, k, 6, dtype=dt)
    for t in range(T):
        hprev = a[:, t, :, None] * hprev + b[:, t]
        assert torch.allclose(hs[:, t], hprev, atol=1e-12, rtol=1e-12)
    b2 = torch.einsum("nij,ntkj->ntki", A, b)
    assert torch.allclose(affine_scan(a, b2), torch.einsum("nij,ntkj->ntki", A, hs), atol=tol, rtol=tol)


@requires_sim
@requires_torch
@pytest.mark.parametrize("dtype_name,tol", [("float64", 1e-9), ("float32", 2e-4)])
def test_typed_encoder_hidden_channels_are_covariant(dtype_name, tol, rng):
    """Forward twist pass and backward wrench pass on the real chain: hidden twist channels transform
    as ``A_i m``, hidden wrench channels as ``A_i^{-T} f``, scalar hidden states are invariant."""
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.models.ligra_chain import build_model
    from tests.test_models_and_heads import _synthetic_batch

    dtype = getattr(torch, dtype_name)
    chain = reference_chain(XML)
    tc0 = TorchChain.from_chain(chain, dtype=dtype)
    batch = _synthetic_batch(chain, rng, B=3, T=12, dtype=dtype)
    batch["inertia"] = tc0.inertia[None].expand(3, -1, -1, -1)
    model = build_model("ligra_v2_typed", tc0, 6, {"ligra_v2": {"scalar_hidden": 16, "twist_channels": 3, "wrench_channels": 3}}).to(dtype)
    model.fit_normalizers(tc0, [batch])
    for trial in range(2):
        frames = sample_link_frames(chain, rng)
        new, adj = chain.reparameterize(frames)
        A = torch.as_tensor(adj, dtype=dtype)
        tc1 = TorchChain.from_chain(new, dtype=dtype)
        b1 = dict(batch)
        b1["inertia"] = tc1.inertia[None].expand(3, -1, -1, -1)
        with torch.no_grad():
            _, e0 = model.encode(batch, tc0)
            _, e1 = model.encode(b1, tc1)
        for i in range(chain.n_links):
            Ai = A[i]
            AiT = torch.linalg.inv(Ai).T
            hv_pred = torch.einsum("ij,btkj->btki", Ai, e0["hV"][:, :, i])
            hf_pred = torch.einsum("ij,btkj->btki", AiT, e0["hF"][:, :, i])
            sv = max(float(e0["hV"].abs().max()), 1e-9)
            sf = max(float(e0["hF"].abs().max()), 1e-9)
            assert float((e1["hV"][:, :, i] - hv_pred).abs().max()) < tol * sv
            assert float((e1["hF"][:, :, i] - hf_pred).abs().max()) < tol * sf
        for key in ("h1", "h2"):
            assert float((e1[key] - e0[key]).abs().max()) < tol * max(float(e0[key].abs().max()), 1e-9)
