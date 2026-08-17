"""The canonical reference implementations compute the frozen quantity, five different ways.

The load-bearing test is the first one: the reference module must reproduce
``certo_fdi.stage2b.rank_aware_scores.project`` -- the code that actually produced the Stage 2A
and Stage 2B numbers -- **bit-exactly**. Everything after it measures how far the same quantity
moves between LAPACK paths, memory layouts, candidate orderings and thread counts, which is what
the numerical envelope is built from.

No frozen run artifact is required: these run on synthetic arrays and pin the arithmetic itself.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from certo_fdi.stage2b import rank_aware_scores as RS
from certo_fdi.stage2br import canonical_scores as CS

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "stage2br_reproduction_gate.yaml").read_text())
SE = CFG["score_equivalence"]
ATOL, RTOL = float(SE["score_absolute_scale"]), float(SE["score_relative_tolerance"])


def _dicts(rng, n=24, d=16, p=3, rank=None):
    """A batch of dictionaries, optionally rank-deficient by construction."""
    D = rng.normal(size=(n, d, p))
    if rank is not None and rank < p:
        for i in range(n):
            D[i, :, rank:] = D[i, :, :rank] @ rng.normal(size=(rank, p - rank))
    return D


# --------------------------------------------------------------------- 1. exact agreement
@pytest.mark.parametrize("rank", [None, 1, 2])
def test_frozen_batched_backend_is_bit_identical_to_the_production_code(rank):
    """The definitional reference must BE the frozen code, not a re-implementation of it."""
    rng = np.random.default_rng(260817)
    D = _dicts(rng, rank=rank)
    z = rng.normal(size=(D.shape[0], D.shape[1]))
    ess_f, rss_f, rank_f = RS.project(D, z)
    for i in range(D.shape[0]):
        r = CS.project(D[i], z[i], "frozen_batched")
        assert r.ess == ess_f[i], f"window {i}: ESS differs"
        assert r.rss == rss_f[i], f"window {i}: RSS differs"
        assert r.rank == int(rank_f[i]), f"window {i}: rank differs"


@pytest.mark.parametrize("rank", [None, 1, 2])
def test_single_matrix_backend_agrees_with_the_frozen_path_to_a_few_ulp(rank):
    """Batched-plus-einsum and single-matrix-plus-matmul are the same mathematics.

    They are not bit-identical -- different contraction order, different LAPACK entry -- and that
    residue is exactly the implementation noise the envelope is supposed to contain. It is
    measured here (a few ULP) rather than asserted to be zero, because asserting it away would
    hide the only scale a genuine floating-point tie can live at.
    """
    rng = np.random.default_rng(260817)
    D = _dicts(rng, rank=rank)
    z = rng.normal(size=(D.shape[0], D.shape[1]))
    _e, rss_f, rank_f = RS.project(D, z)
    worst = 0.0
    for i in range(D.shape[0]):
        r = CS.project(D[i], z[i], "numpy_svd")
        assert r.rank == int(rank_f[i]), f"window {i}: rank must be identical, not merely close"
        rel = abs(r.rss - rss_f[i]) / max(abs(float(rss_f[i])), 1e-300)
        worst = max(worst, rel)
    ulp = worst / np.finfo(float).eps
    assert ulp <= CS.BATCHED_VS_SINGLE_MAX_ULP, f"single-matrix path drifted {ulp:.1f} ULP"
    # and that noise must sit far INSIDE the roundoff floor a tie is measured against
    assert worst < float(SE["roundoff_factor"]) * np.finfo(float).eps


def test_frozen_rank_rule_is_the_frozen_constant():
    assert CS.RANK_RTOL == RS.RANK_RTOL == 1e-8


def test_zero_dictionary_explains_nothing():
    z = np.array([1.0, 2.0, 3.0])
    r = CS.project(np.zeros((3, 2)), z, "numpy_svd")
    assert r.rank == 0 and r.ess == 0.0
    assert r.rss == pytest.approx(float(z @ z))


def test_rank_deficient_dictionary_contributes_only_its_range():
    rng = np.random.default_rng(11)
    base = rng.normal(size=(8, 2))
    D = np.column_stack([base, base @ rng.normal(size=(2, 2))])   # 4 columns, rank 2
    z = rng.normal(size=8)
    r = CS.project(D, z, "numpy_svd")
    assert r.rank == 2
    Q = np.linalg.qr(base)[0]
    assert r.ess == pytest.approx(float(np.sum((Q.T @ z) ** 2)))


# --------------------------------------------------------------------- 2. backend agreement
def test_all_svd_backends_agree_within_the_frozen_score_tolerance():
    rng = np.random.default_rng(260815)
    D, z = _dicts(rng, n=12), None
    z = rng.normal(size=(12, 16))
    for i in range(12):
        res = CS.project_all_backends(D[i], z[i])
        ref = res["numpy_svd"].rss
        for name in ("scipy_svd_gesdd", "scipy_svd_gesvd"):
            assert abs(res[name].rss - ref) <= ATOL * max(1.0, abs(ref)) + RTOL * abs(ref), name
            assert res[name].rank == res["numpy_svd"].rank


def test_gelsd_matches_the_svd_projection_when_its_rank_matches():
    """Master prompt §11.6: the canonical SVD score matches an independent least-squares score."""
    rng = np.random.default_rng(9)
    D = _dicts(rng, n=12)
    z = rng.normal(size=(12, 16))
    checked = 0
    for i in range(12):
        r = CS.project(D[i], z[i], "scipy_lstsq_gelsd")
        ref = CS.project(D[i], z[i], "numpy_svd").rss
        if r.rank_matches_frozen:
            assert abs(r.rss - ref) <= ATOL * max(1.0, abs(ref)) + RTOL * abs(ref)
            checked += 1
    assert checked == 12, "gelsd should match the frozen rank on well-conditioned dictionaries"


def test_gelsy_result_carries_a_rank_compatibility_flag():
    """gelsy's rank criterion is a condition estimate, so its comparability must be explicit."""
    rng = np.random.default_rng(3)
    D = _dicts(rng, n=6)
    z = rng.normal(size=(6, 16))
    for i in range(6):
        r = CS.project(D[i], z[i], "scipy_lstsq_gelsy")
        assert isinstance(r.rank_matches_frozen, bool)
        assert r.frozen_rank >= 0
        if r.rank_matches_frozen:
            ref = CS.project(D[i], z[i], "numpy_svd").rss
            assert abs(r.rss - ref) <= ATOL * max(1.0, abs(ref)) + RTOL * abs(ref)


