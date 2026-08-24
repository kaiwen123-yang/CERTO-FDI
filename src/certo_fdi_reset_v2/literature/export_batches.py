"""Print one screening batch in compact reviewer form.

Each line: ``rank|record_id|year|tier|venue|lineage_codes|title`` followed by a
truncated abstract line (or ``[no abstract]``). The reviewer reads every record
and emits a decision JSON; nothing here decides anything.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

BATCH = 40
ABS_WORDS = 60

LIN_SHORT = {
    "L2_manipulator_actuator_sensor_fdi": "FDI",
    "L3_learned_momentum_observer": "MOB",
    "L4_structured_chain_graph_dynamics": "CHAIN",
    "L5_lie_geometry_equivariant": "LIE",
    "L6_contact_collision_localization": "CONTACT",
    "L7_mtsad_context_ood_sequential": "MTSAD",
    "L8_public_benchmarks_transfer": "BENCH",
    "L9_foundation_multimodal": "FOUND",
    "L10_cross_robot_few_shot": "XROBOT",
    "L11_active_diagnosis": "ACTIVE",
    "L_killer_precision": "KILLER",
    "L_recent_2025_2026": "R25",
}


def main(set_csv: Path, batch_no: int) -> None:
    with set_csv.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    start = (batch_no - 1) * BATCH
    chunk = rows[start : start + BATCH]
    if not chunk:
        print(f"BATCH {batch_no}: EMPTY (total rows {len(rows)})")
        return
    print(f"BATCH {batch_no}: rows {start + 1}-{start + len(chunk)} of {len(rows)}")
    for r in chunk:
        lins = ",".join(
            sorted({LIN_SHORT.get(l.strip(), l.strip()) for l in (r.get("lineages") or "").replace("; ", ";").split(";") if l.strip()})
        )
        print(f"@{r['screen_rank']}|{r['record_id'][:60]}|{r.get('year','')}|{r.get('venue_tier','')}|{(r.get('venue') or '')[:40]}|{lins}")
        title = " ".join((r.get("title") or "").split())
        print(f"  T: {title[:220]}")
        abstract = " ".join((r.get("abstract_text") or "").split())
        if abstract:
            words = abstract.split()
            print(f"  A: {' '.join(words[:ABS_WORDS])}{'…' if len(words) > ABS_WORDS else ''}")
        else:
            print("  A: [no abstract]")


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]))
