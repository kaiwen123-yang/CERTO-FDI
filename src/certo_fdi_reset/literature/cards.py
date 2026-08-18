"""Roll the full-text method cards up into the evidence and occupancy matrices.

The cards are the primary record; these matrices are derived views of them, so
the occupancy picture can never drift from what the cards actually say. Only
evidence levels A1, A2 and B1 may carry an occupancy verdict
(``04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md`` §7.2) -- a card written at
level C or FULLTEXT_UNAVAILABLE is counted as discovery, never as coverage.

    python -m certo_fdi_reset.literature.cards --config configs/paper_reset.yaml
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import yaml

from ..config import load_config

CLAIMS = ("C1", "C2", "C3", "C4", "C5", "C6")
OCCUPANCY_CAPABLE_LEVELS = frozenset({"A1", "A2", "B1"})
VERDICTS = ("OCCUPIED", "PARTIALLY_OCCUPIED", "PLAUSIBLY_OPEN", "UNKNOWN", "FALSELY_FRAMED")

#: Strongest verdict first: the roll-up reports the strongest verdict any
#: full-text card assigns, because one occupying paper is enough to occupy.
VERDICT_RANK = {v: i for i, v in enumerate(VERDICTS)}


def load_cards(cards_dir: Path) -> list[dict]:
    cards: list[dict] = []
    for path in sorted(cards_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"```yaml\n(.*?)```", text, re.S)
        if not match:
            continue
        data = yaml.safe_load(match.group(1))
        data["_path"] = str(path)
        cards.append(data)
    return cards


def strongest(verdicts: list[str]) -> str:
    ranked = sorted((v for v in verdicts if v in VERDICT_RANK), key=lambda v: VERDICT_RANK[v])
    return ranked[0] if ranked else "UNKNOWN"


def evidence_rows(cards: list[dict]) -> list[dict]:
    rows = []
    for card in cards:
        row = {
            "paper_id": card.get("paper_id", ""),
            "evidence_level": card.get("evidence_level", ""),
            "venue": card.get("venue", ""),
            "year": card.get("canonical_citation_year") or card.get("year", ""),
            "occupancy_capable": str(card.get("evidence_level") in OCCUPANCY_CAPABLE_LEVELS).lower(),
            "fixed_or_floating_base": card.get("fixed_or_floating_base", ""),
            "healthy_only": str((card.get("training") or {}).get("healthy_only", "")),
            "killer_status": card.get("killer_status", ""),
            "killer_for_fdi_story": str(card.get("killer_for_fdi_story", "")),
            "novelty_status": card.get("novelty_status", ""),
            "confidence": card.get("confidence", ""),
            "pages_read": card.get("pages_actually_read", ""),
        }
        collisions = card.get("collision_with_claims") or {}
        for claim in CLAIMS:
            row[claim] = collisions.get(claim, "")
        rows.append(row)
    return rows


def render_matrix(cards: list[dict], rows: list[dict]) -> str:
    capable = [r for r in rows if r["occupancy_capable"] == "true"]
    lines = [
        "# Nearest-neighbour and occupancy matrix — Wave A (partial)",
        "",
        f"Cards written: **{len(rows)}**. Of these, **{len(capable)}** are at evidence level "
        "A1/A2/B1 and may carry an occupancy verdict under §7.2; the rest count only as discovery.",
        "",
        "## Per-claim occupancy, from full-text cards only",
        "",
        "| claim | strongest verdict | papers occupying | papers partially occupying |",
        "| --- | --- | --- | --- |",
    ]
    for claim in CLAIMS:
        verdicts = [r[claim] for r in capable if r[claim]]
        occ = [r["paper_id"] for r in capable if r[claim] == "OCCUPIED"]
        part = [r["paper_id"] for r in capable if r[claim] == "PARTIALLY_OCCUPIED"]
        lines.append(
            f"| {claim} | **{strongest(verdicts)}** | {', '.join(occ) or '—'} | {', '.join(part) or '—'} |"
        )
    lines += [
        "",
        "## Per-paper summary",
        "",
        "| paper | level | base | healthy-only | killer status | " + " | ".join(CLAIMS) + " |",
        "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in CLAIMS) + " |",
    ]
    for r in rows:
        lines.append(
            f"| {r['paper_id']} | {r['evidence_level']} | {r['fixed_or_floating_base']} | "
            f"{r['healthy_only']} | {r['killer_status']} | "
            + " | ".join(r[c] or "—" for c in CLAIMS)
            + " |"
        )
    killers = [c for c in cards if c.get("killer_for_fdi_story") is True]
    lines += [
        "",
        "## Killer papers for the FDI story",
        "",
        (
            "**None so far.** "
            if not killers
            else "".join(f"- {c['paper_id']}\n" for c in killers)
        ),
        "",
        "This is a statement about the cards written so far, not a conclusion: 7 of the 15 Wave A",
        "targets have no card yet, and 5 of those are metadata-only at publishers that refuse this",
        "host. §7.2 forbids reading a missing full text as evidence that no competitor exists.",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.literature.cards")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--cards-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    cards_dir = args.cards_dir or (cfg.layout.research_docs / "literature" / "fulltext_method_cards")
    out_dir = cfg.layout.research_docs / "literature"
    out_dir.mkdir(parents=True, exist_ok=True)

    cards = load_cards(cards_dir)
    if not cards:
        print(f"No method cards found in {cards_dir}")
        return 1
    rows = evidence_rows(cards)

    csv_path = out_dir / "fulltext_evidence_matrix.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    matrix_path = out_dir / "nearest_neighbor_matrix.md"
    matrix_path.write_text(render_matrix(cards, rows), encoding="utf-8")

    capable = sum(1 for r in rows if r["occupancy_capable"] == "true")
    print(f"cards              {len(rows)} (occupancy-capable: {capable})")
    for claim in CLAIMS:
        verdicts = [r[claim] for r in rows if r["occupancy_capable"] == "true" and r[claim]]
        print(f"  {claim}  {strongest(verdicts)}")
    print(f"evidence matrix    {csv_path}")
    print(f"nearest-neighbour  {matrix_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
