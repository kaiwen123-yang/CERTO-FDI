"""Phase L500 step 2: deterministic pre-ranking and screening-set construction.

Selects the records that receive an individual title/abstract screening
decision. The ranking is a frozen, reproducible function of the pool row --
it never decides inclusion in the review; it only decides which records are
*worth a human-auditable look*, with quota floors per lineage so no contract
4.3 lineage is starved by a globally popular one. The per-record decisions
themselves are made downstream (apply_screening.py) and are the auditable
artifact the 500-screen gate counts.

Abstract enrichment: OpenAlex batch-by-DOI (abstract_inverted_index unfolded),
then arXiv by id for DOI-less preprints. Missing abstracts are recorded as
missing -- screening such a record leans on title/venue only and its decision
says so.
"""

from __future__ import annotations

import csv
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from certo_fdi_reset.literature.sources import CONTACT_EMAIL, USER_AGENT

# --- Frozen venue tiers (contract 4.4) ---
TIER_S_PAT = re.compile(
    r"science robotics|nature machine intelligence|nature communications|science advances",
    re.I,
)
TIER_R_PAT = re.compile(
    r"transactions on robotics|international journal of robotics research|"
    r"robotics: science and systems|robotics and automation letters|"
    r"international conference on robotics and automation|\bicra\b|\biros\b|"
    r"intelligent robots and systems|conference on robot learning|\bcorl\b",
    re.I,
)
TIER_C_PAT = re.compile(
    r"automatica|transactions on automatic control|transactions on mechatronics|"
    r"transactions on industrial electronics|transactions on automation science|"
    r"mechanical systems and signal processing|neurips|neural information processing|"
    r"international conference on machine learning|\bicml\b|\biclr\b|aistats|"
    r"learning for dynamics|l4dc|transactions on industrial informatics",
    re.I,
)
MDPI_VENUES = {
    "sensors", "machines", "electronics", "applied sciences", "actuators",
    "robotics", "mathematics", "symmetry", "entropy", "micromachines",
    "processes", "algorithms", "aerospace", "drones", "designs", "computation",
}

LINEAGE_WEIGHT = {
    "L_killer_precision": 5.0,
    "L2_manipulator_actuator_sensor_fdi": 4.0,
    "L3_learned_momentum_observer": 4.0,
    "L6_contact_collision_localization": 4.0,
    "L8_public_benchmarks_transfer": 4.0,
    "L5_lie_geometry_equivariant": 3.0,
    "L4_structured_chain_graph_dynamics": 3.0,
    "L9_foundation_multimodal": 3.0,
    "L10_cross_robot_few_shot": 3.5,
    "L11_active_diagnosis": 3.0,
    "L7_mtsad_context_ood_sequential": 2.0,
    "L_recent_2025_2026": 1.0,
}

# Per-lineage floors for the screening set: every contract 4.3 lineage gets at
# least this many candidate rows in front of the screener.
LINEAGE_FLOOR = {
    "L2_manipulator_actuator_sensor_fdi": 60,
    "L3_learned_momentum_observer": 45,
    "L4_structured_chain_graph_dynamics": 40,
    "L5_lie_geometry_equivariant": 45,
    "L6_contact_collision_localization": 50,
    "L7_mtsad_context_ood_sequential": 40,
    "L8_public_benchmarks_transfer": 45,
    "L9_foundation_multimodal": 30,
    "L10_cross_robot_few_shot": 30,
    "L11_active_diagnosis": 25,
}

ROBOT_PAT = re.compile(
    r"robot|manipulat|\barm\b|end.?effector|cobot|\bur5\b|\bur5e\b|\bur10\b|"
    r"kuka|franka|panda\b|sawyer|screwdriv|joint torque|propriocepti", re.I,
)
FAULT_PAT = re.compile(
    r"fault|anomal|collision|contact detect|fdi\b|diagnos|health|degradat|"
    r"novelty detect|out.?of.?distribution|\bood\b|monitor", re.I,
)
DATASET_PAT = re.compile(
    r"voraus|\bAURSAD\b|\bRoAD\b|screwdriv|\bUR5e\b|robot anomaly dataset|"
    r"anomaly detection dataset.*robot|robot.*anomaly.*benchmark",
)
WINDOW_START = 2021


