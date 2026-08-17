"""The frozen Stage 2B-R integrity decision: terminal-state precedence and the tie predicate.

Committed before any Stage 2B-R score is extracted. Every threshold is read from
``configs/stage2br_reproduction_gate.yaml``; nothing is hard-coded here, and no expected outcome
is baked in. The module deliberately has no import path to training, data generation or model
architecture code -- ``tests/test_stage2br_frozen_protocol.py`` enforces that.

Precedence (master prompt §9, decision rules §A) is evaluated **in order**; the first state whose
conditions hold is the answer:

1. ``BLOCKED_INPUT_PROVENANCE``            -- a frozen input is missing or its hash disagrees
2. ``BLOCKED_SCIENTIFIC_HEAD_MISMATCH``    -- code/config/data changed after the scientific commit
3. ``BLOCKED_MISSING_REFERENCE_EVIDENCE``  -- the frozen score arrays needed do not exist
4. ``BLOCKED_UNRESOLVABLE_SCORE_HISTORY``  -- the arrays exist but cannot be joined or resolved
5. ``FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH``
6. ``PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP``
7. ``PASS_EXACT_REPRODUCTION``

``RANK_THRESHOLD_UNSTABLE`` is **not** a terminal state. It is a modifier reported alongside the
terminal state whenever a label change is caused by a singular value crossing the rank threshold.
It positively forbids the numerical-tie pass, so such a run falls through to (5).
"""

from __future__ import annotations

from typing import Any

TERMINAL_STATES = (
    "BLOCKED_INPUT_PROVENANCE",
    "BLOCKED_SCIENTIFIC_HEAD_MISMATCH",
    "BLOCKED_MISSING_REFERENCE_EVIDENCE",
    "BLOCKED_UNRESOLVABLE_SCORE_HISTORY",
    "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH",
    "PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP",
    "PASS_EXACT_REPRODUCTION",
)
PASS_STATES = ("PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP", "PASS_EXACT_REPRODUCTION")
RANK_INSTABILITY = "RANK_THRESHOLD_UNSTABLE"


def _b(x: Any) -> bool:
    return bool(x) if x is not None else False


