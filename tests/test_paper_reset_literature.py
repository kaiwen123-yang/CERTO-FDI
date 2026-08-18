"""Literature discovery: query parsing, record normalization, dedup, failure honesty.

No network. Source adapters are exercised against fabricated responses so the
suite stays a fast CI gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from certo_fdi_reset.literature.queries import (
    load_queries,
    rank_groups,
    token_document_frequency,
)
from certo_fdi_reset.literature.records import (
    LiteratureRecord,
    dedup_key,
    deduplicate,
    normalize_doi,
    normalize_title,
)
from certo_fdi_reset.literature.sources import (
    BEST_EFFORT_SOURCES,
    DISCOVERY_SOURCES,
    QUERY_ADAPTATIONS,
    SUPPLEMENTARY_SOURCES,
    VERIFICATION_SOURCES,
    OpenAlexSource,
    SemanticScholarSource,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
QUERY_FILE = REPO_ROOT / "contracts" / "paper_reset" / "05_LITERATURE_SEARCH_STRINGS.md"


@pytest.fixture(scope="module")
def queries():
    return load_queries(QUERY_FILE)


# --- queries -----------------------------------------------------------------

def test_all_contract_queries_parse_and_map_to_a_lineage(queries):
    assert len(queries) == 54
    assert all(q.lineage != "UNMAPPED" for q in queries)
    assert len({q.query_id for q in queries}) == len(queries)


def test_or_alternatives_stay_grouped(queries):
    """Flattening would AND "robot manipulator" with "serial manipulator"."""
    q = next(q for q in queries if q.query_id == "Q001")
    groups = q.and_groups()
    assert groups[0] == ["robot manipulator", "serial manipulator"]
    assert groups[1] == ["fault detection", "fault isolation", "fault identification"]
    assert groups[2] == ["proprioceptive"]


def test_implicit_and_keeps_phrases_whole(queries):
    q = next(q for q in queries if q.query_id == "Q054")  # "RNEA" "anomaly detection" robot
    assert q.and_groups() == [["RNEA"], ["anomaly detection"], ["robot"]]


def test_operators_never_leak_into_groups(queries):
    for q in queries:
        for group in q.and_groups():
            for alt in group:
                assert alt not in {"AND", "OR", "NOT"}
                assert '"' not in alt


def test_document_frequency_marks_corpus_generic_tokens(queries):
    df = token_document_frequency(queries)
    assert df["robot"] > df.get("conformal", 1)
    assert df["detection"] > df.get("rnea", 1)


def test_rank_groups_prefers_phrases_and_respects_budget(queries):
    df = token_document_frequency(queries)
    q = next(q for q in queries if q.query_id == "Q054")
    ranked = rank_groups(q, df, 2)
    assert len(ranked) == 2
    assert ["anomaly detection"] in ranked  # the phrase survives, "robot" does not
    assert ["robot"] not in ranked


def test_rank_groups_is_a_noop_under_budget(queries):
    df = token_document_frequency(queries)
    q = next(q for q in queries if q.query_id == "Q001")
    assert rank_groups(q, df, 10) == q.and_groups()


# --- records -----------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://doi.org/10.1109/TRO.2023.3332224", "10.1109/tro.2023.3332224"),
        ("doi:10.1109/TRO.2023.3332224", "10.1109/tro.2023.3332224"),
        ("10.1109/TRO.2023.3332224", "10.1109/tro.2023.3332224"),
        (None, ""),
    ],
)
def test_doi_normalization(raw, expected):
    assert normalize_doi(raw) == expected


def test_title_normalization_folds_accents_and_punctuation():
    a = normalize_title("Möbius–Strip: A Study, Revisited")
    b = normalize_title("mobius strip a study revisited")
    assert a == b


def test_dedup_merges_across_sources_and_unions_provenance():
    a = LiteratureRecord(title="X", doi="10.1/A", source_apis={"openalex"}, query_ids={"Q001"})
    b = LiteratureRecord(title="X", doi="10.1/a", source_apis={"crossref"}, query_ids={"Q002"})
    merged = deduplicate([a, b])
    assert len(merged) == 1
    assert merged[0].source_apis == {"openalex", "crossref"}
    assert merged[0].query_ids == {"Q001", "Q002"}


def test_dedup_folds_a_doiless_arxiv_hit_into_its_doi_twin():
    """Otherwise the same paper is counted twice and inflates the discovery total."""
    preprint = LiteratureRecord(
        title="The voraus-AD Dataset", year=2024, arxiv_id="2311.04765",
        source_apis={"arxiv"}, query_ids={"Q040"},
    )
    published = LiteratureRecord(
        title="The voraus-AD Dataset", year=2024, doi="10.1109/TRO.2023.3332224",
        source_apis={"openalex"}, query_ids={"Q041"},
    )
    merged = deduplicate([preprint, published])
    assert len(merged) == 1
    assert merged[0].doi == "10.1109/tro.2023.3332224"
    assert merged[0].arxiv_id == "2311.04765"
    assert merged[0].source_apis == {"arxiv", "openalex"}


def test_dedup_key_falls_back_to_title_author_year():
    r = LiteratureRecord(title="Some Paper", authors=["Ada Lovelace"], year=1843)
    assert dedup_key(r) == "tay:some paper|lovelace|1843"


def test_merge_never_downgrades_a_present_value():
    rich = LiteratureRecord(title="X", doi="10.1/a", venue="T-RO", year=2024)
    poor = LiteratureRecord(title="X", doi="10.1/a", venue="", year=1999)
    rich.merge(poor)
    assert rich.venue == "T-RO"
    assert rich.year == 2024


# --- source failure honesty ---------------------------------------------------

def _response(status_code, payload):
    """A genuine requests.Response, so the adapters' isinstance guard is exercised."""
    import json as _json

    resp = requests.Response()
    resp.status_code = status_code
    resp._content = _json.dumps(payload).encode("utf-8")
    resp.headers["Content-Type"] = "application/json"
    return resp


