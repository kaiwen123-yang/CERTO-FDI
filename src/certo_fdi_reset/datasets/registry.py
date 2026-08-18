"""Read the frozen dataset registry (08_PUBLIC_DATASET_REGISTRY.csv)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RegistryRow:
    dataset_id: str
    priority: str
    official_source: str
    paper_or_doi: str
    robot_task: str
    public_signals_claim: str
    native_code: str
    license_status: str
    required_role: str
    physics_level: str
    notes: str

    @property
    def is_mandatory(self) -> bool:
        return self.priority.startswith("MANDATORY")

    @property
    def is_fault_evidence_eligible(self) -> bool:
        """SARCOS is healthy dynamics only and must never count as fault evidence."""
        return self.priority != "NORMAL_ONLY_OPTIONAL"


def load_registry(path: str | Path) -> list[RegistryRow]:
    with Path(path).open(encoding="utf-8") as fh:
        return [RegistryRow(**row) for row in csv.DictReader(fh)]
