"""Frozen-decision-code tests.

These pin the Phase 0 semantics of contracts/paper_reset/14_DECISION_RULES.md.
If a change to decision.py makes one of these fail, that is a protocol amendment,
not a bug fix.
"""

from __future__ import annotations

import itertools

import pytest

from certo_fdi_reset.decision import (
    CANDIDATE_MAX_FPR_AT_TPR90_DEGRADATION,
    CANDIDATE_MIN_AUPRC_GAIN,
    CANDIDATE_MIN_AUROC_GAIN,
    CANDIDATE_MIN_DATASETS,
    FINAL_STATE_PRIORITY,
    MANDATORY_DATASETS,
    CandidateGate,
    DecisionEvidence,
    FinalState,
    LiteratureGate,
    PublicBenchmarkGate,
    explain_final_state,
    resolve_final_state,
)


def ready_evidence(**overrides) -> DecisionEvidence:
    """The unique evidence combination that should yield PAPER_CANDIDATE_READY."""
    base = dict(
        literature_gate=LiteratureGate.PASS_PLAUSIBLY_OPEN,
        public_benchmark_gate=PublicBenchmarkGate.PASS,
        candidate_gate=CandidateGate.EXTERNAL_VALUE,
        candidate_stable_on_n_mandatory_datasets=2,
        has_cross_context_or_sample_efficiency_win=True,
        increment_explained_by_capacity_or_head=False,
        all_claims_free_of_invented_physics=True,
        single_paper_hypothesis_definable=True,
    )
    base.update(overrides)
    return DecisionEvidence(**base)


def test_thresholds_match_contract():
    assert CANDIDATE_MIN_AUROC_GAIN == 0.03
    assert CANDIDATE_MIN_AUPRC_GAIN == 0.05
    assert CANDIDATE_MAX_FPR_AT_TPR90_DEGRADATION == 0.10
    assert CANDIDATE_MIN_DATASETS == 2
    assert MANDATORY_DATASETS == ("voraus_ad", "road", "aursad")


def test_priority_order_is_the_contract_order():
    assert [s.value for s in FINAL_STATE_PRIORITY] == [
        "BLOCKED",
        "NO_GO_NOVELTY_KILLER_PAPER",
        "NO_GO_CURRENT_METHOD_PUBLIC_DATA",
        "PIVOT_PUBLIC_ANOMALY_BENCHMARK",
        "PIVOT_CONTACT_SPECIALIST",
        "PAPER_CANDIDATE_READY_FOR_REAL_ROBOT",
        "LITERATURE_OR_BENCHMARK_INCONCLUSIVE",
    ]


def test_blocked_wins_over_everything():
    for lit, bench in [
        (LiteratureGate.BLOCKED_ACCESS, PublicBenchmarkGate.PASS),
        (LiteratureGate.PASS_PLAUSIBLY_OPEN, PublicBenchmarkGate.BLOCKED_DATA),
        (LiteratureGate.BLOCKED_ACCESS, PublicBenchmarkGate.BLOCKED_DATA),
    ]:
        ev = ready_evidence(literature_gate=lit, public_benchmark_gate=bench)
        assert resolve_final_state(ev) is FinalState.BLOCKED


def test_killer_paper_outranks_a_perfect_candidate():
    ev = ready_evidence(literature_gate=LiteratureGate.OCCUPIED_KILLER_PAPER)
    assert resolve_final_state(ev) is FinalState.NO_GO_NOVELTY_KILLER_PAPER


def test_no_go_current_method_outranks_benchmark_pivot():
    """Both predicates can fire; frozen priority says NO_GO is reported."""
    ev = DecisionEvidence(
        literature_gate=LiteratureGate.PARTIALLY_OCCUPIED,
        public_benchmark_gate=PublicBenchmarkGate.PASS,
        candidate_gate=CandidateGate.NO_VALUE,
        geometry_increment_beats_strong_baseline=False,
        benchmark_quality_sufficient=True,
    )
    explanation = explain_final_state(ev)
    assert explanation["predicate_matches"]["PIVOT_PUBLIC_ANOMALY_BENCHMARK"] is True
    assert resolve_final_state(ev) is FinalState.NO_GO_CURRENT_METHOD_PUBLIC_DATA


