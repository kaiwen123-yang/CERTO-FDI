"""Phase L1: execute the frozen query set, export raw results, deduplicate.

    python -m certo_fdi_reset.literature.discover --config configs/paper_reset.yaml

Produces the Phase L1 outputs named in
``contracts/paper_reset/19_EXPECTED_OUTPUTS_AND_SCHEMAS.md``:
``literature_search_log.csv``, ``literature_raw_export/``,
``literature_deduplicated_library.csv``, ``database_availability.csv``, and the
identified/deduplicated rows of ``prisma_flow.csv``.

This step performs no screening and reaches no novelty conclusion. It only
establishes, with an auditable trail, what exists.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ..config import load_config
from ..provenance import sha256_file, utc_stamp
from .queries import QUERY_SET_VERSION, load_queries, token_document_frequency
from .records import CSV_COLUMNS, LiteratureRecord, deduplicate
from .sources import (
    BEST_EFFORT_SOURCES,
    DISCOVERY_SOURCES,
    QUERY_ADAPTATIONS,
    SEARCH_LOG_COLUMNS,
    SUPPLEMENTARY_SOURCES,
    SearchLogEntry,
)

# Databases named by the contract that this host cannot reach. Recorded so the
# PRISMA flow shows them as unavailable rather than silently omitted
# (04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md §D.1).
UNREACHABLE_DATABASES: dict[str, str] = {
    "ieee_xplore": "HTTP 418 from this host; no institutional subscription. Metadata still reached via OpenAlex/Crossref.",
    "scopus": "No subscription and no API key.",
    "web_of_science": "No subscription and no API key.",
    "acm_dl": "HTTP 403 from this host. Metadata still reached via OpenAlex/Crossref.",
    "sciencedirect": "HTTP 403 from this host. Metadata still reached via OpenAlex/Crossref.",
    "google_scholar": "Reachable but captchas under programmatic load; excluded to avoid an unreproducible export.",
}


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return sha256_file(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.literature.discover")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        help="Output directory. Defaults to <run_dir>/literature on the persist root.",
    )
    parser.add_argument("--per-page", type=int, default=50)
    parser.add_argument(
        "--limit-queries", type=int, default=0, help="Smoke mode: first N queries only."
    )
    parser.add_argument(
        "--skip-best-effort",
        action="store_true",
        help="Skip rate-limited best-effort sources (still logged as skipped).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    repo_root = args.config.resolve().parent.parent

    out_dir = args.out or (cfg.layout.run_dir(cfg.run_id) / "literature")
    raw_dir = out_dir / "literature_raw_export"
    out_dir.mkdir(parents=True, exist_ok=True)

    queries_path = repo_root / cfg.get(
        "literature.seed_queries_file",
        "contracts/paper_reset/05_LITERATURE_SEARCH_STRINGS.md",
    )
    queries = load_queries(queries_path)
    if args.limit_queries:
        queries = queries[: args.limit_queries]
    token_df = token_document_frequency(queries)

    planned = dict(DISCOVERY_SOURCES) | dict(SUPPLEMENTARY_SOURCES)
    if not args.skip_best_effort:
        planned |= dict(BEST_EFFORT_SOURCES)

    log_rows: list[SearchLogEntry] = []
    records: list[LiteratureRecord] = []
    per_source_counts: dict[str, dict[str, int]] = {}

    for name, source_cls in planned.items():
        kwargs = {"per_page": args.per_page}
        if name == "arxiv":
            kwargs["token_df"] = token_df
        source = source_cls(**kwargs)
        ok = failed = returned = 0
        for query in queries:
            result = source.search(query)
            export = raw_dir / name / f"{query.query_id}.json"
            export.parent.mkdir(parents=True, exist_ok=True)
            payload = result.raw if result.raw is not None else {"error": result.log.note}
            if isinstance(payload, str):
                export = export.with_suffix(".xml")
                export.write_text(payload, encoding="utf-8")
            else:
                export.write_text(
                    json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8"
                )
            result.log.raw_export = str(export.relative_to(out_dir))
            log_rows.append(result.log)
            records.extend(result.records)
            if result.log.note.startswith("UNAVAILABLE"):
                failed += 1
            else:
                ok += 1
                returned += result.log.returned_count
            print(
                f"  {name:17s} {query.query_id} http={result.log.http_status} "
                f"got={result.log.returned_count}",
                flush=True,
            )
        per_source_counts[name] = {
            "queries_ok": ok,
            "queries_failed": failed,
            "records_returned": returned,
        }

    # Databases the contract names but this host cannot reach.
    for db, reason in UNREACHABLE_DATABASES.items():
        log_rows.append(
            SearchLogEntry(
                database=db,
                query_id="ALL",
                query_text="(entire frozen query set)",
                executed_query="",
                search_date=utc_stamp()[:8],
                http_status="UNAVAILABLE",
                reported_total=None,
                returned_count=0,
                raw_export="",
                query_adaptation="",
                note=f"UNAVAILABLE: {reason}",
            )
        )
    if args.skip_best_effort:
        for db in BEST_EFFORT_SOURCES:
            log_rows.append(
                SearchLogEntry(
                    database=db,
                    query_id="ALL",
                    query_text="(entire frozen query set)",
                    executed_query="",
                    search_date=utc_stamp()[:8],
                    http_status="SKIPPED",
                    reported_total=None,
                    returned_count=0,
                    raw_export="",
                    query_adaptation=QUERY_ADAPTATIONS.get(db, ""),
                    note=(
                        "SKIPPED: --skip-best-effort. Measured HTTP 429 on 3 probe "
                        "queries at 3.5 s spacing with 4 retries; the unauthenticated "
                        "shared pool is exhausted from this host. Set "
                        "SEMANTIC_SCHOLAR_API_KEY and re-run to include it. Its "
                        "absence is a coverage limitation, not a zero-result search."
                    ),
                )
            )

    deduped = deduplicate(records)
    deduped.sort(key=lambda r: (-(r.cited_by_count or 0), r.title.casefold()))

    log_sha = write_csv(
        out_dir / "literature_search_log.csv",
        SEARCH_LOG_COLUMNS,
        [entry.as_csv_row() for entry in log_rows],
    )
    lib_sha = write_csv(
        out_dir / "literature_deduplicated_library.csv",
        CSV_COLUMNS,
        [record.as_csv_row() for record in deduped],
    )
    avail_sha = write_csv(
        out_dir / "database_availability.csv",
        ("database", "role", "status", "queries_ok", "queries_failed", "records_returned", "note"),
        [
            {
                "database": name,
                "role": (
                    "discovery"
                    if name in DISCOVERY_SOURCES
                    else "supplementary" if name in SUPPLEMENTARY_SOURCES else "best_effort"
                ),
                "status": "OK" if counts["queries_ok"] else "UNAVAILABLE",
                "queries_ok": counts["queries_ok"],
                "queries_failed": counts["queries_failed"],
                "records_returned": counts["records_returned"],
                "note": QUERY_ADAPTATIONS.get(name, ""),
            }
            for name, counts in per_source_counts.items()
        ]
        + [
            {
                "database": db,
                "role": "contract_named",
                "status": "UNAVAILABLE",
                "queries_ok": 0,
                "queries_failed": 0,
                "records_returned": 0,
                "note": reason,
            }
            for db, reason in UNREACHABLE_DATABASES.items()
        ],
    )

    summary = {
        "run_id": cfg.run_id,
        "phase": "L1_discovery",
        "generated_utc": utc_stamp(),
        "query_set_version": QUERY_SET_VERSION,
        "queries_executed": len(queries),
        "sources_executed": sorted(planned),
        "records_raw": len(records),
        "records_deduplicated": len(deduped),
        "discovery_threshold": cfg.get("literature.discovery_min"),
        "discovery_threshold_met": len(deduped) >= int(cfg.get("literature.discovery_min", 0)),
        "per_source": per_source_counts,
        "unreachable_databases": UNREACHABLE_DATABASES,
        "outputs": {
            "literature_search_log.csv": log_sha,
            "literature_deduplicated_library.csv": lib_sha,
            "database_availability.csv": avail_sha,
        },
    }
    (out_dir / "discovery_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print(f"queries          {len(queries)}")
    print(f"raw records      {len(records)}")
    print(f"deduplicated     {len(deduped)}  (threshold {summary['discovery_threshold']})")
    print(f"threshold met    {summary['discovery_threshold_met']}")
    print(f"outputs          {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
