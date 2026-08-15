"""Generate the Smoke/Pilot 7-DoF dataset on the persistent data root with manifests."""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import numpy as np

from certo_fdi.data.episode_io import write_episode
from certo_fdi.data.franka_generator import generate_episode, make_truth_params, reference_chain
from certo_fdi.data.schema import CONTEXT_FIELDS, FAULT_FAMILIES, LABELS, REGIONS, SIGNALS, SPEED_BANDS, TOOLS
from certo_fdi.data.splits import PlannedEpisode, build_plan, leakage_report
from certo_fdi.dynamics.mujoco_backend import MujocoPlant, model_parameter_audit, sha256_file
from certo_fdi.experiments.common import load_config, sha256_file as sha_file, utc_now, write_csv, write_json
from certo_fdi.geometry.frame_reparameterization import sample_link_frames
from certo_fdi.paths import git_sha


def _worker(args):
    cfg, xml, truth, plan_row, out_path = args
    from certo_fdi.data.schema import EpisodeContext, FaultSpec

    ctx = EpisodeContext(**plan_row["context"])
    fault = FaultSpec(**plan_row["fault"])
    try:
        ep = generate_episode(cfg, xml, truth, ctx, fault, plan_row["seed"], plan_row["episode_id"])
        write_episode(out_path, ep)
        return {"episode_id": plan_row["episode_id"], "status": "OK", "path": out_path, "n_samples": ep.n_samples, "tracking_rms_rad": ep.meta["tracking_rms_rad"], "sha256": sha_file(out_path)}
    except Exception as e:  # pragma: no cover
        return {"episode_id": plan_row["episode_id"], "status": f"FAILED: {type(e).__name__}: {e}", "path": out_path, "trace": traceback.format_exc()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--profile", choices=("smoke", "pilot"), required=True)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--dataset-seed", type=int, default=260815)
    ap.add_argument("--workers", type=int, default=max(1, min(12, (os.cpu_count() or 2) - 2)))
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    cfg, cfg_sha = load_config(args.config)
    xml = cfg["paths"]["mjcf_path"]
    data_root = Path(args.data_root or cfg["paths"]["data_root"]) / f"{args.profile}_seed{args.dataset_seed}"
    data_root.mkdir(parents=True, exist_ok=True)
    ep_dir = data_root / "episodes"
    ep_dir.mkdir(exist_ok=True)
    t0 = time.time()

    n = int(cfg["robot"]["dof"])
    truth = make_truth_params(cfg, n, np.random.default_rng(args.dataset_seed + 7))
    plan = build_plan(cfg, args.profile, args.dataset_seed)
    leak = leakage_report(plan)
    if not leak["all_pass"]:
        write_json(data_root / "leakage_report.json", leak)
        raise SystemExit(f"leakage checks failed: {leak}")

    # model audit
    plant = MujocoPlant(xml)
    audit = model_parameter_audit(plant.model, plant.chain, xml)
    audit["menagerie_commit"] = cfg["paths"].get("menagerie_commit")
    write_json(data_root / "model_parameter_audit.json", audit)

    jobs = []
    for p in plan:
        out = ep_dir / f"{p.episode_id}.h5"
        if out.exists() and not args.force:
            continue
        jobs.append((cfg, xml, truth, {"context": asdict(p.context), "fault": asdict(p.fault), "seed": p.seed, "episode_id": p.episode_id}, str(out)))
    results = []
    print(f"generating {len(jobs)} episodes with {args.workers} workers -> {data_root}")
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            results.append(r)
            if not r["status"].startswith("OK"):
                print(r["status"], r.get("trace", "")[-500:])
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(jobs)} done ({time.time() - t0:.0f}s)")
    failed = [r for r in results if not r["status"].startswith("OK")]

    # episode index & manifests
    by_id = {r["episode_id"]: r for r in results}
    rows = []
    for p in plan:
        row = p.to_row()
        path = ep_dir / f"{p.episode_id}.h5"
        row["path"] = str(path)
        row["exists"] = path.exists()
        row["sha256"] = by_id.get(p.episode_id, {}).get("sha256", sha_file(path) if path.exists() else "")
        row["status"] = by_id.get(p.episode_id, {}).get("status", "EXISTING")
        row["tracking_rms_rad"] = by_id.get(p.episode_id, {}).get("tracking_rms_rad", "")
        rows.append(row)
    write_csv(data_root / "episode_index.csv", rows)
    split_manifest = {
        "dataset_seed": args.dataset_seed, "profile": args.profile,
        "partitions": {part: sorted(p.episode_id for p in plan if p.partition == part) for part in ("train", "val", "test", "calib")},
        "context_splits": {s: sorted(p.episode_id for p in plan if p.split == s) for s in ("S0", "S1", "S2", "S3", "S4")},
        "S5": "frame-reparameterized duplicates: see frame_variant_manifest.json (same physical episodes)",
        "rules": {"healthy_only_training": True, "threshold_calibration_partition": "val (healthy)", "fault_episodes_partitions": ["test", "calib"], "few_shot_partition": "calib", "windows_cross_episodes": False},
        "leakage_report": leak,
        "id_context": {"regions": [REGIONS[i]["name"] for i in (0, 1)], "tools": [TOOLS[i]["name"] for i in (0, 1, 2)], "speed_bands": ["slow", "medium"]},
        "ood_context": {"S1_region": REGIONS[2], "S2_tool": TOOLS[3], "S3_speed": SPEED_BANDS["fast"], "S4": "combined"},
    }
    write_json(data_root / "split_manifest.json", split_manifest)
    fault_manifest = {
        "families": list(FAULT_FAMILIES),
        "episodes": {p.episode_id: {"family": p.family, **asdict(p.fault), "partition": p.partition, "split": p.split} for p in plan if p.kind == "fault"},
        "severity_grids": cfg["faults"],
        "units": {"F1_actuator": "fractional efficiency loss", "F2_friction": "fractional increase of the truth coefficient", "F3_payload": "kg (mass) | m (com_shift) | 1e-2 kg m^2 (inertia)", "F4_contact": "N (soft persistent; impact pulses are 3x)", "F5_encoder": "rad (bias/drift) | s (timestamp) | rad/s (velocity bias)", "F6_command": "s (delay/hold max) | fraction (scale)"},
    }
    write_json(data_root / "fault_manifest.json", fault_manifest)
    # frame variants (S5) for selected episodes: sample legal H_i sets and store them
    ft = cfg["frame_trials"]
    frng = np.random.default_rng(args.dataset_seed + 99)
    chain = reference_chain(xml)
    frame_variants = {}
    selected = [p.episode_id for p in plan if p.partition == "test"][: (8 if args.profile == "smoke" else 48)]
    for eid in selected:
        variants = []
        for v in range(int(ft["variants_per_episode"])):
            frames = sample_link_frames(chain, frng, rotation_angle_max_deg=float(ft["rotation_angle_max_deg"]), translation_fraction_of_link_length=float(ft["translation_fraction_of_link_length"]))
            variants.append([f.matrix().tolist() for f in frames])
        frame_variants[eid] = variants
    write_json(data_root / "frame_variant_manifest.json", {"description": "H_i (pose of old link frame in new frame) per link per variant; applied at evaluation time to the SAME physical episode", "rotation_angle_max_deg": ft["rotation_angle_max_deg"], "translation_fraction_of_link_length": ft["translation_fraction_of_link_length"], "episodes": frame_variants})
    dataset_manifest = {
        "created_utc": utc_now(), "git_sha": git_sha(Path(args.repo_root)), "config_sha256": cfg_sha, "profile": args.profile,
        "dataset_seed": args.dataset_seed, "n_planned": len(plan), "n_generated_now": len(results), "n_failed": len(failed),
        "failed": [r["episode_id"] for r in failed], "elapsed_s": time.time() - t0,
        "mjcf_path": xml, "mjcf_sha256": sha256_file(Path(xml)), "menagerie_commit": cfg["paths"].get("menagerie_commit"),
        "signals": SIGNALS, "labels": LABELS, "context_fields": list(CONTEXT_FIELDS),
        "simulation": cfg["simulation"], "plant_mismatch": cfg["plant_mismatch"],
        "truth_parameters_hidden_from_models": truth,
        "storage_format": "HDF5 (one file per episode, gzip)",
    }
    write_json(data_root / "dataset_manifest.json", dataset_manifest)
    print(json.dumps({"n_planned": len(plan), "generated": len(results), "failed": len(failed), "elapsed_s": round(time.time() - t0, 1), "data_root": str(data_root)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
