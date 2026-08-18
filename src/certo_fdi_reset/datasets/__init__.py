"""Public-dataset feasibility, licence, schema and applicability auditing.

Contracts: ``09_DATASET_FEASIBILITY_AND_DOWNLOAD_PROTOCOL.md``,
``24_DATASET_LICENSE_AND_ACCESS_CHECKLIST.md``.

Nothing here downloads bulk data. Phase D0 resolves *what a dataset is* -- version,
licence, files, checksums, declared signals -- so that the physics grade (P0-P3)
and the applicability matrix are decided before a single byte of bulk data is
fetched, and never inferred from a robot model name.
"""

from .registry import RegistryRow, load_registry
from .feasibility import FeasibilityCard, PhysicsGrade

__all__ = ["RegistryRow", "load_registry", "FeasibilityCard", "PhysicsGrade"]
