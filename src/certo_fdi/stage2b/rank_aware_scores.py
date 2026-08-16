"""The five pre-registered rank-aware localization scores (kickoff §04.5).

Stage 2A ranked links by the raw projection residual of a 3-column point-force dictionary. That
score is **not rank fair**: a link whose dictionary happens to have higher numerical rank spans
more of the residual space and therefore fits *anything* better, including healthy noise. With
per-link ranks running from 1 to 3 on this arm, that is a real bias, so Stage 2B compares five
scores that penalise dimension differently and selects one on a separate calibration partition.

For each link ``l`` with whitened dictionary ``D_l``, a numerically stable orthogonal projector
is built from the SVD orthonormal basis ``Q_l`` (never from normal equations), giving

    r_l  = numerical rank,
    ESS_l = ||Q_l^T z||^2,       RSS_l = ||z||^2 - ESS_l.

Scores, and the direction that means "this link explains the residual":

=============================  ===============================================  ==========
``raw_projection_residual``    ``RSS_l``                                         argmin
``df_normalized_residual``     ``RSS_l / (d - r_l)``                             argmin
``rank_aware_glrt``            ``-log10 P(chi2_{r_l} > ESS_l)``                  argmax
``bic_penalized_fit``          ``d log(RSS_l/d) + r_l log d``                     argmin
``minimal_consistent_link``    smallest ``l`` with ``RSS_l`` not rejected        (rule)
=============================  ===============================================  ==========

``raw_projection_residual`` is kept as the **audit control**: it is exactly the frozen Stage 2A
score, so any Stage 2B improvement is measured against it rather than against a strawman.

The chi-square null is the standard one for a projection of a whitened residual. The whitening
is *estimated* from healthy data, so this is a calibrated approximation, not an exact test --
which is why ``minimal_consistent_link`` takes its acceptance threshold empirically from healthy
validation rather than from a nominal chi-square quantile, and why no CFAR claim is made
anywhere in this stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SCORES = (
    "raw_projection_residual",
    "df_normalized_residual",
    "rank_aware_glrt",
    "bic_penalized_fit",
    "minimal_consistent_link",
)
AUDIT_CONTROL_SCORE = "raw_projection_residual"
#: True when a *larger* value of the score means "this link explains the residual better"
HIGHER_IS_BETTER = {"raw_projection_residual": False, "df_normalized_residual": False,
                    "rank_aware_glrt": True, "bic_penalized_fit": False,
                    "minimal_consistent_link": False}
RANK_RTOL = 1e-8


@dataclass
class ProjectionStats:
    """Per-window, per-link projection statistics of one control's dictionaries."""

    rss: np.ndarray            # (Nw, n_links)
    ess: np.ndarray            # (Nw, n_links)
    rank: np.ndarray           # (Nw, n_links) int
    z_energy: np.ndarray       # (Nw,)
    dimension: int
    best_hypothesis: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=int))  # (Nw, n_links)


def project(D: np.ndarray, z: np.ndarray, rtol: float = RANK_RTOL) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact orthogonal projection of ``z`` (N,d) onto ``range(D)`` for ``D`` (N,d,p).

    Returns ``(ess, rss, rank)``. The projector comes from the SVD basis with a relative
    singular-value tolerance, so a rank-deficient dictionary contributes only its true range and
    an identically zero dictionary yields ``ess = 0`` rather than a spurious fit.
    """
    D = np.asarray(D, dtype=float)
    z = np.asarray(z, dtype=float)
    U, s, _ = np.linalg.svd(D, full_matrices=False)             # U (N,d,p), s (N,p)
    keep = s > np.maximum(s[:, :1] * rtol, 1e-300)              # (N,p)
    coef = np.einsum("ndp,nd->np", U, z)                        # (N,p)
    ess = ((coef * keep) ** 2).sum(1)
    z_energy = (z ** 2).sum(1)
    rss = np.maximum(z_energy - ess, 0.0)
    return ess, rss, keep.sum(1).astype(int)


def best_hypothesis_stats(hypotheses: list[np.ndarray], z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Project ``z`` on every hypothesis of one link and keep the best-fitting one per window.

    "Best" is the smallest RSS, matching what Stage 2A did over its candidate contact points.
    Every control gets the same number of hypotheses, so this selection is matched, not free.
    """
    if not hypotheses:
        n = z.shape[0]
        return np.zeros(n), (z ** 2).sum(1), np.zeros(n, dtype=int), np.zeros(n, dtype=int)
    ess_all, rss_all, rank_all = [], [], []
    for D in hypotheses:
        e, r, k = project(D, z)
        ess_all.append(e)
        rss_all.append(r)
        rank_all.append(k)
    ess_all = np.stack(ess_all, 1)
    rss_all = np.stack(rss_all, 1)
    rank_all = np.stack(rank_all, 1)
    best = np.argmin(rss_all, axis=1)
    idx = np.arange(len(best))
    return ess_all[idx, best], rss_all[idx, best], rank_all[idx, best], best


def stack_links(per_link: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]], z: np.ndarray, dimension: int) -> ProjectionStats:
    ess = np.stack([p[0] for p in per_link], 1)
    rss = np.stack([p[1] for p in per_link], 1)
    rank = np.stack([p[2] for p in per_link], 1)
    best = np.stack([p[3] for p in per_link], 1)
    return ProjectionStats(rss=rss, ess=ess, rank=rank, z_energy=(np.asarray(z) ** 2).sum(1),
                           dimension=int(dimension), best_hypothesis=best)


