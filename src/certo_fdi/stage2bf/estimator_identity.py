"""The two contact-localizer estimators, named apart and each bound to its frozen implementation.

Stage 2B described its ``raw_projection_residual`` as "exactly the frozen Stage 2A score". It is
not, and Stage 2B-R proved it at score level. Two genuinely different estimators had been given one
name. This module gives each its own name and, more importantly, binds each to the *frozen code
that actually produced the historical numbers* — neither is re-derived from its formula here,
because an "equivalent" re-implementation is precisely the error being corrected.

``stage2a_ridge_residual_norm``
    Ridge-regularised weighted least squares. ``λ = max(1e-6·σ_max², σ_max²/1e6, 1e-12)``,
    ``θ = (DᵀD + λI)⁻¹Dᵀz``, score ``‖z − Dθ‖₂``. Every column is kept and shrunk continuously;
    nothing is truncated. Frozen in ``pathways/geometry.py`` at Stage 2A commit ``bcf2ad5`` — and
    that file is byte-identical at ``bee5f9b`` and at this branch's HEAD, so importing it here is
    reuse, not reconstruction.

``truncated_svd_orthogonal_projection_rss``
    Exact orthogonal projection onto the SVD range, truncated at ``σᵢ > 1e-8·σ₁``, score
    ``‖(I − P_D)z‖₂²``. Frozen in ``stage2b/rank_aware_scores.py``.

The difference is not the norm-versus-square: that is monotone and moves no ``argmin``. It is the
per-direction gain,

    ridge:  gᵢ = σᵢ²/(σᵢ² + λ)        continuous shrinkage
    svd:    gᵢ ∈ {0, 1}                hard keep/discard

which disagree over ``σᵢ/σ_max ∈ (1e-8, 1e-3)``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# The frozen implementations. Imported, never re-derived.
from certo_fdi.pathways.geometry import batched_projection, ridge_lambda
from certo_fdi.stage2b.rank_aware_scores import RANK_RTOL
from certo_fdi.stage2b.rank_aware_scores import project as _svd_project

RIDGE_CANONICAL = "stage2a_ridge_residual_norm"
SVD_CANONICAL = "truncated_svd_orthogonal_projection_rss"
ESTIMATORS = (RIDGE_CANONICAL, SVD_CANONICAL)

#: historical name -> canonical name. The left column may appear only in legacy readers and in the
#: migration table; never in a new result, figure, schema or sentence.
LEGACY_NAME_MAPPING = {
    "raw_projection_residual": SVD_CANONICAL,
    "df_normalized_residual": "df_normalized_truncated_svd_rss",
    "rank_aware_glrt": "rank_aware_glrt",
    "bic_penalized_fit": "bic_penalized_truncated_svd_fit",
    "minimal_consistent_link": "minimal_consistent_link",
}
#: the Stage 2A score array key, which held the ridge residual norm under a neutral name
LEGACY_STAGE2A_SCORE_KEY = "contact_residual"
FORBIDDEN_IN_NEW_RESULTS = tuple(k for k, v in LEGACY_NAME_MAPPING.items() if k != v)


@dataclass
class RidgeResult:
    """Per-window ridge statistics for one dictionary (contract 04 §1)."""

    residual_norm: np.ndarray        # (N,)  the Stage 2A score
    residual_energy: np.ndarray      # (N,)  its square, for comparison against the SVD unit
    ridge_lambda: np.ndarray         # (N,)
    theta: np.ndarray                # (N, p)
    explained_energy: np.ndarray     # (N,)
    z_energy: np.ndarray             # (N,)


def stage2a_ridge_residual_norm(D: np.ndarray, z: np.ndarray) -> RidgeResult:
    """The frozen Stage 2A contact-localization score, as a thin wrapper.

    ``D`` is ``(N, d, p)`` (or ``(d, p)``, broadcast), ``z`` is ``(N, d)``. The wrapper changes no
    dtype, no lambda, no candidate reduction and no unit: it calls
    :func:`certo_fdi.pathways.geometry.batched_projection` and renames its outputs.

    ``batched_projection`` computes ``λ`` internally via :func:`ridge_lambda` when none is passed,
    which is exactly what Stage 2A did, so ``λ`` is never supplied here.
    """
    p = batched_projection(np.asarray(D, dtype=float), np.asarray(z, dtype=float))
    return RidgeResult(
        residual_norm=p["projection_residual"],
        residual_energy=p["projection_residual_energy"],
        ridge_lambda=p["ridge_lambda"],
        theta=p["theta"],
        explained_energy=p["explained_energy"],
        z_energy=p["z_energy"],
    )


def truncated_svd_orthogonal_projection_rss(D: np.ndarray, z: np.ndarray,
                                            rtol: float = RANK_RTOL) -> dict[str, np.ndarray]:
    """The frozen Stage 2B contact-localization score, as a thin wrapper.

    Calls :func:`certo_fdi.stage2b.rank_aware_scores.project` unchanged; ``rtol`` defaults to the
    frozen ``RANK_RTOL = 1e-8`` and is exposed only so the diagnostic sweep can vary it.
    """
    ess, rss, rank = _svd_project(np.asarray(D, dtype=float), np.asarray(z, dtype=float), rtol)
    return {"residual_energy": rss, "explained_energy": ess, "rank": rank,
            "z_energy": (np.asarray(z, dtype=float) ** 2).sum(1)}


def ridge_gain(sigma: np.ndarray, lam: float) -> np.ndarray:
    """Ridge's per-direction retention ``σᵢ²/(σᵢ²+λ)`` — continuous, in ``(0, 1)``."""
    s2 = np.asarray(sigma, dtype=float) ** 2
    return s2 / (s2 + float(lam))


