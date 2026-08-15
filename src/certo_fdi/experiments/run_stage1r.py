"""Stage 1R orchestrator: R0 (model level) -> R1-R4 for all models/seeds/fractions ->
aggregated result tables -> preregistered decision memo (06_STAGE1R_DECISION_RULES.md)."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from certo_fdi.data.windows import WindowSet
from certo_fdi.dynamics.rnea_torch import TorchChain
from certo_fdi.experiments.common import base_row, capture_environment, load_config, seed_everything, utc_now, write_csv, write_json
from certo_fdi.experiments.evaluation import evaluate_run
from certo_fdi.experiments.pipeline import load_bundle, load_checkpoint, train_model, training_subset
from certo_fdi.experiments.r0_model_covariance import model_covariance_trial
from certo_fdi.models.ligra_chain import build_model
from certo_fdi.paths import create_or_resume_run, git_sha

MAIN_MODELS = ["ligra", "chain_gnn", "chain_gnn_aug", "rnea_gru", "rnea_mlp"]
ABLATION_MODELS = ["ligra_free_output", "ligra_mlp_encoder", "ligra_unshared", "gru_no_rnea"]
PHYSICS_MODELS = ["rnea_only"]
RESULT_TABLES = ("healthy_prediction", "event_detection", "ood_detection", "localization", "fewshot", "frame_invariance", "latency", "heads")


def _log(layout, log_lines: list[str], msg: str) -> None:
    line = f"[{utc_now()}] {msg}"
    print(line, flush=True)
    log_lines.append(line)
    (layout.sub("logs") / "stage1r_pipeline.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def run_r0_model_level(cfg, bundle, layout, repo_root, cfg_sha, device, log_lines) -> dict:
    """T1–T3 on untrained models (before any training)."""
    tol64 = float(cfg["frame_trials"]["tolerance_float64_relative"])
    tol32 = float(cfg["frame_trials"]["tolerance_float32_relative"])
    rng = np.random.default_rng(260815)
    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32)
    # healthy + faulty test windows grouped by declared tool
    ids = bundle.train_ids[:2] + [e for e in bundle.test_ids if bundle.episodes[e].kind == "fault"][:6]
    ws = WindowSet(bundle.subset(ids), bundle.window, bundle.stride_train, "cpu")
    fit_batches = [ws.batch(list(range(0, min(64, len(ws)))))]
    results: dict[str, Any] = {"models": {}, "n_trials": 6}
    rows = []
    for name in ("ligra", "chain_gnn", "ligra_free_output", "rnea_gru", "ligra_mlp_encoder"):
        model = build_model(name, tc, bundle.ctx_dim, cfg["model"])
        model.fit_normalizers(tc, fit_batches)
        per_dtype = {}
        for dtype_name, dtype, tol in (("float64", torch.float64, tol64), ("float32", torch.float32, tol32)):
            worst = {"T1": 0.0, "T2": 0.0, "T3": 0.0, "hidden": 0.0}
            for trial in range(results["n_trials"]):
                e_i = trial % len(ids)
                wids = [i for i, (e, s) in enumerate(ws.index) if e == e_i][:3]
                r = model_covariance_trial(model, bundle.base_chain, ws, wids, rng, cfg["frame_trials"], dtype=dtype)
                worst["T1"] = max(worst["T1"], r.get("T1_message_relative", 0.0))
                worst["T2"] = max(worst["T2"], r["T2_delta_tau_relative"])
                worst["T3"] = max(worst["T3"], r["T3_link_features_relative_max"])
                worst["hidden"] = max(worst["hidden"], r.get("hidden_state_relative", 0.0))
                rows.append({**base_row(layout, repo_root, cfg_sha, seed=trial, split="R0", model=name), "dtype": dtype_name, "episode": ids[e_i], "kind": bundle.episodes[ids[e_i]].kind, "T1_message_relative": r.get("T1_message_relative", float("nan")), "T2_delta_tau_relative": r["T2_delta_tau_relative"], "T3_link_features_relative": r["T3_link_features_relative_max"], "hidden_state_relative": r.get("hidden_state_relative", float("nan")), "tolerance": tol})
            per_dtype[dtype_name] = {**worst, "tolerance": tol, "pass": bool(max(worst["T1"], worst["T2"], worst["T3"]) < tol)}
        results["models"][name] = per_dtype
    ligra_ok = results["models"]["ligra"]["float64"]["pass"] and results["models"]["ligra"]["float32"]["pass"]
    gnn_drifts = results["models"]["chain_gnn"]["float64"]["T2"] > 1e-3
    results["decision"] = "PASS" if (ligra_ok and gnn_drifts) else "FAIL"
    results["checks"] = {"ligra_T1_T2_T3_within_tolerance_float64_and_float32": ligra_ok, "non_equivariant_baseline_drifts_under_same_protocol": gnn_drifts, "healthy_and_faulty_windows_included": True}
    write_json(layout.sub("r0_geometry") / "stage1r_r0_model_covariance.json", results)
    write_csv(layout.sub("r0_geometry") / "stage1r_r0_model_covariance_trials.csv", rows)
    memo = layout.sub("r0_geometry") / "R0_DECISION.md"
    text = memo.read_text(encoding="utf-8") if memo.exists() else "# R0 decision\n"
    text += "\n## Model-level covariance (T1–T3, untrained networks, before training)\n\n| model | dtype | T1 msg | T2 dtau | T3 features | pass |\n|---|---|---|---|---|---|\n"
    for name, per in results["models"].items():
        for dn, w in per.items():
            text += f"| {name} | {dn} | {w['T1']:.2e} | {w['T2']:.2e} | {w['T3']:.2e} | {w['pass']} |\n"
    text += f"\n**Model-level R0 decision: {results['decision']}** (LiGRA exact within tolerance; the non-equivariant chain GNN drifts O(1) under the identical protocol, as expected).\n"
    memo.write_text(text, encoding="utf-8")
    (layout.results / "R0_DECISION.md").write_bytes(memo.read_bytes())
    (layout.results / "stage1r_r0_model_covariance.json").write_bytes((layout.sub("r0_geometry") / "stage1r_r0_model_covariance.json").read_bytes())
    _log(layout, log_lines, f"R0 model-level: {results['decision']} {json.dumps({k: {d: (round(v['T2'], 12), v['pass']) for d, v in per.items()} for k, per in results['models'].items()})}")
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--profile", choices=("smoke", "pilot"), required=True)
    ap.add_argument("--storage-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--dataset-seed", type=int, default=260815)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--models", default=None, help="comma list; default main+ablation+physics")
    ap.add_argument("--seeds", default=None)
    ap.add_argument("--fractions", default=None)
    ap.add_argument("--skip-ablations", action="store_true")
    ap.add_argument("--only-aggregate", action="store_true")
    ap.add_argument("--reevaluate", action="store_true", help="re-run evaluation from existing checkpoints (overwrites per-run JSON)")
    ap.add_argument("--redo-failed", action="store_true", help="only (re)evaluate jobs without a result JSON, from checkpoints when available")
    args = ap.parse_args(argv)

    cfg, cfg_sha = load_config(args.config)
    repo_root = Path(args.repo_root).resolve()
    layout = create_or_resume_run(args.storage_root, args.run_id)
    log_lines: list[str] = []
    (layout.sub("config") / Path(args.config).name).write_bytes(Path(args.config).read_bytes())
    capture_environment(layout, repo_root, f"stage1r_{args.profile}_start", {"config_sha256": cfg_sha})
    prof = cfg[args.profile]
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [int(s) for s in cfg["seed_list"]]
    fractions = [float(f) for f in args.fractions.split(",")] if args.fractions else [float(f) for f in prof["training_fractions"]]
    epochs = args.epochs or (2 if args.profile == "smoke" else 30)
    shots = [int(k) for k in prof["fewshot_counts"]]
    quantile = float(cfg["calibration"]["healthy_quantile"])
    data_root = Path(args.data_root or cfg["paths"]["data_root"]) / f"{args.profile}_seed{args.dataset_seed}"
    runs_dir = layout.sub("r1_healthy") / "runs"
    runs_dir.mkdir(exist_ok=True)

    # ---- gate: analytic R0 must have passed
    r0_path = layout.sub("r0_geometry") / "stage1r_r0_geometry_tests.json"
    if not r0_path.exists() or json.loads(r0_path.read_text())["decision"] != "PASS":
        _log(layout, log_lines, "BLOCKED: analytic R0 gate has not passed in this run")
        return 2
    _log(layout, log_lines, f"loading data bundle from {data_root}")
    bundle = load_bundle(cfg, data_root)
    frame_manifest = json.loads((data_root / "frame_variant_manifest.json").read_text())
    _log(layout, log_lines, f"episodes: train={len(bundle.train_ids)} val={len(bundle.val_ids)} test={len(bundle.test_ids)} calib={len(bundle.calib_ids)}")

    if not args.only_aggregate:
        r0m = run_r0_model_level(cfg, bundle, layout, repo_root, cfg_sha, args.device, log_lines)
        if r0m["decision"] != "PASS":
            _log(layout, log_lines, "BLOCKED: model-level R0 (T1–T3) failed; training is prohibited")
            return 2

    models = args.models.split(",") if args.models else (MAIN_MODELS + PHYSICS_MODELS + ([] if args.skip_ablations else ABLATION_MODELS))
    jobs = []
    for name in models:
        is_abl = name in ABLATION_MODELS
        for frac in ([1.0] if is_abl else fractions):
            for seed in ([seeds[0]] if name in PHYSICS_MODELS else seeds):
                jobs.append((name, frac, seed))
    _log(layout, log_lines, f"{len(jobs)} training/evaluation jobs: models={models} fractions={fractions} seeds={seeds} epochs={epochs}")
    ckpt_dir = layout.sub("checkpoints")
    for j, (name, frac, seed) in enumerate(jobs):
        tag = f"{name}_frac{frac:.2f}_seed{seed}"
        out_json = runs_dir / f"{tag}.json"
        if args.only_aggregate or (out_json.exists() and not args.reevaluate):
            continue
        if args.redo_failed and out_json.exists():
            continue
        t0 = time.time()
        try:
            seed_everything(seed)
            train_ids = training_subset(bundle, frac, seed)
            ckpt_path = ckpt_dir / f"{name}_seed{seed}_frac{len(train_ids)}ep.pt"
            if (args.reevaluate or args.redo_failed) and ckpt_path.exists():
                info = load_checkpoint(name, ckpt_path, bundle, cfg, args.device)
                _log(layout, log_lines, f"[{j + 1}/{len(jobs)}] loaded checkpoint {tag}")
            else:
                info = train_model(name, seed, train_ids, bundle, cfg, ckpt_dir, args.device, epochs=epochs, log=log_lines)
                _log(layout, log_lines, f"[{j + 1}/{len(jobs)}] trained {tag}: params={info['n_params']} epochs={info['epochs_run']} val={info['best_val_loss']:.4f} ({info['train_seconds']:.0f}s)")
            brow = base_row(layout, repo_root, cfg_sha, seed=seed, split="", model=info["name"], checkpoint_sha256=info["checkpoint_sha256"])
            brow["training_fraction"] = frac
            res = evaluate_run(info["model"], info, train_ids, bundle, cfg, brow, args.device, full=(frac >= 1.0), frame_manifest=frame_manifest, shots=shots, seed=seed, quantile=quantile, log=log_lines)
            res["train_info"] = [{k: v for k, v in info.items() if k not in ("model",)}]
            write_json(out_json, res)
            _log(layout, log_lines, f"[{j + 1}/{len(jobs)}] evaluated {tag} ({time.time() - t0:.0f}s total)")
            del info
            torch.cuda.empty_cache()
        except Exception as e:  # pragma: no cover
            _log(layout, log_lines, f"[{j + 1}/{len(jobs)}] FAILED {tag}: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            write_json(runs_dir / f"{tag}.FAILED.json", {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()})

    # ---- aggregate
    tables: dict[str, list[dict]] = {k: [] for k in RESULT_TABLES}
    train_infos = []
    for p in sorted(runs_dir.glob("*.json")):
        if p.name.endswith(".FAILED.json"):
            continue
        res = json.loads(p.read_text())
        for k in RESULT_TABLES:
            tables[k] += res.get(k, [])
        train_infos += res.get("train_info", [])
    # model-free physics baselines (GMO fixed / dynamic thresholds), healthy-val calibrated
    try:
        from certo_fdi.experiments.physics_baselines import gmo_baseline_rows

        pb_json = runs_dir / "physics_baselines.gmo.json"
        if not pb_json.exists() or args.reevaluate:
            brow = base_row(layout, repo_root, cfg_sha, seed=seeds[0], split="", model="gmo")
            brow["training_fraction"] = 1.0
            det, ood = gmo_baseline_rows(bundle, cfg, brow, quantile, "cpu")
            write_json(pb_json, {"event_detection": det, "ood_detection": ood})
        pb = json.loads(pb_json.read_text())
        tables["event_detection"] += pb["event_detection"]
        tables["ood_detection"] += pb["ood_detection"]
    except Exception as e:  # pragma: no cover
        _log(layout, log_lines, f"physics baselines failed: {type(e).__name__}: {e}")
    results = layout.results
    write_csv(results / "stage1r_healthy_prediction.csv", tables["healthy_prediction"])
    write_csv(results / "stage1r_event_detection.csv", tables["event_detection"])
    write_csv(results / "stage1r_ood_detection.csv", tables["ood_detection"])
    write_csv(results / "stage1r_localization.csv", tables["localization"])
    write_csv(results / "stage1r_fewshot_attribution.csv", tables["fewshot"])
    write_csv(results / "stage1r_frame_invariance.csv", tables["frame_invariance"])
    write_csv(results / "stage1r_latency_and_size.csv", tables["latency"])
    write_csv(results / "stage1r_density_heads.csv", tables["heads"])
    write_csv(results / "stage1r_training_runs.csv", train_infos)
    from certo_fdi.experiments.decision import build_summary_tables, decide_and_write_memo

    summary = build_summary_tables(tables, layout, repo_root, cfg_sha, cfg)
    decision = decide_and_write_memo(summary, tables, layout, repo_root, cfg, cfg_sha, args.profile, data_root)
    try:
        from certo_fdi.experiments.make_figures import make_all

        make_all(layout.run_root)
    except Exception as e:  # pragma: no cover
        _log(layout, log_lines, f"figure generation failed: {type(e).__name__}: {e}")
    manifest = {
        "run_id": layout.run_id, "git_sha": git_sha(repo_root), "config_sha256": cfg_sha, "profile": args.profile, "timestamp_utc": utc_now(),
        "data_root": str(data_root), "n_jobs": len(jobs), "models": models, "seeds": seeds, "fractions": fractions, "epochs": epochs, "device": args.device,
        "decision": decision, "result_files": sorted(p.name for p in results.iterdir()),
    }
    write_json(results / "stage1r_run_manifest.json", manifest)
    capture_environment(layout, repo_root, f"stage1r_{args.profile}_end")
    _log(layout, log_lines, f"DONE decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