def venue_tier(venue: str, publisher: str) -> str:
    v = venue or ""
    if TIER_S_PAT.search(v):
        return "S"
    if TIER_R_PAT.search(v):
        return "R"
    if TIER_C_PAT.search(v):
        return "C"
    if "mdpi" in (publisher or "").lower() or v.strip().lower() in MDPI_VENUES:
        return "MDPI"
    return "other"


def score_row(row: dict) -> float:
    lineages = [s for s in (row.get("lineages") or "").replace("; ", ";").split(";") if s]
    score = sum(LINEAGE_WEIGHT.get(l, 0.0) for l in lineages)
    if len([l for l in lineages if l != "L_recent_2025_2026"]) >= 2:
        score += 2.0
    tier = venue_tier(row.get("venue", ""), row.get("publisher", ""))
    score += {"S": 2.0, "R": 2.5, "C": 1.5, "MDPI": -2.0, "other": 0.0}[tier]
    cited = row.get("cited_by_count") or ""
    if cited.strip().isdigit():
        score += min(2.5, 0.6 * math.log1p(int(cited)))
    title = row.get("title", "")
    robot = bool(ROBOT_PAT.search(title))
    fault = bool(FAULT_PAT.search(title))
    if robot and fault:
        score += 4.0
    elif robot or fault:
        score += 1.0
    if DATASET_PAT.search(title):
        score += 3.0
    year = row.get("year") or ""
    if year.strip().isdigit() and int(year) >= 2025:
        score += 0.5
    return round(score, 3)


