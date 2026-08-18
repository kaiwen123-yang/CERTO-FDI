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
from ..provenance import sha256_bytes, sha256_file, sha256_text, utc_stamp, write_manifest

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
    #: Institutional-repository copy located via OpenAIRE when neither Unpaywall,
    #: OpenAlex nor Semantic Scholar exposes a PDF (§7.6 rung 2). Recorded here so
    #: the fetch is reproducible instead of a one-off manual download.
    repository_pdf_url: str = ""


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
    Target("kim_lim_park_transferable",
           "Transferable Collision Detection Learning for Collaborative Manipulator Using Versatile Modularized Neural Network",
           "10.1109/TRO.2021.3129630", role="nearest_neighbour",
           why_wave_a="cross-context transfer of collision detection"),
    Target("park_unsupervised_collision", "Collision Detection for Robot Manipulators Using Unsupervised Anomaly Detection Algorithms",
           "10.1109/TMECH.2021.3119057", role="nearest_neighbour",
           why_wave_a="healthy-only/unsupervised collision detection — the closest problem statement to ours"),
    Target("lim_lstm_mo", "Momentum Observer-Based Collision Detection Using LSTM for Model Uncertainty Learning",
           "10.1109/ICRA48506.2021.9561667", role="nearest_neighbour",
           why_wave_a="LSTM residual on a momentum observer"),
    Target("voraus_ad", "The voraus-AD Dataset for Anomaly Detection in Robot Applications",
           "10.1109/TRO.2023.3332224", arxiv_id="2311.04765", role="benchmark",
           why_wave_a="mandatory dataset 1 and its native MVT-Flow baseline"),
    Target("road", "Robotic Arm Dataset (RoAD): A Dataset to Support the Design and Test of Machine Learning-Driven Anomaly Detection in a Production Line",
           "10.1109/IECON51785.2023.10311726", role="benchmark",
           why_wave_a="mandatory dataset 2; the only source for its sampling rate and frame conventions",
           repository_pdf_url="https://iris.polito.it/bitstream/11583/2982400/1/TAD_dataset.pdf"),
    Target("varade", "VARADE: a Variational-based AutoRegressive model for Anomaly Detection on the Edge",
           "10.1145/3649329.3655691", arxiv_id="2409.14816", role="native_baseline",
           why_wave_a="RoAD's native baseline; needed for a faithful reproduction level"),
    Target("aursad", "AURSAD: Universal Robot Screwdriving Anomaly Detection Dataset",
           "10.48550/arXiv.2102.01409", arxiv_id="2102.01409", role="benchmark",
           why_wave_a="mandatory dataset 3; the only documented source for its schema"),
    Target("diffnea", "Encoding Physical Constraints in Differentiable Newton-Euler Algorithm",
           "10.48550/arXiv.2001.08861", arxiv_id="2001.08861", role="nearest_neighbour",
           why_wave_a="differentiable Newton-Euler — structured dynamics prior art"),
    Target("ms_hgnn", "Morphological-Symmetry-Equivariant Heterogeneous Graph Neural Network for Robotic Dynamics Learning",
           "10.48550/arXiv.2412.01297", arxiv_id="2412.01297", role="killer_candidate",
           why_wave_a="symmetry-equivariant robot graph: collides with the representation novelty claims"),
    # Contract 20 lists these two only as prose descriptions ("Sheikhi et al., data-driven
    # subspace fault isolation, L-CSS 2025"; "Tan et al., confidence-set residual
    # separation/MDF, Automatica 2023") with no title and no DOI. Both titles below are
    # reconstructions, so a failure to resolve them means the SEED was never verified --
    # it is not evidence that the work does not exist.
    # Resolved from the Annual Review author list: Sheikhi is a TU Delft co-author of both.
    Target("sheikhi_subspace", "Data-Driven Fault Isolation in Linear Time-Invariant Systems: A Subspace Classification Approach",
           "10.1109/LCSYS.2025.3581854", arxiv_id="2509.01347", role="nearest_neighbour",
           why_wave_a="data-driven subspace fault isolation, the geometric-FDI rival"),
    # Resolved: a Crossref search restricted to container-title Automatica returns
    # Tan, Zheng, Meng & Yuan 2023, whose subject IS confidence-set analysis of the
    # minimal detectable fault -- i.e. the contract's "confidence-set residual
    # separation/MDF, Automatica 2023" prose description, with MDF = minimal
    # detectable fault. The earlier title here was a reconstruction and never matched.
    Target("tan_confidence_set",
           "Confidence set-based analysis of minimal detectable fault under hybrid Gaussian and bounded uncertainties",
           "10.1016/j.automatica.2023.111141", role="nearest_neighbour",
           why_wave_a="confidence-set residual separation / maximum distinguishability"),
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

