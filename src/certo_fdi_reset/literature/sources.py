"""Bibliographic source adapters for Phase L1 discovery.

Each adapter turns one frozen query into normalized ``LiteratureRecord`` objects
plus a ``SearchLogEntry`` recording database, query, execution date, HTTP status
and result count -- the audit trail required by
``contracts/paper_reset/04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md`` §D.2.

Per-source query adaptations are declared in ``QUERY_ADAPTATIONS`` and copied into
every log entry, so a reviewer can see exactly how a contract query was rewritten
for an API that does not speak the contract's syntax.

Source roles follow ``04_…§A`` exactly, and the split is deliberate:

* **Discovery** -- OpenAlex and Crossref. Both accept the frozen query text
  verbatim and index the blocked publishers' metadata (IEEE, ACM, Elsevier,
  Springer), so a paywalled paper is still *discovered* even when its full text
  is not reachable.
* **Supplementary discovery** -- arXiv, category-scoped and term-budgeted. The
  contract scopes arXiv to "public full text or preprint status", so it is not a
  primary discovery database; it is swept only to catch very recent work that
  has not yet reached the indexes.
* **Verification / resolution** -- arXiv and DBLP by title or DOI lookup, for
  open full text, preprint-vs-formal status, and formal venue. DBLP keyword
  search is deliberately *not* used for discovery: it ANDs prefix matches and
  collapses to zero hits on a six-token query, which would understate coverage.

None of these sources establishes occupancy. They are discovery only; occupancy
requires a full text at evidence level A1/A2/B1.
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests

from .queries import Query, rank_groups
from .records import LiteratureRecord

CONTACT_EMAIL = "tarekmasserini291@gmail.com"
USER_AGENT = f"CERTO-FDI-paper-reset/1.0 (mailto:{CONTACT_EMAIL})"

QUERY_ADAPTATIONS: dict[str, str] = {
    "openalex": "contract query text passed verbatim to the `search` parameter (full-text search)",
    "crossref": "contract query text passed to `query.bibliographic`; boolean operators are not honoured by Crossref and act as extra terms",
    "arxiv": (
        "SUPPLEMENTARY discovery only (the contract scopes arXiv to open full text "
        "and preprint status). Scoped to cat:(cs.RO OR cs.LG OR cs.SY OR eess.SY "
        "OR cs.AI) and truncated to the 2 most discriminative AND-groups. "
        "REASON 1: the arXiv API does not implement true phrase matching -- "
        'abs:"momentum observer" returns black-hole papers -- so an unscoped query '
        "is mostly off-domain noise; category scoping restores precision. "
        "REASON 2: arXiv ANDs every token, so a 6-token contract query returns 0-1 "
        "hits; a 2-group budget was measured as the point where recall returns "
        "(voraus-AD dataset paper and MOB-Net both surface at budget 2, neither at 6)."
    ),
    "dblp": (
        "NOT used for keyword discovery. DBLP ANDs prefix matches over title/venue "
        "only and was measured at 6 terms -> 0 hits, 4 -> 1, 3 -> 15 for the same "
        "query, so keyword sweeps would understate coverage. DBLP is queried by "
        "exact title to verify formal venue and publication type."
    ),
    "semantic_scholar": (
        "boolean/quote syntax stripped to plain terms passed to the graph search "
        "endpoint. Unauthenticated shared pool; set SEMANTIC_SCHOLAR_API_KEY to "
        "raise the rate limit. Persistent 429s are logged as UNAVAILABLE, never "
        "as a zero-result search."
    ),
}

ARXIV_CATEGORIES = ("cs.RO", "cs.LG", "cs.SY", "eess.SY", "cs.AI")


@dataclass
class SearchLogEntry:
    """One row of ``literature_search_log.csv``."""

    database: str
    query_id: str
    query_text: str
    executed_query: str
    search_date: str
    http_status: int | str
    reported_total: int | None
    returned_count: int
    raw_export: str
    query_adaptation: str
    note: str = ""

    def as_csv_row(self) -> dict[str, str]:
        return {
            "database": self.database,
            "query_id": self.query_id,
            "query_text": self.query_text,
            "executed_query": self.executed_query,
            "search_date": self.search_date,
            "http_status": str(self.http_status),
            "reported_total": "" if self.reported_total is None else str(self.reported_total),
            "returned_count": str(self.returned_count),
            "raw_export": self.raw_export,
            "query_adaptation": self.query_adaptation,
            "note": self.note,
        }


SEARCH_LOG_COLUMNS: tuple[str, ...] = (
    "database",
    "query_id",
    "query_text",
    "executed_query",
    "search_date",
    "http_status",
    "reported_total",
    "returned_count",
    "raw_export",
    "query_adaptation",
    "note",
)


@dataclass
class SourceResult:
    records: list[LiteratureRecord]
    log: SearchLogEntry
    raw: Any = None


class Source:
    """Base adapter: polite pacing, bounded retries, never raises on HTTP failure."""

    name: str = "base"
    min_interval_s: float = 1.0
    max_retries: int = 3

    def __init__(self, session: requests.Session | None = None, per_page: int = 50):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.per_page = per_page
        self._last_call = 0.0

    def _pace(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_call = time.monotonic()

    def _get(self, url: str, params: dict) -> requests.Response | Exception:
        """Return a 200 response, or the last failure (non-200 response or exception).

        Callers MUST test ``_ok(outcome)``, not ``isinstance(outcome, Response)``:
        a 429 is still a Response, and treating it as success silently records a
        rate-limited database as "searched, zero results" -- which
        04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md §D.1 forbids.
        """
        last: Exception | requests.Response = RuntimeError("no attempt made")
        for attempt in range(self.max_retries):
            self._pace()
            try:
                response = self.session.get(url, params=params, timeout=45)
            except requests.RequestException as exc:
                last = exc
                time.sleep(2.0 * (attempt + 1))
                continue
            if response.status_code == 200:
                return response
            last = response
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(5.0 * (attempt + 1))
                continue
            break
        return last

    @staticmethod
    def _ok(outcome) -> bool:
        return isinstance(outcome, requests.Response) and outcome.status_code == 200

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _failure(self, query: Query, executed: str, outcome) -> SourceResult:
        status = outcome.status_code if isinstance(outcome, requests.Response) else "EXCEPTION"
        note = (
            f"{type(outcome).__name__}: {outcome}"
            if isinstance(outcome, Exception)
            else outcome.text[:200].replace("\n", " ")
        )
        return SourceResult(
            records=[],
            log=SearchLogEntry(
                database=self.name,
                query_id=query.query_id,
                query_text=query.text,
                executed_query=executed,
                search_date=self._now(),
                http_status=status,
                reported_total=None,
                returned_count=0,
                raw_export="",
                query_adaptation=QUERY_ADAPTATIONS.get(self.name, ""),
                note=f"UNAVAILABLE: {note}",
            ),
        )

    def search(self, query: Query) -> SourceResult:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAlexSource(Source):
    name = "openalex"
    min_interval_s = 0.15

    def search(self, query: Query) -> SourceResult:
        executed = query.text
        params = {
            "search": executed,
            "per-page": self.per_page,
            "mailto": CONTACT_EMAIL,
        }
        outcome = self._get("https://api.openalex.org/works", params)
        if not self._ok(outcome):
            return self._failure(query, executed, outcome)
        payload = outcome.json()
        records = []
        for work in payload.get("results", []):
            source = (work.get("primary_location") or {}).get("source") or {}
            oa = work.get("open_access") or {}
            records.append(
                LiteratureRecord(
                    title=work.get("title") or work.get("display_name") or "",
                    doi=work.get("doi") or "",
                    authors=[
                        a["author"]["display_name"]
                        for a in work.get("authorships", [])
                        if a.get("author", {}).get("display_name")
                    ],
                    year=work.get("publication_year"),
                    venue=source.get("display_name") or "",
                    venue_type=work.get("type") or "",
                    publisher=source.get("host_organization_name") or "",
                    is_oa=oa.get("is_oa"),
                    oa_url=oa.get("oa_url") or "",
                    cited_by_count=work.get("cited_by_count"),
                    abstract_available=bool(work.get("abstract_inverted_index")),
                    source_apis={self.name},
                    query_ids={query.query_id},
                    lineages={query.lineage},
                    retrieved_utc=self._now(),
                )
            )
        return SourceResult(
            records=records,
            log=SearchLogEntry(
                database=self.name,
                query_id=query.query_id,
                query_text=query.text,
                executed_query=executed,
                search_date=self._now(),
                http_status=200,
                reported_total=(payload.get("meta") or {}).get("count"),
                returned_count=len(records),
                raw_export="",
                query_adaptation=QUERY_ADAPTATIONS[self.name],
            ),
            raw=payload,
        )


class CrossrefSource(Source):
    name = "crossref"
    min_interval_s = 0.3

    def search(self, query: Query) -> SourceResult:
        executed = query.text
        params = {
            "query.bibliographic": executed,
            "rows": self.per_page,
            "mailto": CONTACT_EMAIL,
            "select": "DOI,title,author,issued,container-title,type,publisher,is-referenced-by-count,abstract",
        }
        outcome = self._get("https://api.crossref.org/works", params)
        if not self._ok(outcome):
            return self._failure(query, executed, outcome)
        message = outcome.json().get("message", {})
        records = []
        for item in message.get("items", []):
            titles = item.get("title") or []
            issued = (item.get("issued") or {}).get("date-parts") or [[None]]
            year = issued[0][0] if issued and issued[0] else None
            containers = item.get("container-title") or []
            records.append(
                LiteratureRecord(
                    title=titles[0] if titles else "",
                    doi=item.get("DOI") or "",
                    authors=[
                        " ".join(filter(None, [a.get("given"), a.get("family")])).strip()
                        for a in item.get("author", [])
                        if a.get("family")
                    ],
                    year=year,
                    venue=containers[0] if containers else "",
                    venue_type=item.get("type") or "",
                    publisher=item.get("publisher") or "",
                    cited_by_count=item.get("is-referenced-by-count"),
                    abstract_available=bool(item.get("abstract")),
                    source_apis={self.name},
                    query_ids={query.query_id},
                    lineages={query.lineage},
                    retrieved_utc=self._now(),
                )
            )
        return SourceResult(
            records=records,
            log=SearchLogEntry(
                database=self.name,
                query_id=query.query_id,
                query_text=query.text,
                executed_query=executed,
                search_date=self._now(),
                http_status=200,
                reported_total=message.get("total-results"),
                returned_count=len(records),
                raw_export="",
                query_adaptation=QUERY_ADAPTATIONS[self.name],
            ),
            raw=message,
        )


class ArxivSource(Source):
    name = "arxiv"
    min_interval_s = 3.2  # arXiv asks for >= 3 s between API calls
    NS = {"a": "http://www.w3.org/2005/Atom"}
    TOTAL_TAG = "{http://a9.com/-/spec/opensearch/1.1/}totalResults"
    ARXIV_NS = "{http://arxiv.org/schemas/atom}"

    TERM_BUDGET = 2

    def __init__(self, *args, token_df: dict[str, int] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_df = token_df or {}

    def _build_query(self, query: Query) -> str:
        categories = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
        groups = rank_groups(query, self.token_df, self.TERM_BUDGET)
        if not groups:
            groups = [[w] for w in query.plain_terms().split()[: self.TERM_BUDGET]]
        anded = []
        for group in groups:
            ored = " OR ".join(
                f'all:"{alt}"' if " " in alt else f"all:{alt}" for alt in group
            )
            anded.append(f"({ored})" if len(group) > 1 else ored)
        return f"({categories}) AND " + " AND ".join(anded)

    def search(self, query: Query) -> SourceResult:
        executed = self._build_query(query)
        params = {
            "search_query": executed,
            "max_results": self.per_page,
            "sortBy": "relevance",
        }
        outcome = self._get("http://export.arxiv.org/api/query", params)
        if not self._ok(outcome):
            return self._failure(query, executed, outcome)
        try:
            root = ET.fromstring(outcome.text)
        except ET.ParseError as exc:
            return self._failure(query, executed, exc)

        records = []
        for entry in root.findall("a:entry", self.NS):
            abs_id = (entry.findtext("a:id", namespaces=self.NS) or "").strip()
            arxiv_id = abs_id.rsplit("/", 1)[-1] if abs_id else ""
            published = entry.findtext("a:published", namespaces=self.NS) or ""
            journal_ref = entry.findtext(f"{self.ARXIV_NS}journal_ref")
            records.append(
                LiteratureRecord(
                    title=" ".join((entry.findtext("a:title", namespaces=self.NS) or "").split()),
                    doi=entry.findtext(f"{self.ARXIV_NS}doi") or "",
                    authors=[
                        (a.findtext("a:name", namespaces=self.NS) or "").strip()
                        for a in entry.findall("a:author", self.NS)
                    ],
                    year=int(published[:4]) if published[:4].isdigit() else None,
                    venue=journal_ref or "arXiv",
                    # A journal_ref means a formal version exists; that distinction
                    # decides preprint-vs-formal status for 2025-2026 entries.
                    venue_type="preprint" if not journal_ref else "preprint_with_journal_ref",
                    publisher="arXiv",
                    is_oa=True,
                    oa_url=abs_id,
                    arxiv_id=arxiv_id,
                    abstract_available=bool(entry.findtext("a:summary", namespaces=self.NS)),
                    source_apis={self.name},
                    query_ids={query.query_id},
                    lineages={query.lineage},
                    retrieved_utc=self._now(),
                )
            )
        total_text = root.findtext(self.TOTAL_TAG)
        return SourceResult(
            records=records,
            log=SearchLogEntry(
                database=self.name,
                query_id=query.query_id,
                query_text=query.text,
                executed_query=executed,
                search_date=self._now(),
                http_status=200,
                reported_total=int(total_text) if (total_text or "").isdigit() else None,
                returned_count=len(records),
                raw_export="",
                query_adaptation=QUERY_ADAPTATIONS[self.name],
            ),
            raw=outcome.text,
        )


class DblpSource(Source):
    """Title-lookup verification of formal venue and publication type.

    Not a discovery source -- see ``QUERY_ADAPTATIONS['dblp']``.
    """

    name = "dblp"
    min_interval_s = 1.2

    _TYPE_MAP = {
        "Journal Articles": "journal-article",
        "Conference and Workshop Papers": "proceedings-article",
        "Informal and Other Publications": "preprint",
        "Books and Theses": "book-or-thesis",
    }

    def verify_title(self, title: str) -> dict | None:
        """Return DBLP's record for an exact-ish title match, or None.

        Used to settle formal-vs-preprint status for 2025-2026 entries
        (``01_MASTER_PROMPT.md`` §6) without trusting a search snippet.
        """
        from .records import normalize_title

        probe = " ".join(title.split()[:12])
        outcome = self._get(
            "https://dblp.org/search/publ/api",
            {"q": probe, "format": "json", "h": 10},
        )
        if not self._ok(outcome):
            return None
        try:
            hits = outcome.json()["result"]["hits"]
        except (ValueError, KeyError):
            return None
        raw_hits = hits.get("hit", [])
        if isinstance(raw_hits, dict):
            raw_hits = [raw_hits]
        wanted = normalize_title(title)
        for hit in raw_hits:
            info = hit.get("info", {})
            if normalize_title((info.get("title") or "").rstrip(".")) == wanted:
                return {
                    "venue": info.get("venue") or "",
                    "venue_type": self._TYPE_MAP.get(
                        info.get("type", ""), info.get("type", "")
                    ),
                    "year": info.get("year"),
                    "doi": info.get("doi") or "",
                    "access": info.get("access") or "",
                    "ee": info.get("ee") or "",
                    "dblp_key": info.get("key") or "",
                }
        return None


class SemanticScholarSource(Source):
    name = "semantic_scholar"
    min_interval_s = 3.5  # unauthenticated shared pool 429s aggressively
    max_retries = 4

    FIELDS = "title,year,externalIds,venue,publicationTypes,openAccessPdf,citationCount,abstract,authors"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        if api_key:
            self.session.headers["x-api-key"] = api_key
            self.min_interval_s = 1.1

    def search(self, query: Query) -> SourceResult:
        executed = query.plain_terms()
        params = {"query": executed, "limit": min(self.per_page, 100), "fields": self.FIELDS}
        outcome = self._get(
            "https://api.semanticscholar.org/graph/v1/paper/search", params
        )
        if not self._ok(outcome):
            return self._failure(query, executed, outcome)
        payload = outcome.json()
        records = []
        for paper in payload.get("data", []) or []:
            ext = paper.get("externalIds") or {}
            types = paper.get("publicationTypes") or []
            records.append(
                LiteratureRecord(
                    title=paper.get("title") or "",
                    doi=ext.get("DOI") or "",
                    authors=[a.get("name", "") for a in paper.get("authors", []) if a.get("name")],
                    year=paper.get("year"),
                    venue=paper.get("venue") or "",
                    venue_type=";".join(types),
                    is_oa=bool(paper.get("openAccessPdf")),
                    oa_url=(paper.get("openAccessPdf") or {}).get("url", "") or "",
                    arxiv_id=ext.get("ArXiv") or "",
                    cited_by_count=paper.get("citationCount"),
                    abstract_available=bool(paper.get("abstract")),
                    source_apis={self.name},
                    query_ids={query.query_id},
                    lineages={query.lineage},
                    retrieved_utc=self._now(),
                )
            )
        return SourceResult(
            records=records,
            log=SearchLogEntry(
                database=self.name,
                query_id=query.query_id,
                query_text=query.text,
                executed_query=executed,
                search_date=self._now(),
                http_status=200,
                reported_total=payload.get("total"),
                returned_count=len(records),
                raw_export="",
                query_adaptation=QUERY_ADAPTATIONS[self.name],
            ),
            raw=payload,
        )


# Keyword-sweep sources, in the order they are executed.
DISCOVERY_SOURCES: dict[str, type[Source]] = {
    OpenAlexSource.name: OpenAlexSource,
    CrossrefSource.name: CrossrefSource,
}

SUPPLEMENTARY_SOURCES: dict[str, type[Source]] = {
    ArxivSource.name: ArxivSource,
}

# Best-effort: the unauthenticated pool 429s persistently. Kept so its
# unavailability is *logged* rather than silently absent.
BEST_EFFORT_SOURCES: dict[str, type[Source]] = {
    SemanticScholarSource.name: SemanticScholarSource,
}

# Title/DOI lookup only, never keyword-swept.
VERIFICATION_SOURCES: dict[str, type[Source]] = {
    DblpSource.name: DblpSource,
}

ALL_SOURCES: dict[str, type[Source]] = {
    **DISCOVERY_SOURCES,
    **SUPPLEMENTARY_SOURCES,
    **BEST_EFFORT_SOURCES,
    **VERIFICATION_SOURCES,
}
