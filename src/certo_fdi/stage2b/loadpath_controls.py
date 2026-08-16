"""The five source-of-gain controls that decompose Stage 2A's contact-localization gain.

Stage 2A found that a shuffled-time control reproduced ~90 % of the localization gain, so the
gain was attributed to serial-chain **load-path support** rather than to configuration-dependent
Cartesian geometry. Stage 2B has to say *how much* comes from each ingredient, which needs
controls that are matched in every respect except the ingredient under test.

The ladder, from least to most information:

===============================  =====================================================
``support_prefix_rankmatched``   only the serial-chain support mask: link ``l`` loads joints
                                 ``0..l``. A deterministic DCT basis inside that support, with
                                 **exactly** the aligned dictionary's numerical rank. No
                                 configuration value is read at all.
``random_within_support_rank…``  the same support and rank, but fixed-seed random orthonormal
                                 bases. 16 replicates; the distribution is reported, never the
                                 best one. Answers "would any subspace of this shape do?".
``fixed_reference_jacobian``     genuine Cartesian subspace shape from one reference
                                 configuration chosen on healthy **training** data, repeated
                                 across the window. Real geometry, no trajectory alignment.
``shuffled_time_jacobian``       the frozen Stage 2A control: real per-window Jacobians at
                                 permuted time indices of the same episode.
``time_aligned_jacobian``        the deployed Stage 2A dictionary at the observed configurations.
===============================  =====================================================

Matching rules, all asserted in ``tests/test_stage2b_rank_matching.py`` and
``tests/test_stage2b_support_masks.py``:

* **support** — every control's dictionary has non-zero rows only on link ``l``'s prefix
  support, in the *unwhitened* residual coordinates. Support is defined before whitening,
  because ``W_0`` mixes rows and would otherwise destroy it.
* **rank** — the support and random controls are built at exactly the numerical rank of that
  window's aligned dictionary, so a control can never win or lose through extra dimensions.
* **hypothesis count** — the aligned/shuffled/fixed methods pick the best of the 10 geometric
  candidate points per link. The support control therefore also picks the best of 10
  deterministic bases, and each random replicate picks the best of 10 random bases. Without
  this the aligned method would carry an unmatched model-selection advantage.

The window residual is laid out time-major: row ``m*n + j`` is joint ``j`` at window time point
``m``. Link ``l``'s support is ``{m*n + j : j <= l}``, of size ``(l+1)*M``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from certo_fdi.pathways.dictionaries import EpisodePathways, contact_columns_batched
from certo_fdi.pathways.geometry import orthonormal_basis

METHODS = (
    "support_prefix_rankmatched",
    "random_within_support_rankmatched",
    "fixed_reference_jacobian",
    "shuffled_time_jacobian",
    "time_aligned_jacobian",
)
#: methods that read a real configuration (the ones a Cartesian-geometry claim could rest on)
GEOMETRIC_METHODS = ("fixed_reference_jacobian", "shuffled_time_jacobian", "time_aligned_jacobian")
#: methods that read no configuration value at all
NON_GEOMETRIC_METHODS = ("support_prefix_rankmatched", "random_within_support_rankmatched")


def support_rows(link: int, n_joints: int, n_time: int) -> np.ndarray:
    """Row indices of link ``link``'s prefix support in the time-major window residual."""
    j = np.arange(link + 1)
    return np.concatenate([m * n_joints + j for m in range(n_time)])


def support_mask(link: int, n_joints: int, n_time: int) -> np.ndarray:
    m = np.zeros(n_joints * n_time, dtype=bool)
    m[support_rows(link, n_joints, n_time)] = True
    return m


# --------------------------------------------------------------------------- deterministic basis
def dct_basis(k: int, rank: int, offset: int = 0) -> np.ndarray:
    """(k, rank) orthonormal DCT-II frame, taking ``rank`` frequencies from ``offset``.

    Deterministic, configuration-free and reproducible; ``offset`` gives the 10 distinct
    hypotheses that match the aligned method's 10 candidate points.
    """
    if rank <= 0 or k <= 0:
        return np.zeros((max(k, 0), 0))
    rank = int(min(rank, k))
    idx = (offset + np.arange(rank)) % k
    t = (np.arange(k)[:, None] + 0.5) * np.pi / k
    B = np.cos(t * idx[None, :])
    q = orthonormal_basis(B)
    if q.shape[1] < rank:  # pathological offsets can collide; fall back to the leading frequencies
        B = np.cos(t * np.arange(rank)[None, :])
        q = orthonormal_basis(B)
    return q[:, :rank]


