"""Stage 2B-F Phase 0: input, Git and data provenance, recomputed from disk.

Every hash here is recomputed from the bytes on disk. A run's own record of what it hashed is not
evidence about that run, so none of the frozen runs' self-reported hashes are read.

Also records the baseline SHA256 of every historical artifact, so Phase 6 can prove Stage 2B-F did
not mutate one.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from certo_fdi.experiments.common import write_json
from certo_fdi.stage2bf import estimator_identity as EI
from certo_fdi.stage2bf.decision_stage2bf import sha256_file

PACKAGES = {
    "stage2a_full": ("full/CERTO_FDI_stage2a_chain_jacobian_pathway_AUDIT_20260816T075436Z_bcf2ad5_FULL.zip",
                     "stage2a_full_zip_sha256"),
    "stage2b_full": ("full/CERTO_FDI_stage2b_contact_loadpath_sequential_AUDIT_20260816T112827Z_bee5f9b_FULL.zip",
                     "stage2b_full_zip_sha256"),
    "stage2br_full": ("full/CERTO_FDI_stage2br_reproduction_gate_FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH_"
                      "20260817T042510Z_d947edb_FULL.zip", "stage2br_full_zip_sha256"),
}
HISTORICAL = {
    "stage2a": ["results/stage2a_localization_metrics.csv", "results/stage2a_decision_evidence.json",
                "p5_ablations/scores_seed260815.npz", "p5_ablations/scores_seed260816.npz",
                "p5_ablations/scores_seed260817.npz"],
    "stage2b": ["results/stage2b_decision_evidence.json", "results/stage2b_decision_memo.md",
                "results/stage2b_contact_reproduction_gate.json", "results/stage2b_reproduction_gate.json",
                "results/stage2b_localizer_selection.json", "results/stage2b_loadpath_controls.csv",
                "results/stage2b_input_freeze.json",
                "p1_loadpath/controls_seed260815.npz", "p1_loadpath/controls_seed260816.npz",
                "p1_loadpath/controls_seed260817.npz"],
    "stage2br": ["results/stage2br_reproduction_gate.json", "results/stage2br_execution_summary.md"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(repo: Path, *a: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *a], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def dataset_manifest(data_root: Path) -> tuple[str, int, int]:
    """Recompute the 590-episode content manifest, byte-identical construction to the frozen runs."""
    rows = list(csv.DictReader((data_root / "episode_index.csv").open(newline="", encoding="utf-8")))
    per = [(r["episode_id"], sha256_file(r["path"]) if Path(r["path"]).is_file() else "MISSING")
           for r in rows]
    joint = hashlib.sha256("\n".join(f"{e},{s}" for e, s in sorted(per)).encode()).hexdigest()
    return joint, len(per), sum(1 for _, s in per if s == "MISSING")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2B-F phase 0")
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()

    fcfg = yaml.safe_load(Path(args.config).read_text())
    repo = Path(args.repo_root).resolve()
    root = Path(args.run_root)
    res = root / "results"
    res.mkdir(parents=True, exist_ok=True)
    fi = fcfg["frozen_inputs"]
    exch = Path(fcfg["paths"]["review_exchange"])
    log: list[str] = []

    def say(m: str) -> None:
        line = f"[{utc_now()}] {m}"
        print(line, flush=True)
        log.append(line)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "logs" / "stage2bf_provenance.log").write_text("\n".join(log) + "\n", encoding="utf-8")

    say("Stage 2B-F Phase 0 start")

    # ---- /mnt/g must be a real mount, not a directory on the Linux root
    persistent = Path(fcfg["paths"]["persistent_root"])
    # the drive itself, e.g. /mnt/g -- not /mnt, which is part of the Linux root filesystem and
    # would report False even when the drive is correctly mounted
    parts = persistent.parts
    mnt = Path(*parts[:3]) if len(parts) >= 3 and parts[1] == "mnt" else persistent
    is_mount = os.path.ismount(str(mnt))
    say(f"{mnt} is a real mountpoint: {is_mount} (persistent root {persistent}, exists {persistent.is_dir()})")

    # ---- packages
    pkg_rows, pkg_ok = [], True
    for name, (rel, key) in PACKAGES.items():
        p = exch / rel
        obs = sha256_file(p) if p.is_file() else "ABSENT"
        exp = fi[key]
        crc_ok = extract_ok = manifest_ok = False
        if p.is_file():
            with zipfile.ZipFile(p) as zf:
                crc_ok = zf.testzip() is None
                names = zf.namelist()
                extract_ok = bool(names)
                sha_member = next((n for n in names if n.endswith("SHA256SUMS.txt")), None)
                if sha_member:
                    import tempfile
                    with tempfile.TemporaryDirectory(prefix="s2bf_pkg_") as td:
                        zf.extractall(td)
                        base = Path(td) / Path(sha_member).parent
                        bad = 0
                        for line in (Path(td) / sha_member).read_text().splitlines():
                            if not line.strip():
                                continue
                            want, rel_m = line.split("  ", 1)
                            f = base / rel_m
                            if not f.is_file() or sha256_file(f) != want:
                                bad += 1
                        manifest_ok = bad == 0
        ok = (obs == exp) and crc_ok and extract_ok and manifest_ok
        pkg_ok &= ok
        pkg_rows.append({"package": name, "path": str(p), "expected_sha256": exp,
                         "observed_sha256": obs, "sha_match": obs == exp, "crc_ok": crc_ok,
                         "fresh_extract_ok": extract_ok, "internal_manifest_ok": manifest_ok,
                         "verdict": "VERIFIED" if ok else "FAILED"})
        say(f"  {name:14s} {'VERIFIED' if ok else 'FAILED'} sha={obs[:16]} crc={crc_ok} manifest={manifest_ok}")

    # ---- dataset
    data_root = Path(fcfg["paths"]["data_root"]) / "pilot_seed260815"
    ds_sha, n_ep, n_missing = dataset_manifest(data_root)
    ds_ok = ds_sha == fi["dataset_content_manifest_sha256"] and n_missing == 0
    say(f"  dataset manifest {'VERIFIED' if ds_ok else 'FAILED'}: {n_ep} episodes, {n_missing} missing, {ds_sha[:16]}")

    # ---- git
    base_head = git(repo, "rev-parse", f"origin/{fcfg['repository']['base_branch']}")
    head_ok = base_head == fi["stage2b_branch_head_at_stage2br"]
    say(f"  base head {base_head[:12]} == expected {fi['stage2b_branch_head_at_stage2br'][:12]}: {head_ok}")

    code_rows, code_ok = [], True
    for rel in fcfg["frozen_scientific_files"]:
        a = git(repo, "rev-parse", f"{fi['stage2b_scientific_git_sha']}:{rel}")
        b = git(repo, "rev-parse", f"HEAD:{rel}")
        same = bool(a) and a == b
        code_ok &= same
        row = {"path": rel, "blob_at_scientific_commit": a, "blob_at_head": b, "identical": same,
               "sha256_on_disk": sha256_file(repo / rel)}
        if rel == "src/certo_fdi/pathways/geometry.py":
            row["blob_at_stage2a_commit"] = git(repo, "rev-parse", f"{fi['stage2a_git_sha']}:{rel}")
            row["identical_at_stage2a"] = row["blob_at_stage2a_commit"] == b
        code_rows.append(row)
        say(f"  {rel}: identical to {fi['stage2b_scientific_git_sha'][:8]} = {same}")
    geom = next(r for r in code_rows if r["path"].endswith("geometry.py"))
    say(f"  geometry.py identical at Stage 2A commit {fi['stage2a_git_sha'][:8]}: "
        f"{geom.get('identical_at_stage2a')}  <- the ridge import really is Stage 2A's code")
    decision_ok = next(r["identical"] for r in code_rows if r["path"].endswith("decision_stage2b.py"))

    # ---- reference score precision
    a0 = np.load(Path(fcfg["paths"]["stage2a_run_root"]) / "p5_ablations" / "scores_seed260817.npz",
                 allow_pickle=False)
    b0 = np.load(Path(fcfg["paths"]["stage2b_run_root"]) / "p1_loadpath" / "controls_seed260817.npz",
                 allow_pickle=False)
    prec_ok = (a0[EI.LEGACY_STAGE2A_SCORE_KEY].dtype == np.float64
               and b0["time_aligned_jacobian__rss"].dtype == np.float64)
    say(f"  reference arrays are float64 (value-by-value comparison possible): {prec_ok}")

    # ---- historical baseline hashes
    roots = {k: Path(fcfg["paths"][f"{k}_run_root"]) for k in ("stage2a", "stage2b", "stage2br")}
    hist_sha = {}
    for stage, rels in HISTORICAL.items():
        for rel in rels:
            p = roots[stage] / rel
            hist_sha[f"{stage}/{rel}"] = sha256_file(p) if p.is_file() else "ABSENT"
    say(f"  baselined {len(hist_sha)} historical artifacts for the Phase 6 mutation check")

    out = {
        "generated_utc": utc_now(), "run_id": root.name,
        "host": {"platform": platform.platform(), "python": sys.version.split()[0],
                 "numpy": np.__version__, "persistent_root_is_mount": is_mount},
        "packages": pkg_rows,
        "dataset": {"root": str(data_root), "n_episodes": n_ep, "n_missing": n_missing,
                    "observed_sha256": ds_sha, "expected_sha256": fi["dataset_content_manifest_sha256"],
                    "verified": ds_ok},
        "git": {"base_branch": fcfg["repository"]["base_branch"], "observed_base_head": base_head,
                "expected_base_head": fi["stage2b_branch_head_at_stage2br"], "matches": head_ok,
                "stage2bf_head": git(repo, "rev-parse", "HEAD"),
                "worktree_clean": git(repo, "status", "--porcelain=v1") == ""},
        "frozen_scientific_files": code_rows,
        "reference_score_precision": {
            "stage2a_dtype": str(a0[EI.LEGACY_STAGE2A_SCORE_KEY].dtype),
            "stage2b_dtype": str(b0["time_aligned_jacobian__rss"].dtype), "ok": bool(prec_ok)},
        "historical_artifact_sha256": hist_sha,
        # the booleans Phase 6 consumes
        "input_provenance_ok": bool(pkg_ok and ds_ok and is_mount),
        "base_head_matches": bool(head_ok),
        "scientific_code_identical": bool(code_ok),
        "decision_code_identical": bool(decision_ok),
        "reference_score_precision_ok": bool(prec_ok),
    }
    write_json(res / "stage2bf_input_provenance.json", out)
    with (res / "stage2bf_estimator_identity_map.csv").open("w", newline="", encoding="utf-8") as f:
        rows = EI.identity_map_rows()
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    say(f"Phase 0: provenance={out['input_provenance_ok']} head={head_ok} code={code_ok} "
        f"decision={decision_ok} precision={prec_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
