"""Build 04_100_fulltext_evidence_matrix.csv from the V2 method cards.

Each card is a Markdown file with one ```yaml block. Reviewers vary in exact
fields; this extracts the shared audit spine and never invents a value —
missing keys are left empty. V1 cards (10) are folded in from the V1 card
directory so the 100-fulltext count is a single auditable table.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

V2_CARDS = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2/literature/fulltext_method_cards")
V1_CARDS = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset/literature/fulltext_method_cards")
OUT = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2/literature/04_100_fulltext_evidence_matrix.csv")

KEYS = (
    "paper_id", "venue", "year", "formal_status", "doi", "evidence_level",
    "healthy_only", "real_robot", "novelty_status", "kills_which_candidate",
    "reviewer", "fulltext_read_date", "pages_actually_read", "confidence",
)


def _grab(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+?)\s*$", text, re.M)
    if not m:
        return ""
    val = m.group(1).strip().strip('"')
    return re.sub(r"\s+", " ", val)[:300]


def build() -> dict:
    rows = []
    for src, origin in ((V2_CARDS, "v2"), (V1_CARDS, "v1")):
        if not src.is_dir():
            continue
        for path in sorted(src.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            row = {k: _grab(text, k) for k in KEYS}
            row["paper_id"] = row["paper_id"] or path.stem
            row["card_origin"] = origin
            row["card_path"] = str(path)
            rows.append(row)
    seen: dict[str, dict] = {}
    for row in rows:  # v2 sorts first; keep first occurrence per paper_id
        seen.setdefault(row["paper_id"], row)
    out_rows = list(seen.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(KEYS) + ["card_origin", "card_path"])
        writer.writeheader()
        writer.writerows(out_rows)
    counts = {
        "cards_total": len(out_rows),
        "v2": sum(1 for r in out_rows if r["card_origin"] == "v2"),
        "v1": sum(1 for r in out_rows if r["card_origin"] == "v1"),
        "by_novelty": {},
    }
    for r in out_rows:
        k = r["novelty_status"].split(" ")[0] if r["novelty_status"] else "UNSET"
        counts["by_novelty"][k] = counts["by_novelty"].get(k, 0) + 1
    return counts


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
