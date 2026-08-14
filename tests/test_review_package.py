from __future__ import annotations

from pathlib import Path

from certo_fdi.packaging.build_review_package import _write_manifest, _write_tree, _zip_tree
from certo_fdi.packaging.validate_review_package import (
    REQUIRED_DIRECTORIES,
    REQUIRED_FILES,
    validate_zip,
)


def test_review_package_fresh_extract_checksum_and_smoke(tmp_path: Path):
    tree = tmp_path / "tree"
    tree.mkdir()
    generated = {"08_FILE_TREE.txt", "09_MANIFEST.json", "10_SHA256SUMS.txt"}
    for relative in REQUIRED_FILES:
        if relative in generated:
            continue
        path = tree / relative
        if relative == "19_REPRODUCE_REVIEW.sh":
            path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n[ \"$1\" = --smoke ]\n")
            path.chmod(0o755)
        elif relative.endswith(".json"):
            path.write_text('{"validation_status":"PASS"}\n')
        else:
            path.write_text("test artifact\n")
    for relative in REQUIRED_DIRECTORIES:
        (tree / relative).mkdir()
    _write_tree(tree)
    _write_manifest(tree)
    archive = tmp_path / "review.zip"
    _zip_tree(tree, archive)
    result = validate_zip(archive)
    assert result["validation_status"] == "PASS"