def test_every_configured_backend_is_implemented():
    assert set(SE["independent_backends"]) == set(CS.BACKENDS)


# --------------------------------------------------------------------- 3. layout / order / threads
def test_c_and_fortran_memory_order_give_identical_results():
    """Master prompt §11.8."""
    rng = np.random.default_rng(77)
    D = _dicts(rng, n=8)
    z = rng.normal(size=(8, 16))
    for i in range(8):
        c = CS.project_all_backends(D[i], z[i], memory_order="C")
        f = CS.project_all_backends(D[i], z[i], memory_order="F")
        for name in CS.BACKENDS:
            ref = c[name].rss
            assert abs(f[name].rss - ref) <= ATOL * max(1.0, abs(ref)) + RTOL * abs(ref), name


def test_candidate_ordering_does_not_change_the_link_score_vector():
    """Master prompt §11.7: reordering permutes the vector, it does not alter it."""
    rng = np.random.default_rng(5)
    n_links, d, p = 7, 16, 3
    z = rng.normal(size=d)
    dicts = [rng.normal(size=(d, p)) for _ in range(n_links)]
    base = np.array([CS.project(D, z, "numpy_svd").rss for D in dicts])
    for ordering in CFG["score_equivalence"]["candidate_orderings"]:
        perm = CS.candidate_order_permutation(n_links, ordering)
        permuted = np.array([CS.project(dicts[k], z, "numpy_svd").rss for k in perm])
        assert CS.scores_are_permutation_invariant(base, permuted, perm, ATOL, RTOL), ordering


def test_permutation_invariance_check_rejects_a_real_change():
    base = np.array([1.0, 2.0, 3.0])
    perm = np.array([2, 1, 0])
    assert CS.scores_are_permutation_invariant(base, base[perm], perm, ATOL, RTOL)
    assert not CS.scores_are_permutation_invariant(base, base[perm] + 1e-3, perm, ATOL, RTOL)


def test_candidate_order_permutations_are_permutations():
    for ordering in CFG["score_equivalence"]["candidate_orderings"]:
        perm = CS.candidate_order_permutation(7, ordering)
        assert sorted(perm.tolist()) == list(range(7))


# --------------------------------------------------------------------- 4. the frozen chain
def test_candidate_reduction_takes_the_minimum_rss_and_reports_which():
    rng = np.random.default_rng(21)
    z = rng.normal(size=12)
    cands = [rng.normal(size=(12, 3)) for _ in range(4)]
    out = CS.link_rss_from_candidates(cands, z)
    assert out["rss"] == pytest.approx(out["candidate_rss"].min())
    assert out["best_candidate"] == int(np.argmin(out["candidate_rss"]))


