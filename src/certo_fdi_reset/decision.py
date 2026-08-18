"""Frozen machine-readable decision code for the CERTO-FDI Paper Reset.

Contract: ``contracts/paper_reset/14_DECISION_RULES.md``.

This module is committed in Phase 0, *before* any full public-benchmark result
exists. ``resolve_final_state`` is a pure function of pre-declared evidence
fields; it must not be edited to make a conclusion sound better
(01_MASTER_PROMPT.md section 13). Any change after the freeze commit must be a
separate, explicitly justified commit that re-states the old and new outcome.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

FREEZE_COMMIT_DATE = "2026-08-18"
DECISION_CODE_VERSION = "1.0.0"


class LiteratureGate(str, Enum):
    PASS_PLAUSIBLY_OPEN = "LITERATURE_PASS_PLAUSIBLY_OPEN"
    PARTIALLY_OCCUPIED = "LITERATURE_PARTIALLY_OCCUPIED"
    OCCUPIED_KILLER_PAPER = "LITERATURE_OCCUPIED_KILLER_PAPER"
    UNKNOWN_INSUFFICIENT_FULLTEXT = "LITERATURE_UNKNOWN_INSUFFICIENT_FULLTEXT"
    BLOCKED_ACCESS = "BLOCKED_LITERATURE_ACCESS"


class PublicBenchmarkGate(str, Enum):
    PASS = "PUBLIC_BENCHMARK_PASS"
    PARTIAL = "PUBLIC_BENCHMARK_PARTIAL"
    FAIL_REPRODUCTION = "PUBLIC_BENCHMARK_FAIL_REPRODUCTION"
    BLOCKED_DATA = "PUBLIC_BENCHMARK_BLOCKED_DATA"


class CandidateGate(str, Enum):
    EXTERNAL_VALUE = "CANDIDATE_EXTERNAL_VALUE"
    SIMULATION_ONLY = "CANDIDATE_SIMULATION_ONLY"
    NO_VALUE = "CANDIDATE_NO_VALUE"
    NOT_APPLICABLE = "CANDIDATE_NOT_APPLICABLE"


class ClaimStatus(str, Enum):
    OCCUPIED = "OCCUPIED"
    PARTIALLY_OCCUPIED = "PARTIALLY_OCCUPIED"
    PLAUSIBLY_OPEN = "PLAUSIBLY_OPEN"
    UNKNOWN = "UNKNOWN"
    FALSELY_FRAMED = "FALSELY_FRAMED"


class ReproductionLevel(str, Enum):
    EXACT_OFFICIAL = "EXACT_OFFICIAL"
    FAITHFUL_OFFICIAL = "FAITHFUL_OFFICIAL"
    FAITHFUL_PAPER = "FAITHFUL_PAPER"
    POLICY_BASELINE = "POLICY_BASELINE"
    REFERENCE_IMPLEMENTATION = "REFERENCE_IMPLEMENTATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BLOCKED = "BLOCKED"
    FAITHFUL_NOT_NUMERICALLY_VERIFIED = "FAITHFUL_NOT_NUMERICALLY_VERIFIED"


class PhysicsLevel(str, Enum):
    P0_TIME_SERIES_ONLY = "P0_TIME_SERIES_ONLY"
    P1_JOINT_TOPOLOGY_ONLY = "P1_JOINT_TOPOLOGY_ONLY"
    P2_PARTIAL_PHYSICS_SIGNALS = "P2_PARTIAL_PHYSICS_SIGNALS"
    P3_FULL_DYNAMICS_METADATA = "P3_FULL_DYNAMICS_METADATA"


class FinalState(str, Enum):
    """Combined terminal states, declared in strict priority order."""

    BLOCKED = "BLOCKED"
    NO_GO_NOVELTY_KILLER_PAPER = "NO_GO_NOVELTY_KILLER_PAPER"
    NO_GO_CURRENT_METHOD_PUBLIC_DATA = "NO_GO_CURRENT_METHOD_PUBLIC_DATA"
    PIVOT_PUBLIC_ANOMALY_BENCHMARK = "PIVOT_PUBLIC_ANOMALY_BENCHMARK"
    PIVOT_CONTACT_SPECIALIST = "PIVOT_CONTACT_SPECIALIST"
    PAPER_CANDIDATE_READY_FOR_REAL_ROBOT = "PAPER_CANDIDATE_READY_FOR_REAL_ROBOT"
    LITERATURE_OR_BENCHMARK_INCONCLUSIVE = "LITERATURE_OR_BENCHMARK_INCONCLUSIVE"


FINAL_STATE_PRIORITY: tuple[FinalState, ...] = (
    FinalState.BLOCKED,
    FinalState.NO_GO_NOVELTY_KILLER_PAPER,
    FinalState.NO_GO_CURRENT_METHOD_PUBLIC_DATA,
    FinalState.PIVOT_PUBLIC_ANOMALY_BENCHMARK,
    FinalState.PIVOT_CONTACT_SPECIALIST,
    FinalState.PAPER_CANDIDATE_READY_FOR_REAL_ROBOT,
    FinalState.LITERATURE_OR_BENCHMARK_INCONCLUSIVE,
)


# --- Frozen numeric survival thresholds (13_CANDIDATE_MODEL_ADAPTER_PROTOCOL.md section 5) ---
CANDIDATE_MIN_AUROC_GAIN = 0.03
CANDIDATE_MIN_AUPRC_GAIN = 0.05
CANDIDATE_MAX_FPR_AT_TPR90_DEGRADATION = 0.10
CANDIDATE_MIN_DATASETS = 2
CANDIDATE_MIN_CONCORDANT_SEEDS = 2
CANDIDATE_MIN_CONCORDANT_CONTEXTS = 2
CANDIDATE_SAMPLE_EFFICIENCY_FRACTION = 0.25

# --- Frozen reproduction tolerances (11_PUBLIC_BASELINE_REPRODUCTION_PROTOCOL.md section C) ---
REPRODUCTION_ABS_TOLERANCE = 0.01
REPRODUCTION_REL_TOLERANCE = 0.02

MANDATORY_DATASETS: tuple[str, ...] = ("voraus_ad", "road", "aursad")


@dataclass(frozen=True)
class DecisionEvidence:
    """Pre-declared evidence fields. Every field must be set from audited output.

    No field may be derived from test-set anomalies used for model selection.
    """

    literature_gate: LiteratureGate
    public_benchmark_gate: PublicBenchmarkGate
    candidate_gate: CandidateGate

    # Literature-side qualifiers
    residual_contribution_nontrivial: bool = False

    # Candidate-side qualifiers
    geometry_increment_beats_strong_baseline: bool = False
    candidate_stable_on_n_mandatory_datasets: int = 0
    has_cross_context_or_sample_efficiency_win: bool = False
    increment_explained_by_capacity_or_head: bool = True
    all_claims_free_of_invented_physics: bool = False
    single_paper_hypothesis_definable: bool = False

    # Benchmark-as-contribution qualifiers
    benchmark_quality_sufficient: bool = False

    # Contact-specialist qualifiers
    contact_specialist_external_evidence: bool = False
    general_fdi_externally_supported: bool = False

    def as_dict(self) -> dict:
        out = asdict(self)
        for key, value in list(out.items()):
            if isinstance(value, Enum):
                out[key] = value.value
        return out


def _is_blocked(e: DecisionEvidence) -> bool:
    return (
        e.literature_gate is LiteratureGate.BLOCKED_ACCESS
        or e.public_benchmark_gate is PublicBenchmarkGate.BLOCKED_DATA
    )


def _is_killer_paper(e: DecisionEvidence) -> bool:
    return e.literature_gate is LiteratureGate.OCCUPIED_KILLER_PAPER


def _is_no_go_current_method(e: DecisionEvidence) -> bool:
    return (
        e.candidate_gate is CandidateGate.NO_VALUE
        and not e.geometry_increment_beats_strong_baseline
    )


def _is_pivot_benchmark(e: DecisionEvidence) -> bool:
    no_stable_increment = e.candidate_gate in (
        CandidateGate.SIMULATION_ONLY,
        CandidateGate.NO_VALUE,
        CandidateGate.NOT_APPLICABLE,
    )
    return no_stable_increment and e.benchmark_quality_sufficient


def _is_pivot_contact(e: DecisionEvidence) -> bool:
    return e.contact_specialist_external_evidence and not e.general_fdi_externally_supported


def _is_paper_candidate_ready(e: DecisionEvidence) -> bool:
    literature_ok = e.literature_gate is LiteratureGate.PASS_PLAUSIBLY_OPEN or (
        e.literature_gate is LiteratureGate.PARTIALLY_OCCUPIED
        and e.residual_contribution_nontrivial
    )
    return (
        literature_ok
        and e.public_benchmark_gate is PublicBenchmarkGate.PASS
        and e.candidate_gate is CandidateGate.EXTERNAL_VALUE
        and e.candidate_stable_on_n_mandatory_datasets >= CANDIDATE_MIN_DATASETS
        and e.has_cross_context_or_sample_efficiency_win
        and not e.increment_explained_by_capacity_or_head
        and e.all_claims_free_of_invented_physics
        and e.single_paper_hypothesis_definable
    )


_PREDICATES = {
    FinalState.BLOCKED: _is_blocked,
    FinalState.NO_GO_NOVELTY_KILLER_PAPER: _is_killer_paper,
    FinalState.NO_GO_CURRENT_METHOD_PUBLIC_DATA: _is_no_go_current_method,
    FinalState.PIVOT_PUBLIC_ANOMALY_BENCHMARK: _is_pivot_benchmark,
    FinalState.PIVOT_CONTACT_SPECIALIST: _is_pivot_contact,
    FinalState.PAPER_CANDIDATE_READY_FOR_REAL_ROBOT: _is_paper_candidate_ready,
}


def resolve_final_state(evidence: DecisionEvidence) -> FinalState:
    """Return exactly one combined terminal state, by frozen priority order.

    Priority is the declaration order of ``FINAL_STATE_PRIORITY``; the first
    matching predicate wins even when a lower-priority predicate also matches.
    ``LITERATURE_OR_BENCHMARK_INCONCLUSIVE`` is the fallthrough.
    """
    for state in FINAL_STATE_PRIORITY:
        predicate = _PREDICATES.get(state)
        if predicate is not None and predicate(evidence):
            return state
    return FinalState.LITERATURE_OR_BENCHMARK_INCONCLUSIVE


def explain_final_state(evidence: DecisionEvidence) -> dict:
    """Return the resolved state plus every predicate outcome, for the audit trail."""
    matches = {
        state.value: bool(pred(evidence)) for state, pred in _PREDICATES.items()
    }
    matches[FinalState.LITERATURE_OR_BENCHMARK_INCONCLUSIVE.value] = True
    return {
        "decision_code_version": DECISION_CODE_VERSION,
        "freeze_commit_date": FREEZE_COMMIT_DATE,
        "evidence": evidence.as_dict(),
        "predicate_matches": matches,
        "priority_order": [s.value for s in FINAL_STATE_PRIORITY],
        "final_state": resolve_final_state(evidence).value,
    }
