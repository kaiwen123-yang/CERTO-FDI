"""Phase D0 evidence collection: probe official dataset and code endpoints.

A feasibility card may only assert what was actually observed
(``09_DATASET_FEASIBILITY_AND_DOWNLOAD_PROTOCOL.md``): a license claim needs the
license file or record metadata, a size claim needs ``Content-Length``, a version
claim needs a resolved record or commit. This module performs those requests and
writes every response body plus the provenance-bearing headers to the persistent
root, so the cards can later be re-derived from stored evidence rather than from
a transcript.

Nothing here decides anything. It only fetches, hashes, and records -- including
failures, which are evidence too (a 403 is why a card says ``BLOCKED``).

    python -m certo_fdi_reset.datasets.probe --config configs/paper_reset.yaml
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import requests

from ..config import load_config
from ..provenance import sha256_bytes, utc_stamp, write_manifest

USER_AGENT = "CERTO-FDI-paper-reset/1.0 (research audit; mailto:tarekmasserini291@gmail.com)"
TIMEOUT = 45

#: Headers that carry provenance and must be preserved verbatim in the evidence.
PROVENANCE_HEADERS: tuple[str, ...] = (
    "ETag",
    "Last-Modified",
    "Content-Length",
    "Content-Type",
    "Content-Disposition",
    "Content-Encoding",
    "Location",
    "Server",
    "Date",
)


@dataclass(frozen=True)
class Endpoint:
    dataset_id: str
    key: str
    url: str
    purpose: str
    method: str = "GET"
    allow_redirects: bool = True


ENDPOINTS: tuple[Endpoint, ...] = (
    # --- voraus-AD (MANDATORY_1) ---
    Endpoint("voraus_ad", "repo", "https://api.github.com/repos/vorausrobotik/voraus-ad-dataset", "official repo metadata"),
    Endpoint("voraus_ad", "commits", "https://api.github.com/repos/vorausrobotik/voraus-ad-dataset/commits?per_page=5", "head commit to freeze"),
    Endpoint("voraus_ad", "license", "https://api.github.com/repos/vorausrobotik/voraus-ad-dataset/license", "code license"),
    Endpoint("voraus_ad", "contents", "https://api.github.com/repos/vorausrobotik/voraus-ad-dataset/contents", "top-level file listing"),
    Endpoint("voraus_ad", "releases", "https://api.github.com/repos/vorausrobotik/voraus-ad-dataset/releases", "released data assets"),
    Endpoint("voraus_ad", "readme", "https://raw.githubusercontent.com/vorausrobotik/voraus-ad-dataset/main/README.md", "documented schema and download route"),
    # --- RoAD (MANDATORY_2) ---
    Endpoint("road", "repo", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset", "official repo metadata"),
    Endpoint("road", "tree", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/tree?recursive=true&per_page=100", "file inventory"),
    Endpoint("road", "commits", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/commits?per_page=5", "head commit to freeze"),
    Endpoint("road", "readme", "https://gitlab.com/AlessioMascolini/roaddataset/-/raw/main/README.md", "documented schema"),
    # --- AURSAD (MANDATORY_3) ---
    Endpoint("aursad", "zenodo_4487073", "https://zenodo.org/api/records/4487073", "dataset record, files, MD5, license"),
    Endpoint("aursad", "zenodo_4559556", "https://zenodo.org/api/records/4559556", "second referenced record"),
    Endpoint("aursad", "arxiv", "https://export.arxiv.org/api/query?id_list=2102.01409", "canonical paper metadata"),
    Endpoint("aursad", "code_search", "https://api.github.com/search/repositories?q=aursad+in:name,description", "official loader package"),
    # --- supplementary ---
    Endpoint("ur5e_graabaek", "zenodo_5849300", "https://zenodo.org/api/records/5849300", "dataset record and license"),
    Endpoint("pyscrew", "repo", "https://api.github.com/repos/nikolaiwest/pyscrew", "official package"),
    Endpoint("pyscrew", "readme", "https://raw.githubusercontent.com/nikolaiwest/pyscrew/main/README.md", "scenarios and data route"),
    Endpoint("pyscrew", "zenodo_search", "https://zenodo.org/api/records?q=pyscrew&size=20", "dataset records per scenario"),
    Endpoint("pyscrew", "arxiv", "https://export.arxiv.org/api/query?id_list=2505.11925", "canonical paper metadata"),
    # --- baselines / native code ---
    Endpoint("varade", "code_search", "https://api.github.com/search/repositories?q=VARADE", "VARADE official repository"),
    Endpoint("varade", "paper", "https://api.crossref.org/works?query.bibliographic=VARADE+variational+autoencoder+anomaly+detection+robotic+arm&rows=5", "canonical paper record"),
    # --- SARCOS (healthy dynamics only) ---
    Endpoint("sarcos", "gpml", "http://gaussianprocess.org/gpml/data/", "classic distribution point"),
    Endpoint("sarcos", "train_headers", "http://gaussianprocess.org/gpml/data/sarcos_inv.mat", "train file size", method="HEAD"),
    Endpoint("sarcos", "test_headers", "http://gaussianprocess.org/gpml/data/sarcos_inv_test.mat", "test file size", method="HEAD"),
    # --- round 2: schema and license evidence ---
    Endpoint("voraus_ad", "dataset_module", "https://raw.githubusercontent.com/vorausrobotik/voraus-ad-dataset/a91a86a642d23df58833b792a53de01edfd81abe/voraus_ad.py", "column schema, split, categories"),
    Endpoint("voraus_ad", "requirements", "https://raw.githubusercontent.com/vorausrobotik/voraus-ad-dataset/a91a86a642d23df58833b792a53de01edfd81abe/requirements.txt", "Track A exact environment"),
    Endpoint("voraus_ad", "train_module", "https://raw.githubusercontent.com/vorausrobotik/voraus-ad-dataset/a91a86a642d23df58833b792a53de01edfd81abe/train.py", "paper hyperparameters and metric code"),
    Endpoint("voraus_ad", "data_100hz_headers", "https://media.vorausrobotik.com/voraus-ad-dataset-100hz.parquet", "ETag/Last-Modified/Content-Length", method="HEAD"),
    Endpoint("voraus_ad", "data_500hz_headers", "https://media.vorausrobotik.com/voraus-ad-dataset-500hz.parquet", "ETag/Last-Modified/Content-Length", method="HEAD"),
    Endpoint("road", "functions", "https://gitlab.com/AlessioMascolini/roaddataset/-/raw/main/RoADDataset/functions.py", "loader semantics and split"),
    Endpoint("road", "setup", "https://gitlab.com/AlessioMascolini/roaddataset/-/raw/main/setup.py", "package metadata and declared license"),
    Endpoint("road", "blob_training", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/files/RoADDataset%2Fdata%2Ftraining.pkl?ref=main", "subset size"),
    Endpoint("road", "blob_collision", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/files/RoADDataset%2Fdata%2Fcollision.pkl?ref=main", "subset size"),
    Endpoint("road", "blob_columns", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/files/RoADDataset%2Fdata%2Fcolumns.pkl?ref=main", "channel names"),
    Endpoint("road", "license_probe", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/files/LICENSE?ref=main", "presence or absence of a license file"),
    Endpoint("aursad", "code_repo", "https://api.github.com/repos/CptPirx/AURSAD", "official loader package"),
    Endpoint("aursad", "code_readme", "https://raw.githubusercontent.com/CptPirx/AURSAD/master/README.md", "documented schema and feature count"),
    Endpoint("aursad", "code_source_repo", "https://api.github.com/repos/CptPirx/AURSAD-source", "dataset construction code"),
    Endpoint("pyscrew", "zenodo_14769379", "https://zenodo.org/api/records/14769379", "scenario record, files, license"),
    Endpoint("pyscrew", "zenodo_concept", "https://zenodo.org/api/records/14729547", "concept record for all scenarios"),
    Endpoint("varade", "openalex", "https://api.openalex.org/works/doi:10.1145/3649329.3655691", "canonical record, venue, OA status"),
    Endpoint("varade", "unpaywall", "https://api.unpaywall.org/v2/10.1145/3649329.3655691?email=tarekmasserini291@gmail.com", "open full-text location"),
    Endpoint("varade", "gitlab_search", "https://gitlab.com/api/v4/projects?search=varade&per_page=20", "author group hosts RoAD on GitLab"),
    Endpoint("varade", "gitlab_user", "https://gitlab.com/api/v4/users?username=AlessioMascolini", "author account for repository discovery"),
    Endpoint("varade", "github_code_search", "https://api.github.com/search/code?q=filename:VAAR.py", "contract-named source file"),
    Endpoint("road", "blob_control", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/files/RoADDataset%2Fdata%2Fcontrol.pkl?ref=main", "subset size"),
    Endpoint("road", "blob_weight", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/files/RoADDataset%2Fdata%2Fweight.pkl?ref=main", "subset size"),
    Endpoint("road", "blob_velocity", "https://gitlab.com/api/v4/projects/AlessioMascolini%2Froaddataset/repository/files/RoADDataset%2Fdata%2Fvelocity.pkl?ref=main", "subset size"),
    # --- round 3: close the supplementary-dataset gaps ---
    Endpoint("aursad", "code_commits", "https://api.github.com/repos/CptPirx/AURSAD/commits?per_page=5", "loader head commit to freeze"),
    Endpoint("aursad", "code_license", "https://api.github.com/repos/CptPirx/AURSAD/license", "loader code license"),
    Endpoint("ur5e_graabaek", "openalex_paper", "https://api.openalex.org/works?filter=title.search:experimental%20comparison%20anomaly%20detection%20collaborative%20robot%20manipulators&per-page=5", "publication status of the associated paper"),
    Endpoint("ur5e_graabaek", "crossref_paper", "https://api.crossref.org/works?query.bibliographic=experimental+comparison+of+anomaly+detection+methods+for+collaborative+robot+manipulators&rows=5", "formal version, if one exists"),
    Endpoint("ur5e_graabaek", "zenodo_concept", "https://zenodo.org/api/records/5849299", "concept record: all versions"),
    Endpoint("pyscrew", "zenodo_16031381", "https://zenodo.org/api/records/16031381", "v1.2.3 record the scenario archive was fetched from"),
    Endpoint("sarcos", "train_headers_identity", "http://gaussianprocess.org/gpml/data/sarcos_inv.mat", "uncompressed Content-Length and strong ETag", method="HEAD"),
    Endpoint("sarcos", "test_headers_identity", "http://gaussianprocess.org/gpml/data/sarcos_inv_test.mat", "uncompressed Content-Length and strong ETag", method="HEAD"),
)


RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
RETRIES = 3


def _request_with_retry(endpoint: Endpoint, session: requests.Session) -> requests.Response:
    """Retry transient upstream failures; a persistent error is returned as-is."""
    response = None
    for attempt in range(RETRIES):
        response = session.request(
            endpoint.method,
            endpoint.url,
            timeout=TIMEOUT,
            allow_redirects=endpoint.allow_redirects,
        )
        if response.status_code not in RETRY_STATUS:
            return response
        if attempt < RETRIES - 1:
            time.sleep(2 ** attempt)
    return response


def probe(endpoint: Endpoint, session: requests.Session, out_dir: Path) -> dict:
    record: dict = {
        "dataset_id": endpoint.dataset_id,
        "key": endpoint.key,
        "url": endpoint.url,
        "purpose": endpoint.purpose,
        "method": endpoint.method,
        "requested_utc": utc_stamp(),
        "status": "",
        "http_status": "",
        "final_url": "",
        "body_sha256": "",
        "body_bytes": 0,
        "evidence_file": "",
        "error": "",
    }
    headers = {name: "" for name in PROVENANCE_HEADERS}
    try:
        response = _request_with_retry(endpoint, session)
        record["http_status"] = response.status_code
        record["final_url"] = response.url
        for name in PROVENANCE_HEADERS:
            headers[name] = response.headers.get(name, "")
        body = response.content
        record["body_bytes"] = len(body)
        record["body_sha256"] = sha256_bytes(body)
        # An error body is evidence too, but it must never overwrite a payload a
        # previous successful probe already stored: upstreams here (Zenodo) return
        # transient 5xx, and a later failure must not destroy the good record.
        if response.ok:
            suffix = ".json" if "json" in response.headers.get("Content-Type", "") else ".txt"
            name = f"{endpoint.key}{suffix}"
        else:
            name = f"{endpoint.key}.http{response.status_code}.txt"
        evidence = out_dir / endpoint.dataset_id / name
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_bytes(body)
        record["evidence_file"] = str(evidence)
        record["status"] = "OK" if response.ok else "HTTP_ERROR"
    except requests.RequestException as exc:
        record["status"] = "REQUEST_FAILED"
        record["error"] = f"{type(exc).__name__}: {exc}"
    record.update({f"header_{name.lower().replace('-', '_')}": value for name, value in headers.items()})
    return record


class GitHubOnlyAuth(requests.auth.AuthBase):
    """Attach the GitHub token to GitHub hosts only.

    A ``Session``-level Authorization header is sent to *every* host the session
    talks to, including redirect targets. That both leaks the credential to
    unrelated services and breaks them: GitLab and Crossref answer 401 to a
    bearer token they cannot interpret.
    """

    def __init__(self, token: str) -> None:
        self.token = token

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        host = urlsplit(request.url or "").hostname or ""
        if host == "api.github.com" or host.endswith(".github.com"):
            request.headers["Authorization"] = f"Bearer {self.token}"
        else:
            request.headers.pop("Authorization", None)
        return request


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    # Identity encoding: a HEAD that accepts gzip reports the *compressed*
    # Content-Length, which is not the size of the file a later download stores.
    # gaussianprocess.org differs by 60% between the two, and the gzip answer also
    # downgrades the ETag to a weak one. See dataset_known_issues.md.
    session.headers["Accept-Encoding"] = "identity"
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        # Only raises the GitHub rate limit; no endpoint here needs authorisation.
        session.auth = GitHubOnlyAuth(token)
    return session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.datasets.probe")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--only", default="", help="Comma-separated dataset_ids to probe.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    run_dir = cfg.layout.run_dir(cfg.run_id)
    out_dir = run_dir / "d0_evidence"
    out_dir.mkdir(parents=True, exist_ok=True)

    wanted = {s.strip() for s in args.only.split(",") if s.strip()}
    endpoints = [e for e in ENDPOINTS if not wanted or e.dataset_id in wanted]

    session = build_session()
    records = [probe(endpoint, session, out_dir) for endpoint in endpoints]

    log_path = out_dir / "probe_log.csv"
    fieldnames = list(records[0].keys())
    with log_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    manifest_path = out_dir / "probe_manifest.json"
    manifest_sha = write_manifest(
        manifest_path,
        {
            "run_id": cfg.run_id,
            "generated_utc": utc_stamp(),
            "config_sha": cfg.config_sha,
            "endpoint_count": len(records),
            "ok": sum(1 for r in records if r["status"] == "OK"),
            "http_error": sum(1 for r in records if r["status"] == "HTTP_ERROR"),
            "failed": sum(1 for r in records if r["status"] == "REQUEST_FAILED"),
            "records": records,
        },
    )

    for record in records:
        print(
            f"{record['dataset_id']:16s} {record['key']:16s} "
            f"{str(record['http_status']):5s} {record['status']:14s} "
            f"{record['body_bytes']:>9,} B  {record['error']}"
        )
    print(f"\nlog       {log_path}")
    print(f"manifest  {manifest_path}  sha256={manifest_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
