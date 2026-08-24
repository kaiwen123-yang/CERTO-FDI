"""Phase L500 step 3: join per-record screening decisions into the audited table.

The screening decisions are made record by record (title + abstract + venue)
by the executing reviewer and handed to this script as JSON batches::

    [{"record_id": "...", "decision": "INCLUDE_PRIORITY",
      "reason_code": "DIRECT_NEIGHBOR_CANDIDATE", "note": "...",
      "lineage_final": "L6_contact_collision_localization"}, ...]

This script only validates and joins -- it never invents or alters a decision.
Output: ``03_500_paper_screening.csv`` with one auditable row per screened
record. A record without a decision stays out of the output, so the screened
count is exactly the number of individually decided records.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

DECISIONS = {
    "INCLUDE_PRIORITY",     # direct-neighbor / killer-paper candidate
    "INCLUDE_FULLTEXT",     # relevant; feeds the 100-fulltext queue
    "INCLUDE_BACKGROUND",   # relevant context; not in the fulltext queue for now
    "EXCLUDE",
}
REASON_CODES = {
    "DIRECT_NEIGHBOR_CANDIDATE", "KILLER_CANDIDATE", "DATASET_OR_CODE_PAPER",
    "LINEAGE_QUOTA", "CLASSIC_ANCHOR", "METHOD_RELEVANT", "CONTEXT_RELEVANT",
    "NOT_ROBOT_DOMAIN", "NOT_FAULT_ANOMALY_TOPIC", "WRONG_OBJECT",
    "PROCESS_MACHINERY_ONLY", "SURVEY_TANGENTIAL", "VENUE_EXCLUDED_MDPI",
    "DUPLICATE_VARIANT", "METADATA_TOO_THIN", "PRE_WINDOW_NOT_CLASSIC",
    "OFF_TOPIC_OTHER",
}

OUT_COLUMNS = (
    "screen_seq", "record_id", "doi", "arxiv_id", "title", "authors", "year",
    "venue", "venue_tier", "lineages", "screen_score", "abstract_available",
    "decision", "reason_code", "note", "lineage_final", "screened_utc",
    "screener",
)


def apply(set_csv: Path, decisions_dir: Path, out_csv: Path, summary_json: Path) -> dict:
    with set_csv.open(encoding="utf-8") as fh:
        records = {r["record_id"]: r for r in csv.DictReader(fh)}

    decisions: dict[str, dict] = {}
    for path in sorted(decisions_dir.glob("batch_*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            rid = item["record_id"]
            if rid not in records:
                raise SystemExit(f"{path.name}: unknown record_id {rid}")
            if item["decision"] not in DECISIONS:
                raise SystemExit(f"{path.name}: bad decision {item['decision']}")
            if item["reason_code"] not in REASON_CODES:
                raise SystemExit(f"{path.name}: bad reason_code {item['reason_code']}")
            if rid in decisions and decisions[rid] != item:
                raise SystemExit(f"{path.name}: conflicting duplicate for {rid}")
            item["_source_batch"] = path.name
            decisions[rid] = item

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_rows = []
    for rid, dec in decisions.items():
        r = records[rid]
        out_rows.append({
            "record_id": rid,
            "doi": r.get("doi", ""),
            "arxiv_id": r.get("arxiv_id", ""),
            "title": r.get("title", ""),
            "authors": r.get("authors", ""),
            "year": r.get("year", ""),
            "venue": r.get("venue", ""),
            "venue_tier": r.get("venue_tier", ""),
            "lineages": r.get("lineages", ""),
            "screen_score": r.get("screen_score", ""),
            "abstract_available": "true" if r.get("abstract_text") else "false",
            "decision": dec["decision"],
            "reason_code": dec["reason_code"],
            "note": dec.get("note", ""),
            "lineage_final": dec.get("lineage_final", ""),
            "screened_utc": now,
            "screener": "claude_fable_5_paper_reset_v2",
        })
    out_rows.sort(key=lambda x: (-float(x["screen_score"] or 0), x["record_id"]))
    for seq, row in enumerate(out_rows, start=1):
        row["screen_seq"] = seq

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUT_COLUMNS)
        writer.writeheader()
        writer.writerows(out_rows)

    by_decision: dict[str, int] = {}
    for row in out_rows:
        by_decision[row["decision"]] = by_decision.get(row["decision"], 0) + 1
    summary = {
        "screened_total": len(out_rows),
        "screening_set_size": len(records),
        "undecided_remaining": len(records) - len(out_rows),
        "by_decision": by_decision,
        "written_utc": now,
        "output": str(out_csv),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.set, args.decisions, args.out, args.summary), indent=2))
