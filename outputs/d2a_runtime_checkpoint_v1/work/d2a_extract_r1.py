"""Safely restore immutable R1 source; no archived code is executed."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import stat
import zipfile

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "inputs/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip"
DEST = ROOT / "work/r1_extract"
EXPECTED = "f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b"

def longpath(path):
    value = str(path.resolve())
    return "\\\\?\\" + value if os.name == "nt" else value

def digest(path):
    with open(longpath(path), "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def main():
    initial = digest(ARCHIVE)
    assert initial == EXPECTED, (initial, EXPECTED)
    DEST.mkdir(parents=True, exist_ok=False)
    resolved_root = DEST.resolve()
    seen = set()
    file_hashes = {}
    size = 0
    with zipfile.ZipFile(longpath(ARCHIVE)) as archive:
        # Validate all target paths before the first content write.
        planned = []
        for entry in archive.infolist():
            name = entry.filename
            part = PurePosixPath(name)
            assert "\\" not in name and ":" not in name, name
            assert not part.is_absolute() and ".." not in part.parts, name
            assert part.parts and all(p not in ("", ".") for p in part.parts), name
            mode = entry.external_attr >> 16
            assert not stat.S_ISLNK(mode), name
            folded = str(part).rstrip("/").casefold()
            assert folded not in seen, name
            seen.add(folded)
            target = (DEST / Path(*part.parts)).resolve()
            target.relative_to(resolved_root)
            assert target != resolved_root, name
            planned.append((entry, target))
        for entry, target in planned:
            if entry.is_dir():
                os.makedirs(longpath(target), exist_ok=True)
                continue
            os.makedirs(longpath(target.parent), exist_ok=True)
            with archive.open(entry) as source, open(longpath(target), "xb") as output:
                shutil.copyfileobj(source, output)
            file_hashes[entry.filename] = digest(target)
            size += entry.file_size
    final = digest(ARCHIVE)
    assert final == initial
    receipt = {
        "archive": str(ARCHIVE), "archive_sha256_before": initial,
        "archive_sha256_after": final, "destination": str(resolved_root),
        "members": len(planned), "extracted_files": len(file_hashes),
        "uncompressed_file_bytes": size,
        "checks": ["no absolute paths", "no parent traversal", "no symlinks",
                   "no casefold duplicate paths", "all resolved targets within destination",
                   "all ZIP member CRCs checked by full stream reads", "archive unchanged"],
        "execution": "safe extraction only; archived Python and verifier not executed",
        "file_sha256": file_hashes,
    }
    (ROOT / "work/d2a_extraction_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k != "file_sha256"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
