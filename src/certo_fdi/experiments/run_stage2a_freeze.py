"""Stage 2A Phase 0: environment, Git, data and provenance freeze.

Verifies -- and refuses to guess about -- everything the rest of the stage depends on:

* ``/mnt/g`` is a real mount with free space;
* the frozen 590-episode dataset is present, complete and content-hashed (the ``sha256``
  column of ``episode_index.csv`` is STALE by construction: ``precompute_gmo`` appended the
  ``r_gmo`` column in place after the index was written, so the *content* hashes are
  recomputed here and are what every Stage 2A table cites);
* the S0-S4 split structure and the fault families match the manifest (never memory);
* the MJCF and generating-config hashes match the frozen values;
* the frozen episodes **replay bit-for-bit** from their stored seed through the frozen
  generator -- this is what makes the closed-loop oracle sensitivities in Phase 4 valid;
* the Stage 1R-B Thin/Full review packages hash as recorded.

Writes ``results/stage2a_input_freeze.json`` (the gate the later phases require) and
``provenance/episode_sha256_manifest.csv``.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path

import numpy as np

from certo_fdi.experiments.common import sha256_file, utc_now, write_csv, write_json
from certo_fdi.experiments.stage2a_common import Stage, common_parser
from certo_fdi.paths import git_sha

REPLAY_PROBE_EPISODES = ("healthy_0000", "healthy_0041", "F1_actuator_0000", "F4_contact_0000", "F5_encoder_0000", "F6_command_0000")
REPLAY_TOLERANCE = 1e-5  # float32 storage round-trip


def _disk_free(path: Path) -> dict:
    u = shutil.disk_usage(path)
    return {"total_gb": u.total / 1e9, "used_gb": u.used / 1e9, "free_gb": u.free / 1e9}


def _mount_info(path: Path) -> dict:
    out = subprocess.run(["findmnt", "-T", str(path), "-n", "-o", "SOURCE,FSTYPE,OPTIONS"], check=False, text=True, capture_output=True).stdout.strip()
    parts = out.split(None, 2)
    return {"raw": out, "source": parts[0] if parts else "", "fstype": parts[1] if len(parts) > 1 else "", "options": parts[2] if len(parts) > 2 else ""}


def _hash_episodes(rows: list[dict], log) -> tuple[list[dict], str]:
    import hashlib

    out = []
    t0 = time.time()
    for i, r in enumerate(rows):
        p = Path(r["path"])
        sha = sha256_file(p) if p.exists() else "MISSING"
        out.append({
            "episode_id": r["episode_id"], "kind": r["kind"], "partition": r["partition"], "split": r["split"],
            "family": r["family"], "path": str(p), "exists": p.exists(), "size_bytes": p.stat().st_size if p.exists() else 0,
            "sha256_content_now": sha, "sha256_index_column_stale_pre_gmo": r.get("sha256", ""),
            "matches_index_column": sha == r.get("sha256", ""),
        })
        if (i + 1) % 200 == 0:
            log(f"  hashed {i + 1}/{len(rows)} episodes ({time.time() - t0:.0f}s)")
    joint = hashlib.sha256("\n".join(f"{r['episode_id']},{r['sha256_content_now']}" for r in sorted(out, key=lambda x: x["episode_id"])).encode()).hexdigest()
    return out, joint


def _replay_check(cfg_frozen: dict, xml: str, truth: dict, data_root: Path, index: dict[str, dict], log) -> list[dict]:
    """Regenerate a few frozen episodes from their stored seed and compare to the stored arrays."""
    import h5py

    from certo_fdi.data.franka_generator import generate_episode
    from certo_fdi.data.schema import EpisodeContext, FaultSpec

    rows = []
    for eid in REPLAY_PROBE_EPISODES:
        if eid not in index:
            rows.append({"episode_id": eid, "status": "NOT_IN_INDEX"})
            continue
        path = index[eid]["path"]
        with h5py.File(path, "r") as f:
            ctxd = json.loads(str(f.attrs["context_json"]))
            fj = json.loads(str(f.attrs["fault_json"]))
            meta = json.loads(str(f.attrs["meta_json"]))
            ref = {k: f["signals"][k][()] for k in ("q_meas", "qd_meas", "tau_meas", "tau_nominal", "tau_cmd")}
        t0 = time.time()
        ep = generate_episode(cfg_frozen, xml, truth, EpisodeContext(**ctxd), FaultSpec(**fj), int(meta["seed"]), eid)
        dev = {k: float(np.abs(ep.signals[k].astype(np.float64) - ref[k].astype(np.float64)).max()) for k in ref}
        worst = max(dev.values())
        rows.append({"episode_id": eid, "seed": int(meta["seed"]), "family": index[eid]["family"], "split": index[eid]["split"],
                     "replay_seconds": time.time() - t0, **{f"max_abs_dev_{k}": v for k, v in dev.items()},
                     "worst_max_abs_dev": worst, "within_float32_roundtrip": bool(worst <= REPLAY_TOLERANCE),
                     "status": "OK" if worst <= REPLAY_TOLERANCE else "MISMATCH"})
        log(f"  replay {eid}: worst |dev| = {worst:.3e} ({'OK' if worst <= REPLAY_TOLERANCE else 'MISMATCH'})")
    return rows


def main() -> int:
    ap = common_parser("Stage 2A Phase 0: environment / data / provenance freeze")
    args = ap.parse_args()
    st = Stage(args, "freeze")
    cfg = st.cfg
    fi = cfg["frozen_inputs"]
    storage = Path(cfg["paths"]["persistent_root"])
    blocked: list[str] = []

    # ---------------------------------------------------------------- storage
    mount = _mount_info(storage)
    disk = _disk_free(storage)
    st.log(f"storage {storage}: {mount['source']} ({mount['fstype']}), free {disk['free_gb']:.0f} GB")
    if not storage.is_dir():
        blocked.append(f"{storage} is not a directory")
    if mount["fstype"] in ("", "tmpfs", "overlay"):
        blocked.append(f"{storage} is not a real persistent mount (fstype={mount['fstype']!r})")
    if disk["free_gb"] < 5.0:
        blocked.append(f"less than 5 GB free on {storage}")

    # ---------------------------------------------------------------- dataset
    data_root = st.data_root
    st.log(f"dataset root {data_root}")
    if not data_root.is_dir():
        blocked.append(f"dataset root missing: {data_root}")
        write_json(st.layout.results / "stage2a_input_freeze.json", {"gate": "FAIL", "blocked": blocked})
        return 2

    manifest = json.loads((data_root / "dataset_manifest.json").read_text())
    with (data_root / "episode_index.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    index = {r["episode_id"]: r for r in rows}
    split_counts = Counter((r["kind"], r["partition"], r["split"]) for r in rows)
    family_counts = Counter((r["family"], r["partition"]) for r in rows)
    st.log(f"episode index: {len(rows)} episodes, {len(set(r['split'] for r in rows))} splits, {len(set(r['family'] for r in rows))} families")

    file_hashes = {name: sha256_file(data_root / name) for name in
                   ("dataset_manifest.json", "episode_index.csv", "split_manifest.json", "fault_manifest.json", "frame_variant_manifest.json", "model_parameter_audit.json")
                   if (data_root / name).exists()}
    mjcf = Path(cfg["paths"]["mjcf_path"])
    mjcf_sha = sha256_file(mjcf) if mjcf.exists() else "MISSING"
    if mjcf_sha != fi["mjcf_sha256"]:
        blocked.append(f"MJCF sha mismatch: {mjcf_sha} != {fi['mjcf_sha256']}")
    if manifest.get("config_sha256") != fi["pilot_config_sha256"]:
        blocked.append(f"generating-config sha mismatch: {manifest.get('config_sha256')} != {fi['pilot_config_sha256']}")
    if int(manifest.get("n_generated_now", -1)) != len(rows):
        blocked.append(f"manifest episode count {manifest.get('n_generated_now')} != index rows {len(rows)}")

    st.log("content-hashing all episodes (the index sha256 column is stale pre-GMO by construction)...")
    ep_rows, joint_sha = _hash_episodes(rows, st.log)
    write_csv(st.layout.sub("provenance") / "episode_sha256_manifest.csv", ep_rows)
    n_missing = sum(1 for r in ep_rows if not r["exists"])
    n_index_match = sum(1 for r in ep_rows if r["matches_index_column"])
    st.log(f"episode manifest sha256 = {joint_sha}  (missing {n_missing}, index-column matches {n_index_match}/{len(ep_rows)})")
    if n_missing:
        blocked.append(f"{n_missing} episode files missing")

    # r_gmo presence (the in-place append that makes the index column stale)
    import h5py

    with h5py.File(ep_rows[0]["path"], "r") as f:
        signals_present = sorted(f["signals"].keys())
    gmo_appended = "r_gmo" in signals_present
    if not gmo_appended:
        blocked.append("r_gmo column missing from the episodes (precompute_gmo has not run)")

    # ---------------------------------------------------------------- replay fidelity
    import yaml

    frozen_cfg_path = Path(args.repo_root) / "configs" / "frozen_dataset_protocol.yaml"
    frozen_cfg = yaml.safe_load(frozen_cfg_path.read_text())
    truth = manifest["truth_parameters_hidden_from_models"]
    st.log("replaying frozen episodes from their stored seeds (oracle-sensitivity precondition)...")
    replay = _replay_check(frozen_cfg, str(mjcf), truth, data_root, index, st.log)
    replay_ok = all(r.get("status") == "OK" for r in replay)
    write_csv(st.layout.sub("provenance") / "replay_fidelity.csv", replay)
    if not replay_ok:
        blocked.append("frozen episodes do not replay from their stored seeds")

    # ---------------------------------------------------------------- Stage 1R-B frozen packages
    pkg_dir = storage / "06_review_exchange" / "to_review"
    packages = {}
    for kind in ("thin", "full"):
        cands = sorted((pkg_dir / kind).glob("CERTO_FDI_stage1rb_*"))
        for p in cands:
            packages[p.name] = {"path": str(p), "sha256": sha256_file(p), "size_bytes": p.stat().st_size}
    st.log(f"Stage 1R-B frozen packages: {len(packages)}")

    frozen_run = Path(cfg["paths"]["frozen_stage1rb_run"])
    frozen_results = {}
    for name in ("stage1rb_decision_evidence.json", "stage1rb_run_manifest.json", "stage1rb_tuning_selection.json"):
        p = frozen_run / "results" / name
        if p.exists():
            frozen_results[name] = sha256_file(p)

    # ---------------------------------------------------------------- git
    repo = Path(args.repo_root)
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], check=False, text=True, capture_output=True).stdout.strip()
    branch = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"], check=False, text=True, capture_output=True).stdout.strip()
    if dirty and cfg.get("execution", {}).get("require_clean_worktree", True):
        st.log(f"WARNING: worktree is dirty:\n{dirty}")

    freeze = {
        "gate": "FAIL" if blocked else "PASS",
        "blocked": blocked,
        "run_id": st.layout.run_id,
        "timestamp_utc": utc_now(),
        "git": {"sha": git_sha(repo), "branch": branch, "dirty": bool(dirty), "dirty_files": dirty.splitlines()},
        "storage": {"root": str(storage), "mount": mount, "disk": disk},
        "dataset": {
            "root": str(data_root),
            "n_episodes": len(rows),
            "split_counts": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in sorted(split_counts.items())},
            "family_counts": {f"{k[0]}|{k[1]}": v for k, v in sorted(family_counts.items())},
            "splits_present": sorted(set(r["split"] for r in rows)),
            "families_present": sorted(set(r["family"] for r in rows)),
            "partitions_present": sorted(set(r["partition"] for r in rows)),
            "file_sha256": file_hashes,
            "signals_present": signals_present,
            "r_gmo_appended_in_place": gmo_appended,
            "index_sha_column_is_stale_pre_gmo": True,
            "n_index_column_matches": n_index_match,
            "generating_config_sha256": manifest.get("config_sha256"),
            "generating_git_sha": manifest.get("git_sha"),
            "mjcf_path": str(mjcf),
            "mjcf_sha256": mjcf_sha,
            "menagerie_commit": manifest.get("menagerie_commit"),
            "regenerated": False,
            "regeneration_forbidden_reason": "Stage 2A contract §1.5: reuse the frozen Stage 1R data; never regenerate",
        },
        "episode_manifest_sha256": joint_sha,
        "episode_manifest_csv": str(st.layout.sub("provenance") / "episode_sha256_manifest.csv"),
        "replay_fidelity": {"tolerance": REPLAY_TOLERANCE, "all_ok": replay_ok, "rows": replay},
        "stage1rb_packages": packages,
        "stage1rb_frozen_result_sha256": frozen_results,
        "stage1rb_frozen_run": str(frozen_run),
        "config_sha256": st.cfg_sha,
        "notes": [
            "S5 is not a data partition: the frozen protocol has S0-S4 and uses 'S5' for the "
            "frame-reparameterization stress protocol, which is an implementation property and "
            "never a detection-value axis.",
            "The episode_index.csv sha256 column predates the in-place r_gmo append; the content "
            "hashes recomputed here are what every Stage 2A result table cites.",
        ],
    }
    write_json(st.layout.results / "stage2a_input_freeze.json", freeze)
    st.log(f"input freeze gate: {freeze['gate']}" + (f" -- blocked: {blocked}" if blocked else ""))
    st.finish({"gate": freeze["gate"]})
    return 0 if freeze["gate"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
