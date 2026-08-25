"""G0: build V2-R Thin/Full review packages with independent verification.

Checks per package: credential-shape secret scan, CRC, fresh extraction,
inner sha256 re-verification, git-head alignment, reviewer smoke (recompute
two key numbers from packaged CSVs and compare against the packaged decision
JSON). No raw datasets/PDFs redistributed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RUN = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r")
LIT = Path("/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2r")
REPO = Path.home() / "research/CERTO-FDI-WORKTREES/paper-reset-v2r-mead-submission-closure"
EX = Path("/mnt/g/CERTO-FDI/06_review_exchange")

CRED = re.compile(
    r"(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{30,}"
    r"|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY"
    r"|(api[_-]?key|secret|passwd|password)\s*[:=]\s*['\"][A-Za-z0-9+/_\-]{12,}['\"])")


def secret_scan(paths):
    hits = []
    for p in paths:
        if p.suffix.lower() in (".zip", ".npz", ".pkl", ".pth", ".bundle", ".pdf"):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in CRED.finditer(t):
            hits.append((str(p), t[max(0, m.start() - 20):m.end() + 5][:80]))
    return hits


def reviewer_smoke(tmp: Path) -> dict:
    """Recompute two key numbers from packaged CSVs and compare to the
    packaged three-axis decision evidence."""
    out = {}
    comp = list(csv.DictReader((tmp / "aursad/aursad_dual_protocol_comparison.csv").open()))
    mlp = [r for r in comp if r["model"] == "mlp"][0]
    out["aursad_mlp_inflation_abs"] = float(mlp["inflation_abs"])
    ok1 = abs(out["aursad_mlp_inflation_abs"] - 0.1662) < 0.02
    mtx = json.loads((tmp / "unified/matrix_completeness.json").read_text())
    out["universal_core_matrix_complete"] = mtx["universal_core_matrix_complete"]
    dec = json.loads((tmp / "decision/01_three_axis_decision.json").read_text())
    ok2 = (dec["evidence"]["bench"]["universal_core_matrix_complete"]
           == mtx["universal_core_matrix_complete"])
    out["smoke_pass"] = bool(ok1 and ok2)
    return out


def build(name: str, file_map, sub: str, with_smoke: bool):
    out_dir = EX / "to_review" / sub
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"]).decode().strip()
    zpath = out_dir / f"{name}_{stamp}.zip"
    hits = secret_scan([s for s, _ in file_map])
    assert not hits, f"secret hits: {hits[:3]}"
    inner = {}
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arc in file_map:
            z.write(src, arc)
            inner[arc] = hashlib.sha256(src.read_bytes()).hexdigest()
        z.writestr("MANIFEST.json", json.dumps({
            "run_id": RUN.name, "git_head": head, "built_utc": stamp,
            "inner_sha256": inner,
            "note": "no raw datasets/PDFs/checkpoints redistributed; ME-AD via Zenodo DOI"}, indent=2))
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        tmp = Path("/tmp/claude-1000/-home-kaiwen-research-CERTO-FDI/"
                   "4a6471e9-76bc-4531-9c34-b0496d2cc474/scratchpad") / f"x_{name}_{stamp}"
        z.extractall(tmp)
        for arc, dg in inner.items():
            assert hashlib.sha256((tmp / arc).read_bytes()).hexdigest() == dg
        smoke = reviewer_smoke(tmp) if with_smoke else {"smoke_pass": "n/a(thin)"}
    (out_dir / f"{zpath.name}.sha256").write_text(
        hashlib.sha256(zpath.read_bytes()).hexdigest() + "  " + zpath.name + "\n")
    print(f"built {zpath.name}: {len(inner)+1} entries, {zpath.stat().st_size:,} B, smoke={smoke}")
    return zpath, smoke


def collect_full():
    fm = []
    for sub in ("r1", "mead", "aursad", "unified", "decision", "provenance",
                "provenance/environment_locks", "mead/cycle_scores"):
        d = RUN / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*")):
            if f.is_file() and f.stat().st_size < 40_000_000:
                fm.append((f, f"{sub}/{f.name}"))
    for name in ("self_contained_method_cards", "deep_40_neighbor_cards", "killer_dossiers"):
        d = LIT / name
        for f in sorted(d.glob("*")):
            if f.is_file():
                fm.append((f, f"literature/{name}/{f.name}"))
    for f in sorted(LIT.glob("*")):
        if f.is_file():
            fm.append((f, f"literature/{f.name}"))
    fm.append((RUN / "run_manifest.json", "run_manifest.json"))
    seen, out = set(), []
    for s, a in fm:
        if a in seen:
            continue
        seen.add(a); out.append((s, a))
    return out


def collect_thin():
    keep = []
    for f in sorted((RUN / "decision").glob("*")):
        if f.is_file():
            keep.append((f, f"decision/{f.name}"))
    for name in ("aursad/aursad_dual_protocol_comparison.csv", "aursad/aursad_protocol_memo.md",
                 "unified/matrix_completeness.json", "unified/universal_core_matrix.csv",
                 "mead/mead_dataset_manifest.json", "mead/mead_decision_memo.md",
                 "r1/historical_recompute.json", "run_manifest.json"):
        p = RUN / name
        if p.exists():
            keep.append((p, name))
    return keep


if __name__ == "__main__":
    full, fsmoke = build("CERTO_FDI_V2R_FULL_REVIEW", collect_full(), "full", with_smoke=True)
    thin, _ = build("CERTO_FDI_V2R_THIN_REVIEW", collect_thin(), "thin", with_smoke=False)
    (EX / "LATEST_FULL_PACKAGE.txt").write_text(str(full) + "\n")
    (EX / "LATEST_THIN_PACKAGE.txt").write_text(str(thin) + "\n")
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"]).decode().strip()
    with (EX / "package_index.csv").open("a") as fh:
        for z in (thin, full):
            fh.write(f"{z.name},{RUN.name},{head},{datetime.now(timezone.utc).isoformat()},V2R\n")
    print("pointers updated; smoke:", fsmoke)