def build_screening_set(pool_csv: Path, out_csv: Path, summary_json: Path,
                        target_size: int = 640, classics_track: int = 40) -> dict:
    with pool_csv.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    for row in rows:
        row["_score"] = score_row(row)
        row["_tier"] = venue_tier(row.get("venue", ""), row.get("publisher", ""))
        y = (row.get("year") or "").strip()
        row["_year"] = int(y) if y.isdigit() else None

    in_window = [r for r in rows if r["_year"] is not None and r["_year"] >= WINDOW_START]
    pre_window = [r for r in rows if r["_year"] is not None and r["_year"] < WINDOW_START]

    selected: dict[str, dict] = {}

    def take(row: dict, why: str) -> None:
        rid = row["record_id"]
        if rid not in selected:
            row["_selection_reason"] = why
            selected[rid] = row

    # 1. Every in-window record that names a mandatory/supplementary dataset.
    for row in in_window:
        if DATASET_PAT.search(row.get("title", "")):
            take(row, "names_target_dataset")

    # 2. Lineage floors, best-scored first within each lineage.
    for lineage, floor in LINEAGE_FLOOR.items():
        members = sorted(
            (r for r in in_window if lineage in (r.get("lineages") or "")),
            key=lambda r: -r["_score"],
        )
        for row in members[:floor]:
            take(row, f"lineage_floor:{lineage}")

    # 3. Global top-up to target_size.
    for row in sorted(in_window, key=lambda r: -r["_score"]):
        if len(selected) >= target_size:
            break
        take(row, "global_rank")

    # 4. Classics track: pre-window, citation-anchored, core lineages only.
    core = ("L2_", "L3_", "L5_", "L6_", "L_killer")
    classics = sorted(
        (
            r for r in pre_window
            if any(c in (r.get("lineages") or "") for c in core)
            and (r.get("cited_by_count") or "").strip().isdigit()
        ),
        key=lambda r: -int(r["cited_by_count"]),
    )
    for row in classics[:classics_track]:
        take(row, "classics_candidate")

    out = sorted(selected.values(), key=lambda r: -r["_score"])
    fields = list(csv.DictReader(pool_csv.open(encoding="utf-8")).fieldnames) + [
        "screen_rank", "screen_score", "venue_tier", "selection_reason", "abstract_text",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for rank, row in enumerate(out, start=1):
            row = dict(row)
            row["screen_rank"] = rank
            row["screen_score"] = row.pop("_score")
            row["venue_tier"] = row.pop("_tier")
            row["selection_reason"] = row.pop("_selection_reason")
            row["abstract_text"] = ""
            writer.writerow(row)

    summary = {
        "executed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pool_records": len(rows),
        "in_window_2021plus": len(in_window),
        "screening_set": len(out),
        "by_selection_reason": {},
        "by_tier": {},
    }
    for row in out:
        why = row["selection_reason"] if "selection_reason" in row else row.get("_selection_reason", "")
        summary["by_selection_reason"][why.split(":")[0]] = (
            summary["by_selection_reason"].get(why.split(":")[0], 0) + 1
        )
        tier = row.get("venue_tier", row.get("_tier", ""))
        summary["by_tier"][tier] = summary["by_tier"].get(tier, 0) + 1
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


# ---------------------------------------------------------------- abstracts --

def _unfold(inv: dict) -> str:
    slots: dict[int, str] = {}
    for word, positions in (inv or {}).items():
        for p in positions:
            slots[p] = word
    return " ".join(slots[i] for i in sorted(slots))


def enrich_abstracts(set_csv: Path, summary_json: Path, batch: int = 40) -> dict:
    """Fill abstract_text in place: OpenAlex by DOI, then arXiv by id."""
    with set_csv.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    doi_rows = [r for r in rows if r.get("doi") and not r["abstract_text"]]
    fetched_oa = 0
    for i in range(0, len(doi_rows), batch):
        chunk = doi_rows[i : i + batch]
        flt = "doi:" + "|".join(r["doi"] for r in chunk)
        try:
            resp = session.get(
                "https://api.openalex.org/works",
                params={"filter": flt, "per-page": batch,
                        "select": "doi,abstract_inverted_index", "mailto": CONTACT_EMAIL},
                timeout=60,
            )
        except requests.RequestException:
            time.sleep(3)
            continue
        if resp.status_code != 200:
            time.sleep(3)
            continue
        by_doi = {}
        for work in resp.json().get("results", []):
            doi = (work.get("doi") or "").replace("https://doi.org/", "").lower()
            text = _unfold(work.get("abstract_inverted_index"))
            if text:
                by_doi[doi] = text
        for r in chunk:
            key = r["doi"].replace("https://doi.org/", "").lower()
            if key in by_doi:
                r["abstract_text"] = by_doi[key]
                fetched_oa += 1
        print(f"[abs] openalex {i + len(chunk)}/{len(doi_rows)} filled={fetched_oa}", flush=True)
        time.sleep(0.2)

    arxiv_rows = [r for r in rows if r.get("arxiv_id") and not r["abstract_text"]]
    fetched_ax = 0
    for i in range(0, len(arxiv_rows), 50):
        chunk = arxiv_rows[i : i + 50]
        ids = ",".join(r["arxiv_id"].split("v")[0] for r in chunk)
        try:
            resp = session.get(
                "http://export.arxiv.org/api/query",
                params={"id_list": ids, "max_results": len(chunk)},
                timeout=60,
            )
        except requests.RequestException:
            time.sleep(4)
            continue
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET

            ns = {"a": "http://www.w3.org/2005/Atom"}
            try:
                root = ET.fromstring(resp.text)
            except ET.ParseError:
                root = None
            if root is not None:
                by_id = {}
                for entry in root.findall("a:entry", ns):
                    eid = (entry.findtext("a:id", namespaces=ns) or "").rsplit("/", 1)[-1]
                    summary = " ".join((entry.findtext("a:summary", namespaces=ns) or "").split())
                    by_id[eid.split("v")[0]] = summary
                for r in chunk:
                    key = r["arxiv_id"].split("v")[0]
                    if by_id.get(key):
                        r["abstract_text"] = by_id[key]
                        fetched_ax += 1
        print(f"[abs] arxiv {i + len(chunk)}/{len(arxiv_rows)} filled={fetched_ax}", flush=True)
        time.sleep(3.2)

    with set_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    have = sum(1 for r in rows if r["abstract_text"])
    summary = {
        "rows": len(rows),
        "abstracts_filled": have,
        "from_openalex": fetched_oa,
        "from_arxiv": fetched_ax,
        "missing": len(rows) - have,
    }
    prev = json.loads(summary_json.read_text()) if summary_json.exists() else {}
    prev["abstract_enrichment"] = summary
    summary_json.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--enrich", action="store_true")
    args = parser.parse_args()

    if not args.enrich:
        print(json.dumps(build_screening_set(args.pool, args.out, args.summary), indent=2))
    else:
        print(json.dumps(enrich_abstracts(args.out, args.summary), indent=2))