def random_basis(k: int, rank: int, seed: int) -> np.ndarray:
    """(k, rank) fixed-seed random orthonormal frame."""
    if rank <= 0 or k <= 0:
        return np.zeros((max(k, 0), 0))
    rank = int(min(rank, k))
    g = np.random.default_rng(seed).normal(size=(k, rank))
    q = orthonormal_basis(g)
    return q[:, :rank]


def embed(basis: np.ndarray, rows: np.ndarray, d: int) -> np.ndarray:
    """Place a (k, r) support-local basis into the full (d, r) window residual space."""
    out = np.zeros((d, basis.shape[1]))
    out[rows] = basis
    return out


# --------------------------------------------------------------------------- dictionary builders
@dataclass
class LinkDictionaries:
    """Per-link candidate dictionaries of one control, for one batch of windows.

    ``per_hypothesis`` is a list (over hypotheses: candidate points or basis offsets) of
    ``(Nw, d, r)`` **whitened** dictionaries. The scorer takes the best hypothesis per window,
    exactly as Stage 2A did over its candidate points.
    """

    method: str
    link: int
    per_hypothesis: list[np.ndarray]
    ranks: np.ndarray                 # (Nw,) numerical rank actually realised
    support_rows: np.ndarray
    meta: dict


def aligned_dictionaries(ep: EpisodePathways, rows: np.ndarray, link: int, candidate_points: list, whiten) -> LinkDictionaries:
    """``time_aligned_jacobian``: the deployed Stage 2A dictionary."""
    hyps = [whiten(contact_columns_batched(ep, rows, link, r_link)) for _, r_link in candidate_points]
    return LinkDictionaries("time_aligned_jacobian", link, hyps, _ranks(hyps),
                            support_rows(link, ep.n_links, rows.shape[1]),
                            {"n_hypotheses": len(hyps), "reads_configuration": True})


def shuffled_dictionaries(ep: EpisodePathways, shuffle_rows: np.ndarray, link: int, candidate_points: list, whiten) -> LinkDictionaries:
    """``shuffled_time_jacobian``: real Jacobians at permuted time indices of the same episode."""
    hyps = [whiten(contact_columns_batched(ep, shuffle_rows, link, r_link)) for _, r_link in candidate_points]
    return LinkDictionaries("shuffled_time_jacobian", link, hyps, _ranks(hyps),
                            support_rows(link, ep.n_links, shuffle_rows.shape[1]),
                            {"n_hypotheses": len(hyps), "reads_configuration": True,
                             "note": "link identity preserved, time alignment destroyed"})


def fixed_reference_dictionaries(j_ref: np.ndarray, r_ref: np.ndarray, n_windows: int, n_time: int,
                                 link: int, candidate_points: list, whiten, n_joints: int) -> LinkDictionaries:
    """``fixed_reference_jacobian``: one healthy-train configuration repeated across the window.

    ``j_ref`` is ``(n_links, 6, n)`` and ``r_ref`` is ``(n_links, 3, 3)`` at the reference
    configuration. The same block is stacked ``n_time`` times, so the subspace has genuine
    Cartesian shape but no trajectory alignment at all.
    """
    from certo_fdi.pathways.jacobians import skew

    hyps = []
    for _, r_link in candidate_points:
        r_world = r_ref[link] @ np.asarray(r_link, dtype=float)
        Jp = j_ref[link, 3:, :] - skew(r_world) @ j_ref[link, :3, :]      # (3, n)
        block = -Jp.T                                                     # (n, 3)
        D = np.tile(block, (n_time, 1)).reshape(n_time * n_joints, 3)
        hyps.append(whiten(np.broadcast_to(D, (n_windows,) + D.shape).copy()))
    return LinkDictionaries("fixed_reference_jacobian", link, hyps, _ranks(hyps),
                            support_rows(link, n_joints, n_time),
                            {"n_hypotheses": len(hyps), "reads_configuration": True,
                             "note": "one reference configuration chosen on healthy TRAIN data only"})


