"""Frozen machine-readable decision code for CERTO-FDI Paper Reset V2.

Contract: ``contracts/paper_reset_v2/01_MASTER_PROMPT.md`` sections 10-11 and
``contracts/paper_reset_v2/04_DECISION_RULES.yaml``.

This module is committed in the V2 freeze commit, *before* any V2 screening
count, full-text card, benchmark run, or candidate result exists.
``resolve_final_state`` is a pure function of pre-declared evidence fields; it
must not be edited to make a conclusion sound better. Any change after the
freeze commit must be a separate, explicitly justified commit that re-states
the old and new outcome.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

FREEZE_COMMIT_DATE = "2026-08-24"
DECISION_CODE_VERSION = "2.0.0"

# --- Frozen literature gate thresholds (04_DECISION_RULES.yaml: literature_gate) ---
LIT_SCREENED_MIN = 500
LIT_FULLTEXT_MIN = 100
LIT_DIRECT_NEIGHBORS_MIN = 35
LIT_KILLER_DOSSIERS_MIN = 15
LIT_DIRECT_2025_2026_MIN = 25
LIT_DATASET_CODE_PAPERS_MIN = 20
LIT_CITATION_CHAINS_MIN = 10

# --- Frozen benchmark gate requirements (04_DECISION_RULES.yaml: benchmark_gate) ---
MANDATORY_DATASETS: tuple[str, ...] = ("voraus_ad_100hz", "road", "aursad")
DEEP_MODEL_SEEDS_MIN = 3

# --- Frozen method-survival thresholds (04_DECISION_RULES.yaml: method_survival) ---
SURVIVAL_MIN_DATASETS_WITH_GAIN = 2
SURVIVAL_AUROC_GAIN = 0.03
SURVIVAL_AUPRC_GAIN = 0.05
SURVIVAL_MAX_RELATIVE_FPR_TPR90_WORSENING = 0.10
SURVIVAL_MIN_CONCORDANT_SEEDS = 2
SURVIVAL_MIN_CONCORDANT_TYPES_OR_CONTEXTS = 2


class LiteratureGateV2(str, Enum):
    PASS = "LITERATURE_PASS"
    INCONCLUSIVE = "LITERATURE_INCONCLUSIVE"
    BLOCKED_ACCESS = "BLOCKED_LITERATURE_ACCESS"


class BenchmarkGateV2(str, Enum):
    PASS = "PUBLIC_BENCHMARK_PASS"
    PARTIAL = "PUBLIC_BENCHMARK_PARTIAL"
    BLOCKED_DATA = "PUBLIC_BENCHMARK_BLOCKED_DATA"


class MethodSurvivalGate(str, Enum):
    PASS = "METHOD_SURVIVAL_PASS"
    FAIL = "METHOD_SURVIVAL_FAIL"
    NOT_RUN = "METHOD_SURVIVAL_NOT_RUN"


class StoryGate(str, Enum):
    PASS = "STORY_PASS"
    FAIL = "STORY_FAIL"
    NOT_EVALUATED = "STORY_NOT_EVALUATED"


class FinalStateV2(str, Enum):
    """The ten allowed terminal states (01_MASTER_PROMPT.md section 11)."""

    PAPER_GO_TRO_CANDIDATE = "PAPER_GO_TRO_CANDIDATE"
    PAPER_GO_ICRA_RSS_CANDIDATE = "PAPER_GO_ICRA_RSS_CANDIDATE"
    PIVOT_PUBLIC_ROBOT_ANOMALY = "PIVOT_PUBLIC_ROBOT_ANOMALY"
    PIVOT_COLLISION_CONTACT_SPECIALIST = "PIVOT_COLLISION_CONTACT_SPECIALIST"
    PIVOT_BENCHMARK_DATASET_PAPER = "PIVOT_BENCHMARK_DATASET_PAPER"
    NO_GO_CURRENT_METHOD_PUBLIC_DATA = "NO_GO_CURRENT_METHOD_PUBLIC_DATA"
    NO_GO_NOVELTY_OCCUPIED = "NO_GO_NOVELTY_OCCUPIED"
    NO_GO_NO_COHERENT_ROBOT_SCIENCE = "NO_GO_NO_COHERENT_ROBOT_SCIENCE"
    LITERATURE_OR_BENCHMARK_INCONCLUSIVE = "LITERATURE_OR_BENCHMARK_INCONCLUSIVE"
    BLOCKED = "BLOCKED"


FINAL_STATE_PRIORITY: tuple[FinalStateV2, ...] = (
    FinalStateV2.BLOCKED,
    FinalStateV2.NO_GO_NOVELTY_OCCUPIED,
    FinalStateV2.PAPER_GO_TRO_CANDIDATE,
    FinalStateV2.PAPER_GO_ICRA_RSS_CANDIDATE,
    FinalStateV2.PIVOT_PUBLIC_ROBOT_ANOMALY,
    FinalStateV2.PIVOT_COLLISION_CONTACT_SPECIALIST,
    FinalStateV2.PIVOT_BENCHMARK_DATASET_PAPER,
    FinalStateV2.NO_GO_CURRENT_METHOD_PUBLIC_DATA,
    FinalStateV2.NO_GO_NO_COHERENT_ROBOT_SCIENCE,
    FinalStateV2.LITERATURE_OR_BENCHMARK_INCONCLUSIVE,
)


@dataclass(frozen=True)
class LiteratureCounts:
    """Actual audited counts; each row must exist in the screening/evidence CSVs."""

    screened: int = 0
    fulltext: int = 0
    direct_neighbors: int = 0
    killer_dossiers: int = 0
    direct_2025_2026: int = 0
    dataset_code_papers: int = 0
    citation_chains: int = 0

    def meets_gate(self) -> bool:
        return (
            self.screened >= LIT_SCREENED_MIN
            and self.fulltext >= LIT_FULLTEXT_MIN
            and self.direct_neighbors >= LIT_DIRECT_NEIGHBORS_MIN
            and self.killer_dossiers >= LIT_KILLER_DOSSIERS_MIN
            and self.direct_2025_2026 >= LIT_DIRECT_2025_2026_MIN
            and self.dataset_code_papers >= LIT_DATASET_CODE_PAPERS_MIN
            and self.citation_chains >= LIT_CITATION_CHAINS_MIN
        )


@dataclass(frozen=True)
class DecisionEvidenceV2:
    """Pre-declared evidence fields. Every field must be set from audited output.

    No field may be derived from test-set anomalies used for model selection,
    and no field may rest on fabricated physical quantities
    (01_MASTER_PROMPT.md sections 5.2 and 15).
    """

    literature_gate: LiteratureGateV2
    benchmark_gate: BenchmarkGateV2
    method_survival_gate: MethodSurvivalGate
    story_gate: StoryGate

    literature_counts: LiteratureCounts = LiteratureCounts()

    # Literature-side qualifiers
    all_final_contributions_have_neighbors: bool = False
    no_unresolved_doi_or_status_conflicts: bool = False
    killer_paper_occupies_final_story: bool = False

    # Benchmark-side qualifiers (10.2)
    mandatory_datasets_complete: int = 0
    native_baseline_per_mandatory_dataset: bool = False
    universal_baseline_matrix_complete: bool = False
    deep_models_have_min_seeds: bool = False
    no_test_anomaly_tuning: bool = True
    no_fabricated_physics: bool = True

    # Method-survival qualifiers beyond the numeric gate (10.3)
    survival_transfer_or_few_shot_win: bool = False
    geometry_beats_random_feature_control: bool = False
    chain_beats_permutation_controls: bool = False
    gain_not_explained_by_capacity: bool = False

    # Story-gate qualifiers (10.4, compressed)
    coherent_robot_science_question: bool = False
    not_generic_mtsad_dataset_swap: bool = False
    explicit_failure_mechanism_targeted: bool = False
    event_level_results_present: bool = False
    real_robot_followup_plan: bool = False
    single_figure_story: bool = False

    # GO-tier discriminator
    tro_theory_and_system_completeness: bool = False

    # Pivot evidence
    cross_context_low_false_alarm_holds: bool = False
    collision_contact_transfer_holds: bool = False
    benchmark_negative_results_have_standalone_value: bool = False

    # Local numeric gains present even though survival/story failed
    local_numeric_gains_present: bool = False

    def as_dict(self) -> dict:
        out = asdict(self)
        for key, value in list(out.items()):
            if isinstance(value, Enum):
                out[key] = value.value
        return out


def _is_blocked(e: DecisionEvidenceV2) -> bool:
    return (
        e.literature_gate is LiteratureGateV2.BLOCKED_ACCESS
        or e.benchmark_gate is BenchmarkGateV2.BLOCKED_DATA
    )


def _is_no_go_novelty(e: DecisionEvidenceV2) -> bool:
    return e.killer_paper_occupies_final_story


def _benchmark_pass(e: DecisionEvidenceV2) -> bool:
    return (
        e.benchmark_gate is BenchmarkGateV2.PASS
        and e.mandatory_datasets_complete >= len(MANDATORY_DATASETS)
        and e.native_baseline_per_mandatory_dataset
        and e.universal_baseline_matrix_complete
        and e.deep_models_have_min_seeds
        and e.no_test_anomaly_tuning
        and e.no_fabricated_physics
    )


def _literature_pass(e: DecisionEvidenceV2) -> bool:
    return (
        e.literature_gate is LiteratureGateV2.PASS
        and e.literature_counts.meets_gate()
        and e.all_final_contributions_have_neighbors
        and e.no_unresolved_doi_or_status_conflicts
    )


def _survival_pass(e: DecisionEvidenceV2) -> bool:
    return (
        e.method_survival_gate is MethodSurvivalGate.PASS
        and e.survival_transfer_or_few_shot_win
        and e.geometry_beats_random_feature_control
        and e.chain_beats_permutation_controls
        and e.gain_not_explained_by_capacity
    )


def _story_pass(e: DecisionEvidenceV2) -> bool:
    return (
        e.story_gate is StoryGate.PASS
        and e.coherent_robot_science_question
        and e.not_generic_mtsad_dataset_swap
        and e.explicit_failure_mechanism_targeted
        and e.event_level_results_present
        and e.single_figure_story
        and not e.killer_paper_occupies_final_story
    )


def _is_paper_go_tro(e: DecisionEvidenceV2) -> bool:
    return (
        _literature_pass(e)
        and _benchmark_pass(e)
        and _survival_pass(e)
        and _story_pass(e)
        and e.real_robot_followup_plan
        and e.tro_theory_and_system_completeness
    )


def _is_paper_go_icra_rss(e: DecisionEvidenceV2) -> bool:
    return (
        _literature_pass(e)
        and _benchmark_pass(e)
        and _survival_pass(e)
        and _story_pass(e)
        and not e.tro_theory_and_system_completeness
    )


def _is_pivot_public_anomaly(e: DecisionEvidenceV2) -> bool:
    return (
        _benchmark_pass(e)
        and not _survival_pass(e)
        and e.cross_context_low_false_alarm_holds
    )


def _is_pivot_collision_contact(e: DecisionEvidenceV2) -> bool:
    return (
        _benchmark_pass(e)
        and not _survival_pass(e)
        and e.collision_contact_transfer_holds
    )


def _is_pivot_benchmark_paper(e: DecisionEvidenceV2) -> bool:
    return (
        e.method_survival_gate in (MethodSurvivalGate.FAIL, MethodSurvivalGate.NOT_RUN)
        and e.benchmark_negative_results_have_standalone_value
        and e.mandatory_datasets_complete >= len(MANDATORY_DATASETS)
    )


def _is_no_go_current_method(e: DecisionEvidenceV2) -> bool:
    return (
        e.method_survival_gate is MethodSurvivalGate.FAIL
        and not e.cross_context_low_false_alarm_holds
        and not e.collision_contact_transfer_holds
    )


def _is_no_go_no_coherent_science(e: DecisionEvidenceV2) -> bool:
    return (
        e.local_numeric_gains_present
        and not _story_pass(e)
        and e.method_survival_gate is not MethodSurvivalGate.NOT_RUN
    )


_PREDICATES = {
    FinalStateV2.BLOCKED: _is_blocked,
    FinalStateV2.NO_GO_NOVELTY_OCCUPIED: _is_no_go_novelty,
    FinalStateV2.PAPER_GO_TRO_CANDIDATE: _is_paper_go_tro,
    FinalStateV2.PAPER_GO_ICRA_RSS_CANDIDATE: _is_paper_go_icra_rss,
    FinalStateV2.PIVOT_PUBLIC_ROBOT_ANOMALY: _is_pivot_public_anomaly,
    FinalStateV2.PIVOT_COLLISION_CONTACT_SPECIALIST: _is_pivot_collision_contact,
    FinalStateV2.PIVOT_BENCHMARK_DATASET_PAPER: _is_pivot_benchmark_paper,
    FinalStateV2.NO_GO_CURRENT_METHOD_PUBLIC_DATA: _is_no_go_current_method,
    FinalStateV2.NO_GO_NO_COHERENT_ROBOT_SCIENCE: _is_no_go_no_coherent_science,
}


def resolve_final_state(evidence: DecisionEvidenceV2) -> FinalStateV2:
    """Return exactly one terminal state, by frozen priority order.

    Priority is the declaration order of ``FINAL_STATE_PRIORITY``; the first
    matching predicate wins even when a lower-priority predicate also matches.
    ``LITERATURE_OR_BENCHMARK_INCONCLUSIVE`` is the fallthrough: completeness
    outranks any wish for a cleaner-sounding conclusion.
    """
    for state in FINAL_STATE_PRIORITY:
        predicate = _PREDICATES.get(state)
        if predicate is not None and predicate(evidence):
            return state
    return FinalStateV2.LITERATURE_OR_BENCHMARK_INCONCLUSIVE


def explain_final_state(evidence: DecisionEvidenceV2) -> dict:
    """Return the resolved state plus every predicate outcome, for the audit trail."""
    matches = {
        state.value: bool(pred(evidence)) for state, pred in _PREDICATES.items()
    }
    matches[FinalStateV2.LITERATURE_OR_BENCHMARK_INCONCLUSIVE.value] = True
    return {
        "decision_code_version": DECISION_CODE_VERSION,
        "freeze_commit_date": FREEZE_COMMIT_DATE,
        "evidence": evidence.as_dict(),
        "predicate_matches": matches,
        "priority_order": [s.value for s in FINAL_STATE_PRIORITY],
        "final_state": resolve_final_state(evidence).value,
    }