#: The §7.6 acquisition ladder, in order, with how each rung is exercised here. The
#: negative search log is written against this list so "we tried everything" is a
#: checkable statement rather than a claim.
LADDER: tuple[tuple[str, str], ...] = (
    ("1. publisher formal-page metadata", "OpenAlex works record + Crossref, by DOI"),
    ("2. author institutional repository", "OpenAIRE publications API by DOI; Semantic Scholar openAccessPdf; explicit Target.repository_pdf_url when a copy is known"),
    ("3. author accepted manuscript", "Unpaywall oa_locations of host_type=repository"),
    ("4. arXiv cross-checked against the formal version", "arXiv id from OpenAlex/Unpaywall/Semantic Scholar externalIds, else an arXiv title query"),
    ("5. formal conference proceedings", "reached only through the publisher DOI; IEEE returns 418 and ACM 403 from this host"),
    ("6. Unpaywall / OpenAlex OA location", "best_oa_location and every oa_location, PDF first then landing page"),
    ("7. otherwise FULLTEXT_UNAVAILABLE", "recorded as evidence level C, which §7.2 bars from carrying any occupancy verdict"),
)


def render_negative_search_log(resolutions: list["Resolution"], run_id: str) -> str:
    """Write down what was tried and failed, per target.

    This document exists so an absent full text can never be quietly upgraded into
    "no competing work exists". §7.2 makes FULLTEXT_UNAVAILABLE inadmissible as
    evidence of an open field, and that rule is only enforceable if the failure trail
    is explicit.
    """
    blocked = [
        r for r in resolutions
        if r.evidence_level in {EvidenceLevel.C, EvidenceLevel.NONE}
    ]
    got = [r for r in resolutions if r not in blocked]
    lines = [
        "# Negative search log — Wave A full-text acquisition",
        "",
        f"- run_id: `{run_id}`",
        f"- generated (UTC): {utc_stamp()}",
        f"- targets: {len(resolutions)} | full text obtained: {len(got)} | "
        f"unreachable: {len(blocked)}",
        "",
        "## The ladder that was applied to every target (§7.6)",
        "",
        "| rung | how it is exercised here |",
        "| --- | --- |",
        *[f"| {rung} | {how} |" for rung, how in LADDER],
        "",
        "No access control was circumvented at any rung. A paywall that refuses this host is",
        "recorded as a refusal, not worked around.",
        "",
        "## Targets with no lawfully reachable full text",
        "",
    ]
    if not blocked:
        lines += ["None — every Wave A target resolved to A1/A2/B1 full text.", ""]
    for r in blocked:
        lines += [
            f"### `{r.target.target_id}`",
            "",
            f"- title: {r.resolved_title or r.target.title}",
            f"- DOI: `{r.resolved_doi or r.target.doi or 'UNRESOLVED'}`",
            f"- venue: {r.venue or 'unknown'}",
            f"- publisher page: {r.publisher_url or 'n/a'}",
            f"- OA status reported: is_oa={r.is_oa or 'unknown'}, oa_status={r.oa_status or 'unknown'}",
            f"- arXiv id found: {r.arxiv_id or 'none'}",
            f"- evidence level: **{r.evidence_level}** (FULLTEXT_UNAVAILABLE)",
            f"- why it matters: {r.target.why_wave_a}",
            f"- trail: {'; '.join(r.notes) if r.notes else 'no OA location reported by any service'}",
            "",
        ]
    lines += [
        "## What may and may not be concluded",
        "",
        "- These targets count toward **discovery**, never toward full-text coverage.",
        "- None of them may be cited as showing a claim is open, unoccupied, or novel.",
        "- Any C1-C6 verdict that depends on one of them stays `UNKNOWN` until the text is read.",
        "- The literature gate cannot read `LITERATURE_PASS_PLAUSIBLY_OPEN` while nearest-neighbour",
        "  targets sit in this list; the applicable state is",
        "  `LITERATURE_UNKNOWN_INSUFFICIENT_FULLTEXT` (§7.1).",
        "",
    ]
    return "\n".join(lines)


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


