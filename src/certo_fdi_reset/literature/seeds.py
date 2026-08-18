"""Anchor resolution and mandatory backward/forward citation chasing.

Contract ``20_SEED_PAPERS_AND_CITATION_CHAINS.md`` names eight anchors and
requires backward + forward chasing from each; ``04_…§D.5`` requires the same for
core reviews and nearest neighbours.

Every entry in the contract's seed list is a *search seed, not a verified
conclusion* -- the anchors here are resolved against OpenAlex/Crossref and the
resolution is recorded, including anchors that fail to resolve.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

from .records import LiteratureRecord, normalize_title
from .sources import CONTACT_EMAIL, USER_AGENT


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    title: str
    expected_year: int | None = None
    hint_doi: str = ""
    lineage: str = ""


# The eight mandatory chasing anchors of contract 20.
MANDATORY_ANCHORS: tuple[Anchor, ...] = (
    Anchor(
        "annual_review_2026",
        "Fault Diagnosis in Dynamical Systems: Geometric Interpretation and Tractable Algorithms",
        2026,
        lineage="L1_classical_geometric_fdi",
    ),
    Anchor(
        "haddadin_2017",
        "Robot Collisions: A Survey on Detection, Isolation, and Identification",
        2017,
        hint_doi="10.1109/TRO.2017.2723903",
        lineage="L6_contact_collision_localization",
    ),
    Anchor(
        "evangelisti_hirche_2024",
        "Data-Driven Momentum Observers With Physically Consistent Gaussian Processes",
        2024,
        lineage="L3_learned_momentum_observer",
    ),
    Anchor(
        "mobnet_2025",
        "MOB-Net: Limb-modularized uncertainty torque learning of humanoids for sensorless external torque estimation",
        2025,
        hint_doi="10.1177/02783649241260428",
        lineage="L3_learned_momentum_observer",
    ),
    Anchor(
        "voraus_ad_2024",
        "The voraus-AD Dataset for Anomaly Detection in Robot Applications",
        2024,
        hint_doi="10.1109/TRO.2023.3332224",
        lineage="L8_public_benchmarks_transfer",
    ),
    Anchor(
        "road_2023",
        "Robotic Arm Dataset (RoAD): A Dataset to Support the Design and Test of Machine Learning-Driven Anomaly Detection in a Production Line",
        2023,
        hint_doi="10.1109/IECON51785.2023.10311726",
        lineage="L8_public_benchmarks_transfer",
    ),
    Anchor(
        "aursad_2021",
        "AURSAD: Universal Robot Screwdriving Anomaly Detection Dataset",
        2021,
        lineage="L8_public_benchmarks_transfer",
    ),
    Anchor(
        # Contract 20 lists this only as "Xie et al., MS-HGNN, L4DC 2025"; resolved
        # against OpenAlex/arXiv to its full title. Seeds are unverified by contract.
        "ms_hgnn_2025",
        "Morphological-Symmetry-Equivariant Heterogeneous Graph Neural Network for Robotic Dynamics Learning",
        2025,
        hint_doi="10.48550/arxiv.2412.01297",
        lineage="L4_structured_chain_graph_dynamics",
    ),
)


@dataclass
class ChaseResult:
    anchor: Anchor
    resolved: bool
    openalex_id: str = ""
    resolved_title: str = ""
    resolved_year: int | None = None
    resolved_doi: str = ""
    backward: list[LiteratureRecord] = field(default_factory=list)
    forward: list[LiteratureRecord] = field(default_factory=list)
    note: str = ""

    def as_csv_row(self) -> dict[str, str]:
        return {
            "anchor_id": self.anchor.anchor_id,
            "anchor_title": self.anchor.title,
            "expected_year": "" if self.anchor.expected_year is None else str(self.anchor.expected_year),
            "resolved": str(self.resolved).lower(),
            "openalex_id": self.openalex_id,
            "resolved_title": self.resolved_title,
            "resolved_year": "" if self.resolved_year is None else str(self.resolved_year),
            "resolved_doi": self.resolved_doi,
            "backward_count": str(len(self.backward)),
            "forward_count": str(len(self.forward)),
            "note": self.note,
        }


CHASE_LOG_COLUMNS: tuple[str, ...] = (
    "anchor_id",
    "anchor_title",
    "expected_year",
    "resolved",
    "openalex_id",
    "resolved_title",
    "resolved_year",
    "resolved_doi",
    "backward_count",
    "forward_count",
    "note",
)


class CitationChaser:
    """Backward/forward chasing over the OpenAlex graph."""

    BASE = "https://api.openalex.org/works"

    def __init__(self, session: requests.Session | None = None, pause: float = 0.15):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.pause = pause

    def _get(self, url: str, params: dict) -> dict | None:
        params = {**params, "mailto": CONTACT_EMAIL}
        for attempt in range(3):
            time.sleep(self.pause)
            try:
                response = self.session.get(url, params=params, timeout=45)
            except requests.RequestException:
                time.sleep(2.0 * (attempt + 1))
                continue
            if response.status_code == 200:
                return response.json()
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(4.0 * (attempt + 1))
                continue
            return None
        return None

    @staticmethod
    def _to_record(work: dict, lineage: str, tag: str) -> LiteratureRecord:
        source = (work.get("primary_location") or {}).get("source") or {}
        oa = work.get("open_access") or {}
        return LiteratureRecord(
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
            source_apis={"openalex_citation_chase"},
            query_ids={tag},
            lineages={lineage} if lineage else set(),
        )

    def resolve(self, anchor: Anchor) -> dict | None:
        if anchor.hint_doi:
            payload = self._get(f"{self.BASE}/doi:{anchor.hint_doi}", {})
            if payload and payload.get("id"):
                return payload
        payload = self._get(self.BASE, {"search": anchor.title, "per-page": 10})
        if not payload:
            return None
        wanted = normalize_title(anchor.title)
        results = payload.get("results", [])
        for work in results:
            if normalize_title(work.get("title") or "") == wanted:
                return work
        # Fall back to a prefix match: contract titles are sometimes shortened.
        for work in results:
            candidate = normalize_title(work.get("title") or "")
            if candidate.startswith(wanted[:40]) or wanted.startswith(candidate[:40]):
                return work
        return None

    def chase(self, anchor: Anchor, forward_limit: int = 100) -> ChaseResult:
        work = self.resolve(anchor)
        if not work:
            return ChaseResult(
                anchor=anchor,
                resolved=False,
                note="UNRESOLVED: no OpenAlex match for hint DOI or title",
            )

        result = ChaseResult(
            anchor=anchor,
            resolved=True,
            openalex_id=work.get("id", ""),
            resolved_title=work.get("title") or "",
            resolved_year=work.get("publication_year"),
            resolved_doi=work.get("doi") or "",
        )
        if anchor.expected_year and result.resolved_year:
            if abs(result.resolved_year - anchor.expected_year) > 1:
                result.note = (
                    f"YEAR_MISMATCH: contract seed says {anchor.expected_year}, "
                    f"OpenAlex says {result.resolved_year} (seeds are unverified by contract 20)"
                )

        # Backward: works this anchor references.
        referenced = work.get("referenced_works") or []
        for chunk_start in range(0, len(referenced), 50):
            chunk = referenced[chunk_start : chunk_start + 50]
            ids = "|".join(c.rsplit("/", 1)[-1] for c in chunk)
            payload = self._get(self.BASE, {"filter": f"openalex_id:{ids}", "per-page": 50})
            if not payload:
                continue
            for ref in payload.get("results", []):
                result.backward.append(
                    self._to_record(ref, anchor.lineage, f"chase_backward:{anchor.anchor_id}")
                )

        # Forward: works citing this anchor, most-cited first.
        short_id = (work.get("id") or "").rsplit("/", 1)[-1]
        payload = self._get(
            self.BASE,
            {
                "filter": f"cites:{short_id}",
                "per-page": min(forward_limit, 200),
                "sort": "cited_by_count:desc",
            },
        )
        if payload:
            for citing in payload.get("results", [])[:forward_limit]:
                result.forward.append(
                    self._to_record(citing, anchor.lineage, f"chase_forward:{anchor.anchor_id}")
                )
        return result
