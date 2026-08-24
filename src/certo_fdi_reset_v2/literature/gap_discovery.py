"""Phase L500 step 1: supplementary discovery for the 4.6 clusters V1 missed.

The V1 round (169 logged searches, 5458 deduplicated records) already covers
manipulator FDI, collision/MOB, chain/graph, Lie/equivariant, public datasets,
context conditioning and sequential monitoring. Comparing its search log with
``contracts/paper_reset_v2/01_MASTER_PROMPT.md`` section 4.6 leaves these
clusters without a dedicated V1 query:

  foundation-model anomaly detection, multimodal proprioceptive anomaly,
  few-shot healthy adaptation, cross-robot transfer, domain adaptation,
  multiscale time series, symmetry breaking, approximately equivariant,
  active diagnosis / diagnosability (contract 4.3 quota: 5 full texts).

This module sweeps exactly those gaps and merges the results into the V2
screening pool, reusing the V1 source adapters and dedup passes so the merged
library stays one auditable schema. Discovery only -- nothing here supports an
occupancy claim (evidence levels A1/A2/B1 still require the full text).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from certo_fdi_reset.literature.queries import Query, token_document_frequency
from certo_fdi_reset.literature.records import (
    CSV_COLUMNS,
    LiteratureRecord,
    deduplicate,
)
from certo_fdi_reset.literature.sources import (
    SEARCH_LOG_COLUMNS,
    ArxivSource,
    CrossrefSource,
    OpenAlexSource,
    SemanticScholarSource,
)

# V2 lineage taxonomy extends V1's; existing tags are kept verbatim so the two
# rounds stay joinable.
GAP_QUERIES: tuple[Query, ...] = (
    Query("V2Q01", "4.6 foundation/multimodal", "L9_foundation_multimodal",
          "robot foundation model anomaly detection"),
    Query("V2Q02", "4.6 foundation/multimodal", "L9_foundation_multimodal",
          "multimodal proprioceptive anomaly detection robot manipulator"),
    Query("V2Q03", "4.6 cross-robot/few-shot", "L10_cross_robot_few_shot",
          "few-shot healthy-only adaptation anomaly detection robot"),
    Query("V2Q04", "4.6 cross-robot/few-shot", "L10_cross_robot_few_shot",
          "cross-robot anomaly detection transfer manipulator"),
    Query("V2Q05", "4.6 cross-robot/few-shot", "L10_cross_robot_few_shot",
          "domain adaptation fault diagnosis industrial robot time series"),
    Query("V2Q06", "4.6 multiscale MTSAD", "L7_mtsad_context_ood_sequential",
          "multiscale multivariate time series anomaly detection robot"),
    Query("V2Q07", "4.6 symmetry breaking", "L5_lie_geometry_equivariant",
          "symmetry breaking detection dynamical system machine learning"),
    Query("V2Q08", "4.6 approximate equivariance", "L5_lie_geometry_equivariant",
          "approximately equivariant neural network dynamics"),
    Query("V2Q09", "4.3 active diagnosis quota", "L11_active_diagnosis",
          "active fault diagnosis input design robot diagnosability"),
    Query("V2Q10", "4.3 active diagnosis quota", "L11_active_diagnosis",
          "optimal sensor placement fault detection manipulator"),
)


def load_v1_library(path: Path) -> list[LiteratureRecord]:
    """Rehydrate LiteratureRecords from the frozen V1 CSV (inverse of as_csv_row)."""
    records: list[LiteratureRecord] = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            year = row.get("year") or ""
            cited = row.get("cited_by_count") or ""
            is_oa = row.get("is_oa") or ""
            records.append(
                LiteratureRecord(
                    title=row.get("title", ""),
                    doi=row.get("doi", ""),
                    authors=[a for a in (row.get("authors") or "").split("; ") if a],
                    year=int(year) if year.strip().isdigit() else None,
                    venue=row.get("venue", ""),
                    venue_type=row.get("venue_type", ""),
                    publisher=row.get("publisher", ""),
                    is_oa=None if not is_oa else is_oa == "true",
                    oa_url=row.get("oa_url", ""),
                    arxiv_id=row.get("arxiv_id", ""),
                    cited_by_count=int(cited) if cited.strip().isdigit() else None,
                    abstract_available=(row.get("abstract_available") == "true"),
                    source_apis={s for s in (row.get("source_apis") or "").replace("; ", ";").split(";") if s},
                    query_ids={s for s in (row.get("query_ids") or "").replace("; ", ";").split(";") if s},
                    lineages={s for s in (row.get("lineages") or "").replace("; ", ";").split(";") if s},
                    retrieved_utc=row.get("retrieved_utc", ""),
                )
            )
    return records


def run_gap_discovery(
    v1_library_csv: Path,
    out_pool_csv: Path,
    out_log_csv: Path,
    out_summary_json: Path,
    per_page: int = 50,
) -> dict:
    """Sweep the gap queries, merge with V1, and write the V2 screening pool."""
    df = token_document_frequency(list(GAP_QUERIES))
    sources = [
        OpenAlexSource(per_page=per_page),
        CrossrefSource(per_page=per_page),
        ArxivSource(per_page=per_page, token_df=df),
        SemanticScholarSource(per_page=per_page),
    ]

    logs = []
    new_records: list[LiteratureRecord] = []
    for query in GAP_QUERIES:
        for source in sources:
            result = source.search(query)
            logs.append(result.log)
            new_records.extend(result.records)
            print(
                f"[gap] {query.query_id} {source.name}: status={result.log.http_status} "
                f"returned={result.log.returned_count}",
                flush=True,
            )

    v1_records = load_v1_library(v1_library_csv)
    v1_count = len(v1_records)
    merged = deduplicate(v1_records + new_records)

    out_pool_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_pool_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in merged:
            writer.writerow(record.as_csv_row())

    with out_log_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SEARCH_LOG_COLUMNS)
        writer.writeheader()
        for entry in logs:
            writer.writerow(entry.as_csv_row())

    summary = {
        "executed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gap_queries": len(GAP_QUERIES),
        "searches_logged": len(logs),
        "searches_unavailable": sum(1 for l in logs if str(l.http_status) != "200"),
        "raw_new_records": len(new_records),
        "v1_library_records": v1_count,
        "merged_pool_records": len(merged),
        "net_new_after_dedup": len(merged) - v1_count,
        "pool_csv": str(out_pool_csv),
        "log_csv": str(out_log_csv),
    }
    out_summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-library", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()

    summary = run_gap_discovery(
        v1_library_csv=args.v1_library,
        out_pool_csv=args.out_dir / "screening_pool.csv",
        out_log_csv=args.out_dir / "v2_gap_search_log.csv",
        out_summary_json=args.run_dir / "l500" / "gap_discovery_summary.json",
    )
    print(json.dumps(summary, indent=2))
