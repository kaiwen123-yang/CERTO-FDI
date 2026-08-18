"""Persistent-storage root resolution.

The external storage root is never hard-coded in business Python: it comes from
``CERTO_PERSIST_ROOT`` or from the stage config. This keeps the repository
portable between the WSL drvfs mount and a native filesystem, and satisfies the
``scripts/check_repo_hygiene.sh`` rule that forbids hard-coded storage paths in
``src/``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_PERSIST_ROOT = "CERTO_PERSIST_ROOT"


class PersistRootError(RuntimeError):
    """Raised when the persistent storage root cannot be resolved or verified."""


@dataclass(frozen=True)
class PersistLayout:
    """Directory layout mandated by contract 15_GIT_STORAGE_AND_PR_PLAN.md."""

    root: Path

    @property
    def literature_root(self) -> Path:
        return self.root / "01_frozen_sources" / "literature_reset"

    @property
    def literature_metadata(self) -> Path:
        return self.literature_root / "metadata"

    @property
    def literature_open_fulltexts(self) -> Path:
        return self.literature_root / "open_fulltexts"

    @property
    def literature_access_manifest(self) -> Path:
        return self.literature_root / "access_manifest"

    @property
    def baseline_repos(self) -> Path:
        return self.root / "01_frozen_sources" / "public_baseline_repos"

    @property
    def research_docs(self) -> Path:
        return self.root / "02_research_docs" / "paper_reset"

    @property
    def public_data_root(self) -> Path:
        return self.root / "03_data" / "public"

    @property
    def run_root(self) -> Path:
        return self.root / "04_runs" / "paper_reset_public_benchmarks"

    @property
    def reference_results(self) -> Path:
        return self.root / "05_reference_results" / "paper_reset"

    @property
    def review_exchange(self) -> Path:
        return self.root / "06_review_exchange" / "to_review"

    def run_dir(self, run_id: str) -> Path:
        return self.run_root / run_id

    def all_dirs(self) -> list[Path]:
        docs = [self.research_docs / d for d in ("literature", "novelty", "datasets", "decisions")]
        data = [
            self.public_data_root / d
            for d in ("voraus_ad", "road", "aursad", "ur5e_graabaek", "pyscrew")
        ]
        review = [self.review_exchange / d for d in ("thin", "full")]
        return [
            self.literature_metadata,
            self.literature_open_fulltexts,
            self.literature_access_manifest,
            self.baseline_repos,
            *docs,
            *data,
            self.run_root,
            self.reference_results,
            *review,
        ]


def resolve_persist_root(config_default: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the persistent storage root.

    Precedence: ``CERTO_PERSIST_ROOT`` environment variable, then the stage
    config default. Raises if neither is available.
    """
    env_value = os.environ.get(ENV_PERSIST_ROOT)
    chosen = env_value or (str(config_default) if config_default else None)
    if not chosen:
        raise PersistRootError(
            f"No persistent root: set {ENV_PERSIST_ROOT} or storage.persistent_root in the config."
        )
    return Path(chosen).expanduser()


def is_real_mountpoint(path: str | os.PathLike[str]) -> bool:
    """True if ``path`` is an actual mountpoint, not just a directory on the parent fs.

    Delegates to :func:`os.path.ismount`, which also handles the filesystem root
    (its own parent) and bind mounts (same device, different inode) -- a plain
    ``st_dev != parent.st_dev`` comparison gets both of those wrong.

    The case this guards is the one seen at kickoff: the external storage path
    existing as an empty directory on the ext4 root because WSL never automounted
    the underlying Windows volume.
    """
    p = Path(path)
    if not p.is_dir():
        return False
    try:
        return os.path.ismount(p)
    except OSError:
        return False
