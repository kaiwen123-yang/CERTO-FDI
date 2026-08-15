from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from certo_fdi.packaging.validate_review_package import REQUIRED_DIRECTORIES, REQUIRED_FILES, validate_zip


def test_validate_zip_rejects_missing_topology(tmp_path: Path):
    z = tmp_path / "bad.zip"
    with zipfile.ZipFile(z, "w") as h:
        h.writestr("00_READ_ME_FIRST.md", "x")
    with pytest.raises(RuntimeError):
        validate_zip(z)


def test_required_topology_lists_are_consistent():
    assert "19_REPRODUCE_REVIEW.sh" in REQUIRED_FILES
    assert "16_CORE_RESULTS" in REQUIRED_DIRECTORIES and "18_DATASET_MANIFESTS" in REQUIRED_DIRECTORIES
