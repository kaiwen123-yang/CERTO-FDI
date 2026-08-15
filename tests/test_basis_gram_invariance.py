"""Phase A instruments: gauge invariance of the basis Gram, dependency detection, exactness of
the chain projection and of the block-tridiagonal regularized solver / effective-DoF recursion."""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"


def _typed(chain, rng, N=24, dtype=None):
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch

    n = chain.n_links
    tc = TorchChain.from_chain(chain, dtype=dtype)
    q = torch.as_tensor(rng.uniform(chain.joint_lower, chain.joint_upper, size=(N, n)), dtype=dtype)
    qd = torch.as_tensor(rng.normal(size=(N, n)), dtype=dtype)
    qdd = torch.as_tensor(rng.normal(size=(N, n)) * 2, dtype=dtype)
    tb = rnea_batch(tc, q, qd, qdd)
    return tc, tb, (q, qd, qdd)


@requires_sim
@requires_torch
def test_gram_is_gauge_invariant_and_dependencies_are_exact(rng):
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.models.basis_capacity_audit import DEPENDENCY_NAMES, gram_audit, invariant_column_scale

    chain = reference_chain(XML)
    tc0, tb0, (q, qd, qdd) = _typed(chain, rng, dtype=torch.float64)
    scale = invariant_column_scale(tc0, tb0)
    g0 = gram_audit(tc0, tb0, scale, keep_gram=True)
    for trial in range(3):
        new, _ = chain.reparameterize(sample_link_frames(chain, rng))
        tc1 = TorchChain.from_chain(new, dtype=torch.float64)
        tb1 = rnea_batch(tc1, q, qd, qdd)
        g1 = gram_audit(tc1, tb1, scale, keep_gram=True)
        assert torch.allclose(g0.gram, g1.gram, rtol=1e-8, atol=1e-8 * g0.gram.abs().max())
        assert torch.equal(g0.rank, g1.rank)
        assert torch.allclose(g0.evals, g1.evals, rtol=1e-6, atol=1e-8 * g0.evals.abs().max())
    # column scale itself is invariant
    new, _ = chain.reparameterize(sample_link_frames(chain, rng))
    tc1 = TorchChain.from_chain(new, dtype=torch.float64)
    assert torch.allclose(scale, invariant_column_scale(tc1, rnea_batch(tc1, q, qd, qdd)), rtol=1e-8)
    # exact structural dependencies (float64 round-off level)
    deps = g0.dependency_relative_residuals
    assert float(deps[DEPENDENCY_NAMES[0]].max()) < 1e-10  # F_body = I A + ad*_V I V
    assert float(deps[DEPENDENCY_NAMES[1]].max()) < 1e-10  # I A = I X A_p + qdd I S + qd I ad_V S
    leaf = deps[DEPENDENCY_NAMES[2]]
    assert torch.isnan(leaf[:, :-1]).all() and float(leaf[:, -1].max()) < 1e-10  # leaf: F = F_body
    root = deps[DEPENDENCY_NAMES[3]]
    assert float(root[:, 0].max()) < 1e-12 and torch.isnan(root[:, 1:]).all()  # root: I X V_p = 0
    assert float(deps[DEPENDENCY_NAMES[4]][:, 0].max()) < 1e-10  # root: I X A_p = -I X g
    # rank deficiency follows: root <= 8, leaf <= 9, interior <= 10
    assert int(g0.rank[:, 0].max()) <= 8
    assert int(g0.rank[:, -1].max()) <= 9
    assert int(g0.rank[:, 1:-1].max()) <= 10
    assert torch.all(g0.nullity >= 2)


@requires_sim
@requires_torch
def test_chain_projection_matches_backward_recursion(rng):
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.models.basis_capacity_audit import chain_projection
    from certo_fdi.models.ligra_chain import backward_recursion

    chain = reference_chain(XML)
    tc, tb, _ = _typed(chain, rng, N=8, dtype=torch.float64)
    n = chain.n_links
    local = torch.as_tensor(rng.normal(size=(8, n, 6)))
    dF = backward_recursion(tc, tb.X, local)
    tau_ref = (tb.S * dF).sum(-1)
    P = chain_projection(tc, tb.X, tb.S)
    tau = (P @ local.reshape(8, n * 6, 1))[..., 0]
    assert torch.allclose(tau, tau_ref, atol=1e-10, rtol=1e-10)


@requires_torch
def test_block_tridiagonal_solver_matches_dense_and_edf():
    import torch

    from certo_fdi.models.basis_capacity_audit import solve_regularized

    torch.manual_seed(0)
    W, Tn, m, d = 3, 9, 4, 6
    M = torch.randn(W, Tn, m, d, dtype=torch.float64)
    e = torch.randn(W, Tn, m, dtype=torch.float64)
    for lam1, lam2 in ((1e-2, 0.0), (1e-1, 3.0), (1e-3, 0.5)):
        out = solve_regularized(M, e, lam1, lam2)
        for w in range(W):
            # dense assembly
            Mw = torch.block_diag(*[M[w, t] for t in range(Tn)])  # (T m, T d)
            Dm = torch.zeros(Tn - 1, Tn, dtype=torch.float64)
            for t in range(Tn - 1):
                Dm[t, t] = -1.0
                Dm[t, t + 1] = 1.0
            Dt = torch.kron(Dm, torch.eye(d, dtype=torch.float64))
            A = Mw.T @ Mw + lam1 * torch.eye(Tn * d, dtype=torch.float64) + lam2 * Dt.T @ Dt
            x = torch.linalg.solve(A, Mw.T @ e[w].reshape(-1))
            assert torch.allclose(out["coeffs"][w].reshape(-1), x, atol=1e-8, rtol=1e-8)
            H = Mw @ torch.linalg.solve(A, Mw.T)
            assert abs(float(out["edf"][w]) - float(torch.trace(H))) < 1e-7
    # row mask: masked time steps do not enter the data term
    mask = torch.ones(W, Tn)
    mask[:, ::3] = 0.0
    out_m = solve_regularized(M, e, 1e-2, 1.0, row_mask=mask)
    Mm = M * mask[..., None, None]
    out_ref = solve_regularized(Mm, e * mask[..., None], 1e-2, 1.0)
    assert torch.allclose(out_m["coeffs"], out_ref["coeffs"], atol=1e-10)


@requires_sim
@requires_torch
def test_mismatch_wrench_projection_exact_for_uniform_scaling(rng):
    """A uniform inertial scaling dI = eps I is exactly spanned by the columns I A and ad*_V I V."""
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.models.basis_capacity_audit import invariant_column_scale, mismatch_wrench, projection_residual
    from certo_fdi.models.covariant_basis import covariant_basis

    chain = reference_chain(XML)
    tc, tb, _ = _typed(chain, rng, N=6, dtype=torch.float64)
    dI = 0.05 * tc.inertia
    target = mismatch_wrench(dI, tb)
    B = covariant_basis(tc, tb) / invariant_column_scale(tc, tb)
    rel, _ = projection_residual(target, B, torch.linalg.inv(tb.inertia))
    assert float(rel.max()) < 1e-8
    # a non-uniform perturbation is generally NOT exactly spanned
    dI2 = dI.clone()
    dI2[:, 5, 5] *= 3.0
    rel2, _ = projection_residual(mismatch_wrench(dI2, tb), B, torch.linalg.inv(tb.inertia))
    assert float(rel2.max()) > 1e-6