def _f(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _finite(x: Any) -> bool:
    v = _f(x)
    return v == v and abs(v) != float("inf")


# --------------------------------------------------------------------- the numerical envelope
def numerical_envelope(backend_scores: list[float], max_abs_score_episode: float, cfg: dict) -> dict:
    """Frozen per-episode/per-link envelope (contract §4).

    ``backend_range`` is the spread of the *same* score across the independent implementations;
    ``roundoff_floor`` is the unconditional double-precision floor. The envelope is the larger --
    a score that happens to agree bit-for-bit across backends still gets the roundoff floor, so a
    tie can never be declared on the strength of a coincidence.
    """
    se = cfg["score_equivalence"]
    eps64 = 2.220446049250313e-16
    vals = [_f(v) for v in backend_scores if _finite(v)]
    backend_range = (max(vals) - min(vals)) if len(vals) >= 2 else 0.0
    floor = float(se["roundoff_factor"]) * eps64 * max(1.0, abs(_f(max_abs_score_episode)))
    return {"backend_range": float(backend_range), "roundoff_floor": float(floor),
            "envelope": float(max(backend_range, floor)), "n_backends": len(vals)}


def tie_tolerance(envelope_best: float, envelope_second: float, cfg: dict) -> float:
    """``tie_multiplier * max(envelope_best, envelope_second)`` (contract §4)."""
    return float(cfg["score_equivalence"]["tie_multiplier"]) * max(_f(envelope_best), _f(envelope_second))


def tie_set(scores: dict[Any, float], tolerance: float) -> list:
    """``{links whose score - min_score <= tolerance}`` (master prompt §8.3), audit evidence only.

    Reported so a *future* deterministic policy could return ``AMBIGUOUS_LINK_SET``. It is never
    used to re-score the historical Stage 2A/2B unique-label metric.
    """
    vals = {k: _f(v) for k, v in scores.items() if _finite(v)}
    if not vals:
        return []
    lo = min(vals.values())
    return sorted([k for k, v in vals.items() if v - lo <= _f(tolerance)])


def episode_is_numerical_tie(ep: dict, cfg: dict) -> dict:
    """Is one episode's label difference admissible as a numerical tie? (master prompt §8.1)

    ``ep`` carries the measured quantities for a single (seed, episode_id); every condition below
    must hold. Each is reported individually so a failure names itself.
    """
    tol = _f(ep.get("tie_tolerance"))
    margin = _f(ep.get("margin"))
    conditions = {
        # the measured best/second-best margin fits inside the measured envelope
        "margin_within_tolerance": _finite(margin) and _finite(tol) and margin <= tol,
        # Stage 2A and Stage 2B were handed the same numbers
        "raw_inputs_identical": _b(ep.get("raw_inputs_identical")),
        # both labels live in one tie set, and that set does not move between implementations
        "labels_in_common_tie_set": _b(ep.get("labels_in_common_tie_set")),
        "tie_set_stable_across_backends": _b(ep.get("tie_set_stable_across_backends")),
        "tie_set_stable_across_candidate_orders": _b(ep.get("tie_set_stable_across_candidate_orders")),
        # no singular value sits near the rank threshold: a rank flip is not a floating-point tie
        "no_singular_value_near_rank_threshold": _b(ep.get("no_singular_value_near_rank_threshold")),
        "no_rank_instability": not _b(ep.get("rank_threshold_unstable")),
    }
    return {"is_numerical_tie": all(conditions.values()), "conditions": conditions,
            "margin": margin, "tie_tolerance": tol}


# --------------------------------------------------------------------- terminal-state precedence
def integrity_state(evidence: dict, cfg: dict) -> dict:
    """Apply the frozen precedence to measured evidence. No outcome is presumed.

    ``evidence`` keys consumed (all measured elsewhere, never inferred here):

    ``input_provenance_ok``          every frozen hash/presence check passed
    ``scientific_head_clean``        no blocking-class file changed after the scientific commit
    ``reference_evidence_complete``  the per-window/per-episode score arrays required exist
    ``score_history_resolvable``     Stage 2A and Stage 2B evidence joined completely and uniquely
    ``n_label_differences``          how many (seed, episode) labels differ
    ``n_nontie_label_differences``   ...of which are NOT admissible numerical ties
    ``scores_within_score_tolerance`` all compared scores agree inside the frozen tolerance
    ``semantic_difference_found``    a code/config difference that explains the flip
    ``rank_threshold_unstable``      a label moved because a singular value crossed the threshold
    """
    precedence = list(cfg.get("integrity_decision_precedence", TERMINAL_STATES))
    e = evidence
    n_diff = int(_f(e.get("n_label_differences")) if _finite(e.get("n_label_differences")) else -1)
    n_nontie = int(_f(e.get("n_nontie_label_differences")) if _finite(e.get("n_nontie_label_differences")) else -1)
    unstable = _b(e.get("rank_threshold_unstable"))

    triggers = {
        "BLOCKED_INPUT_PROVENANCE": (
            not _b(e.get("input_provenance_ok")),
            "a frozen input is absent or its hash does not match the kickoff expectation",
        ),
        "BLOCKED_SCIENTIFIC_HEAD_MISMATCH": (
            not _b(e.get("scientific_head_clean")),
            "scientific computation, thresholds, data or splits changed after the scientific commit",
        ),
        "BLOCKED_MISSING_REFERENCE_EVIDENCE": (
            not _b(e.get("reference_evidence_complete")),
            "the frozen per-window/per-episode localization score evidence required by §6.2 does not exist",
        ),
        "BLOCKED_UNRESOLVABLE_SCORE_HISTORY": (
            not _b(e.get("score_history_resolvable")),
            "Stage 2A and Stage 2B score evidence exists but cannot be joined completely and uniquely",
        ),
        "FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH": (
            (n_nontie != 0) or unstable or _b(e.get("semantic_difference_found"))
            or not _b(e.get("scores_within_score_tolerance")),
            "a label difference is not explained by the frozen numerical-tie definition",
        ),
        "PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP": (
            n_diff > 0 and n_nontie == 0 and not unstable,
            "every differing label is a measured numerical tie and no non-tie episode moved",
        ),
        "PASS_EXACT_REPRODUCTION": (
            n_diff == 0 and _b(e.get("scores_within_score_tolerance")),
            "every score and every label reproduces inside the frozen tolerance",
        ),
    }

    state, reason = None, ""
    for name in precedence:
        fired, why = triggers.get(name, (False, ""))
        if fired:
            state, reason = name, why
            break
    if state is None:
        # nothing fired: the evidence does not support any terminal state, which is itself
        # unresolved -- never silently a pass
        state = "BLOCKED_UNRESOLVABLE_SCORE_HISTORY"
        reason = "no terminal state's conditions were met by the measured evidence"

    modifiers = [RANK_INSTABILITY] if unstable else []
    return {
        "integrity_state": state,
        "reason": reason,
        "modifiers": modifiers,
        "reproduction_gate_pass": state in PASS_STATES,
        "precedence": precedence,
        "triggers": {k: bool(v[0]) for k, v in triggers.items()},
        "evidence_used": {k: e.get(k) for k in (
            "input_provenance_ok", "scientific_head_clean", "reference_evidence_complete",
            "score_history_resolvable", "n_label_differences", "n_nontie_label_differences",
            "scores_within_score_tolerance", "semantic_difference_found", "rank_threshold_unstable")},
        "note": ("Stage 2B-R resolves an integrity gate only. A PASS here does not mean Stage 2B "
                 "passed; it means the reproduction gate is no longer a reason to block it."),
    }


def scientific_decision_is_permitted(state: str) -> bool:
    """Phase 6 may run only from a PASS state; otherwise Stage 2B stays BLOCKED."""
    return state in PASS_STATES
