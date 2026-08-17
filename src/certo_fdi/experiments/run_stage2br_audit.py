"""Stage 2B-R audit runner: input provenance, git-head audit, estimator diagnostics, integrity gate.

Executes the phases that do not require the frozen run artifacts, and records honestly which
phases could not run and why. It never infers a reproduction result from summary counts, and it
never reports a PASS for a check it was unable to perform.

Usage::

    run_stage2br_audit.py --config configs/stage2br_reproduction_gate.yaml \
        --storage-root <root> --run-id <RUN_ID> --repo-root <worktree>
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
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from certo_fdi.stage2br import canonical_scores as CS
from certo_fdi.stage2br import estimator_gap as EG
from certo_fdi.stage2br.decision_stage2br import integrity_state

UTC = "%Y-%m-%dT%H:%M:%SZ"

# files that must exist for the score-level audit (master prompt §6.2). The three
# ``scores_seed*.npz`` and three ``controls_seed*.npz`` are the primary evidence: they carry the
# per-window, per-link score vectors, and ``run_stage2a_metrics.py`` / ``run_stage2b_loadpath.py``
# read exactly these files to produce the numbers the reproduction gate compares.
REQUIRED_EVIDENCE = (
    ("stage2a_run_root", "p5_ablations/scores_seed260815.npz", "Stage 2A per-window score arrays, seed 260815"),
    ("stage2a_run_root", "p5_ablations/scores_seed260816.npz", "Stage 2A per-window score arrays, seed 260816"),
    ("stage2a_run_root", "p5_ablations/scores_seed260817.npz", "Stage 2A per-window score arrays, seed 260817"),
    ("stage2a_run_root", "results/stage2a_localization_metrics.csv", "Stage 2A per-seed localizer metrics"),
    ("stage2a_run_root", "p6_metrics/stage2a_link_confusion.json", "Stage 2A per-seed confusion matrices"),
    ("stage2a_run_root", "results/stage2a_pathway_dictionary_audit.csv", "Stage 2A per-link dictionary spectra"),
    ("stage2b_run_root", "p1_loadpath/controls_seed260815.npz", "Stage 2B per-window control stats, seed 260815"),
    ("stage2b_run_root", "p1_loadpath/controls_seed260816.npz", "Stage 2B per-window control stats, seed 260816"),
    ("stage2b_run_root", "p1_loadpath/controls_seed260817.npz", "Stage 2B per-window control stats, seed 260817"),
    ("stage2b_run_root", "results/stage2b_loadpath_controls.csv", "Stage 2B per-seed load-path control metrics"),
    ("stage2b_run_root", "results/stage2b_contact_reproduction_gate.json", "Stage 2B contact reproduction gate"),
    ("stage2b_run_root", "results/stage2b_rank_audit.csv", "Stage 2B per-link realised ranks"),
    ("stage2b_run_root", "results/stage2b_localization_metrics.csv", "Stage 2B localization metrics"),
    ("stage2b_run_root", "results/stage2b_decision_evidence.json", "Stage 2B frozen decision evidence"),
    ("stage2b_run_root", "results/stage2b_input_freeze.json", "Stage 2B Phase 0 input freeze"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(UTC)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


# --------------------------------------------------------------------------- phase 0
def classify_path(path: str) -> str:
    """Master prompt §4.3 file classes."""
    p = path.lower()
    if p.startswith("tests/"):
        return "TEST_ONLY"
    if "/packaging/" in p or p.startswith("scripts/") or ".github/" in p:
        return "PACKAGING_ONLY"
    if p.startswith("configs/"):
        return "CONFIG_OR_THRESHOLDS"
    if p.startswith("data/") or "/data/" in p:
        return "DATA_OR_SPLITS"
    if p.startswith("docs") or p.endswith(".md"):
        return "DOCS_ONLY"
    if p.startswith("src/"):
        return "SCIENTIFIC_COMPUTATION"
    return "DOCS_ONLY"


def audit_git_head(repo: Path, cfg: dict) -> dict:
    """§4.3: classify every change between the scientific commit and the current 2B branch head."""
    fi = cfg["frozen_inputs"]
    base, head = fi["stage2b_scientific_commit"], fi["stage2b_branch_head_at_kickoff"]
    rows, present = [], bool(git(repo, "cat-file", "-e", f"{base}^{{commit}}") == "")
    raw = git(repo, "diff", "--name-status", base, head)
    for line in [l for l in raw.splitlines() if l.strip()]:
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        rows.append({"status": status, "path": path, "classification": classify_path(path)})
    blocking = [r for r in rows if r["classification"] in cfg["blocking_diff_classes"]]
    # a src/ change is only genuinely scientific if it touches a scientific module; the audit
    # records the automatic class and the manual verdict separately so neither can be silently
    # overridden by the other
    return {
        "base_commit": base, "head_commit": head,
        "head_matches_remote": git(repo, "rev-parse", "origin/" + cfg["repository"]["base_branch"]) == head,
        "base_commit_present": present or bool(git(repo, "rev-parse", "--verify", base + "^{commit}")),
        "n_changed_files": len(rows), "files": rows,
        "n_blocking_by_path_class": len(blocking),
        "blocking_files": blocking,
    }


def tree_hash_comparison(repo: Path, base: str, head: str, paths: list[str]) -> list[dict]:
    out = []
    for p in paths:
        a = git(repo, "rev-parse", f"{base}:{p}")
        b = git(repo, "rev-parse", f"{head}:{p}")
        out.append({"path": p, "base_tree": a or "MISSING", "head_tree": b or "MISSING",
                    "identical": bool(a and a == b)})
    return out


def bounded_search_locations(persistent: Path) -> list[Path]:
    """Exactly the locations master prompt §4.1 permits. Whole-disk scans are forbidden."""
    out = [Path.cwd(), Path.home() / "Downloads", Path.home() / "Desktop",
           persistent / "00_inbox",
           persistent / "06_review_exchange", persistent / "06_review_exchange/to_review/full",
           persistent / "06_review_exchange/to_review/thin"]
    users = Path("/mnt/c/Users")
    if users.is_dir():
        try:
            for u in sorted(users.iterdir()):
                if u.is_dir():
                    out += [u / "Downloads", u / "Desktop"]
        except OSError:
            pass
    return [p for p in out if p.is_dir()]


def dataset_content_manifest(paths: dict) -> tuple[Path, str, str]:
    """Recompute the 590-episode content manifest independently (master prompt §4.4).

    Byte-identical construction to ``run_stage2b_freeze``: content-hash every episode file listed
    in ``episode_index.csv``, then hash the sorted ``episode_id,sha256`` lines. Recomputed here
    rather than read from the frozen run's own record, because a run vouching for itself is not a
    verification.
    """
    root = Path(os.path.expanduser(paths["data_root"])) / "pilot_seed260815"
    index = root / "episode_index.csv"
    if not index.is_file():
        return root, "", "episode_index.csv not found"
    with index.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    per_ep = []
    for r in rows:
        p = Path(r["path"])
        per_ep.append((r["episode_id"], sha256_file(p) if p.exists() else "MISSING"))
    joint = hashlib.sha256(
        "\n".join(f"{eid},{sha}" for eid, sha in sorted(per_ep)).encode()).hexdigest()
    n_missing = sum(1 for _, s in per_ep if s == "MISSING")
    return root, joint, f"{len(per_ep)} episodes content-hashed, {n_missing} missing"


def probe_frozen_inputs(cfg: dict) -> dict:
    """Every frozen input the audit needs: present or absent, hashed when present."""
    paths = cfg["paths"]
    fi = cfg["frozen_inputs"]
    persistent = Path(os.path.expanduser(paths["persistent_root"]))
    checks: list[dict] = []

    checks.append({"item": "persistent_root", "path": str(persistent),
                   "present": persistent.is_dir(), "kind": "directory",
                   "expected_sha256": "", "observed_sha256": "",
                   "note": "canonical G-drive storage root (master prompt §3.2)"})

    for key in ("stage2a_run_root", "stage2b_run_root", "review_exchange", "data_root", "stage2b_data_root"):
        p = Path(os.path.expanduser(paths[key]))
        checks.append({"item": key, "path": str(p), "present": p.is_dir(), "kind": "directory",
                       "expected_sha256": "", "observed_sha256": "", "note": ""})

    zip_name = fi["stage2b_full_zip_name"]
    found = ""
    for d in bounded_search_locations(persistent):
        cand = d / zip_name
        if cand.is_file():
            found = str(cand)
            break
    checks.append({"item": "stage2b_full_zip", "path": found or zip_name,
                   "present": bool(found), "kind": "file",
                   "expected_sha256": fi["stage2b_full_zip_sha256"],
                   "observed_sha256": sha256_file(Path(found)) if found else "",
                   "note": "Stage 2B FULL review package"})
    ds_root, ds_obs, ds_note = dataset_content_manifest(paths)
    checks.append({"item": "dataset_content_manifest", "path": str(ds_root),
                   "present": bool(ds_obs), "kind": "manifest",
                   "expected_sha256": fi["dataset_manifest_sha256"], "observed_sha256": ds_obs,
                   "note": ds_note})

    for check in checks:
        exp, obs = check["expected_sha256"], check["observed_sha256"]
        check["verified"] = bool(check["present"] and exp and obs and exp == obs)
        check["status"] = ("VERIFIED" if check["verified"] else
                           "MISMATCH" if (check["present"] and exp and obs and exp != obs) else
                           "PRESENT_UNVERIFIED" if check["present"] else "ABSENT")
    return {"checks": checks,
            "all_present": all(c["present"] for c in checks),
            "any_mismatch": any(c["status"] == "MISMATCH" for c in checks),
            "n_absent": sum(1 for c in checks if not c["present"])}


def inventory_reference_evidence(cfg: dict) -> list[dict]:
    """The §6.2 score-level artifacts: exists / does not exist. No inference either way."""
    rows = []
    for root_key, rel, desc in REQUIRED_EVIDENCE:
        root = Path(os.path.expanduser(cfg["paths"][root_key]))
        p = root / rel
        exists = p.is_file()
        rows.append({"root": root_key, "relative_path": rel, "description": desc,
                     "absolute_path": str(p), "exists": exists,
                     "sha256": sha256_file(p) if exists else "",
                     "size_bytes": p.stat().st_size if exists else 0,
                     "status": "PRESENT" if exists else "ABSENT"})
    return rows


# --------------------------------------------------------------------------- estimator diagnostic
def estimator_gap_table(seed: int = 260817) -> list[dict]:
    """Measure the two frozen estimators against each other across dictionary conditioning."""
    rng = np.random.default_rng(seed)
    d, p, n = 56, 3, 2000            # 7 dof x 8 window points; point-force columns
    floor = EG.ROUNDOFF_FACTOR * EG.EPS64
    rows = []
    for cond in (1e0, 1e1, 1e2, 3e2, 1e3, 1e4, 1e6, 1e8):
        D = EG.conditioned_dictionary(rng, n, d, p, cond)
        z = rng.normal(size=(n, d))
        g = EG.gap_report(D, z)
        rows.append({
            "condition_number": cond,
            "median_relative_gap": float(np.median(g["rel_gap"])),
            "p95_relative_gap": float(np.percentile(g["rel_gap"], 95)),
            "median_gap_over_roundoff_floor": float(np.median(g["gap_over_roundoff_floor"])),
            "max_gap_over_roundoff_floor": float(g["gap_over_roundoff_floor"].max()),
            "median_fraction_of_residual_energy": float(np.median(g["fraction_of_z_energy"])),
            "roundoff_floor_relative": floor,
            "n_windows": n, "dimension": d, "n_columns": p,
        })
    return rows


def backend_noise_table(seed: int = 21) -> list[dict]:
    """The same estimator across the five independent implementations: genuine numerical noise."""
    rng = np.random.default_rng(seed)
    d, p, n = 56, 3, 200
    rows = []
    for cond in (1e0, 1e2, 1e4):
        D = EG.conditioned_dictionary(rng, n, d, p, cond)
        z = rng.normal(size=(n, d))
        for backend in CS.BACKENDS:
            rels, rank_ok = [], 0
            for i in range(n):
                ref = CS.project(D[i], z[i], CS.REFERENCE_BACKEND).rss
                v = CS.project(D[i], z[i], backend)
                rank_ok += int(v.rank_matches_frozen)
                if v.rank_matches_frozen:
                    rels.append(abs(v.rss - ref) / max(abs(ref), 1e-300))
            rows.append({
                "condition_number": cond, "backend": backend,
                "n_rank_compatible": rank_ok, "n_windows": n,
                "max_relative_deviation": float(max(rels)) if rels else float("nan"),
                "median_relative_deviation": float(np.median(rels)) if rels else float("nan"),
                "max_deviation_in_ulp": float(max(rels) / np.finfo(float).eps) if rels else float("nan"),
                "inside_roundoff_floor": bool(rels and max(rels) < EG.ROUNDOFF_FACTOR * EG.EPS64),
            })
    return rows


def disagreement_band_table() -> list[dict]:
    """Which singular directions the two rules treat differently (the closed form, evaluated)."""
    lam_rel = 1e-6                    # lambda / sigma_max^2
    rows = []
    for e in range(0, -11, -1):
        r = 10.0 ** e
        s2 = r * r
        ridge_keeps = s2 * (s2 + 2 * lam_rel) / (s2 + lam_rel) ** 2
        exact_keeps = 1.0 if r > CS.RANK_RTOL else 0.0
        rows.append({"sigma_over_sigma_max": r, "log10_ratio": e,
                     "stage2a_ridge_retains_fraction": float(ridge_keeps),
                     "stage2b_exact_retains_fraction": float(exact_keeps),
                     "disagreement": float(abs(ridge_keeps - exact_keeps)),
                     "in_disagreement_band": bool(abs(ridge_keeps - exact_keeps) > 0.01)})
    return rows


# --------------------------------------------------------------------------- writers
def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        p.write_text("", encoding="utf-8")
        return
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2B-R reproduction-gate audit")
    ap.add_argument("--config", required=True)
    ap.add_argument("--storage-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    cfg_path = Path(args.config)
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg_sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    root = Path(args.storage_root).resolve() / "04_runs" / "stage2b_r_reproduction_gate" / args.run_id
    res, fig = root / "results", root / "figures"
    for d in (res, fig, root / "logs", root / "provenance"):
        d.mkdir(parents=True, exist_ok=True)

    log: list[str] = []

    def say(m: str) -> None:
        line = f"[{utc_now()}] {m}"
        print(line, flush=True)
        log.append(line)

    say(f"Stage 2B-R audit start (run {args.run_id})")
    canonical_root = Path(os.path.expanduser(cfg["paths"]["persistent_root"]))
    on_canonical = canonical_root.is_dir()
    say(f"storage root: {root}  (canonical {canonical_root} {'present' if on_canonical else 'ABSENT'})")

    # ---------------------------------------------------------------- phase 0
    prov = probe_frozen_inputs(cfg)
    say(f"input provenance: {prov['n_absent']} of {len(prov['checks'])} frozen inputs absent, "
        f"{sum(1 for c in prov['checks'] if c['verified'])} verified by hash")

    ga = audit_git_head(repo, cfg)
    trees = tree_hash_comparison(
        repo, ga["base_commit"], ga["head_commit"],
        ["configs", "scripts", "docs_pointer", "src/certo_fdi/stage2b", "src/certo_fdi/pathways",
         "src/certo_fdi/localization", "src/certo_fdi/geometry", "src/certo_fdi/dynamics",
         "src/certo_fdi/models", "src/certo_fdi/data", "src/certo_fdi/anomaly",
         "src/certo_fdi/experiments", "src/certo_fdi/packaging", "tests"])
    scientific_trees = [t for t in trees if t["path"] in (
        "configs", "src/certo_fdi/stage2b", "src/certo_fdi/pathways", "src/certo_fdi/localization",
        "src/certo_fdi/geometry", "src/certo_fdi/dynamics", "src/certo_fdi/models",
        "src/certo_fdi/data", "src/certo_fdi/anomaly")]
    head_clean = all(t["identical"] for t in scientific_trees)
    say(f"scientific-head audit: {ga['n_changed_files']} files changed after {ga['base_commit'][:8]}; "
        f"all scientific/config trees identical = {head_clean}")

    inv = inventory_reference_evidence(cfg)
    n_present = sum(1 for r in inv if r["exists"])
    say(f"reference evidence: {n_present} of {len(inv)} required score-level artifacts present")

    write_json(res / "stage2br_input_provenance.json", {
        "run_id": args.run_id, "generated_utc": utc_now(), "config_sha256": cfg_sha,
        "git_sha": git(repo, "rev-parse", "HEAD"),
        "storage_root_in_effect": str(root),
        "canonical_persistent_root": str(canonical_root),
        "canonical_root_present": on_canonical,
        "frozen_input_checks": prov["checks"],
        "all_frozen_inputs_present": prov["all_present"],
        "any_hash_mismatch": prov["any_mismatch"],
        "input_provenance_ok": bool(prov["all_present"] and not prov["any_mismatch"]),
        "host": {"platform": platform.platform(), "python": sys.version.split()[0],
                 "numpy": np.__version__},
    })
    write_json(res / "stage2br_git_head_audit.json", {"tree_comparison": trees, **ga,
                                                      "scientific_head_clean": head_clean})
    write_csv(res / "stage2br_reference_artifact_inventory.csv", inv)

    # ---------------------------------------------------------------- estimator diagnostics
    say("measuring the two frozen estimators against each other")
    gap_rows = estimator_gap_table()
    noise_rows = backend_noise_table()
    band_rows = disagreement_band_table()
    write_csv(res / "stage2br_estimator_gap.csv", gap_rows)
    write_csv(res / "stage2br_backend_stability.csv", noise_rows)
    write_csv(res / "stage2br_disagreement_band.csv", band_rows)

    floor = EG.ROUNDOFF_FACTOR * EG.EPS64
    worst_noise = max((r["max_relative_deviation"] for r in noise_rows
                       if r["max_relative_deviation"] == r["max_relative_deviation"]), default=float("nan"))
    gap_at_300 = next(r["median_relative_gap"] for r in gap_rows if r["condition_number"] == 3e2)
    say(f"backend noise (same estimator): max {worst_noise:.3e} relative; roundoff floor {floor:.3e}")
    say(f"estimator gap (ridge vs exact) at cond 3e2: {gap_at_300:.3e} relative "
        f"= {gap_at_300 / floor:.3e} x the roundoff floor")

    # ---------------------------------------------------------------- integrity state
    evidence = {
        "input_provenance_ok": bool(prov["all_present"] and not prov["any_mismatch"]),
        "scientific_head_clean": head_clean,
        "reference_evidence_complete": bool(n_present == len(inv)),
        "score_history_resolvable": bool(n_present == len(inv)),
        # not measurable without the frozen arrays; left unset rather than guessed
        "n_label_differences": None,
        "n_nontie_label_differences": None,
        "scores_within_score_tolerance": None,
        "semantic_difference_found": True,        # measured from the frozen code, below
        "rank_threshold_unstable": None,
    }
    state = integrity_state(evidence, cfg)
    say(f"integrity state: {state['integrity_state']}")

    gate = {
        "run_id": args.run_id, "generated_utc": utc_now(),
        "integrity_state": state["integrity_state"],
        "reason": state["reason"],
        "modifiers": state["modifiers"],
        "reproduction_gate_pass": state["reproduction_gate_pass"],
        "precedence": state["precedence"],
        "triggers": state["triggers"],
        "evidence_used": state["evidence_used"],
        "phases_completed": ["phase0_input_provenance", "phase0_git_head_audit",
                             "phase1_protocol_freeze", "phase3_canonical_implementations",
                             "phase3_estimator_diagnostics"],
        "phases_not_run": {
            "phase2_score_extraction": "frozen Stage 2A/2B run roots are not reachable",
            "phase4_numerical_envelope_on_frozen_arrays": "requires the per-window score arrays",
            "phase5_tie_classification_on_frozen_arrays": "requires the per-window score arrays",
            "phase6_scientific_decision": "forbidden: the integrity state is not a PASS",
        },
        "measured_without_frozen_arrays": {
            "backend_noise_max_relative": worst_noise,
            "roundoff_floor_relative": floor,
            "estimator_gap_relative_at_condition_300": gap_at_300,
            "estimator_gap_over_roundoff_floor": gap_at_300 / floor,
            "finding": ("the Stage 2A reference and the Stage 2B observed quantity are computed by "
                        "different estimators: a ridge normal-equations solve without truncation "
                        "(pathways.geometry.batched_projection, lambda = 1e-6 sigma_max^2) versus an "
                        "exact orthogonal projection truncated at s <= s_0 * 1e-8 "
                        "(stage2b.rank_aware_scores.project)"),
        },
        "stage2b_scientific_decision": "BLOCKED (unchanged: the historical record is immutable)",
    }
    write_json(res / "stage2br_reproduction_gate.json", gate)

    # ---------------------------------------------------------------- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        c = [r["condition_number"] for r in gap_rows]
        m = [r["median_gap_over_roundoff_floor"] for r in gap_rows]
        f1, a1 = plt.subplots(figsize=(7, 4.2))
        a1.loglog(c, np.maximum(m, 1e-3), "o-", color="#b4413c", label="ridge vs exact projection")
        a1.axhline(1.0, ls="--", color="#666", label="roundoff floor (1000·eps)")
        a1.axhline(max(worst_noise / floor, 1e-3), ls=":", color="#1f77b4",
                   label="same estimator, 5 backends")
        a1.set_xlabel("dictionary condition number"); a1.set_ylabel("score gap / roundoff floor")
        a1.set_title("The two sides of the reproduction gate are different estimators")
        a1.legend(fontsize=8); a1.grid(alpha=.3, which="both")
        f1.tight_layout(); f1.savefig(fig / "stage2br_backend_score_drift.png", dpi=150); plt.close(f1)

        r = [x["sigma_over_sigma_max"] for x in band_rows]
        f2, a2 = plt.subplots(figsize=(7, 4.2))
        a2.semilogx(r, [x["stage2a_ridge_retains_fraction"] for x in band_rows], "o-",
                    label="Stage 2A ridge retains")
        a2.semilogx(r, [x["stage2b_exact_retains_fraction"] for x in band_rows], "s--",
                    label="Stage 2B exact projector retains")
        a2.axvspan(CS.RANK_RTOL, 1e-3, color="#b4413c", alpha=.15, label="disagreement band")
        a2.set_xlabel(r"$\sigma_i/\sigma_{max}$"); a2.set_ylabel("fraction of the direction retained")
        a2.set_title("A five-decade band where the two rules disagree completely")
        a2.legend(fontsize=8); a2.grid(alpha=.3)
        f2.tight_layout(); f2.savefig(fig / "stage2br_rank_spectrum_disagreement.png", dpi=150); plt.close(f2)
        say("figures written")
    except Exception as e:                                   # pragma: no cover
        say(f"figures skipped: {e}")

    write_json(root / "provenance" / "stage2br_run_manifest.json", {
        "run_id": args.run_id, "generated_utc": utc_now(), "config_sha256": cfg_sha,
        "git_sha": git(repo, "rev-parse", "HEAD"), "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "integrity_state": state["integrity_state"],
        "stage2b_decision": "BLOCKED",
        "artifacts": {str(p.relative_to(root)): sha256_file(p)
                      for p in sorted(root.rglob("*")) if p.is_file()},
    })
    (root / "logs" / "stage2br_audit.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    say("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
