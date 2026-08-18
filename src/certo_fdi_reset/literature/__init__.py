"""Systematic literature discovery, deduplication, and screening support.

Contract: ``contracts/paper_reset/04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md``.

Nothing in here decides novelty. It produces the discovery library, the search
log, and the access manifest; occupancy claims come only from full texts read at
evidence level A1/A2/B1 and recorded as method cards.
"""

from .queries import QUERY_SET_VERSION, Query, load_queries
from .records import LiteratureRecord, dedup_key, deduplicate, normalize_title

__all__ = [
    "QUERY_SET_VERSION",
    "Query",
    "load_queries",
    "LiteratureRecord",
    "dedup_key",
    "deduplicate",
    "normalize_title",
]
