"""Independent reference implementations of the **already frozen** projection score.

This module changes no science. It recomputes the same quantity the frozen Stage 2A/2B localizer
computes, by five numerically different routes, so the audit can *measure* how far the score moves
between implementations instead of assuming a figure for roundoff. It reads frozen arrays only and
has no import path to training, data generation or model architecture code.

The frozen quantity (``certo_fdi.stage2b.rank_aware_scores.project``) is, for a dictionary
``D`` (d x p) and a whitened residual ``z`` (d,), with relative rank tolerance ``rtol``:

    U, s, _ = svd(D, full_matrices=False)
    keep    = s > max(s[0] * rtol, 1e-300)
    ESS     = || U[:, keep]^T z ||^2
    RSS     = max(||z||^2 - ESS, 0)
    rank    = keep.sum()

``RSS`` is the frozen Stage 2A audit-control score ``raw_projection_residual`` and the link is
chosen by ``argmin``. Every backend below returns exactly that triple; they differ only in the
LAPACK path used to obtain it.

A note on the two least-squares backends. ``RSS`` is a projection residual, so it equals the
least-squares residual **only when the least-squares solver truncates at the same rank**. ``gelsd``
is an SVD-based solver and takes the same relative singular-value cutoff, so it is directly
comparable. ``gelsy`` decides rank from a pivoted-QR condition estimate, which is a different
criterion; it is computed and reported, but each result carries ``rank_matches_frozen`` and a
backend whose rank disagreed is excluded from the envelope rather than silently averaged into it.
That is what the contract's "where mathematically compatible" means, made explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: the frozen relative rank tolerance -- restated, never redefined here
from certo_fdi.stage2b.rank_aware_scores import RANK_RTOL

#: the production path, used as the definitional reference every other backend is measured against
REFERENCE_BACKEND = "frozen_batched"
BACKENDS = ("numpy_svd", "scipy_svd_gesdd", "scipy_svd_gesvd", "scipy_lstsq_gelsd", "scipy_lstsq_gelsy")
#: reference plus the five configured independent implementations
ALL_BACKENDS = (REFERENCE_BACKEND,) + BACKENDS
#: backends whose rank criterion is the frozen relative singular-value cutoff
RANK_EXACT_BACKENDS = ("numpy_svd", "scipy_svd_gesdd", "scipy_svd_gesvd", "scipy_lstsq_gelsd")
SINGULAR_FLOOR = 1e-300

#: measured on this host: the frozen batched path and a single-matrix path compute the same
#: quantity to 2.83 ULP (max relative 6.28e-16 over 2000 random 56x3 dictionaries), i.e. 0.003 of
#: the 1000*eps roundoff floor. This is the scale a genuine floating-point tie lives at, and it is
#: the reason the batched/single difference is folded into the envelope rather than asserted away.
BATCHED_VS_SINGLE_MAX_ULP = 8.0


@dataclass
class ProjectionResult:
    """One (window, link, candidate) projection under one backend."""

    ess: float
    rss: float
    rank: int
    singular_values: np.ndarray
    backend: str
    rank_matches_frozen: bool = True
    frozen_rank: int = -1
    #: smallest ratio ``s_i / (s_0 * rtol)`` over retained values, and largest over discarded ones;
    #: a value near 1 means a singular value sits on the rank threshold
    nearest_threshold_ratio: float = float("inf")
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- rank, stated once
def frozen_rank(s: np.ndarray, rtol: float = RANK_RTOL) -> tuple[np.ndarray, float]:
    """The frozen keep-mask and the distance of the nearest singular value to the threshold.

    ``nearest_threshold_ratio`` is ``min |log10(s_i / cut)|`` expressed as a plain ratio: the
    closest any singular value comes to the cutoff, from either side. A ratio inside ``[0.5, 2]``
    means the rank of this dictionary is not robust to the diagnostic sweep, which the tie
    predicate treats as disqualifying (master prompt §8.1, §8.2).
    """
    s = np.asarray(s, dtype=float)
    if s.size == 0:
        return np.zeros(0, dtype=bool), float("inf")
    cut = max(float(s[0]) * float(rtol), SINGULAR_FLOOR)
    keep = s > cut
    nz = s[s > 0]
    if nz.size == 0 or cut <= 0:
        return keep, float("inf")
    ratios = nz / cut
    # distance to 1 on a multiplicative scale, in both directions
    nearest = float(np.min(np.where(ratios >= 1.0, ratios, 1.0 / np.maximum(ratios, 1e-300))))
    return keep, nearest


def _from_basis(U: np.ndarray, s: np.ndarray, z: np.ndarray, rtol: float, backend: str) -> ProjectionResult:
    keep, nearest = frozen_rank(s, rtol)
    coef = U.T @ z
    ess = float(np.sum((coef * keep) ** 2))
    z_energy = float(z @ z)
    return ProjectionResult(ess=ess, rss=max(z_energy - ess, 0.0), rank=int(keep.sum()),
                            singular_values=np.asarray(s, dtype=float), backend=backend,
                            frozen_rank=int(keep.sum()), nearest_threshold_ratio=nearest)


# --------------------------------------------------------------------------- the five backends
def project_numpy_svd(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL) -> ProjectionResult:
    """Backend 1 -- ``numpy.linalg.svd`` on a single (d,p) matrix.

    Mathematically identical to the frozen path, but *not* bit-identical to it: the frozen code
    factorises a stacked ``(N,d,p)`` array and contracts with ``einsum``, while this factorises one
    matrix and contracts with ``@``. Measured over 2000 random 56x3 dictionaries the two agree to
    2.83 ULP at worst -- 0.003 of the roundoff floor. That residue is genuine implementation noise
    and belongs in the envelope, so it is measured here rather than asserted away.
    """
    U, s, _ = np.linalg.svd(np.asarray(D, dtype=float), full_matrices=False)
    return _from_basis(U, s, np.asarray(z, dtype=float), rtol, "numpy_svd")


def project_frozen_batched(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL) -> ProjectionResult:
    """The production path itself: ``certo_fdi.stage2b.rank_aware_scores.project``.

    This is the definitional reference -- the code that actually produced the Stage 2B numbers.
    Every other backend is measured against it. It is called on a one-window batch so a single
    ``(d,p)`` dictionary can be compared like any other backend.
    """
    from certo_fdi.stage2b.rank_aware_scores import project as _frozen

    D = np.asarray(D, dtype=float)
    z = np.asarray(z, dtype=float)
    ess, rss, rank = _frozen(D[None, ...], z[None, ...], rtol)
    s = np.linalg.svd(D, compute_uv=False)
    _keep, nearest = frozen_rank(s, rtol)
    return ProjectionResult(ess=float(ess[0]), rss=float(rss[0]), rank=int(rank[0]),
                            singular_values=np.asarray(s, dtype=float), backend="frozen_batched",
                            frozen_rank=int(rank[0]), nearest_threshold_ratio=nearest)


def _scipy_svd(D: np.ndarray, z: np.ndarray, rtol: float, driver: str) -> ProjectionResult:
    from scipy.linalg import svd

    U, s, _ = svd(np.asarray(D, dtype=float), full_matrices=False, lapack_driver=driver)
    return _from_basis(U, s, np.asarray(z, dtype=float), rtol, f"scipy_svd_{driver}")


def project_scipy_gesdd(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL) -> ProjectionResult:
    """Backend 2 -- SciPy SVD, LAPACK divide-and-conquer ``gesdd``."""
    return _scipy_svd(D, z, rtol, "gesdd")


def project_scipy_gesvd(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL) -> ProjectionResult:
    """Backend 3 -- SciPy SVD, LAPACK QR-iteration ``gesvd`` (a genuinely different algorithm)."""
    return _scipy_svd(D, z, rtol, "gesvd")


def _lstsq(D: np.ndarray, z: np.ndarray, rtol: float, driver: str) -> ProjectionResult:
    from scipy.linalg import lstsq, svd

    D = np.asarray(D, dtype=float)
    z = np.asarray(z, dtype=float)
    # the frozen rank, for comparison -- computed independently of the solver
    s_ref = svd(D, compute_uv=False)
    keep, nearest = frozen_rank(s_ref, rtol)
    theta, _res, rank, s_solver = lstsq(D, z, cond=float(rtol), lapack_driver=driver)
    resid = z - D @ theta
    rss = float(resid @ resid)
    z_energy = float(z @ z)
    matches = bool(int(rank) == int(keep.sum()))
    return ProjectionResult(
        ess=max(z_energy - rss, 0.0), rss=max(rss, 0.0), rank=int(rank),
        singular_values=np.asarray(s_ref, dtype=float), backend=f"scipy_lstsq_{driver}",
        rank_matches_frozen=matches, frozen_rank=int(keep.sum()), nearest_threshold_ratio=nearest,
        extra={"solver_rank": int(rank), "solver_singular_values":
               (np.asarray(s_solver, dtype=float) if s_solver is not None else None)})


def project_scipy_gelsd(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL) -> ProjectionResult:
    """Backend 4 -- SciPy least squares, SVD-based ``gelsd`` at the frozen relative cutoff."""
    return _lstsq(D, z, rtol, "gelsd")


def project_scipy_gelsy(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL) -> ProjectionResult:
    """Backend 5 -- SciPy least squares, pivoted-QR ``gelsy``.

    Its rank criterion is a condition estimate, not the frozen singular-value cutoff, so the result
    is only comparable when ``rank_matches_frozen`` is True. The caller must honour that flag.
    """
    return _lstsq(D, z, rtol, "gelsy")


_DISPATCH = {
    "frozen_batched": project_frozen_batched,
    "numpy_svd": project_numpy_svd,
    "scipy_svd_gesdd": project_scipy_gesdd,
    "scipy_svd_gesvd": project_scipy_gesvd,
    "scipy_lstsq_gelsd": project_scipy_gelsd,
    "scipy_lstsq_gelsy": project_scipy_gelsy,
}


def project(D: np.ndarray, z: np.ndarray, backend: str = "numpy_svd", rtol: float = RANK_RTOL) -> ProjectionResult:
    """Project ``z`` onto ``range(D)`` under one named backend."""
    if backend not in _DISPATCH:
        raise ValueError(f"unknown backend {backend!r}; expected one of {BACKENDS}")
    return _DISPATCH[backend](D, z, rtol)


def project_all_backends(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL,
                         backends: tuple[str, ...] = BACKENDS,
                         memory_order: str = "C") -> dict[str, ProjectionResult]:
    """Every backend on the same arrays, in the requested memory order."""
    if memory_order.upper() == "F":
        D = np.asfortranarray(D, dtype=float)
        z = np.asfortranarray(z, dtype=float)
    else:
        D = np.ascontiguousarray(D, dtype=float)
        z = np.ascontiguousarray(z, dtype=float)
    return {b: project(D, z, b, rtol) for b in backends}


# --------------------------------------------------------------------------- the frozen chain
def link_rss_from_candidates(candidate_dicts: list[np.ndarray], z: np.ndarray,
                             backend: str = "numpy_svd", rtol: float = RANK_RTOL) -> dict:
    """Step 3 of the frozen chain: the best candidate contact point for one link.

    ``best_hypothesis_stats`` selects ``argmin`` over candidate RSS. NumPy's ``argmin`` returns the
    *first* minimum, so an exact tie between two candidate points resolves to the earlier one; the
    candidate index is reported so a reordering diagnostic can detect exactly that.
    """
    if not candidate_dicts:
        z = np.asarray(z, dtype=float)
        return {"rss": float(z @ z), "ess": 0.0, "rank": 0, "best_candidate": -1,
                "candidate_rss": np.zeros(0), "nearest_threshold_ratio": float("inf"),
                "rank_matches_frozen": True}
    res = [project(D, z, backend, rtol) for D in candidate_dicts]
    rss = np.array([r.rss for r in res], dtype=float)
    b = int(np.argmin(rss))
    return {"rss": float(res[b].rss), "ess": float(res[b].ess), "rank": int(res[b].rank),
            "best_candidate": b, "candidate_rss": rss,
            "nearest_threshold_ratio": float(min(r.nearest_threshold_ratio for r in res)),
            "rank_matches_frozen": bool(all(r.rank_matches_frozen for r in res)),
            "singular_values": res[b].singular_values}


def window_prediction(link_rss: np.ndarray) -> dict:
    """Step 4: ``argmin`` over links, plus the top-2 margin the tie test needs.

    The frozen code calls ``np.argmin``, which returns the first minimum -- so an exact tie is
    broken towards the *lowest link index*. That is reported explicitly rather than left implicit,
    because it is the mechanism by which a near tie can flip a label.
    """
    v = np.asarray(link_rss, dtype=float)
    order = np.argsort(v, kind="stable")
    pred = int(np.argmin(v))
    margin = float(v[order[1]] - v[order[0]]) if v.size > 1 else 0.0
    return {"predicted_link": pred, "order": order.astype(int),
            "best_score": float(v[order[0]]), "second_best_score": float(v[order[1]]) if v.size > 1 else float("nan"),
            "margin": margin, "is_exact_tie": bool(v.size > 1 and v[order[0]] == v[order[1]]),
            "tie_break": "lowest_link_index"}


def episode_vote(window_predictions: np.ndarray, n_links: int = 7) -> dict:
    """Step 5: the frozen majority vote ``np.bincount(pred, minlength=7).argmax()``.

    Deterministic in the counts, and the tie-break is again the lowest link index. Because of that,
    an episode label cannot move unless some window's prediction moved first -- reported here as
    the vote margin so the audit can state it rather than assume it.
    """
    p = np.asarray(window_predictions, dtype=int)
    p = p[p >= 0]
    if p.size == 0:
        return {"predicted_link": -1, "counts": np.zeros(n_links, dtype=int), "vote_margin": 0,
                "is_vote_tie": False, "n_windows": 0}
    counts = np.bincount(p, minlength=n_links)
    order = np.argsort(-counts, kind="stable")
    return {"predicted_link": int(np.argmax(counts)), "counts": counts.astype(int),
            "vote_margin": int(counts[order[0]] - counts[order[1]]) if counts.size > 1 else int(counts[order[0]]),
            "is_vote_tie": bool(counts.size > 1 and counts[order[0]] == counts[order[1]]),
            "n_windows": int(p.size), "tie_break": "lowest_link_index"}


# --------------------------------------------------------------------------- reordering diagnostic
def candidate_order_permutation(n: int, ordering: str, seed: int = 260816) -> np.ndarray:
    """The three frozen candidate orderings (config ``candidate_orderings``)."""
    if ordering == "identity":
        return np.arange(n)
    if ordering == "reverse":
        return np.arange(n)[::-1].copy()
    if ordering.startswith("fixed_random"):
        return np.random.default_rng(seed).permutation(n)
    raise ValueError(f"unknown ordering {ordering!r}")


def scores_are_permutation_invariant(scores: np.ndarray, permuted_scores: np.ndarray,
                                     perm: np.ndarray, atol: float, rtol: float) -> bool:
    """The score *vector* must be invariant under reordering, even where the argmin is not.

    Reordering may legitimately change the predicted index when two links tie exactly, since the
    tie-break is positional. It may never change the scores themselves.
    """
    a = np.asarray(scores, dtype=float)[np.asarray(perm, dtype=int)]
    b = np.asarray(permuted_scores, dtype=float)
    scale = np.maximum(1.0, np.abs(a))
    return bool(np.all(np.abs(a - b) <= atol * scale + rtol * np.abs(a)))
