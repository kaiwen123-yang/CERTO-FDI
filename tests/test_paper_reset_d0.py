"""Phase D0 card tests: the rules that must hold whatever the observed facts are."""

from __future__ import annotations

import csv
import json

from certo_fdi_reset.datasets.d0 import build_cards, write_matrices
from certo_fdi_reset.datasets.feasibility import PhysicsGrade

MANDATORY = {"voraus_ad", "road", "aursad"}


def test_every_mandatory_dataset_has_a_card():
    ids = {r.card.dataset_id for r in build_cards()}
    assert MANDATORY <= ids


def test_road_cannot_reach_a_physics_residual_grade():
    """No joint angle, torque, or encoder is published, so RNEA must stay unavailable."""
    road = next(r for r in build_cards() if r.card.dataset_id == "road")
    assert road.card.physics_grade is PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS
    assert road.card.has_joint_position is False
    assert road.card.has_joint_torque is False
    assert "rnea_gmo_public" not in road.card.permitted_adapters
    assert any("RNEA" in claim for claim in road.forbidden_claims)


def test_voraus_has_joint_signals_but_no_urdf():
    """It carries joint position/velocity/torque, yet no URDF -- P2, not P3."""
    voraus = next(r for r in build_cards() if r.card.dataset_id == "voraus_ad")
    assert voraus.card.has_joint_position is True
    assert voraus.card.has_joint_torque is True
    assert voraus.card.has_urdf_or_inertia is False
    assert voraus.card.physics_grade is PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS
    assert "rnea_gmo_public" not in voraus.card.permitted_adapters


def test_sarcos_is_never_fault_evidence():
    sarcos = next(r for r in build_cards() if r.card.dataset_id == "sarcos")
    assert "NORMAL_ONLY" in sarcos.role
    assert any("fault" in claim or "anomaly" in claim for claim in sarcos.forbidden_claims)


def test_unaudited_datasets_do_not_claim_a_grade():
    """A dataset whose schema has not been read stays TO_BE_AUDITED."""
    for record in build_cards():
        if record.status.startswith(("BLOCKED", "AVAILABLE_NOT_YET_AUDITED")):
            assert record.card.physics_grade is PhysicsGrade.TO_BE_AUDITED
            assert record.card.permitted_adapters == ()


def test_non_redistributable_datasets_are_flagged():
    by_id = {r.card.dataset_id: r for r in build_cards()}
    assert by_id["voraus_ad"].card.redistribution_allowed is False
    assert by_id["ur5e_graabaek"].card.noncommercial_only is True
    assert by_id["road"].card.redistribution_allowed is False


def test_matrices_are_written_and_internally_consistent(tmp_path):
    records = build_cards()
    paths = write_matrices(records, tmp_path, "run_test", "sha_test")
    assert set(paths) == {
        "dataset_feasibility_matrix.csv",
        "dataset_license_matrix.csv",
        "dataset_signal_schema_matrix.csv",
        "dataset_applicability_matrix.csv",
        "dataset_download_manifest.json",
        "dataset_known_issues.md",
    }
    feas = list(csv.DictReader(paths["dataset_feasibility_matrix.csv"].open(encoding="utf-8")))
    assert len(feas) == len(records)

    applic = {
        row["dataset_id"]: row
        for row in csv.DictReader(paths["dataset_applicability_matrix.csv"].open(encoding="utf-8"))
    }
    # permitted and forbidden adapters must partition the adapter set, never overlap.
    for row in applic.values():
        permitted = {a for a in row["permitted_adapters"].split("; ") if a}
        forbidden = {a for a in row["forbidden_adapters"].split("; ") if a}
        assert not (permitted & forbidden)

    manifest = json.loads(paths["dataset_download_manifest.json"].read_text(encoding="utf-8"))
    assert manifest["planned_download_bytes"] > 0
    assert {d["dataset_id"] for d in manifest["datasets"]} == {r.card.dataset_id for r in records}


def test_d0_exit_gate_states_are_the_contract_ones():
    """§6.10: the round may not enter full training unless these three hold."""
    required = {
        "voraus_ad": "READY",
        "road": "READY_WITH_LICENSE_RESTRICTION",
        "aursad": "READY",
    }
    by_id = {r.card.dataset_id: r for r in build_cards()}
    for dataset_id, status in required.items():
        assert by_id[dataset_id].status == status, dataset_id


def test_aursad_has_no_measured_joint_torque():
    """It publishes commanded target_moment and currents, never a measured joint
    torque, so it must not be promoted to a full-dynamics grade."""
    aursad = next(r for r in build_cards() if r.card.dataset_id == "aursad")
    assert aursad.card.has_joint_position is True
    assert aursad.card.has_commanded_torque is True
    assert aursad.card.has_joint_torque is False
    assert aursad.card.has_urdf_or_inertia is False
    assert aursad.card.physics_grade is PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS
    assert "rnea_gmo_public" not in aursad.card.permitted_adapters


def test_no_mandatory_dataset_permits_rnea():
    """No mandatory dataset publishes a URDF, so RNEA/GMO is unavailable on all of them."""
    for record in build_cards():
        if record.card.dataset_id in MANDATORY:
            assert "rnea_gmo_public" not in record.card.permitted_adapters