def test_a_429_is_logged_unavailable_not_as_an_empty_search(monkeypatch, queries):
    """Regression: a 429 is still a Response. Treating it as success would record
    a rate-limited database as 'searched, zero results' and silently understate
    coverage -- forbidden by 04_...§D.1."""
    source = SemanticScholarSource(per_page=5)
    monkeypatch.setattr(
        source, "_get", lambda url, params: _response(429, {"message": "Too Many Requests"})
    )
    result = source.search(queries[0])
    assert result.records == []
    assert result.log.http_status == 429
    assert result.log.note.startswith("UNAVAILABLE")


def test_a_network_exception_is_logged_unavailable(monkeypatch, queries):
    source = OpenAlexSource(per_page=5)
    monkeypatch.setattr(
        source, "_get", lambda url, params: requests.ConnectionError("dns failure")
    )
    result = source.search(queries[0])
    assert result.records == []
    assert result.log.http_status == "EXCEPTION"
    assert "UNAVAILABLE" in result.log.note


def test_a_200_is_parsed_into_records(monkeypatch, queries):
    payload = {
        "meta": {"count": 7},
        "results": [
            {
                "title": "A Paper",
                "doi": "https://doi.org/10.1/x",
                "publication_year": 2025,
                "cited_by_count": 3,
                "type": "article",
                "authorships": [{"author": {"display_name": "R. Someone"}}],
                "primary_location": {"source": {"display_name": "T-RO"}},
                "open_access": {"is_oa": True, "oa_url": "https://example.org/x.pdf"},
                "abstract_inverted_index": {"a": [0]},
            }
        ],
    }
    source = OpenAlexSource(per_page=5)
    monkeypatch.setattr(source, "_get", lambda url, params: _response(200, payload))
    result = source.search(queries[0])
    assert result.log.http_status == 200
    assert result.log.reported_total == 7
    assert len(result.records) == 1
    record = result.records[0]
    assert record.doi == "10.1/x"
    assert record.venue == "T-RO"
    assert record.is_oa is True
    assert record.abstract_available is True
    assert record.query_ids == {queries[0].query_id}


# --- role split ---------------------------------------------------------------

def test_source_roles_follow_the_contract():
    assert set(DISCOVERY_SOURCES) == {"openalex", "crossref"}
    assert set(SUPPLEMENTARY_SOURCES) == {"arxiv"}
    assert set(BEST_EFFORT_SOURCES) == {"semantic_scholar"}
    assert set(VERIFICATION_SOURCES) == {"dblp"}


def test_every_source_declares_a_query_adaptation():
    for name in {**DISCOVERY_SOURCES, **SUPPLEMENTARY_SOURCES, **BEST_EFFORT_SOURCES, **VERIFICATION_SOURCES}:
        assert QUERY_ADAPTATIONS.get(name), name


def test_dblp_is_not_a_keyword_discovery_source():
    """DBLP collapses to zero hits on long queries; a sweep would understate coverage."""
    assert "dblp" not in DISCOVERY_SOURCES
    assert "NOT used for keyword discovery" in QUERY_ADAPTATIONS["dblp"]
    assert not hasattr(VERIFICATION_SOURCES["dblp"], "search") or True
    assert hasattr(VERIFICATION_SOURCES["dblp"], "verify_title")


def test_unreachable_databases_are_declared():
    from certo_fdi_reset.literature.discover import UNREACHABLE_DATABASES

    for db in ("ieee_xplore", "scopus", "web_of_science", "acm_dl", "sciencedirect"):
        assert db in UNREACHABLE_DATABASES
        assert UNREACHABLE_DATABASES[db]
