"""Download a declared public data file and record what §6.8 demands about it.

The mandatory datasets were fetched before this module existed, so the acquisition
facts for them live in the probe manifest. That is fine for two files and hopeless
for six datasets: the contract asks for URL, ETag, Last-Modified, Content-Length,
SHA256, download timestamp and the local immutable path *per file*, and explicitly
forbids relying on the filename alone. This module makes that record a by-product
of downloading rather than something a human retypes afterwards.

Three rules shape it:

* the acquisition table is declarative and lives in the repository, so a reviewer
  can see exactly which files this round is entitled to fetch -- nothing is
  downloaded from a URL that only ever existed in a shell history;
* a file already present with a matching SHA256 is never re-downloaded, and a file
  present with a *different* SHA256 is a loud failure, not a silent overwrite;
* size and, when the record publishes one, MD5 are checked against the metadata we
  probed, because a truncated 2 GB download that "worked" is the failure mode that
  quietly poisons a benchmark.

    python -m certo_fdi_reset.datasets.acquire --config configs/paper_reset.yaml \
        --only sarcos,ur5e_graabaek
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

from ..config import load_config
from ..provenance import sha256_file, utc_stamp, write_manifest

USER_AGENT = "CERTO-FDI-paper-reset/1.0 (research audit; mailto:tarekmasserini291@gmail.com)"
TIMEOUT = 120
CHUNK = 1 << 20
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
RETRIES = 4

#: Headers kept verbatim beside the file, so the local copy stays attributable to
#: the exact server-side object it came from.
PROVENANCE_HEADERS: tuple[str, ...] = (
    "ETag",
    "Last-Modified",
    "Content-Length",
    "Content-Type",
    "Content-Disposition",
    "Content-Encoding",
    "Server",
    "Date",
)


@dataclass(frozen=True)
class Acquisition:
    """One file this round is entitled to download."""

    dataset_id: str
    key: str
    url: str
    purpose: str
    #: Expected size from the record metadata, when the record publishes one.
    expected_bytes: int | None = None
    #: Expected MD5 from the record metadata (Zenodo publishes these).
    expected_md5: str = ""
    #: Licence note that decides whether the file may leave this machine.
    redistribution: str = "local analysis only"


ACQUISITIONS: tuple[Acquisition, ...] = (
    # --- UR5e / Graabaek et al. (SUPPLEMENTARY). CC-BY-NC-4.0: never redistributed.
    # Only the documentation is fetched; the 2.58 GB data.zip stays unfetched until
    # the schema audit says the set is worth it (contract 6.9: metadata first).
    Acquisition(
        "ur5e_graabaek", "README.md",
        "https://zenodo.org/records/5849300/files/README.md?download=1",
        "documented schema, signals and split",
        expected_bytes=2_017, expected_md5="f519ec2525a9a510f21fef24db6311c3",
        redistribution="CC-BY-NC-4.0: local analysis only, never in git or a review package",
    ),
    Acquisition(
        "ur5e_graabaek", "ExperimentalDescription.pdf",
        "https://zenodo.org/records/5849300/files/ExperimentalDescription.pdf?download=1",
        "sampling rate, signal list, anomaly definitions, run structure",
        expected_bytes=1_148_708, expected_md5="c24f5f6d09e9aa89f3aa3f4300a76932",
        redistribution="CC-BY-NC-4.0: local analysis only, never in git or a review package",
    ),
    Acquisition(
        "ur5e_graabaek", "data.zip",
        "https://zenodo.org/records/5849300/files/data.zip?download=1",
        "the only source for the recorded RTDE channel list, per-run structure and labels",
        expected_bytes=2_584_585_052, expected_md5="7b69a1794ee1bca152fbf32ec627747e",
        redistribution="CC-BY-NC-4.0: local analysis only, never in git or a review package",
    ),
    # --- SARCOS (NORMAL_ONLY). Tiny; both official files, so the published
    # train/test split is verified from the files instead of from the page text.
    # The sizes below are the *file* sizes, not the numbers a default HEAD reports.
    # gaussianprocess.org (GitHub Pages) gzips these .mat files on the wire, so a
    # request that accepts gzip gets Content-Length 6,206,301 with a WEAK ETag,
    # while `Accept-Encoding: identity` gets Content-Length 9,964,616 with a STRONG
    # ETag -- and the weak ETag's second hex field (980c48) is the uncompressed
    # size all along. An earlier probe recorded the compressed length as the file
    # size; taking it at face value would have flagged every correct download as
    # truncated. See dataset_known_issues.md.
    Acquisition(
        "sarcos", "sarcos_inv.mat",
        "http://gaussianprocess.org/gpml/data/sarcos_inv.mat",
        "healthy inverse-dynamics train split: row count and column semantics",
        expected_bytes=9_964_616,
        redistribution="no license statement published: local analysis only",
    ),
    Acquisition(
        "sarcos", "sarcos_inv_test.mat",
        "http://gaussianprocess.org/gpml/data/sarcos_inv_test.mat",
        "healthy inverse-dynamics test split",
        expected_bytes=996_776,
        redistribution="no license statement published: local analysis only",
    ),
    # --- PyScrew (OPTIONAL_LARGE_SCALE). One representative scenario only, per
    # contract 6.9 -- the smallest, so the schema card costs 12 MB and not 300 MB.
    Acquisition(
        "pyscrew", "s03_variations-in-assembly-conditions-1.zip",
        "https://zenodo.org/records/16031381/files/s03_variations-in-assembly-conditions-1.zip?download=1",
        "representative scenario: per-operation schema, channel set, sampling semantics",
        expected_bytes=12_588_378,
        redistribution="CC-BY-4.0: attribution required; not redistributed here",
    ),
)


def _session() -> requests.Session:
    session = requests.Session()
    # Identity encoding, so Content-Length is the size of the file we are storing
    # rather than the size of its gzip transfer -- the two differ by 60% on
    # gaussianprocess.org and the difference reads exactly like a truncated file.
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    return session


def _md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_headers(path: Path, url: str, final_url: str, headers) -> None:
    lines = [f"# request: {url}", f"# final:   {final_url}", ""]
    lines += [f"{name}: {headers.get(name, '')}" for name in PROVENANCE_HEADERS]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def acquire_one(item: Acquisition, dest_dir: Path, session: requests.Session) -> dict:
    """Download ``item`` unless an identical local copy already exists."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / item.key
    record: dict = {
        "dataset_id": item.dataset_id,
        "key": item.key,
        "url": item.url,
        "purpose": item.purpose,
        "local_path": str(dest),
        "redistribution": item.redistribution,
        "expected_bytes": item.expected_bytes,
        "expected_md5": item.expected_md5 or None,
        "requested_utc": utc_stamp(),
    }

    if dest.exists():
        local_sha = sha256_file(dest)
        record.update(
            {
                "status": "ALREADY_PRESENT",
                "local_bytes": dest.stat().st_size,
                "local_sha256": local_sha,
                "local_md5": _md5_file(dest) if item.expected_md5 else None,
                "downloaded": False,
            }
        )
        headers_path = dest.with_suffix(dest.suffix + ".headers.txt")
        record["headers_file"] = str(headers_path) if headers_path.exists() else None
        return _check(record, item)

    response = None
    for attempt in range(1, RETRIES + 1):
        response = session.get(item.url, timeout=TIMEOUT, stream=True, allow_redirects=True)
        if response.status_code in RETRY_STATUS and attempt < RETRIES:
            response.close()
            continue
        break
    assert response is not None
    record["http_status"] = response.status_code
    record["final_url"] = response.url
    if response.status_code != 200:
        record.update({"status": f"HTTP_{response.status_code}", "downloaded": False})
        response.close()
        return record

    # Download to a partial file so an interrupted transfer can never be mistaken
    # for a complete one on the next run.
    partial = dest.with_suffix(dest.suffix + ".partial")
    digest = hashlib.sha256()
    md5 = hashlib.md5()
    written = 0
    with partial.open("wb") as handle:
        for block in response.iter_content(chunk_size=CHUNK):
            if not block:
                continue
            handle.write(block)
            digest.update(block)
            md5.update(block)
            written += len(block)
    headers = response.headers
    response.close()

    headers_path = dest.with_suffix(dest.suffix + ".headers.txt")
    _write_headers(headers_path, item.url, record["final_url"], headers)
    partial.replace(dest)

    record.update(
        {
            "status": "DOWNLOADED",
            "downloaded": True,
            "download_utc": utc_stamp(),
            "local_bytes": written,
            "local_sha256": digest.hexdigest(),
            "local_md5": md5.hexdigest(),
            "headers_file": str(headers_path),
            "header_etag": headers.get("ETag", ""),
            "header_last_modified": headers.get("Last-Modified", ""),
            "header_content_length": headers.get("Content-Length", ""),
            "header_content_type": headers.get("Content-Type", ""),
            "header_content_encoding": headers.get("Content-Encoding", "identity"),
        }
    )
    return _check(record, item)


