"""How far apart are the two estimators the reproduction gate compares?

The Stage 2B contact reproduction gate compares a Stage 2A reference number against a Stage 2B
observed number. Reading the frozen code shows the two sides do not compute the same statistic:

``Stage 2A`` -- ``pathways.window_features._project`` -> ``pathways.geometry.batched_projection``
    a **ridge normal-equations** solve. ``lambda = max(1e-6 sigma_max^2, sigma_max^2/1e6, 1e-12)``,
    ``theta = (D^T D + lambda I)^-1 D^T z``, and the link is ranked by the residual **norm**.
    Every column is kept; nothing is truncated.

``Stage 2B`` -- ``stage2b.rank_aware_scores.project``
    an **exact rank-truncated orthogonal projection**. Columns with ``s <= s_0 * 1e-8`` are
    discarded outright, and the link is ranked by the residual **energy**.

The norm-versus-energy difference is monotone and cannot change an ``argmin``. The other two
differences can. This module measures how much, using the repository's own frozen functions --
never a re-implementation -- so the size of the gap is a measurement rather than an argument.

The closed form explains what the measurement shows. Writing ``c_i = u_i^T z`` for the residual's
component along the i-th left singular direction, the ridge leaves

    resid^2_ridge - resid^2_exact = sum_i c_i^2 * lambda^2 / (sigma_i^2 + lambda)^2

over the directions the exact projector retains. With ``lambda = 1e-6 sigma_max^2`` that weight is

    ~1e-12 c_i^2                 when sigma_i ~ sigma_max        (negligible)
    ~0.25  c_i^2                 when sigma_i = 1e-3 sigma_max   (a quarter of the direction)
    ~0.98  c_i^2                 when sigma_i = 1e-4 sigma_max   (essentially the whole direction)

So the two scores agree to roundoff only for well-conditioned dictionaries. Once the condition
number passes about 1e3 they differ by an O(1) fraction of a singular direction's energy -- ten
or more orders of magnitude above the ``1000 * eps64`` roundoff floor. The frozen code itself
records that this regime is the normal one: ``geometry.orthonormal_basis`` notes the per-link
contact dictionaries are "frequently rank deficient -- link l loads only joints 0..l, and nearby
window samples are almost collinear".

Nothing here changes any scientific quantity. It is a diagnostic that measures two frozen
implementations against each other.
"""

from __future__ import annotations

import numpy as np

from certo_fdi.pathways.geometry import batched_projection
from certo_fdi.stage2b.rank_aware_scores import project as exact_project

EPS64 = 2.220446049250313e-16
#: the frozen roundoff floor a numerical tie would have to fit inside (contract §4, factor 1000)
ROUNDOFF_FACTOR = 1000


def stage2a_residual_energy(D: np.ndarray, z: np.ndarray) -> np.ndarray:
    """The Stage 2A score, squared onto the Stage 2B scale so the two are comparable.

    Stage 2A ranks by ``projection_residual`` (a norm); squaring is monotone and therefore changes
    no label, but it puts both estimators in the same units.
    """
    return np.asarray(batched_projection(D, z)["projection_residual_energy"], dtype=float)


def stage2b_residual_energy(D: np.ndarray, z: np.ndarray) -> np.ndarray:
    """The Stage 2B score: exact rank-truncated projection residual energy."""
    _ess, rss, _rank = exact_project(D, z)
    return np.asarray(rss, dtype=float)


def conditioned_dictionary(rng: np.random.Generator, n: int, d: int, p: int, condition: float) -> np.ndarray:
    """A batch of (d, p) dictionaries with a prescribed condition number.

    Singular values are geometrically spaced from 1 down to ``1/condition``, which is how an
    almost-collinear stack of window samples actually degrades.
    """
    s = np.geomspace(1.0, 1.0 / float(condition), p)
    D = np.empty((n, d, p))
    for i in range(n):
        U = np.linalg.qr(rng.normal(size=(d, p)))[0]
        V = np.linalg.qr(rng.normal(size=(p, p)))[0]
        D[i] = (U * s) @ V.T
    return D


def gap_report(D: np.ndarray, z: np.ndarray) -> dict:
    """Per-window absolute and relative gap between the two frozen estimators."""
    a = stage2a_residual_energy(D, z)
    b = stage2b_residual_energy(D, z)
    z_energy = (np.asarray(z, dtype=float) ** 2).sum(1)
    scale = np.maximum(1.0, np.maximum(np.abs(a), np.abs(b)))
    abs_gap = np.abs(a - b)
    floor = ROUNDOFF_FACTOR * EPS64 * scale
    return {
        "stage2a_rss": a, "stage2b_rss": b,
        "abs_gap": abs_gap,
        "rel_gap": abs_gap / np.maximum(np.abs(b), 1e-300),
        "gap_over_roundoff_floor": abs_gap / floor,
        "fraction_of_z_energy": abs_gap / np.maximum(z_energy, 1e-300),
    }


def label_disagreement(link_dicts: list[np.ndarray], z: np.ndarray) -> dict:
    """How often the two estimators pick a different link, over the same frozen arrays.

    ``link_dicts`` is one (Nw, d, p) dictionary per candidate link. Both sides use the frozen
    ``argmin`` over links, so any disagreement is caused by the score, not by the aggregation.
    """
    A = np.stack([stage2a_residual_energy(D, z) for D in link_dicts], 1)
    B = np.stack([stage2b_residual_energy(D, z) for D in link_dicts], 1)
    pa, pb = np.argmin(A, axis=1), np.argmin(B, axis=1)
    order_a = np.sort(A, axis=1)
    order_b = np.sort(B, axis=1)
    margin_a = order_a[:, 1] - order_a[:, 0]
    margin_b = order_b[:, 1] - order_b[:, 0]
    differ = pa != pb
    return {
        "predicted_stage2a": pa, "predicted_stage2b": pb,
        "n_windows": int(len(pa)), "n_differ": int(differ.sum()),
        "fraction_differ": float(differ.mean()),
        "margin_stage2a": margin_a, "margin_stage2b": margin_b,
        "median_margin_when_differing": float(np.median(margin_b[differ])) if differ.any() else float("nan"),
        "median_margin_overall": float(np.median(margin_b)),
    }
