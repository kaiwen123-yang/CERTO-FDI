"""Normalized literature record and deduplication.

Dedup is by DOI when present, else by a normalized (title, first-author-surname,
year) key. Contract ``04_…§D.3`` requires DOI/title/author deduplication before
any count is reported.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, fields

# Fields written to literature_deduplicated_library.csv, in order.
CSV_COLUMNS: tuple[str, ...] = (
    "record_id",
    "doi",
    "title",
    "authors",
    "year",
    "venue",
    "venue_type",
    "publisher",
    "is_oa",
    "oa_url",
    "arxiv_id",
    "cited_by_count",
    "source_apis",
    "query_ids",
    "lineages",
    "abstract_available",
    "retrieved_utc",
)

_GREEK_AND_MATH = {
    "–": "-", "—": "-", "−": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
}


def normalize_title(title: str) -> str:
    """Casefold, strip accents/punctuation/whitespace so near-identical titles collide."""
    if not title:
        return ""
    text = "".join(_GREEK_AND_MATH.get(ch, ch) for ch in title)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"<[^>]+>", " ", text)          # stray markup from some APIs
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    text = doi.strip().casefold()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.strip()


def surname(author: str) -> str:
    """Best-effort surname from a display name; used only for the dedup key."""
    cleaned = normalize_title(author)
    return cleaned.split()[-1] if cleaned else ""


@dataclass
class LiteratureRecord:
    title: str
    doi: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    venue_type: str = ""
    publisher: str = ""
    is_oa: bool | None = None
    oa_url: str = ""
    arxiv_id: str = ""
    cited_by_count: int | None = None
    abstract_available: bool = False
    source_apis: set[str] = field(default_factory=set)
    query_ids: set[str] = field(default_factory=set)
    lineages: set[str] = field(default_factory=set)
    retrieved_utc: str = ""

    def __post_init__(self) -> None:
        self.doi = normalize_doi(self.doi)

    @property
    def record_id(self) -> str:
        return dedup_key(self)

    def merge(self, other: LiteratureRecord) -> None:
        """Fold a duplicate in, preferring existing non-empty values."""
        self.source_apis |= other.source_apis
        self.query_ids |= other.query_ids
        self.lineages |= other.lineages
        for name in ("doi", "title", "venue", "venue_type", "publisher", "oa_url", "arxiv_id"):
            if not getattr(self, name) and getattr(other, name):
                setattr(self, name, getattr(other, name))
        if self.year is None:
            self.year = other.year
        if self.is_oa is None:
            self.is_oa = other.is_oa
        if not self.authors:
            self.authors = other.authors
        if other.cited_by_count is not None:
            self.cited_by_count = max(self.cited_by_count or 0, other.cited_by_count)
        self.abstract_available = self.abstract_available or other.abstract_available

    def as_csv_row(self) -> dict[str, str]:
        return {
            "record_id": self.record_id,
            "doi": self.doi,
            "title": self.title,
            "authors": "; ".join(self.authors),
            "year": "" if self.year is None else str(self.year),
            "venue": self.venue,
            "venue_type": self.venue_type,
            "publisher": self.publisher,
            "is_oa": "" if self.is_oa is None else str(self.is_oa).lower(),
            "oa_url": self.oa_url,
            "arxiv_id": self.arxiv_id,
            "cited_by_count": "" if self.cited_by_count is None else str(self.cited_by_count),
            "source_apis": "; ".join(sorted(self.source_apis)),
            "query_ids": "; ".join(sorted(self.query_ids)),
            "lineages": "; ".join(sorted(self.lineages)),
            "abstract_available": str(self.abstract_available).lower(),
            "retrieved_utc": self.retrieved_utc,
        }


def dedup_key(record: LiteratureRecord) -> str:
    """DOI when available, else normalized title + first-author surname + year."""
    if record.doi:
        return f"doi:{record.doi}"
    title = normalize_title(record.title)
    author = surname(record.authors[0]) if record.authors else ""
    year = record.year if record.year is not None else ""
    return f"tay:{title}|{author}|{year}"


def deduplicate(records: list[LiteratureRecord]) -> list[LiteratureRecord]:
    """Collapse duplicates, then fold title-keyed records into DOI-keyed twins.

    A record found on arXiv without a DOI and again on Crossref with one would
    otherwise be counted twice and inflate the discovery total.
    """
    merged: dict[str, LiteratureRecord] = {}
    for record in records:
        key = dedup_key(record)
        if key in merged:
            merged[key].merge(record)
        else:
            merged[key] = record

    by_title: dict[tuple[str, str], LiteratureRecord] = {}
    for record in merged.values():
        if record.doi:
            title = normalize_title(record.title)
            if title:
                by_title[(title, str(record.year or ""))] = record

    survivors: dict[str, LiteratureRecord] = {}
    for key, record in merged.items():
        if not record.doi:
            title = normalize_title(record.title)
            twin = by_title.get((title, str(record.year or "")))
            if twin is None and title:
                # Same title, unknown year on one side: accept a year-agnostic match.
                candidates = [v for (t, _y), v in by_title.items() if t == title]
                twin = candidates[0] if len(candidates) == 1 else None
            if twin is not None:
                twin.merge(record)
                continue
        survivors[key] = record
    return list(survivors.values())


assert CSV_COLUMNS[0] == "record_id"
assert {f.name for f in fields(LiteratureRecord)} >= set(CSV_COLUMNS) - {"record_id"}
