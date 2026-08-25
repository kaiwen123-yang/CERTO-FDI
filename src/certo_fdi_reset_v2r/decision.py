"""Frozen three-axis decision code for CERTO-FDI Paper Reset V2-R.

Contract: ``contracts/paper_reset_v2r/01_MASTER_PROMPT.md`` sections 4/10/15/16
and ``03_DECISION_RULES.yaml``. Committed BEFORE any ME-AD/AURSAD V2-R result.

Three independent axes — algorithm, benchmark artifact, submission readiness —
plus a combined state that must never mask the axes (section 16). The
historical PR #9 terminal state (PIVOT_BENCHMARK_DATASET_PAPER) is immutable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

FREEZE_COMMIT_DATE = "2026-08-24"
DECISION_CODE_VERSION = "2.1.0"


class AlgorithmState(str, Enum):
    NO_GO_CURRENT_METHOD_PUBLIC_DATA = "ALGORITHM_NO_GO_CURRENT_METHOD_PUBLIC_DATA"
    EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL = "ALGORITHM_EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL"
    EVIDENCE_REOPENED_CONTEXT_CALIBRATION = "ALGORITHM_EVIDENCE_REOPENED_CONTEXT_CALIBRATION"
    INCONCLUSIVE = "ALGORITHM_INCONCLUSIVE"


class BenchmarkArtifactState(str, Enum):
    SUBMISSION_READY = "BENCHMARK_ARTIFACT_SUBMISSION_READY"
    MAJOR_REVISION = "BENCHMARK_ARTIFACT_MAJOR_REVISION"
    NO_GO = "BENCHMARK_ARTIFACT_NO_GO"
    BLOCKED = "BENCHMARK_ARTIFACT_BLOCKED"


class SubmissionReadiness(str, Enum):
    READY_RAL_ICRA_BENCHMARK = "READY_RAL_ICRA_BENCHMARK"
    READY_TRO_EVALUATION_PAPER = "READY_TRO_EVALUATION_PAPER"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"


class CombinedState(str, Enum):
    READY_BENCHMARK_PAPER = "V2R_READY_BENCHMARK_PAPER"
    MAJOR_REVISION_REQUIRED = "V2R_MAJOR_REVISION_REQUIRED"
    NO_GO_BENCHMARK_PAPER = "V2R_NO_GO_BENCHMARK_PAPER"
    REOPEN_METHOD_DISCUSSION = "V2R_REOPEN_METHOD_DISCUSSION"
    BLOCKED = "V2R_BLOCKED"


# ---- frozen gate thresholds (03_DECISION_RULES.yaml) ----
MEAD_MIN_TASKS_WITH_GAIN = 4
MEAD_TASKS_TOTAL = 7
MEAD_AUROC_GAIN = 0.03
MEAD_AUPRC_GAIN = 0.05
MEAD_MAX_REL_FPR90_WORSENING = 0.10
MEAD_MIN_CONCORDANT_SEEDS = 2
MEAD_MIN_TASKS_EARLIER_DETECTION = 4

CTX_MIN_DATASETS = 2
CTX_MIN_FA_REDUCTION = 0.30
CTX_MIN_FRONTENDS = 3
CTX_MIN_CONCORDANT_SEEDS = 2

MANDATORY_DATASETS: tuple[str, ...] = ("voraus_ad", "road", "aursad", "me_ad")


@dataclass(frozen=True)
class MeadPhysicsResidualEvidence:
    """10.1 gate inputs — every field from audited outputs."""

    tasks_with_auroc_or_auprc_gain: int = 0
    concordant_seeds: int = 0
    fpr90_relative_worsening_max: float = 1.0
    tasks_with_earlier_detection_at_fixed_fpr: int = 0
    blind_all_joint_score_holds: bool = False
    permuted_joint_control_clean: bool = False
    not_capacity_or_context_id_leak: bool = False
    ood_not_catastrophic: bool = False

    def passes(self) -> bool:
        return (
            self.tasks_with_auroc_or_auprc_gain >= MEAD_MIN_TASKS_WITH_GAIN
            and self.concordant_seeds >= MEAD_MIN_CONCORDANT_SEEDS
            and self.fpr90_relative_worsening_max <= MEAD_MAX_REL_FPR90_WORSENING
            and self.tasks_with_earlier_detection_at_fixed_fpr >= MEAD_MIN_TASKS_EARLIER_DETECTION
            and self.blind_all_joint_score_holds
            and self.permuted_joint_control_clean
            and self.not_capacity_or_context_id_leak
            and self.ood_not_catastrophic
        )


@dataclass(frozen=True)
class ContextCalibrationEvidence:
    """10.2 gate inputs."""

    datasets_with_fa_reduction: int = 0
    min_fa_reduction_fraction: float = 0.0
    frontends_with_effect: int = 0
    concordant_seeds: int = 0
    permutation_control_clean: bool = False
    no_detection_degradation: bool = False

    def passes(self) -> bool:
        return (
            self.datasets_with_fa_reduction >= CTX_MIN_DATASETS
            and self.min_fa_reduction_fraction >= CTX_MIN_FA_REDUCTION
            and self.frontends_with_effect >= CTX_MIN_FRONTENDS
            and self.concordant_seeds >= CTX_MIN_CONCORDANT_SEEDS
            and self.permutation_control_clean
            and self.no_detection_degradation
        )


@dataclass(frozen=True)
class BenchmarkReadinessEvidence:
    """15.1 checklist — computed from artifacts, never hand-set."""

    datasets_complete: tuple[str, ...] = ()
    native_or_faithful_status_explicit: bool = False
    universal_core_matrix_complete: bool = False       # computed from rows
    aursad_dual_protocol_complete: bool = False
    mead_progressive_metrics_complete: bool = False
    claims_match_tables: bool = False
    self_contained_evidence_package: bool = False
    code_snapshot_or_bundle: bool = False
    per_seed_predictions_or_metrics: bool = False
    no_flag_csv_conflicts: bool = False
    min_two_cross_dataset_findings: bool = False
    no_first_claims: bool = False
    single_figure_story: bool = False
    independent_reviewer_smoke_pass: bool = False
    main_conclusions_reproducible: bool = True
    standalone_value_holds: bool = True

    def all_ready(self) -> bool:
        return (
            set(MANDATORY_DATASETS) <= set(self.datasets_complete)
            and self.native_or_faithful_status_explicit
            and self.universal_core_matrix_complete
            and self.aursad_dual_protocol_complete
            and self.mead_progressive_metrics_complete
            and self.claims_match_tables
            and self.self_contained_evidence_package
            and self.code_snapshot_or_bundle
            and self.per_seed_predictions_or_metrics
            and self.no_flag_csv_conflicts
            and self.min_two_cross_dataset_findings
            and self.no_first_claims
            and self.single_figure_story
            and self.independent_reviewer_smoke_pass
        )


@dataclass(frozen=True)
class V2REvidence:
    integrity_or_provenance_blocked: bool = False
    historical_state_recompute_matches: bool = True   # 5.1: must be PIVOT_BENCHMARK_DATASET_PAPER

    mead: MeadPhysicsResidualEvidence = field(default_factory=MeadPhysicsResidualEvidence)
    ctx: ContextCalibrationEvidence = field(default_factory=ContextCalibrationEvidence)
    bench: BenchmarkReadinessEvidence = field(default_factory=BenchmarkReadinessEvidence)

    # TRO-tier extras (15.2)
    tro_mechanism_beyond_curation: bool = False
    tro_unified_protocol_changes_field_conclusions: bool = False
    tro_constructive_component_on_two_datasets: bool = False
    no_direct_benchmark_audit_killer: bool = True

    mead_inconclusive: bool = False   # data/audit prevented the gate from being evaluated

    def as_dict(self) -> dict:
        out = asdict(self)
        return out


def resolve_algorithm_state(e: V2REvidence) -> AlgorithmState:
    if e.mead_inconclusive:
        return AlgorithmState.INCONCLUSIVE
    if e.mead.passes():
        return AlgorithmState.EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL
    if e.ctx.passes():
        return AlgorithmState.EVIDENCE_REOPENED_CONTEXT_CALIBRATION
    return AlgorithmState.NO_GO_CURRENT_METHOD_PUBLIC_DATA


def resolve_benchmark_state(e: V2REvidence) -> BenchmarkArtifactState:
    if e.integrity_or_provenance_blocked or not e.historical_state_recompute_matches:
        return BenchmarkArtifactState.BLOCKED
    if not e.bench.main_conclusions_reproducible or not e.bench.standalone_value_holds:
        return BenchmarkArtifactState.NO_GO
    if e.bench.all_ready():
        return BenchmarkArtifactState.SUBMISSION_READY
    return BenchmarkArtifactState.MAJOR_REVISION


def resolve_submission_readiness(e: V2REvidence) -> SubmissionReadiness:
    b = resolve_benchmark_state(e)
    if b is BenchmarkArtifactState.BLOCKED:
        return SubmissionReadiness.BLOCKED
    if b is not BenchmarkArtifactState.SUBMISSION_READY:
        return SubmissionReadiness.NOT_READY
    tro = (
        e.tro_mechanism_beyond_curation
        and e.tro_unified_protocol_changes_field_conclusions
        and e.tro_constructive_component_on_two_datasets
        and e.no_direct_benchmark_audit_killer
        and e.mead.passes()  # "ME-AD 真实渐进故障带来新的系统性发现" tier
    )
    return (SubmissionReadiness.READY_TRO_EVALUATION_PAPER if tro
            else SubmissionReadiness.READY_RAL_ICRA_BENCHMARK)


def resolve_combined_state(e: V2REvidence) -> CombinedState:
    """Priority (16): blocked > benchmark no-go > ready > major revision > reopened."""
    b = resolve_benchmark_state(e)
    if b is BenchmarkArtifactState.BLOCKED:
        return CombinedState.BLOCKED
    if b is BenchmarkArtifactState.NO_GO:
        return CombinedState.NO_GO_BENCHMARK_PAPER
    if b is BenchmarkArtifactState.SUBMISSION_READY:
        return CombinedState.READY_BENCHMARK_PAPER
    a = resolve_algorithm_state(e)
    if a in (AlgorithmState.EVIDENCE_REOPENED_MEAD_PHYSICS_RESIDUAL,
             AlgorithmState.EVIDENCE_REOPENED_CONTEXT_CALIBRATION) \
            and b is BenchmarkArtifactState.MAJOR_REVISION:
        # combined must not mask the axes: reopened method + unfinished artifact
        return CombinedState.REOPEN_METHOD_DISCUSSION
    return CombinedState.MAJOR_REVISION_REQUIRED


def three_axis(e: V2REvidence) -> dict:
    return {
        "decision_code_version": DECISION_CODE_VERSION,
        "freeze_commit_date": FREEZE_COMMIT_DATE,
        "algorithm_state": resolve_algorithm_state(e).value,
        "benchmark_artifact_state": resolve_benchmark_state(e).value,
        "submission_readiness": resolve_submission_readiness(e).value,
        "combined_state": resolve_combined_state(e).value,
        "evidence": e.as_dict(),
        "historical_pr9_state_immutable": "PIVOT_BENCHMARK_DATASET_PAPER",
    }
