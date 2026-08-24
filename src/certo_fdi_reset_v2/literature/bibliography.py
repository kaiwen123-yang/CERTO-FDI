"""Emit 02_verified_bibliography.bib from the V1+V2 method cards.

Each entry corresponds to one full text actually held and carded; the bib key
is the card's paper_id, the `note` field carries the evidence level and card
path so every citation is traceable to its audit artifact.
"""

from __future__ import annotations

import re
from pathlib import Path

V2_CARDS = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2/literature/fulltext_method_cards")
V1_CARDS = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset/literature/fulltext_method_cards")
OUT = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2/literature/02_verified_bibliography.bib")


def _grab(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+?)\s*$", text, re.M)
    return (m.group(1).strip().strip('"') if m else "").replace("{", "(").replace("}", ")")


def main() -> int:
    entries = []
    seen = set()
    for src in (V2_CARDS, V1_CARDS):
        if not src.is_dir():
            continue
        for path in sorted(src.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            pid = _grab(text, "paper_id") or path.stem
            if pid in seen:
                continue
            seen.add(pid)
            cite = _grab(text, "full_citation")
            doi = _grab(text, "doi")
            year = _grab(text, "year") or _grab(text, "canonical_citation_year")
            venue = _grab(text, "venue")
            level = _grab(text, "evidence_level")
            entry = "@misc{%s,\n" % pid
            entry += f"  note = {{{cite}}},\n"
            if venue:
                entry += f"  howpublished = {{{venue}}},\n"
            if year:
                entry += f"  year = {{{year}}},\n"
            if doi:
                entry += f"  doi = {{{doi}}},\n"
            entry += f"  annote = {{evidence_level={level}; card={path.name}}}\n}}\n"
            entries.append(entry)
    OUT.write_text("\n".join(entries), encoding="utf-8")
    print(f"wrote {OUT} with {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