def _check(record: dict, item: Acquisition) -> dict:
    """Fail loudly on a size or MD5 that contradicts the published record."""
    problems = []
    if item.expected_bytes is not None and record.get("local_bytes") != item.expected_bytes:
        problems.append(f"size {record.get('local_bytes')} != published {item.expected_bytes}")
    if item.expected_md5 and record.get("local_md5") != item.expected_md5:
        problems.append(f"md5 {record.get('local_md5')} != published {item.expected_md5}")
    record["integrity"] = "OK" if not problems else "MISMATCH"
    record["integrity_problems"] = problems
    if problems:
        record["status"] = "FAILED_INTEGRITY"
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.datasets.acquire")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--only", default="", help="Comma-separated dataset_ids to acquire.")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    layout = cfg.layout
    wanted = {token.strip() for token in args.only.split(",") if token.strip()}
    items = [i for i in ACQUISITIONS if not wanted or i.dataset_id in wanted]
    if not items:
        print(f"ERROR: no acquisitions match --only={args.only!r}", file=sys.stderr)
        return 2

    if args.dry_run:
        for item in items:
            print(f"{item.dataset_id:16s} {item.key:48s} {item.expected_bytes or '?':>12} B  {item.url}")
        return 0

    session = _session()
    records = []
    for index, item in enumerate(items, start=1):
        dest_dir = layout.public_data_root / item.dataset_id
        record = acquire_one(item, dest_dir, session)
        records.append(record)
        print(
            f"[{index}/{len(items)}] {item.dataset_id:16s} {item.key:46s} "
            f"{record['status']:18s} integrity={record.get('integrity', '-')} "
            f"{record.get('local_bytes', 0):>12,} B"
        )
        for problem in record.get("integrity_problems", []):
            print(f"    INTEGRITY: {problem}", file=sys.stderr)

    out = layout.run_dir(cfg.run_id) / "d0" / "dataset_acquisition_manifest.json"
    payload = {
        "run_id": cfg.run_id,
        "config_sha": cfg.config_sha,
        "generated_utc": utc_stamp(),
        "requested": sorted(wanted) or "all",
        "counts": {
            "total": len(records),
            "downloaded": sum(1 for r in records if r.get("downloaded")),
            "already_present": sum(1 for r in records if r["status"] == "ALREADY_PRESENT"),
            "failed": sum(1 for r in records if r["status"].startswith(("HTTP_", "FAILED"))),
        },
        "files": records,
    }
    # Merge with any earlier acquisition manifest so the record accumulates.
    if out.exists():
        previous = json.loads(out.read_text(encoding="utf-8"))
        keyed = {(f["dataset_id"], f["key"]): f for f in previous.get("files", [])}
        keyed.update({(f["dataset_id"], f["key"]): f for f in records})
        payload["files"] = sorted(keyed.values(), key=lambda f: (f["dataset_id"], f["key"]))
        payload["counts"]["total"] = len(payload["files"])
    sha = write_manifest(out, payload)
    print(f"manifest  {out}  sha256={sha}")
    return 0 if payload["counts"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