def svd_gain(sigma: np.ndarray, rtol: float = RANK_RTOL) -> np.ndarray:
    """Truncated-SVD's per-direction retention — hard ``{0, 1}`` at ``σᵢ > rtol·σ₁``."""
    s = np.asarray(sigma, dtype=float)
    if s.size == 0:
        return s
    return (s > max(float(s[0]) * float(rtol), 1e-300)).astype(float)


def best_candidate_reduction(scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-window minimum over candidate contact points, and which candidate won.

    ``scores`` is ``(n_candidates, N)``. Both stages take ``argmin`` over candidate points, and
    NumPy's ``argmin`` returns the first minimum, so an exact tie resolves to the earlier candidate
    index. Stated here because the candidate index has to reproduce exactly, not merely the score.
    """
    s = np.asarray(scores, dtype=float)
    best = np.argmin(s, axis=0)
    return s[best, np.arange(s.shape[1])], best.astype(int)


def canonical_name(name: str) -> str:
    """Map a historical score name to its canonical one; canonical names pass through."""
    if name in LEGACY_NAME_MAPPING:
        return LEGACY_NAME_MAPPING[name]
    if name in set(LEGACY_NAME_MAPPING.values()) or name in ESTIMATORS:
        return name
    raise KeyError(f"unknown score name {name!r}")


def assert_no_legacy_names(payload) -> None:
    """Raise if a new result carries a historical name that has been renamed.

    Applied to every Stage 2B-F table and JSON before it is written. ``rank_aware_glrt`` and
    ``minimal_consistent_link`` are unchanged names and are therefore allowed.
    """
    text = payload if isinstance(payload, str) else repr(payload)
    hits = sorted({n for n in FORBIDDEN_IN_NEW_RESULTS if n in text})
    if hits:
        raise ValueError(f"new Stage 2B-F output carries legacy estimator name(s): {hits}")


def identity_map_rows() -> list[dict]:
    """The migration table shipped with every result set (contract 04 §6)."""
    return [
        {"historical_stage": "Stage2A", "historical_name": LEGACY_STAGE2A_SCORE_KEY,
         "actual_definition": "ridge WLS residual norm; lambda=max(1e-6*smax^2,smax^2/1e6,1e-12)",
         "canonical_name": RIDGE_CANONICAL, "estimator_family": "ridge",
         "score_unit": "residual_norm", "higher_is_better": False,
         "selection_role": "audit_baseline",
         "historical_source_commit": "bcf2ad5c978f58dc159636d64d0b5c81efb9e396",
         "source_file": "src/certo_fdi/pathways/geometry.py",
         "source_functions": "ridge_lambda|batched_projection"},
        {"historical_stage": "Stage2B", "historical_name": "raw_projection_residual",
         "actual_definition": "rank-truncated SVD orthogonal projection residual energy; rtol=1e-8",
         "canonical_name": SVD_CANONICAL, "estimator_family": "truncated_svd",
         "score_unit": "residual_energy", "higher_is_better": False,
         "selection_role": "stage2b_candidate",
         "historical_source_commit": "bee5f9b7e21b511c39936a047acaff39cfcfb395",
         "source_file": "src/certo_fdi/stage2b/rank_aware_scores.py", "source_functions": "project"},
        {"historical_stage": "Stage2B", "historical_name": "df_normalized_residual",
         "actual_definition": "truncated-SVD RSS divided by residual degrees of freedom",
         "canonical_name": "df_normalized_truncated_svd_rss",
         "estimator_family": "truncated_svd_rank_aware", "score_unit": "normalized_energy",
         "higher_is_better": False, "selection_role": "stage2b_candidate",
         "historical_source_commit": "bee5f9b7e21b511c39936a047acaff39cfcfb395",
         "source_file": "src/certo_fdi/stage2b/rank_aware_scores.py", "source_functions": "score_matrix"},
        {"historical_stage": "Stage2B", "historical_name": "rank_aware_glrt",
         "actual_definition": "rank-aware chi-square/GLRT score from truncated-SVD explained energy",
         "canonical_name": "rank_aware_glrt", "estimator_family": "truncated_svd_rank_aware",
         "score_unit": "log_tail_score", "higher_is_better": True,
         "selection_role": "stage2b_candidate",
         "historical_source_commit": "bee5f9b7e21b511c39936a047acaff39cfcfb395",
         "source_file": "src/certo_fdi/stage2b/rank_aware_scores.py", "source_functions": "score_matrix"},
        {"historical_stage": "Stage2B", "historical_name": "bic_penalized_fit",
         "actual_definition": "BIC-penalized truncated-SVD fit",
         "canonical_name": "bic_penalized_truncated_svd_fit",
         "estimator_family": "truncated_svd_rank_aware", "score_unit": "bic_score",
         "higher_is_better": False, "selection_role": "stage2b_candidate",
         "historical_source_commit": "bee5f9b7e21b511c39936a047acaff39cfcfb395",
         "source_file": "src/certo_fdi/stage2b/rank_aware_scores.py", "source_functions": "score_matrix"},
        {"historical_stage": "Stage2B", "historical_name": "minimal_consistent_link",
         "actual_definition": "smallest link whose truncated-SVD RSS passes healthy-calibrated adequacy",
         "canonical_name": "minimal_consistent_link", "estimator_family": "truncated_svd_rank_aware",
         "score_unit": "link_rule", "higher_is_better": False, "selection_role": "stage2b_candidate",
         "historical_source_commit": "bee5f9b7e21b511c39936a047acaff39cfcfb395",
         "source_file": "src/certo_fdi/stage2b/rank_aware_scores.py", "source_functions": "score_matrix"},
    ]
