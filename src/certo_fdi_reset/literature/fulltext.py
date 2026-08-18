"""Phase L2 Wave A: resolve the killer / nearest-neighbour papers to real full text.

``04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md`` §7.2 only lets evidence levels
A1, A2 and B1 support an occupancy decision, and §7.6 fixes the order in which a
full text may be sought once the publisher answers 403/418: publisher metadata,
then institutional repository, then author manuscript, then arXiv cross-checked
against the formal version, then the OA locations Unpaywall and OpenAlex know
about. Bypassing access control is not on that list and is not attempted.

This module walks that order for each Wave A target, stores whatever full text is
lawfully reachable on the persistent root, and records for every target the level
actually achieved -- including ``FULLTEXT_UNAVAILABLE``, which §7.2 forbids
treating as evidence that a competitor does not exist.

    python -m certo_fdi_reset.literature.fulltext --config configs/paper_reset.yaml
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import requests

from ..config import load_config
from ..provenance import sha256_bytes, utc_stamp, write_manifest

CONTACT_EMAIL = "tarekmasserini291@gmail.com"
USER_AGENT = f"CERTO-FDI-paper-reset/1.0 (research audit; mailto:{CONTACT_EMAIL})"
TIMEOUT = 45


class EvidenceLevel:
    A1 = "A1"  # publisher PDF / official proceedings full text
    A2 = "A2"  # author accepted manuscript / institutional repository
    B1 = "B1"  # arXiv full text cross-checked against the formal version
    B2 = "B2"  # thesis / patent / code documentation
    C = "C"  # abstract or metadata only
    NONE = "FULLTEXT_UNAVAILABLE"


@dataclass(frozen=True)
class Target:
    """One Wave A paper. ``doi`` may be empty -- then the title resolves it."""

    target_id: str
    title: str
    doi: str = ""
    arxiv_id: str = ""
    role: str = ""
    why_wave_a: str = ""


WAVE_A: tuple[Target, ...] = (
    Target("annual_review_fdi", "Fault Diagnosis in Dynamical Systems: Geometric Interpretation and Tractable Algorithms",
           "10.1146/annurev-control-030123-015422", role="survey",
           why_wave_a="states the current geometric-FDI frontier; decides whether the framing is already standard"),
    Target("haddadin_2017", "Robot Collisions: A Survey on Detection, Isolation, and Identification",
           "10.1109/TRO.2017.2723903", role="survey",
           why_wave_a="canonical taxonomy of detection/isolation/identification for manipulators"),
    Target("evangelisti_hirche_2024", "Data-Driven Momentum Observers With Physically Consistent Gaussian Processes",
           "10.1109/TRO.2024.3366818", role="nearest_neighbour",
           why_wave_a="learned momentum observer with physical consistency — closest to the residual claim"),
    Target("mobnet", "MOB-Net: Limb-modularized uncertainty torque learning of humanoids for sensorless external torque estimation",
           "10.1177/02783649241260428", role="killer_candidate",
           why_wave_a="limb-modularised uncertainty torque learning collides with the modular-chain claim"),
    Target("kim_lim_park_transferable", "Transferable Collision Detection Learning for Collaborative Manipulator",
           role="nearest_neighbour", why_wave_a="cross-context transfer of collision detection"),
    Target("park_unsupervised_collision", "Collision Detection for Robot Manipulators Using Unsupervised Anomaly Detection Algorithms",
           "10.1109/TMECH.2021.3119057", role="nearest_neighbour",
           why_wave_a="healthy-only/unsupervised collision detection — the closest problem statement to ours"),
    Target("lim_lstm_mo", "Momentum Observer-Based Collision Detection Using LSTM for Model Uncertainty Learning",
           role="nearest_neighbour", why_wave_a="LSTM residual on a momentum observer"),
    Target("voraus_ad", "The voraus-AD Dataset for Anomaly Detection in Robot Applications",
           "10.1109/TRO.2023.3332224", arxiv_id="2311.04765", role="benchmark",
           why_wave_a="mandatory dataset 1 and its native MVT-Flow baseline"),
    Target("road", "Robotic Arm Dataset (RoAD): A Dataset to Support the Design and Test of Machine Learning-Driven Anomaly Detection in a Production Line",
           "10.1109/IECON51785.2023.10311726", role="benchmark",
           why_wave_a="mandatory dataset 2; the only source for its sampling rate and frame conventions"),
    Target("varade", "VARADE: a Variational-based AutoRegressive model for Anomaly Detection on the Edge",
           "10.1145/3649329.3655691", arxiv_id="2409.14816", role="native_baseline",
           why_wave_a="RoAD's native baseline; needed for a faithful reproduction level"),
    Target("aursad", "AURSAD: Universal Robot Screwdriving Anomaly Detection Dataset",
           "10.48550/arXiv.2102.01409", arxiv_id="2102.01409", role="benchmark",
           why_wave_a="mandatory dataset 3; the only documented source for its schema"),
    Target("diffnea", "Encoding Physical Constraints in Differentiable Newton-Euler Algorithm",
           role="nearest_neighbour", why_wave_a="differentiable Newton-Euler — structured dynamics prior art"),
    Target("ms_hgnn", "Morphological-Symmetry-Equivariant Heterogeneous Graph Neural Network for Robotic Dynamics Learning",
           arxiv_id="2412.01297", role="killer_candidate",
           why_wave_a="symmetry-equivariant robot graph: collides with the representation novelty claims"),
    # Contract 20 lists these two only as prose descriptions ("Sheikhi et al., data-driven
    # subspace fault isolation, L-CSS 2025"; "Tan et al., confidence-set residual
    # separation/MDF, Automatica 2023") with no title and no DOI. Both titles below are
    # reconstructions, so a failure to resolve them means the SEED was never verified --
    # it is not evidence that the work does not exist.
    Target("sheikhi_subspace", "Data-Driven Fault Isolation via Subspace Identification",
           role="nearest_neighbour", why_wave_a="data-driven subspace fault isolation, the geometric-FDI rival"),
    Target("tan_confidence_set", "Fault detection and isolation via confidence-set separation",
           role="nearest_neighbour", why_wave_a="confidence-set residual separation / maximum distinguishability"),
)


@dataclass
class Resolution:
    target: Target
    resolved_doi: str = ""
    resolved_title: str = ""
    publication_year: str = ""
    online_first_date: str = ""
    issue_publication_date: str = ""
    canonical_citation_year: str = ""
    venue: str = ""
    publication_status: str = ""
    is_oa: str = ""
    oa_status: str = ""
    publisher_url: str = ""
    open_fulltext_url: str = ""
    arxiv_id: str = ""
    evidence_level: str = EvidenceLevel.NONE
    local_pdf: str = ""
    local_sha256: str = ""
    local_bytes: int = 0
    access_route: str = ""
    notes: list[str] = field(default_factory=list)


MIN_TITLE_OVERLAP = 0.6


def _title_tokens(text: str) -> set[str]:
    stop = {"a", "an", "the", "of", "for", "on", "in", "and", "with", "via", "to", "using"}
    return {w for w in re.sub(r"[^a-z0-9]+", " ", text.casefold()).split() if w and w not in stop}


def _title_overlap(left: str, right: str) -> float:
    """Token F1 between two titles. 1.0 is identical wording, 0.0 shares nothing."""
    a, b = _title_tokens(left), _title_tokens(right)
    if not a or not b:
        return 0.0
    shared = len(a & b)
    if not shared:
        return 0.0
    precision, recall = shared / len(a), shared / len(b)
    return 2 * precision * recall / (precision + recall)


def _best_title_match(results: list[dict], title: str) -> dict | None:
    scored = [(_title_overlap(r.get("title") or "", title), r) for r in results]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if scored and scored[0][0] >= MIN_TITLE_OVERLAP:
        return scored[0][1]
    return None


def _get(session: requests.Session, url: str, **kwargs) -> requests.Response | None:
    try:
        return session.get(url, timeout=TIMEOUT, **kwargs)
    except requests.RequestException:
        return None


def resolve_openalex(resolution: Resolution, session: requests.Session) -> None:
    target = resolution.target
    if target.doi:
        url = f"https://api.openalex.org/works/doi:{target.doi}"
    else:
        url = "https://api.openalex.org/works"
    params = None if target.doi else {"search": target.title, "per-page": 3}
    response = _get(session, url, params=params)
    if response is None or response.status_code != 200:
        resolution.notes.append(f"OpenAlex lookup failed ({getattr(response, 'status_code', 'no response')})")
        return
    payload = response.json()
    if target.doi:
        work = payload
    else:
        # A title search will always return *something*. Accepting the top hit is how
        # "Tan, confidence-set separation" became a Nature Communications paper, which
        # would then have been carded as prior art. Require a real title overlap.
        work = _best_title_match(payload.get("results") or [], target.title)
        if work is None:
            resolution.notes.append(
                "NO_CONFIDENT_TITLE_MATCH: OpenAlex returned hits but none overlapped the "
                "target title enough to accept; resolution left empty rather than guessed."
            )
            return
    if not work:
        resolution.notes.append("OpenAlex returned no match for the title")
        return

    resolution.resolved_doi = (work.get("doi") or "").replace("https://doi.org/", "")
    resolution.resolved_title = work.get("title") or ""
    resolution.publication_year = str(work.get("publication_year") or "")
    resolution.issue_publication_date = work.get("publication_date") or ""
    resolution.publication_status = work.get("type") or ""
    primary = work.get("primary_location") or {}
    resolution.venue = ((primary.get("source") or {}).get("display_name")) or ""
    resolution.publisher_url = primary.get("landing_page_url") or ""
    oa = work.get("open_access") or {}
    resolution.is_oa = str(oa.get("is_oa", ""))
    resolution.oa_status = oa.get("oa_status") or ""

    for location in work.get("locations") or []:
        source_name = ((location.get("source") or {}).get("display_name") or "").lower()
        pdf = location.get("pdf_url") or ""
        landing = location.get("landing_page_url") or ""
        if "arxiv" in source_name or "arxiv.org" in (pdf + landing):
            match = re.search(r"(\d{4}\.\d{4,5})", pdf + " " + landing)
            if match and not resolution.arxiv_id:
                resolution.arxiv_id = match.group(1)
        if pdf and not resolution.open_fulltext_url:
            resolution.open_fulltext_url = pdf


def resolve_unpaywall(resolution: Resolution, session: requests.Session) -> None:
    doi = resolution.resolved_doi or resolution.target.doi
    if not doi:
        return
    response = _get(session, f"https://api.unpaywall.org/v2/{doi}", params={"email": CONTACT_EMAIL})
    if response is None or response.status_code != 200:
        return
    payload = response.json()
    resolution.is_oa = resolution.is_oa or str(payload.get("is_oa", ""))
    resolution.oa_status = resolution.oa_status or (payload.get("oa_status") or "")
    for location in payload.get("oa_locations") or []:
        url = location.get("url_for_pdf") or location.get("url") or ""
        host = location.get("host_type") or ""
        if "arxiv" in url and not resolution.arxiv_id:
            match = re.search(r"(\d{4}\.\d{4,5})", url)
            if match:
                resolution.arxiv_id = match.group(1)
        if url.endswith(".pdf") and not resolution.open_fulltext_url:
            resolution.open_fulltext_url = url
            resolution.access_route = f"unpaywall:{host}"


def resolve_arxiv(resolution: Resolution, session: requests.Session) -> None:
    """Find an arXiv preprint by id, or by exact-ish title when no id is known."""
    arxiv_id = resolution.arxiv_id or resolution.target.arxiv_id
    if arxiv_id:
        resolution.arxiv_id = arxiv_id
        return
    title = resolution.resolved_title or resolution.target.title
    response = _get(
        session,
        "https://export.arxiv.org/api/query",
        params={"search_query": f'ti:"{title}"', "max_results": 3},
    )
    if response is None or response.status_code != 200:
        return
    entries = re.findall(r"<entry>(.*?)</entry>", response.text, re.S)
    for entry in entries:
        found_title = re.search(r"<title>(.*?)</title>", entry, re.S)
        found_id = re.search(r"arxiv\.org/abs/([^<v]+)", entry)
        if not found_title or not found_id:
            continue
        if _titles_match(found_title.group(1), title):
            resolution.arxiv_id = found_id.group(1).strip()
            return


def _titles_match(left: str, right: str) -> bool:
    def norm(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()

    a, b = norm(left), norm(right)
    return a == b or a.startswith(b[:60]) or b.startswith(a[:60])


def resolve_semantic_scholar(resolution: Resolution, session: requests.Session) -> None:
    """Semantic Scholar's OA index, which reaches institutional repositories the
    other services miss. It was unavailable during L1 (429, no API key) and is
    reachable now, so it is queried here as §7.6 step 2 before giving up.
    """
    doi = resolution.resolved_doi or resolution.target.doi
    if not doi or resolution.open_fulltext_url:
        return
    response = _get(
        session,
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
        params={"fields": "title,year,venue,isOpenAccess,openAccessPdf,externalIds"},
    )
    if response is None or response.status_code != 200:
        return
    payload = response.json()
    if payload.get("year") and not resolution.issue_publication_date:
        resolution.notes.append(f"semantic-scholar issue year {payload['year']}")
    arxiv = (payload.get("externalIds") or {}).get("ArXiv")
    if arxiv and not resolution.arxiv_id:
        resolution.arxiv_id = arxiv
    url = (payload.get("openAccessPdf") or {}).get("url") or ""
    if url:
        resolution.open_fulltext_url = url
        resolution.access_route = "semantic_scholar_oa"


def _follow_landing_page(url: str, response: requests.Response, session: requests.Session) -> bytes | None:
    """Turn a repository record URL into the PDF it describes, or None."""
    match = re.search(r"mediatum\.ub\.tum\.de/(\d+)", response.url or url)
    if match:
        doc_id = match.group(1)
        for pattern in (
            f"https://mediatum.ub.tum.de/doc/{doc_id}/{doc_id}.pdf",
            f"https://mediatum.ub.tum.de/download/{doc_id}/{doc_id}.pdf",
        ):
            candidate = _get(session, pattern, allow_redirects=True)
            if candidate is not None and candidate.status_code == 200 and candidate.content.startswith(b"%PDF"):
                return candidate.content
    return None


def fetch_fulltext(resolution: Resolution, session: requests.Session, out_dir: Path) -> None:
    """Download the best lawfully reachable full text and set the evidence level."""
    candidates: list[tuple[str, str, str]] = []
    if resolution.open_fulltext_url:
        candidates.append((resolution.open_fulltext_url, EvidenceLevel.A2, resolution.access_route or "oa_location"))
    if resolution.arxiv_id:
        candidates.append((f"https://arxiv.org/pdf/{resolution.arxiv_id}", EvidenceLevel.B1, "arxiv"))

    for url, level, route in candidates:
        response = _get(session, url, allow_redirects=True)
        if response is None or response.status_code != 200:
            resolution.notes.append(f"{route} fetch returned {getattr(response, 'status_code', 'no response')}")
            continue
        body = response.content
        if not body.startswith(b"%PDF"):
            # Repositories often hand back an HTML landing page for the record. Try the
            # document path that page describes before declaring the text unreachable.
            body = _follow_landing_page(url, response, session)
            if body is None:
                resolution.notes.append(
                    f"{route} returned {response.headers.get('Content-Type','?')}, not a PDF, "
                    "and no document link was derivable"
                )
                continue
        path = out_dir / f"{resolution.target.target_id}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        resolution.local_pdf = str(path)
        resolution.local_bytes = len(body)
        resolution.local_sha256 = sha256_bytes(body)
        resolution.evidence_level = level
        resolution.access_route = route
        return

    resolution.evidence_level = EvidenceLevel.C if resolution.resolved_doi else EvidenceLevel.NONE
    resolution.notes.append(
        "No lawfully reachable full text; metadata only. Per §7.2 this may not be read as "
        "evidence that no competing work exists."
    )


MANIFEST_COLUMNS = (
    "target_id", "role", "resolved_title", "resolved_doi", "venue", "publication_status",
    "publication_year", "issue_publication_date", "canonical_citation_year", "is_oa",
    "oa_status", "arxiv_id", "evidence_level", "access_route", "open_fulltext_url",
    "publisher_url", "local_pdf", "local_bytes", "local_sha256", "why_wave_a", "notes",
)


def strip_control_characters(text: str) -> str:
    """Remove C0 control characters except newline and tab.

    PyMuPDF emits NUL for glyphs it cannot map. Left in place, those bytes make the
    extracted file "binary" to file(1), grep and every other text tool, so a later
    search for a term that is plainly in the paper silently returns nothing.
    """
    return "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch) != "Cc")


def extract_text(pdf_dir: Path) -> list[tuple[str, int, int]]:
    """Extract page-marked plain text next to each PDF. Returns (stem, pages, chars)."""
    import pymupdf

    out_dir = pdf_dir / "text"
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, int, int]] = []
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        doc = pymupdf.open(pdf)
        text = "".join(
            f"\n<<<PAGE {i + 1}>>>\n" + page.get_text() for i, page in enumerate(doc)
        )
        cleaned = strip_control_characters(text)
        (out_dir / f"{pdf.stem}.txt").write_text(cleaned, encoding="utf-8")
        results.append((pdf.stem, doc.page_count, len(cleaned)))
        doc.close()
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.literature.fulltext")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--only", default="")
    parser.add_argument(
        "--extract-text",
        action="store_true",
        help="Only re-extract plain text from the PDFs already stored; no network access.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    layout = cfg.layout
    out_dir = layout.literature_open_fulltexts
    manifest_dir = layout.literature_access_manifest

    if args.extract_text:
        for stem, pages, chars in extract_text(out_dir):
            print(f"  {stem:28s} pages={pages:3d} chars={chars:>8,}")
        return 0

    wanted = {s.strip() for s in args.only.split(",") if s.strip()}
    targets = [t for t in WAVE_A if not wanted or t.target_id in wanted]

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    resolutions: list[Resolution] = []
    for target in targets:
        resolution = Resolution(target=target)
        resolve_openalex(resolution, session)
        resolve_unpaywall(resolution, session)
        resolve_semantic_scholar(resolution, session)
        resolve_arxiv(resolution, session)
        fetch_fulltext(resolution, session, out_dir)
        resolution.canonical_citation_year = resolution.publication_year
        resolutions.append(resolution)
        print(
            f"{target.target_id:28s} {resolution.evidence_level:22s} "
            f"{resolution.access_route:12s} {resolution.local_bytes:>9,} B  {resolution.resolved_doi}"
        )
        time.sleep(0.5)

    manifest_dir.mkdir(parents=True, exist_ok=True)
    csv_path = manifest_dir / "fulltext_access_manifest.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for r in resolutions:
            writer.writerow(
                {
                    "target_id": r.target.target_id,
                    "role": r.target.role,
                    "resolved_title": r.resolved_title or r.target.title,
                    "resolved_doi": r.resolved_doi,
                    "venue": r.venue,
                    "publication_status": r.publication_status,
                    "publication_year": r.publication_year,
                    "issue_publication_date": r.issue_publication_date,
                    "canonical_citation_year": r.canonical_citation_year,
                    "is_oa": r.is_oa,
                    "oa_status": r.oa_status,
                    "arxiv_id": r.arxiv_id,
                    "evidence_level": r.evidence_level,
                    "access_route": r.access_route,
                    "open_fulltext_url": r.open_fulltext_url,
                    "publisher_url": r.publisher_url,
                    "local_pdf": r.local_pdf,
                    "local_bytes": r.local_bytes,
                    "local_sha256": r.local_sha256,
                    "why_wave_a": r.target.why_wave_a,
                    "notes": " | ".join(r.notes),
                }
            )

    levels: dict[str, int] = {}
    for r in resolutions:
        levels[r.evidence_level] = levels.get(r.evidence_level, 0) + 1
    write_manifest(
        manifest_dir / "fulltext_access_summary.json",
        {
            "run_id": cfg.run_id,
            "generated_utc": utc_stamp(),
            "wave": "A",
            "targets": len(resolutions),
            "by_evidence_level": levels,
            "occupancy_capable": sum(
                1 for r in resolutions if r.evidence_level in {EvidenceLevel.A1, EvidenceLevel.A2, EvidenceLevel.B1}
            ),
            "blocked_publishers": sorted(
                {r.venue for r in resolutions if r.evidence_level in {EvidenceLevel.C, EvidenceLevel.NONE} and r.venue}
            ),
        },
    )
    print(f"\nmanifest  {csv_path}")
    print(f"levels    {levels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
