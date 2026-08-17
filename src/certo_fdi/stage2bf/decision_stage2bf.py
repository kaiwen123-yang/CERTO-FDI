"""Stage 2B-F integrity precedence, and the wrapper that guards the frozen scientific decision.

Two separate things happen here and they must not be confused:

**Integrity** is decided by :func:`integrity_state`, from measured evidence, under the frozen
precedence. Only ``PASS_ESTIMATOR_HARMONIZATION`` permits the second step.

**The scientific decision** is *not* made here. :func:`run_scientific_decision` imports the
original frozen ``certo_fdi.stage2b.decision_stage2b.decide`` and calls it. There is no copy of
its logic in this file, no terminal state is written by hand, and the function refuses to run at
all unless the integrity state is the PASS. That refusal is the point: the way this stage could go
wrong is by deciding the answer and then arranging the evidence to match it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

INTEGRITY_PRECEDENCE = (
    "BLOCKED_INPUT_PROVENANCE",
    "BLOCKED_BASE_HEAD_MISMATCH",
    "BLOCKED_SCIENTIFIC_CODE_MISMATCH",
    "BLOCKED_DECISION_CODE_MISMATCH",
    "BLOCKED_MISSING_REFERENCE_SCORE_PRECISION",
    "BLOCKED_STAGE2A_RIDGE_REPRODUCTION",
    "BLOCKED_STAGE2B_SVD_REPRODUCTION",
    "BLOCKED_HISTORICAL_ARTIFACT_MUTATION",
    "PASS_ESTIMATOR_HARMONIZATION",
)
PASS_STATE = "PASS_ESTIMATOR_HARMONIZATION"

#: the original Stage 2B vocabulary; Stage 2B-F may not extend it
SCIENTIFIC_VOCABULARY = (
    "GO_CONTACT_LOADPATH_MONITOR",
    "PIVOT_SUPPORT_ONLY_LOCALIZER",
    "PIVOT_LOADPATH_LOCALIZATION_ONLY",
    "PIVOT_SEQUENTIAL_DETECTION_ONLY",
    "PIVOT_CONTEXT_CALIBRATION_ONLY",
    "NO_GO_CONTACT_PRODUCT",
    "BLOCKED",
)
NOT_RUN = "NOT_RUN"

#: evidence sections the delta may never touch (rules 06 §4)
FORBIDDEN_EVIDENCE_SECTIONS = (
    "detection", "sequential", "localization", "selective", "loadpath", "healthy_expansion",
)


def _b(x: Any) -> bool:
    return bool(x) if x is not None else False


def integrity_state(evidence: dict, cfg: dict | None = None) -> dict:
    """Apply the frozen precedence in order; the first trigger that fires is the answer.

    ``evidence`` keys, all measured elsewhere and never inferred here:

    ``input_provenance_ok``            three FULL packages + dataset manifest verified from disk
    ``base_head_matches``              base branch head equals the expected head
    ``scientific_code_identical``      the five frozen scientific files are byte-identical
    ``decision_code_identical``        ``decision_stage2b.py`` is byte-identical to frozen
    ``reference_score_precision_ok``   the frozen arrays permit value-by-value comparison
    ``ridge_reproduction_ok``          Stage 2A hard gate (score/candidate/label/vote/confusion)
    ``svd_reproduction_ok``            Stage 2B hard gate (score/rank/selection/test metrics)
    ``historical_artifacts_unchanged`` every historical file byte-preserved
    """
    precedence = list((cfg or {}).get("integrity_precedence", INTEGRITY_PRECEDENCE))
    triggers = {
        "BLOCKED_INPUT_PROVENANCE": (
            not _b(evidence.get("input_provenance_ok")),
            "a frozen package or the dataset manifest failed verification from disk"),
        "BLOCKED_BASE_HEAD_MISMATCH": (
            not _b(evidence.get("base_head_matches")),
            "the base branch head is not the expected frozen head"),
        "BLOCKED_SCIENTIFIC_CODE_MISMATCH": (
            not _b(evidence.get("scientific_code_identical")),
            "a frozen scientific source file drifted from the Stage 2B scientific commit"),
        "BLOCKED_DECISION_CODE_MISMATCH": (
            not _b(evidence.get("decision_code_identical")),
            "decision_stage2b.py is not byte-identical to the frozen version"),
        "BLOCKED_MISSING_REFERENCE_SCORE_PRECISION": (
            not _b(evidence.get("reference_score_precision_ok")),
            "the frozen reference arrays do not permit value-by-value comparison"),
        "BLOCKED_STAGE2A_RIDGE_REPRODUCTION": (
            not _b(evidence.get("ridge_reproduction_ok")),
            "the Stage 2A ridge localizer did not reproduce at score/candidate/label/vote/confusion level"),
        "BLOCKED_STAGE2B_SVD_REPRODUCTION": (
            not _b(evidence.get("svd_reproduction_ok")),
            "the Stage 2B truncated-SVD pipeline or its F4_CAL selection did not reproduce"),
        "BLOCKED_HISTORICAL_ARTIFACT_MUTATION": (
            not _b(evidence.get("historical_artifacts_unchanged")),
            "a historical Stage 2A/2B/2B-R artifact changed on disk"),
        PASS_STATE: (
            all(_b(evidence.get(k)) for k in (
                "input_provenance_ok", "base_head_matches", "scientific_code_identical",
                "decision_code_identical", "reference_score_precision_ok",
                "ridge_reproduction_ok", "svd_reproduction_ok", "historical_artifacts_unchanged")),
            "every provenance, code-identity and reproduction gate passed"),
    }
    state, reason = None, ""
    for name in precedence:
        fired, why = triggers.get(name, (False, ""))
        if fired:
            state, reason = name, why
            break
    if state is None:
        state, reason = "BLOCKED_INPUT_PROVENANCE", "no terminal state matched the measured evidence"
    return {
        "integrity_state": state,
        "reason": reason,
        "scientific_decision_permitted": state == PASS_STATE,
        "precedence": precedence,
        "triggers": {k: bool(v[0]) for k, v in triggers.items()},
        "evidence_used": {k: evidence.get(k) for k in (
            "input_provenance_ok", "base_head_matches", "scientific_code_identical",
            "decision_code_identical", "reference_score_precision_ok", "ridge_reproduction_ok",
            "svd_reproduction_ok", "historical_artifacts_unchanged")},
    }


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def evidence_delta(historical: dict, new: dict, allowed_prefixes: tuple[str, ...],
                   forbidden_sections: tuple[str, ...] = FORBIDDEN_EVIDENCE_SECTIONS) -> dict:
    """Every field that differs between the historical and the Stage 2B-F decision evidence.

    A change is admissible only if its dotted path starts with one of ``allowed_prefixes`` and does
    not sit under a forbidden section. Anything else is returned in ``violations``, and the caller
    must block on a non-empty list — a numeric scientific field that moved without explanation is
    exactly what this stage is forbidden to wave through.
    """
    changes: list[dict] = []

    def walk(a, b, path=""):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                walk(a.get(k, "<absent>"), b.get(k, "<absent>"), f"{path}.{k}" if path else k)
        elif a != b:
            changes.append({"path": path, "historical": a, "stage2bf": b})

    walk(historical, new)
    allowed, violations = [], []
    for c in changes:
        p = c["path"]
        top = p.split(".")[0]
        section = p.split(".")[1] if top == "evidence" and "." in p else top
        ok = any(p.startswith(pre) for pre in allowed_prefixes)
        if ok and section not in forbidden_sections:
            allowed.append(c)
        else:
            violations.append(c)
    return {"n_changes": len(changes), "allowed": allowed, "violations": violations,
            "clean": not violations}


def run_scientific_decision(integrity: dict, evidence: dict, thresholds: dict,
                            decide_fn: Callable[[dict, dict], dict] | None = None) -> dict:
    """Call the ORIGINAL frozen Stage 2B decision function — or refuse.

    ``decide_fn`` exists only so a test can prove the refusal path; in production it is ``None`` and
    the frozen function is imported here. No terminal state is ever constructed in this file.
    """
    if not integrity.get("scientific_decision_permitted"):
        return {"stage2bf_scientific_decision": NOT_RUN,
                "reason": f"integrity state {integrity.get('integrity_state')!r} is not {PASS_STATE}",
                "decision_function_called": False}

    if decide_fn is None:
        from certo_fdi.stage2b.decision_stage2b import decide as decide_fn  # noqa: PLC0415

    result = decide_fn(evidence, thresholds)
    decision = result.get("decision")
    if decision not in SCIENTIFIC_VOCABULARY:
        raise ValueError(f"frozen decision function returned {decision!r}, outside the frozen vocabulary")
    return {"stage2bf_scientific_decision": decision,
            "decision_function_called": True,
            "decision_function_module": "certo_fdi.stage2b.decision_stage2b",
            "decision_function_name": "decide",
            "result": result}


def combined_terminal(integrity_state_name: str, scientific_decision: str) -> str:
    """``<integrity>__<scientific>`` (rules 06 §3)."""
    return f"{integrity_state_name}__{scientific_decision}"
