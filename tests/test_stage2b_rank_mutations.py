"""Rank-bias mutation tests (kickoff §04.6).

Artificially enlarging a dictionary's subspace *without adding truth-aligned information* must
not make a rank-aware score look better. The raw residual score necessarily does improve -- that
is the bias Stage 2B set out to measure, so it is pinned as a *positive control* rather than
treated as a bug.
"""

from __future__ import annotations

import numpy as np

from certo_fdi.stage2b import rank_aware_scores as RS

D = 56


def _setup(n=40, seed=0):
    rng = np.random.default_rng(seed)
    truth = rng.normal(size=(D, 2))
    z = (truth @ rng.normal(size=(2, n))).T + 0.3 * rng.normal(size=(n, D))
    hyp = [np.broadcast_to(truth, (n, D, 2)).copy()]
    return hyp, z


def test_inflating_rank_adds_dimensions_without_information():
    hyp, z = _setup()
    big = RS.inflate_rank(hyp, extra=3, seed=1)
    assert big[0].shape[2] == hyp[0].shape[2] + 3
    _, _, r0 = RS.project(hyp[0], z)
    _, _, r1 = RS.project(big[0], z)
    assert (r1 - r0 == 3).all()
    # the added directions are orthogonal to the original subspace
    for i in (0, 5, 17):
        A, B = hyp[0][i], big[0][i][:, 2:]
        assert np.abs(A.T @ B).max() < 1e-8


def test_raw_score_improves_under_rank_inflation_and_rank_aware_scores_do_not():
    hyp, z = _setup()
    big = RS.inflate_rank(hyp, extra=6, seed=2)
    e0, r0, k0 = RS.project(hyp[0], z)
    e1, r1, k1 = RS.project(big[0], z)
    s0 = RS.ProjectionStats(rss=r0[:, None], ess=e0[:, None], rank=k0[:, None], z_energy=(z ** 2).sum(1), dimension=D)
    s1 = RS.ProjectionStats(rss=r1[:, None], ess=e1[:, None], rank=k1[:, None], z_energy=(z ** 2).sum(1), dimension=D)

    # positive control: the raw residual ALWAYS shrinks when dimensions are added
    raw0 = RS.score_matrix(s0, "raw_projection_residual")[:, 0]
    raw1 = RS.score_matrix(s1, "raw_projection_residual")[:, 0]
    assert (raw1 <= raw0 + 1e-9).all()
    assert raw1.mean() < raw0.mean() * 0.999          # a real, systematic improvement

    # BIC must penalise the free dimensions: its score gets worse (larger) on average
    b0 = RS.score_matrix(s0, "bic_penalized_fit")[:, 0]
    b1 = RS.score_matrix(s1, "bic_penalized_fit")[:, 0]
    assert b1.mean() > b0.mean(), (b0.mean(), b1.mean())

    # the chi-square evidence must not increase: 6 extra null dimensions cost more than they explain
    g0 = RS.score_matrix(s0, "rank_aware_glrt")[:, 0]
    g1 = RS.score_matrix(s1, "rank_aware_glrt")[:, 0]
    assert g1.mean() <= g0.mean() + 1e-9, (g0.mean(), g1.mean())


def test_a_rank_inflated_link_must_not_steal_the_prediction_from_a_rank_aware_score():
    """Two links: the true one at rank 2, a decoy inflated to rank 8 with no real information."""
    rng = np.random.default_rng(7)
    n = 60
    truth = rng.normal(size=(D, 2))
    decoy = rng.normal(size=(D, 2))
    z = (truth @ rng.normal(size=(2, n))).T + 0.4 * rng.normal(size=(n, D))
    hyp_true = [np.broadcast_to(truth, (n, D, 2)).copy()]
    hyp_decoy = RS.inflate_rank([np.broadcast_to(decoy, (n, D, 2)).copy()], extra=6, seed=3)
    per_link = [RS.best_hypothesis_stats(hyp_true, z), RS.best_hypothesis_stats(hyp_decoy, z)]
    stats = RS.stack_links(per_link, z, D)
    assert stats.rank[:, 0].mean() == 2 and stats.rank[:, 1].mean() == 8

    raw_pred = RS.predict_link(stats, "raw_projection_residual")
    bic_pred = RS.predict_link(stats, "bic_penalized_fit")
    glrt_pred = RS.predict_link(stats, "rank_aware_glrt")
    # the raw score is fooled far more often than the rank-aware ones
    assert (bic_pred == 0).mean() > (raw_pred == 0).mean()
    assert (glrt_pred == 0).mean() >= (raw_pred == 0).mean()


def test_df_normalisation_uses_the_residual_degrees_of_freedom():
    rng = np.random.default_rng(4)
    n = 10
    rss = rng.uniform(1, 10, size=(n, 2))
    rank = np.tile(np.array([2, 8]), (n, 1))
    stats = RS.ProjectionStats(rss=rss, ess=rss, rank=rank, z_energy=rss.sum(1), dimension=D)
    s = RS.score_matrix(stats, "df_normalized_residual")
    np.testing.assert_allclose(s[:, 0], rss[:, 0] / (D - 2))
    np.testing.assert_allclose(s[:, 1], rss[:, 1] / (D - 8))