def test_simulation_only_with_good_benchmark_pivots():
    ev = DecisionEvidence(
        literature_gate=LiteratureGate.PARTIALLY_OCCUPIED,
        public_benchmark_gate=PublicBenchmarkGate.PASS,
        candidate_gate=CandidateGate.SIMULATION_ONLY,
        benchmark_quality_sufficient=True,
    )
    assert resolve_final_state(ev) is FinalState.PIVOT_PUBLIC_ANOMALY_BENCHMARK


def test_contact_specialist_requires_general_fdi_to_be_unsupported():
    supported = DecisionEvidence(
        literature_gate=LiteratureGate.PARTIALLY_OCCUPIED,
        public_benchmark_gate=PublicBenchmarkGate.PARTIAL,
        candidate_gate=CandidateGate.EXTERNAL_VALUE,
        contact_specialist_external_evidence=True,
        general_fdi_externally_supported=True,
    )
    assert resolve_final_state(supported) is FinalState.LITERATURE_OR_BENCHMARK_INCONCLUSIVE

    unsupported = DecisionEvidence(
        literature_gate=LiteratureGate.PARTIALLY_OCCUPIED,
        public_benchmark_gate=PublicBenchmarkGate.PARTIAL,
        candidate_gate=CandidateGate.EXTERNAL_VALUE,
        contact_specialist_external_evidence=True,
        general_fdi_externally_supported=False,
    )
    assert resolve_final_state(unsupported) is FinalState.PIVOT_CONTACT_SPECIALIST


def test_paper_candidate_ready_is_reachable():
    assert resolve_final_state(ready_evidence()) is FinalState.PAPER_CANDIDATE_READY_FOR_REAL_ROBOT


@pytest.mark.parametrize(
    "override",
    [
        {"public_benchmark_gate": PublicBenchmarkGate.PARTIAL},
        {"candidate_stable_on_n_mandatory_datasets": 1},
        {"has_cross_context_or_sample_efficiency_win": False},
        {"increment_explained_by_capacity_or_head": True},
        {"all_claims_free_of_invented_physics": False},
        {"single_paper_hypothesis_definable": False},
        {"literature_gate": LiteratureGate.UNKNOWN_INSUFFICIENT_FULLTEXT},
    ],
)
def test_every_ready_condition_is_load_bearing(override):
    ev = ready_evidence(**override)
    assert resolve_final_state(ev) is not FinalState.PAPER_CANDIDATE_READY_FOR_REAL_ROBOT


def test_partially_occupied_needs_nontrivial_residual_contribution():
    trivial = ready_evidence(
        literature_gate=LiteratureGate.PARTIALLY_OCCUPIED,
        residual_contribution_nontrivial=False,
    )
    assert resolve_final_state(trivial) is not FinalState.PAPER_CANDIDATE_READY_FOR_REAL_ROBOT

    nontrivial = ready_evidence(
        literature_gate=LiteratureGate.PARTIALLY_OCCUPIED,
        residual_contribution_nontrivial=True,
    )
    assert resolve_final_state(nontrivial) is FinalState.PAPER_CANDIDATE_READY_FOR_REAL_ROBOT


def test_exactly_one_state_over_the_full_gate_cross_product():
    """Exhaustive over the three gates x the boolean qualifiers that gate them."""
    bool_fields = (
        "geometry_increment_beats_strong_baseline",
        "benchmark_quality_sufficient",
        "contact_specialist_external_evidence",
        "general_fdi_externally_supported",
        "residual_contribution_nontrivial",
    )
    seen: set[FinalState] = set()
    for lit, bench, cand in itertools.product(
        LiteratureGate, PublicBenchmarkGate, CandidateGate
    ):
        for combo in itertools.product([False, True], repeat=len(bool_fields)):
            ev = DecisionEvidence(
                literature_gate=lit,
                public_benchmark_gate=bench,
                candidate_gate=cand,
                candidate_stable_on_n_mandatory_datasets=2,
                has_cross_context_or_sample_efficiency_win=True,
                increment_explained_by_capacity_or_head=False,
                all_claims_free_of_invented_physics=True,
                single_paper_hypothesis_definable=True,
                **dict(zip(bool_fields, combo)),
            )
            state = resolve_final_state(ev)
            assert isinstance(state, FinalState)
            seen.add(state)
    # All seven terminal states must be reachable, or the code is over-constrained.
    assert seen == set(FINAL_STATE_PRIORITY)