def support_dictionaries(link: int, target_rank: np.ndarray, n_windows: int, n_time: int,
                         n_joints: int, whiten, n_hypotheses: int = 10) -> LinkDictionaries:
    """``support_prefix_rankmatched``: deterministic DCT bases inside the prefix support.

    ``target_rank`` is per window; bases are precomputed per distinct rank so the construction
    stays cheap. No configuration value is read.
    """
    d = n_joints * n_time
    rows = support_rows(link, n_joints, n_time)
    k = len(rows)
    target_rank = np.asarray(target_rank, dtype=int)
    rmax = int(target_rank.max()) if target_rank.size else 0
    cache = {(r, o): embed(dct_basis(k, r, offset=o * max(1, k // max(n_hypotheses, 1))), rows, d)
             for r in range(rmax + 1) for o in range(n_hypotheses)}
    hyps = []
    for o in range(n_hypotheses):
        D = np.zeros((n_windows, d, max(rmax, 1)))
        for w in range(n_windows):
            b = cache[(int(target_rank[w]), o)]
            D[w, :, : b.shape[1]] = b
        hyps.append(whiten(D))
    return LinkDictionaries("support_prefix_rankmatched", link, hyps, target_rank.copy(), rows,
                            {"n_hypotheses": n_hypotheses, "reads_configuration": False,
                             "basis": "DCT-II orthonormal, restricted to the prefix support",
                             "support_size": k})


def random_support_dictionaries(link: int, target_rank: np.ndarray, n_windows: int, n_time: int,
                                n_joints: int, whiten, replicate: int, seed_base: int,
                                n_hypotheses: int = 10) -> LinkDictionaries:
    """``random_within_support_rankmatched``: one fixed-seed replicate of random support bases."""
    d = n_joints * n_time
    rows = support_rows(link, n_joints, n_time)
    k = len(rows)
    target_rank = np.asarray(target_rank, dtype=int)
    rmax = int(target_rank.max()) if target_rank.size else 0
    cache = {(r, o): embed(random_basis(k, r, seed=seed_base + 1009 * replicate + 97 * o + 7 * link + r), rows, d)
             for r in range(rmax + 1) for o in range(n_hypotheses)}
    hyps = []
    for o in range(n_hypotheses):
        D = np.zeros((n_windows, d, max(rmax, 1)))
        for w in range(n_windows):
            b = cache[(int(target_rank[w]), o)]
            D[w, :, : b.shape[1]] = b
        hyps.append(whiten(D))
    return LinkDictionaries("random_within_support_rankmatched", link, hyps, target_rank.copy(), rows,
                            {"n_hypotheses": n_hypotheses, "reads_configuration": False,
                             "replicate": replicate, "seed_base": seed_base, "support_size": k})


def _ranks(hyps: list[np.ndarray], rtol: float = 1e-8) -> np.ndarray:
    """(Nw,) numerical rank of the *best* (largest-rank) hypothesis, used as the match target."""
    if not hyps:
        return np.zeros(0, dtype=int)
    n = hyps[0].shape[0]
    out = np.zeros((len(hyps), n), dtype=int)
    for h, D in enumerate(hyps):
        s = np.linalg.svd(D, compute_uv=False)                 # (Nw, p)
        smax = s[:, :1]
        out[h] = (s > np.maximum(smax * rtol, 1e-300)).sum(1)
    return out.max(0)


def unwhitened_support_check(ep: EpisodePathways, rows: np.ndarray, link: int, r_link) -> dict:
    """Assert that the *raw* aligned dictionary really has the prefix support (audit helper)."""
    D = contact_columns_batched(ep, rows, link, r_link)          # (Nw, d, 3) unwhitened
    d = D.shape[1]
    mask = support_mask(link, ep.n_links, rows.shape[1])
    outside = float(np.abs(D[:, ~mask, :]).max()) if (~mask).any() else 0.0
    inside = float(np.abs(D[:, mask, :]).max())
    return {"link": link, "support_size": int(mask.sum()), "dimension": int(d),
            "max_abs_outside_support": outside, "max_abs_inside_support": inside,
            "support_respected": bool(outside <= 1e-12 * max(inside, 1.0))}


def reference_configuration(q_healthy_train: np.ndarray) -> np.ndarray:
    """The fixed reference configuration: the element-wise median of healthy TRAIN configurations.

    Healthy training data only -- no validation, no fault, no test episode contributes. Using the
    median rather than a random draw makes it deterministic and reproducible from the manifest.
    """
    return np.median(np.asarray(q_healthy_train, dtype=float), axis=0)