# --------------------------------------------------------------------------- the five scores
def chi2_log10_sf(x: np.ndarray, df: np.ndarray) -> np.ndarray:
    """``-log10 P(chi2_df > x)``; large means the fit is far better than the null allows."""
    from scipy.stats import chi2

    x = np.asarray(x, dtype=float)
    df = np.asarray(df, dtype=float)
    out = np.zeros_like(x)
    ok = df > 0
    if ok.any():
        sf = chi2.sf(x[ok], df[ok])
        out[ok] = -np.log10(np.clip(sf, 1e-300, 1.0))
    out[~ok] = 0.0                       # a rank-0 dictionary explains nothing: no evidence
    return out


def score_matrix(stats: ProjectionStats, name: str, acceptance: np.ndarray | None = None) -> np.ndarray:
    """(Nw, n_links) matrix of one score. Lower is better unless ``HIGHER_IS_BETTER[name]``."""
    d = stats.dimension
    rss = np.maximum(stats.rss, 1e-300)
    if name == "raw_projection_residual":
        return rss.copy()
    if name == "df_normalized_residual":
        return rss / np.maximum(d - stats.rank, 1)
    if name == "rank_aware_glrt":
        return chi2_log10_sf(stats.ess, stats.rank)
    if name == "bic_penalized_fit":
        return d * np.log(rss / d) + stats.rank * np.log(d)
    if name == "minimal_consistent_link":
        if acceptance is None:
            raise ValueError("minimal_consistent_link needs healthy-calibrated per-link acceptance thresholds")
        # rank-ordered preference: accepted links get their index, rejected links get a large value
        consistent = stats.rss <= np.asarray(acceptance, dtype=float)[None, :]
        pref = np.where(consistent, np.arange(stats.rss.shape[1])[None, :].astype(float), np.inf)
        # ties impossible by construction (link index is unique); fall back to raw RSS when nothing
        # is consistent, which is the honest "no link explains this window" case
        none_ok = ~consistent.any(1)
        if none_ok.any():
            pref[none_ok] = rss[none_ok]
        return pref
    raise ValueError(f"unknown score {name!r}")


def predict_link(stats: ProjectionStats, name: str, acceptance: np.ndarray | None = None) -> np.ndarray:
    """(Nw,) per-window predicted contact link under one score."""
    S = score_matrix(stats, name, acceptance)
    return (np.argmax(S, axis=1) if HIGHER_IS_BETTER[name] else np.argmin(S, axis=1)).astype(int)


def link_ranking(stats: ProjectionStats, name: str, acceptance: np.ndarray | None = None) -> np.ndarray:
    """(Nw, n_links) links ordered best-first under one score (used for top-2)."""
    S = score_matrix(stats, name, acceptance)
    return np.argsort(-S if HIGHER_IS_BETTER[name] else S, axis=1).astype(int)


def normalized_link_evidence(stats: ProjectionStats, name: str, acceptance: np.ndarray | None = None) -> np.ndarray:
    """(Nw, n_links) posterior-like normalised evidence, used as an accept/defer feature."""
    S = score_matrix(stats, name, acceptance)
    v = S if HIGHER_IS_BETTER[name] else -S
    v = np.where(np.isfinite(v), v, np.nanmin(np.where(np.isfinite(v), v, np.inf)) - 1.0)
    v = v - v.max(1, keepdims=True)
    e = np.exp(np.clip(v, -50.0, 0.0))
    return e / np.maximum(e.sum(1, keepdims=True), 1e-300)


def score_margin(stats: ProjectionStats, name: str, acceptance: np.ndarray | None = None) -> np.ndarray:
    """(Nw,) best-vs-second-best margin of one score, in that score's own units."""
    S = score_matrix(stats, name, acceptance)
    v = -S if HIGHER_IS_BETTER[name] else S       # smaller is better in v
    part = np.sort(np.where(np.isfinite(v), v, np.inf), axis=1)
    if part.shape[1] < 2:
        return np.zeros(part.shape[0])
    m = part[:, 1] - part[:, 0]
    return np.where(np.isfinite(m), m, 0.0)


def healthy_acceptance_thresholds(rss_healthy: np.ndarray, quantile: float) -> np.ndarray:
    """(n_links,) per-link RSS acceptance thresholds from **healthy validation** windows only."""
    return np.nanquantile(np.asarray(rss_healthy, dtype=float), quantile, axis=0)


# --------------------------------------------------------------------------- rank-bias mutation
def inflate_rank(hypotheses: list[np.ndarray], extra: int, seed: int = 0) -> list[np.ndarray]:
    """Append ``extra`` orthonormal columns carrying no truth-aligned information.

    The added directions are drawn from a fixed seed and orthogonalised against the existing
    dictionary, so they enlarge the subspace without adding any information about the contact.
    A rank-aware score must **not** improve under this mutation; the raw residual score
    necessarily does, which is exactly the bias Stage 2B is testing for
    (``tests/test_stage2b_rank_mutations.py``).
    """
    from certo_fdi.pathways.geometry import orthonormal_basis

    out = []
    rng = np.random.default_rng(seed)
    for h, D in enumerate(hypotheses):
        N, d, p = D.shape
        add = rng.normal(size=(d, extra))
        big = np.empty((N, d, p + extra))
        big[:, :, :p] = D
        for i in range(N):
            Q = orthonormal_basis(D[i])
            a = add - (Q @ (Q.T @ add)) if Q.shape[1] else add
            qa = orthonormal_basis(a)
            k = min(extra, qa.shape[1])
            big[i, :, p:p + k] = qa[:, :k]
            if k < extra:
                big[i, :, p + k:] = 0.0
        out.append(big)
    return out
