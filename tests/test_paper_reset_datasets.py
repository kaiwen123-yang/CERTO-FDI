"""Dataset registry parsing and physics-grade derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

from certo_fdi_reset.datasets.feasibility import (
    ADAPTERS_BY_GRADE,
    FeasibilityCard,
    PhysicsGrade,
)
from certo_fdi_reset.datasets.registry import load_registry

REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "contracts" / "paper_reset" / "08_PUBLIC_DATASET_REGISTRY.csv"
)


@pytest.fixture(scope="module")
def registry():
    return load_registry(REGISTRY)


def test_registry_parses_and_marks_the_three_mandatory_datasets(registry):
    assert {r.dataset_id for r in registry if r.is_mandatory} == {"voraus_ad", "road", "aursad"}


def test_sarcos_is_never_fault_evidence(registry):
    """Contract 15 hard prohibition: SARCOS must not count as fault data."""
    sarcos = next(r for r in registry if r.dataset_id == "sarcos")
    assert sarcos.is_fault_evidence_eligible is False
    assert sarcos.physics_level == "PHYSICS_NORMAL_ONLY"


def test_every_registry_row_starts_unaudited_or_explicitly_graded(registry):
    for row in registry:
        assert row.physics_level, row.dataset_id


# --- physics grade ------------------------------------------------------------

def test_time_series_only_permits_the_joint_gru_alone():
    card = FeasibilityCard(dataset_id="x", channel_count=10, documented_signals=["torque_total"])
    assert card.grade() is PhysicsGrade.P0_TIME_SERIES_ONLY
    assert card.permitted_adapters == ("joint_gru_public",)


def test_per_joint_grouping_without_physics_is_p1():
    card = FeasibilityCard(
        dataset_id="x",
        channel_count=20,
        documented_signals=["joint 1 temperature", "joint 2 temperature"],
    )
    assert card.grade() is PhysicsGrade.P1_JOINT_TOPOLOGY_ONLY
    assert "chain_gnn_public" in card.permitted_adapters
    assert "geometry_aware_chain_public" not in card.permitted_adapters


def test_link_orientation_lifts_a_dataset_to_p2():
    """RoAD's per-joint IMU quaternions are documented geometry, not invented."""
    card = FeasibilityCard(
        dataset_id="road",
        channel_count=87,
        documented_signals=["joint 1 quaternion orientation component 1"],
        has_link_orientation=True,
        has_joint_position=False,
        has_joint_torque=False,
        has_urdf_or_inertia=False,
    )
    assert card.grade() is PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS
    assert "geometry_aware_chain_public" in card.permitted_adapters
    assert "rnea_gmo_public" not in card.permitted_adapters


def test_p3_requires_urdf_position_and_torque_together():
    card = FeasibilityCard(
        dataset_id="x",
        has_urdf_or_inertia=True,
        has_joint_position=True,
        has_joint_torque=True,
    )
    assert card.grade() is PhysicsGrade.P3_FULL_DYNAMICS_METADATA
    assert "rnea_gmo_public" in card.permitted_adapters

    missing_urdf = FeasibilityCard(
        dataset_id="y", has_urdf_or_inertia=False, has_joint_position=True, has_joint_torque=True
    )
    assert missing_urdf.grade() is PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS
    assert "rnea_gmo_public" not in missing_urdf.permitted_adapters


def test_adapter_ladder_is_monotonic():
    """Each grade permits everything the grade below it permits."""
    order = [
        PhysicsGrade.P0_TIME_SERIES_ONLY,
        PhysicsGrade.P1_JOINT_TOPOLOGY_ONLY,
        PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS,
        PhysicsGrade.P3_FULL_DYNAMICS_METADATA,
    ]
    for lower, higher in zip(order, order[1:]):
        assert set(ADAPTERS_BY_GRADE[lower]) <= set(ADAPTERS_BY_GRADE[higher])


def test_unknown_signals_stay_unknown_not_false():
    """A missing quantity must not silently read as 'absent' in the matrix."""
    card = FeasibilityCard(dataset_id="x")
    row = card.as_csv_row()
    assert row["has_joint_torque"] == "UNKNOWN"
    assert row["redistribution_allowed"] == "UNKNOWN"
