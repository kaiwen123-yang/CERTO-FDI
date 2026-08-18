"""Feasibility cards and the physics grade.

The grade decides which candidate adapters may run at all
(``13_CANDIDATE_MODEL_ADAPTER_PROTOCOL.md`` §2). It is derived only from signals
the dataset *documents*; a missing quantity is ``NOT_APPLICABLE``, never guessed
from the robot model (§3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PhysicsGrade(str, Enum):
    P0_TIME_SERIES_ONLY = "P0_TIME_SERIES_ONLY"
    P1_JOINT_TOPOLOGY_ONLY = "P1_JOINT_TOPOLOGY_ONLY"
    P2_PARTIAL_PHYSICS_SIGNALS = "P2_PARTIAL_PHYSICS_SIGNALS"
    P3_FULL_DYNAMICS_METADATA = "P3_FULL_DYNAMICS_METADATA"
    TO_BE_AUDITED = "TO_BE_AUDITED"


# Which adapters each grade permits. Anything absent is NOT_APPLICABLE and may not
# be reported as a method failure (14_DECISION_RULES.md, CANDIDATE_NOT_APPLICABLE).
ADAPTERS_BY_GRADE: dict[PhysicsGrade, tuple[str, ...]] = {
    PhysicsGrade.P0_TIME_SERIES_ONLY: ("joint_gru_public",),
    PhysicsGrade.P1_JOINT_TOPOLOGY_ONLY: ("joint_gru_public", "chain_gnn_public"),
    PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS: (
        "joint_gru_public",
        "chain_gnn_public",
        "geometry_aware_chain_public",
    ),
    PhysicsGrade.P3_FULL_DYNAMICS_METADATA: (
        "joint_gru_public",
        "chain_gnn_public",
        "geometry_aware_chain_public",
        "frame_aug_chain_public",
        "rnea_gmo_public",
    ),
}


@dataclass
class FeasibilityCard:
    """One dataset's Phase D0 record. Unknown fields stay empty, never guessed."""

    dataset_id: str
    official_url: str = ""
    paper_doi: str = ""
    version: str = ""
    publication_date: str = ""
    license_id: str = ""
    license_url: str = ""
    license_verified: bool = False
    redistribution_allowed: bool | None = None
    noncommercial_only: bool | None = None
    access_route: str = ""
    files: list[dict] = field(default_factory=list)
    total_bytes: int = 0
    robot: str = ""
    task: str = ""
    sampling_rate_hz: float | None = None
    episode_unit: str = ""
    channel_count: int | None = None
    documented_signals: list[str] = field(default_factory=list)
    has_joint_position: bool | None = None
    has_joint_velocity: bool | None = None
    has_joint_torque: bool | None = None
    has_commanded_torque: bool | None = None
    has_link_orientation: bool | None = None
    has_urdf_or_inertia: bool | None = None
    official_split: str = ""
    label_semantics: str = ""
    native_code_url: str = ""
    native_code_commit: str = ""
    native_code_license: str = ""
    physics_grade: PhysicsGrade = PhysicsGrade.TO_BE_AUDITED
    permitted_adapters: tuple[str, ...] = ()
    supportable_claims: list[str] = field(default_factory=list)
    unsupportable_claims: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def grade(self) -> PhysicsGrade:
        """Derive the physics grade from documented signals only."""
        if self.has_urdf_or_inertia and self.has_joint_position and self.has_joint_torque:
            grade = PhysicsGrade.P3_FULL_DYNAMICS_METADATA
        elif self.has_joint_position or self.has_link_orientation or self.has_joint_torque:
            grade = PhysicsGrade.P2_PARTIAL_PHYSICS_SIGNALS
        elif self.channel_count and self.documented_signals and self._has_per_joint_grouping():
            grade = PhysicsGrade.P1_JOINT_TOPOLOGY_ONLY
        else:
            grade = PhysicsGrade.P0_TIME_SERIES_ONLY
        self.physics_grade = grade
        self.permitted_adapters = ADAPTERS_BY_GRADE[grade]
        return grade

    def _has_per_joint_grouping(self) -> bool:
        return any("joint" in s.casefold() or "axis" in s.casefold() for s in self.documented_signals)

    def as_csv_row(self) -> dict[str, str]:
        return {
            "dataset_id": self.dataset_id,
            "official_url": self.official_url,
            "paper_doi": self.paper_doi,
            "version": self.version,
            "publication_date": self.publication_date,
            "license_id": self.license_id,
            "license_verified": str(self.license_verified).lower(),
            "redistribution_allowed": _tri(self.redistribution_allowed),
            "noncommercial_only": _tri(self.noncommercial_only),
            "access_route": self.access_route,
            "file_count": str(len(self.files)),
            "total_bytes": str(self.total_bytes),
            "robot": self.robot,
            "task": self.task,
            "sampling_rate_hz": "" if self.sampling_rate_hz is None else str(self.sampling_rate_hz),
            "channel_count": "" if self.channel_count is None else str(self.channel_count),
            "has_joint_position": _tri(self.has_joint_position),
            "has_joint_velocity": _tri(self.has_joint_velocity),
            "has_joint_torque": _tri(self.has_joint_torque),
            "has_link_orientation": _tri(self.has_link_orientation),
            "has_urdf_or_inertia": _tri(self.has_urdf_or_inertia),
            "official_split": self.official_split,
            "native_code_url": self.native_code_url,
            "native_code_commit": self.native_code_commit,
            "native_code_license": self.native_code_license,
            "physics_grade": self.physics_grade.value,
            "permitted_adapters": "; ".join(self.permitted_adapters),
            "blockers": "; ".join(self.blockers),
            "notes": " | ".join(self.notes),
        }


CARD_CSV_COLUMNS: tuple[str, ...] = (
    "dataset_id", "official_url", "paper_doi", "version", "publication_date",
    "license_id", "license_verified", "redistribution_allowed", "noncommercial_only",
    "access_route", "file_count", "total_bytes", "robot", "task", "sampling_rate_hz",
    "channel_count", "has_joint_position", "has_joint_velocity", "has_joint_torque",
    "has_link_orientation", "has_urdf_or_inertia", "official_split",
    "native_code_url", "native_code_commit", "native_code_license",
    "physics_grade", "permitted_adapters", "blockers", "notes",
)


def _tri(value: bool | None) -> str:
    """Tri-state: unknown stays UNKNOWN rather than collapsing to false."""
    return "UNKNOWN" if value is None else str(value).lower()
