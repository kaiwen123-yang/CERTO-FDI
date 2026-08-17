"""Stage 2B-R: numerical-tie-aware contact-localizer reproduction-gate resolution.

This package answers exactly one integrity question and is not allowed to answer any other:

    Did the single Stage 2A/Stage 2B contact-localization label difference arise from a
    numerically equivalent near tie, or from a real difference in frozen inputs, score
    computation, rank handling, candidate ordering, aggregation, or implementation?

Nothing here trains, tunes, generates data, or changes a scientific threshold. The modules are
deliberately narrow:

``decision_stage2br``
    the frozen terminal-state precedence and the tie predicate, reading every number from
    ``configs/stage2br_reproduction_gate.yaml``.
``canonical_scores``
    independent reference implementations of the *already frozen* projection score, used only to
    measure how much the score moves between numerical backends.
``tie_envelope``
    the frozen numerical envelope, tie tolerance and tie sets built from those measurements.

The scientific localizer itself lives in :mod:`certo_fdi.stage2b.rank_aware_scores` and
:mod:`certo_fdi.pathways` and is imported read-only, never modified.
"""

from __future__ import annotations

__all__ = ["decision_stage2br", "canonical_scores", "tie_envelope"]
