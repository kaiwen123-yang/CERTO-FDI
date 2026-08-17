"""Stage 2B-F: contact-localizer estimator harmonization and finalization.

Not a new research stage. Stage 2B gave one name to two different estimators — a ridge-regularised
least-squares residual norm (what Stage 2A actually used) and a rank-truncated SVD orthogonal
projection RSS (what Stage 2B actually computed) — and documented the second as "exactly the frozen
Stage 2A score". Stage 2B-R proved that wrong at score level. Stage 2B-F does four bounded things:

1. reuses the frozen Stage 2A ridge code to build a real ``stage2a_ridge_residual_norm`` control
   and reproduce Stage 2A at score, candidate, window-label, vote and confusion level;
2. renames Stage 2B's score to ``truncated_svd_orthogonal_projection_rss`` and reproduces the
   Stage 2B pipeline, its F4_CAL selection and its F4_TEST metrics unchanged;
3. recomputes the five load-path controls under *both* estimators on identical residuals,
   whitening, dictionaries and episode pairing, so the mechanism conclusions can be checked for
   estimator dependence;
4. only if the integrity gate passes, re-runs the ORIGINAL frozen ``decision_stage2b.decide`` with
   every scientific metric and threshold unchanged.

Modules:

``estimator_identity``
    the two canonical estimators, each bound to its frozen implementation, plus the legacy
    name migration and the guard that keeps historical names out of new results.
``decision_stage2bf``
    integrity precedence, evidence-delta accounting, and the wrapper that refuses to call the
    scientific decision unless integrity passes.
``robustness``
    the 2x5 estimator/control matrix, paired episode-cluster contrasts and robustness labelling.
"""

from __future__ import annotations

__all__ = ["estimator_identity", "decision_stage2bf", "robustness"]