def resolve_openaire(resolution: Resolution, session: requests.Session) -> None:
    """§7.6 rung 2, mechanised: OpenAIRE aggregates institutional repositories.

    This is the rung that recovered the RoAD postprint from iris.polito.it. Doing it
    programmatically matters for a different reason than convenience: when it finds
    nothing, that is the evidence which lets a target be marked FULLTEXT_UNAVAILABLE
    honestly, instead of the weaker claim that nobody looked.
    """
    doi = resolution.resolved_doi or resolution.target.doi
    if not doi or resolution.open_fulltext_url:
        return
    response = _get(
        session,
        "https://api.openaire.eu/search/publications",
        params={"doi": doi, "format": "json"},
    )
    if response is None or response.status_code != 200:
        return
    try:
        payload = response.json()
    except ValueError:
        return
    results = ((payload.get("response") or {}).get("results") or {}).get("result") or []
    if isinstance(results, dict):
        results = [results]
    for item in results:
        try:
            metadata = item["metadata"]["oaf:entity"]["oaf:result"]
        except (KeyError, TypeError):
            continue
        access = (metadata.get("bestaccessright") or {}).get("@classname", "")
        resolution.notes.append(f"openaire bestaccessright={access or 'unknown'}")
        instances = (metadata.get("children") or {}).get("instance") or metadata.get("instance") or []
        if isinstance(instances, dict):
            instances = [instances]
        for instance in instances:
            resources = instance.get("webresource") or []
            if isinstance(resources, dict):
                resources = [resources]
            for resource in resources:
                url = (resource.get("url") or {}).get("$", "")
                # A doi.org link is the publisher again, not a repository copy.
                if url and "doi.org" not in url:
                    resolution.open_fulltext_url = url
                    resolution.access_route = "openaire_repository"
                    return
    if not resolution.open_fulltext_url:
        resolution.notes.append("openaire: no repository copy, only publisher links")


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
    if resolution.target.repository_pdf_url:
        candidates.append((resolution.target.repository_pdf_url, EvidenceLevel.A2, "institutional_repository"))
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


def extract_text(pdf_dir: Path) -> list[tuple[str, int, int, str]]:
    """Extract page-marked plain text next to each PDF.

    Also writes ``text/text_manifest.json`` holding each extraction's SHA256, because
    for at least one Wave A source the PDF itself cannot serve as the reproduction
    anchor. iris.polito.it regenerates its postprint on every request -- two
    consecutive fetches of the RoAD paper differ in length (437,446 vs 437,447 bytes)
    since the repository stamps a cover page and PDF metadata per download -- while the
    extracted text is byte-identical across fetches. A reviewer re-running the fetch
    would otherwise see a SHA256 mismatch and reasonably suspect tampering. The text
    hash is the quantity that is actually stable, so it is the one recorded for
    reproduction.

    Returns (stem, pages, chars, text_sha256).
    """
    import pymupdf

    out_dir = pdf_dir / "text"
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, int, int, str]] = []
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        doc = pymupdf.open(pdf)
        text = "".join(
            f"\n<<<PAGE {i + 1}>>>\n" + page.get_text() for i, page in enumerate(doc)
        )
        cleaned = strip_control_characters(text)
        text_path = out_dir / f"{pdf.stem}.txt"
        text_path.write_text(cleaned, encoding="utf-8")
        results.append((pdf.stem, doc.page_count, len(cleaned), sha256_text(cleaned)))
        doc.close()

    write_manifest(
        out_dir / "text_manifest.json",
        {
            "note": (
                "SHA256 of the EXTRACTED TEXT, which is the stable reproduction anchor. "
                "Some repository PDFs are regenerated per request and are not "
                "byte-reproducible; see the docstring of extract_text."
            ),
            "generated_utc": utc_stamp(),
            "extractor": "pymupdf get_text(), page-marked, control characters stripped",
            "texts": [
                {
                    "stem": stem,
                    "pages": pages,
                    "chars": chars,
                    "pdf_sha256": sha256_file(pdf_dir / f"{stem}.pdf"),
                    "pdf_bytes": (pdf_dir / f"{stem}.pdf").stat().st_size,
                    "text_sha256": text_sha,
                }
                for stem, pages, chars, text_sha in results
            ],
        },
    )
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
        for stem, pages, chars, text_sha in extract_text(out_dir):
            print(f"  {stem:28s} pages={pages:3d} chars={chars:>8,}  text_sha256={text_sha[:16]}")
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
        resolve_openaire(resolution, session)
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
    log_path = manifest_dir / "negative_search_log.md"
    log_text = render_negative_search_log(resolutions, cfg.run_id)
    log_path.write_text(log_text, encoding="utf-8")

    print(f"\nmanifest  {csv_path}")
    print(f"neg log   {log_path}  sha256={sha256_text(log_text)[:16]}")
    print(f"levels    {levels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