def test_candidate_reduction_matches_the_frozen_best_hypothesis_stats():
    rng = np.random.default_rng(260816)
    n, d, p = 10, 14, 3
    z = rng.normal(size=(n, d))
    hyps = [rng.normal(size=(n, d, p)) for _ in range(4)]
    ess_f, rss_f, rank_f, best_f = RS.best_hypothesis_stats(hyps, z)
    for i in range(n):
        out = CS.link_rss_from_candidates([h[i] for h in hyps], z[i], backend="frozen_batched")
        assert out["rss"] == rss_f[i]
        assert out["ess"] == ess_f[i]
        assert out["rank"] == int(rank_f[i])
        assert out["best_candidate"] == int(best_f[i])
        # the same selection must survive the single-matrix path, which is the property that
        # matters: the candidate argmin may not depend on the contraction order
        single = CS.link_rss_from_candidates([h[i] for h in hyps], z[i], backend="numpy_svd")
        assert single["best_candidate"] == int(best_f[i])


def test_window_prediction_is_argmin_and_breaks_ties_to_the_lowest_index():
    out = CS.window_prediction([5.0, 3.0, 3.0, 9.0])
    assert out["predicted_link"] == 1                 # first minimum, not the second
    assert out["is_exact_tie"] is True
    assert out["margin"] == 0.0
    assert out["tie_break"] == "lowest_link_index"


def test_window_prediction_margin_is_second_best_minus_best():
    out = CS.window_prediction([5.0, 3.0, 4.0, 9.0])
    assert out["predicted_link"] == 1
    assert out["best_score"] == 3.0 and out["second_best_score"] == 4.0
    assert out["margin"] == pytest.approx(1.0)
    assert out["is_exact_tie"] is False


def test_window_prediction_matches_the_frozen_predict_link():
    rng = np.random.default_rng(1234)
    n, n_links = 30, 7
    rss = rng.random((n, n_links))
    stats = RS.ProjectionStats(rss=rss, ess=1.0 - rss, rank=np.full((n, n_links), 3),
                               z_energy=np.ones(n), dimension=16)
    frozen = RS.predict_link(stats, "raw_projection_residual")
    for i in range(n):
        assert CS.window_prediction(rss[i])["predicted_link"] == int(frozen[i])


def test_episode_vote_matches_the_frozen_majority_vote():
    rng = np.random.default_rng(42)
    from certo_fdi.experiments.run_stage2b_loadpath import _episode_vote

    for _ in range(50):
        pred = rng.integers(0, 7, size=int(rng.integers(1, 30)))
        assert CS.episode_vote(pred)["predicted_link"] == _episode_vote(pred)


def test_episode_vote_breaks_a_count_tie_to_the_lowest_index():
    out = CS.episode_vote(np.array([3, 3, 5, 5]))
    assert out["predicted_link"] == 3
    assert out["is_vote_tie"] is True and out["vote_margin"] == 0


def test_episode_vote_reports_the_margin_that_makes_a_flip_possible():
    out = CS.episode_vote(np.array([1, 1, 1, 4, 4]))
    assert out["predicted_link"] == 1 and out["vote_margin"] == 1
    assert out["is_vote_tie"] is False
    assert out["n_windows"] == 5


def test_episode_vote_ignores_negative_predictions():
    assert CS.episode_vote(np.array([-1, -1, 2, 2]))["n_windows"] == 2


# --------------------------------------------------------------------- 5. rank threshold proximity
def test_a_singular_value_on_the_threshold_is_reported_as_near():
    """A dictionary built to sit on the cutoff must not look robust."""
    d = 8
    U = np.linalg.qr(np.random.default_rng(0).normal(size=(d, d)))[0]
    s = np.array([1.0, 1.0e-8])                       # exactly at s0 * rtol
    D = U[:, :2] * s
    r = CS.project(D, np.ones(d), "numpy_svd")
    assert r.nearest_threshold_ratio == pytest.approx(1.0, rel=1e-9)


def test_a_well_separated_spectrum_is_reported_as_far_from_the_threshold():
    d = 8
    U = np.linalg.qr(np.random.default_rng(0).normal(size=(d, d)))[0]
    D = U[:, :2] * np.array([1.0, 0.5])
    r = CS.project(D, np.ones(d), "numpy_svd")
    assert r.nearest_threshold_ratio > 1e6


def test_the_rank_diagnostic_sweep_scales_the_cutoff_as_configured():
    """The {0.5, 1, 2} x tol sweep is a diagnostic: it must actually move the rank when it should."""
    d = 8
    U = np.linalg.qr(np.random.default_rng(0).normal(size=(d, d)))[0]
    D = U[:, :2] * np.array([1.0, 1.5e-8])            # sits between 1x and 2x the cutoff
    ranks = {scale: CS.project(D, np.ones(d), "numpy_svd", rtol=CS.RANK_RTOL * scale).rank
             for scale in CFG["score_equivalence"]["rank_tolerance_scale_diagnostic"]}
    assert ranks[0.5] == 2 and ranks[1.0] == 2 and ranks[2.0] == 1
