"""Rank matching and projection correctness (kickoff §04.3, §04.5, §07.1).

If the controls are not rank matched the whole source-of-gain decomposition is meaningless --
a control could lose simply by spanning fewer dimensions. Kickoff §07.1 makes an unmatched
control an integrity failure (`BLOCKED`), so it is tested here rather than assumed.
"""

from __future__ import annotations

import numpy as np

from certo_fdi.stage2b import loadpath_controls as LC
from certo_fdi.stage2b import rank_aware_scores as RS

N_JOINTS, N_TIME = 7, 8
D = N_JOINTS * N_TIME


def _random_dicts(n_windows: int, rank: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n_windows, D, rank))


def test_projection_matches_an_explicit_projector():
    rng = np.random.default_rng(11)
    Dm = _random_dicts(6, 3, seed=2)
    z = rng.normal(size=(6, D))
    ess, rss, rank = RS.project(Dm, z)
    for i in range(6):
        Q, _ = np.linalg.qr(Dm[i])
        P = Q @ Q.T
        np.testing.assert_allclose(ess[i], float(z[i] @ P @ z[i]), rtol=1e-9)
        np.testing.assert_allclose(rss[i], float(z[i] @ (np.eye(D) - P) @ z[i]), rtol=1e-9)
        assert rank[i] == 3
    np.testing.assert_allclose(ess + rss, (z ** 2).sum(1), rtol=1e-12)


def test_projection_reports_true_numerical_rank():
    rng = np.random.default_rng(5)
    base = rng.normal(size=(D, 2))
    Dm = np.zeros((4, D, 3))
    Dm[:, :, :2] = base
    Dm[:, :, 2] = base[:, 0] * 3.0          # exactly collinear -> rank 2, not 3
    z = rng.normal(size=(4, D))
    _, _, rank = RS.project(Dm, z)
    assert (rank == 2).all(), rank
    # an identically zero dictionary explains nothing
    ess0, rss0, r0 = RS.project(np.zeros((2, D, 3)), z[:2])
    assert (ess0 == 0).all() and (r0 == 0).all()
    np.testing.assert_allclose(rss0, (z[:2] ** 2).sum(1))


def test_static_control_bases_have_exactly_the_target_rank():
    """A support/random basis built at rank r must project onto exactly r dimensions."""
    from certo_fdi.pathways.geometry import orthonormal_basis

    rng = np.random.default_rng(0)
    W = np.eye(D) + 0.05 * rng.normal(size=(D, D))          # a non-trivial whitener
    for l in (0, 1, 3, 6):
        rows = LC.support_rows(l, N_JOINTS, N_TIME)
        k = len(rows)
        for r in (1, 2, 3):
            if r > k:
                continue
            U = orthonormal_basis(W @ LC.embed(LC.dct_basis(k, r, offset=2), rows, D))
            assert U.shape[1] == r, (l, r, U.shape)
            Ur = orthonormal_basis(W @ LC.embed(LC.random_basis(k, r, seed=3), rows, D))
            assert Ur.shape[1] == r, (l, r, Ur.shape)


def test_rank_match_target_is_the_aligned_rank():
    """`_ranks` takes the largest realised rank over the aligned hypotheses, per window."""
    a = np.zeros((3, D, 3))
    rng = np.random.default_rng(1)
    a[:, :, :2] = rng.normal(size=(3, D, 2))                # rank 2
    b = rng.normal(size=(3, D, 3))                          # rank 3
    r = LC._ranks([a, b])
    assert (r == 3).all(), r
    r_single = LC._ranks([a])
    assert (r_single == 2).all(), r_single


def test_score_directions_are_declared_consistently():
    assert set(RS.SCORES) == set(RS.HIGHER_IS_BETTER)
    assert RS.HIGHER_IS_BETTER["rank_aware_glrt"] is True
    for s in ("raw_projection_residual", "df_normalized_residual", "bic_penalized_fit", "minimal_consistent_link"):
        assert RS.HIGHER_IS_BETTER[s] is False
    assert RS.AUDIT_CONTROL_SCORE == "raw_projection_residual"


def test_all_five_scores_produce_a_prediction():
    rng = np.random.default_rng(4)
    n, L = 20, 7
    rss = rng.uniform(1.0, 50.0, size=(n, L))
    ess = rng.uniform(0.0, 20.0, size=(n, L))
    rank = rng.integers(1, 4, size=(n, L))
    stats = RS.ProjectionStats(rss=rss, ess=ess, rank=rank, z_energy=rss.sum(1), dimension=D)
    acc = np.full(L, 30.0)
    for name in RS.SCORES:
        pred = RS.predict_link(stats, name, acceptance=acc)
        assert pred.shape == (n,)
        assert pred.min() >= 0 and pred.max() < L
        rk = RS.link_ranking(stats, name, acceptance=acc)
        assert rk.shape == (n, L)
        assert (rk[:, 0] == pred).all(), name
        ev = RS.normalized_link_evidence(stats, name, acceptance=acc)
        np.testing.assert_allclose(ev.sum(1), 1.0, atol=1e-9)
        m = RS.score_margin(stats, name, acceptance=acc)
        assert m.shape == (n,) and (m >= -1e-12).all()


def test_minimal_consistent_link_picks_the_most_proximal_accepted_link():
    L = 7
    rss = np.array([[100.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.5]])      # distal links always fit better
    stats = RS.ProjectionStats(rss=rss, ess=rss.sum() - rss, rank=np.full((1, L), 3),
                               z_energy=np.array([120.0]), dimension=D)
    acc = np.full(L, 6.0)                                        # links 1..6 are all "consistent"
    assert int(RS.predict_link(stats, "minimal_consistent_link", acceptance=acc)[0]) == 1
    # the raw score, by contrast, always prefers the most distal link
    assert int(RS.predict_link(stats, "raw_projection_residual")[0]) == 6
    # when nothing is consistent it falls back to the raw residual and says so
    acc_tight = np.full(L, 0.1)
    assert int(RS.predict_link(stats, "minimal_consistent_link", acceptance=acc_tight)[0]) == 6


def test_healthy_acceptance_thresholds_are_per_link_quantiles():
    rng = np.random.default_rng(9)
    healthy = rng.uniform(0, 10, size=(500, 7)) * np.arange(1, 8)[None, :]
    thr = RS.healthy_acceptance_thresholds(healthy, 0.95)
    assert thr.shape == (7,)
    for l in range(7):
        assert abs(float((healthy[:, l] <= thr[l]).mean()) - 0.95) < 0.03


def test_chi2_evidence_is_monotone_and_rank_penalising():
    """More explained energy is more evidence; at equal energy a higher rank is less surprising."""
    ess = np.array([5.0, 10.0, 20.0])
    ev = RS.chi2_log10_sf(ess, np.array([3.0, 3.0, 3.0]))
    assert ev[0] < ev[1] < ev[2]
    same = np.array([10.0, 10.0, 10.0])
    ev_rank = RS.chi2_log10_sf(same, np.array([1.0, 2.0, 3.0]))
    assert ev_rank[0] > ev_rank[1] > ev_rank[2]
    assert float(RS.chi2_log10_sf(np.array([5.0]), np.array([0.0]))[0]) == 0.0
