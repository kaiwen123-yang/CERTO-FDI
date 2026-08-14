from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path


REQUIRED_FILES = (
    "00_READ_ME_FIRST.md",
    "01_REVIEW_PROMPT.md",
    "02_EXECUTION_SUMMARY.md",
    "03_DECISION_MEMO.md",
    "04_KNOWN_ISSUES.md",
    "05_OPEN_PROOF_OBLIGATIONS.md",
    "06_CLAIMS_LEDGER.csv",
    "07_THEOREM_STATUS.csv",
    "08_FILE_TREE.txt",
    "09_MANIFEST.json",
    "10_SHA256SUMS.txt",
    "19_REPRODUCE_REVIEW.sh",
    "REVIEW_PACKAGE_STATUS.json",
)
REQUIRED_DIRECTORIES = (
    "11_ENVIRONMENT",
    "12_GIT_PROVENANCE",
    "13_CODE_SNAPSHOT",
    "14_CONFIGS",
    "15_TEST_REPORTS",
    "16_CORE_RESULTS",
    "17_SELECTED_FIGURES",
    "18_DOCUMENT_DIFFS",
)
SECRET_PATTERNS = (
    re.compile(rb"ghp_[A-Za-z0-9]{20,}"),
    re.compile(rb"gho_[A-Za-z0-9]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_checksums(root: Path) -> None:
    for line in (root / "10_SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", maxsplit=1)
        target = root / relative
        if not target.is_file() or sha256_file(target) != expected:
            raise RuntimeError(f"checksum mismatch: {relative}")


def _scan_secrets(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        data = path.read_bytes()
        for pattern in SECRET_PATTERNS:
            if pattern.search(data):
                raise RuntimeError(f"secret-like pattern in {path.relative_to(root)}")


def validate_zip(path: str | Path) -> dict[str, object]:
    archive = Path(path).resolve()
    with zipfile.ZipFile(archive) as handle:
        bad_member = handle.testzip()
        if bad_member is not None:
            raise RuntimeError(f"zip CRC failure: {bad_member}")
        with tempfile.TemporaryDirectory(prefix="certo_review_validate_") as temporary:
            root = Path(temporary)
            handle.extractall(root)
            for relative in REQUIRED_FILES:
                if not (root / relative).is_file():
                    raise RuntimeError(f"required file missing: {relative}")
            for relative in REQUIRED_DIRECTORIES:
                if not (root / relative).is_dir():
                    raise RuntimeError(f"required directory missing: {relative}")
            _verify_checksums(root)
            subprocess.run(
                ["bash", str(root / "19_REPRODUCE_REVIEW.sh"), "--smoke"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            _scan_secrets(root)
            json.loads((root / "09_MANIFEST.json").read_text(encoding="utf-8"))
    return {
        "archive": str(archive),
        "sha256": sha256_file(archive),
        "size_bytes": archive.stat().st_size,
        "validation_status": "PASS",
        "checks": [
            "zip_crc",
            "fresh_extract",
            "sha256_manifest",
            "required_topology",
            "reproduce_smoke",
            "secret_scan",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    args = parser.parse_args()
    print(json.dumps(validate_zip(args.archive), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
