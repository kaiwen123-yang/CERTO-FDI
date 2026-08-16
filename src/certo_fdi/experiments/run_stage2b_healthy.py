"""Stage 2B Phase 4: nested healthy-data expansion H40 / H80 / H160.

Generates 120 new healthy episodes with disjoint seeds on a fixed context-balanced design,
verifies that the three training sets are strictly nested and that no frozen episode was
touched, then retrains **only** the frozen ``chain_gnn_aug`` at each scale with unchanged
hyperparameters and three seeds. Calibration is refitted per scale; the encoder is never
retuned. The fault tests, including the final F4 test episodes, stay frozen throughout.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from certo_fdi.experiments.common import seed_everything, write_csv, write_json
from certo_fdi.experiments.stage2b_common import (
    Stage,
    common_parser,
    ensure_model_cfg,
    episode_seed_map,
    seedwise,
    train_cfg,
    truth_parameters,
)
from certo_fdi.stage2b import event_accounting as EA
from certo_fdi.stage2b import healthy_expansion as HE


def main() -> int:
    ap = common_parser("Stage 2B Phase 4: nested healthy-data expansion")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--scales", default="")
    args = ap.parse_args()
    st = Stage(args, "healthy")
    if not st.require_freeze():
        return 3
    import torch
    import yaml

    from certo_fdi.data.windows import load_episode_arrays
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.evaluation_chain_baseline import evaluate_run_stage1rb
    from certo_fdi.experiments.pipeline import load_checkpoint, train_model
    from certo_fdi.experiments.run_stage2a_baseline import summarise

    cfg = ensure_model_cfg(st.cfg)
    bundle = st.bundle
    he = cfg["healthy_expansion"]
    totals = [int(t) for t in he["totals"]]
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [int(s) for s in he["retrain_seeds"]]
    scales = [s for s in (args.scales.split(",") if args.scales else [f"H{t}" for t in totals])]
    out_root = Path(cfg["paths"]["stage2b_data_root"]) / "healthy_expansion"
    frozen_cfg = yaml.safe_load((st.repo_root / "configs" / "frozen_dataset_protocol.yaml").read_text())

    # ---------------------------------------------------------------- generate
    specs = HE.design_table(cfg)
    other = set(episode_seed_map(st.data_root).values())
    cal_root = Path(cfg["paths"]["stage2b_data_root"]) / "contact_calibration_F4"
    if (cal_root / "episode_index.csv").exists():
        other |= set(episode_seed_map(cal_root).values())
    disjoint = HE.seeds_are_disjoint(specs, other)
    st.log(f"healthy expansion seed disjointness: {disjoint['disjoint']} (new range {disjoint['new_seed_range']})")
    if not disjoint["disjoint"]:
        st.log("BLOCKED: healthy-expansion seeds collide with existing episode seeds")
        return 5
    truth = truth_parameters(st.data_root)
    rows = HE.generate(frozen_cfg, str(cfg["paths"]["mjcf_path"]), truth, specs, out_root,
                       log=st.log, workers=args.workers)
    from certo_fdi.experiments.precompute_gmo import main as gmo_main

    gmo_main(["--config", str(st.repo_root / "configs" / "frozen_dataset_protocol.yaml"),
              "--data-root", str(out_root), "--workers", str(args.workers)])

    sets = HE.nested_ids(list(bundle.train_ids), specs, totals)
    nested = HE.check_nested(sets, totals)
    st.log(f"nested check: {nested['nested']} sizes {nested['sizes']}")
    if not (nested["nested"] and nested["sizes_correct"]):
        st.log("BLOCKED: the H40/H80/H160 training sets are not strictly nested")
        return 6
    man = HE.write_manifest(out_root, rows, cfg, nested, disjoint)
    st.log(f"healthy expansion ready: {man['n_new_episodes']} new episodes, manifest {man['content_manifest_sha256'][:16]}")

    # ---------------------------------------------------------------- extend the bundle in memory
    ext_index = {r["episode_id"]: r for r in rows}
    for eid, r in ext_index.items():
        if eid not in bundle.episodes:
            bundle.episodes[eid] = load_episode_arrays(r, bundle.base_chain)
    st.log(f"bundle extended to {len(bundle.episodes)} episodes (frozen episodes untouched on disk)")

    # ---------------------------------------------------------------- retrain per scale
    tcfg = train_cfg(cfg)
    fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
    ckpt_dir = st.layout.sub("checkpoints")
    runs = st.layout.sub("p4_healthy") / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    ecfg = EA.EventConfig.from_cfg(cfg)
    lc_rows: list[dict] = []
    tables_by_scale: dict[str, dict[str, list[dict]]] = {}
    infos_by_scale: dict[str, list[dict]] = {}

    for scale in scales:
        train_ids = sets[scale]
        tables: dict[str, list[dict]] = {k: [] for k in ("healthy_prediction", "detection", "ood_healthy", "localization", "localization_detail", "frame_invariance", "latency", "heads")}
        infos: list[dict] = []
        for seed in seeds:
            out_json = runs / f"chain_gnn_aug_{scale}_seed{seed}.json"
            if out_json.exists():
                res = json.loads(out_json.read_text())
                st.log(f"[{scale} seed {seed}] cached")
            else:
                seed_everything(seed)
                t0 = time.time()
                info = train_model("chain_gnn_aug", seed, list(train_ids), bundle, cfg, ckpt_dir, st.device,
                                   epochs=tcfg["epochs"], batch_size=tcfg["batch_size"], lr=float(fc["lr"]),
                                   patience=tcfg["patience"], min_epochs=tcfg["min_epochs"], log=st.lines,
                                   scheduler=fc["scheduler"], weight_decay=tcfg["weight_decay"],
                                   grad_clip=tcfg["grad_clip"], tag=f"{fc['tag']}_{scale}")
                st.log(f"[{scale} seed {seed}] trained on {len(train_ids)} healthy episodes: "
                       f"params={info['n_params']} epochs={info['epochs_run']} best_val={info['best_val_loss']:.4f} ({time.time() - t0:.0f}s)")
                brow = {"run_id": st.layout.run_id, "git_sha": "", "config_sha256": st.cfg_sha,
                        "dataset_sha256_or_manifest_sha": st.manifest_sha, "model": info["name"], "seed": seed,
                        "split": "", "checkpoint_sha256": info["checkpoint_sha256"], "status": "OK",
                        "provisional": False, "strict_claim": "", "training_fraction": 1.0,
                        "config_tag": f"{fc['tag']}_{scale}", "healthy_total": len(train_ids), "scale": scale}
                ev = evaluate_run_stage1rb(info["model"], info, list(train_ids), bundle, cfg, brow, st.device,
                                           full=False, frame_manifest=None, quantile=0.995, log=st.lines,
                                           acceleration_diagnostic=False)
                res = {"train_info": [{k: v for k, v in info.items() if k != "model"}], **ev}
                res["train_info"][0].update({"seed": seed, "scale": scale, "healthy_total": len(train_ids)})
                write_json(out_json, res)
                del info
                if st.device.startswith("cuda"):
                    torch.cuda.empty_cache()
            for k in tables:
                tables[k] += res.get(k, [])
            infos += res.get("train_info", [])
        tables_by_scale[scale] = tables
        infos_by_scale[scale] = infos

        summary = summarise(tables)
        m = summary.get("chain_gnn_aug", {})
        import pandas as pd

        det = pd.DataFrame(tables["detection"]) if tables["detection"] else pd.DataFrame()
        by_seed_auroc, by_seed_rmse, by_seed_f4 = {}, {}, {}
        for seed in seeds:
            si = [t for t in infos if int(t.get("seed", -1)) == seed]
            by_seed_rmse[seed] = float(si[0].get("val_healthy_rmse_nm", float("nan"))) if si else float("nan")
            if not det.empty:
                dd = det[(det.seed == seed) & (det.density_variant == "residual_only") & (det.family == "ALL")
                         & (det.severity.astype(str) == "ALL") & (det.split == "ALL")]
                by_seed_auroc[seed] = float(dd["auroc"].mean()) if len(dd) else float("nan")
                d4 = det[(det.seed == seed) & (det.density_variant == "residual_only") & (det.family == "F4_contact")
                         & (det.severity.astype(str) == "ALL") & (det.split == "ALL")]
                by_seed_f4[seed] = float(d4["auroc"].mean()) if len(d4) else float("nan")
        lc_rows.append(st.base_row(method="chain_gnn_aug", partition="frozen_test", split="ALL", seed="mean",
                                   fault_family="ALL", scale=scale, n_healthy_train_episodes=len(train_ids),
                                   auroc_all=m.get("auroc_ALL"), auroc_s1=m.get("auroc_S1"),
                                   auroc_s2=m.get("auroc_S2"), auroc_s4=m.get("auroc_S4"),
                                   auroc_ood=m.get("auroc_OOD"),
                                   auroc_f4=float(np.nanmean(list(by_seed_f4.values()))) if by_seed_f4 else float("nan"),
                                   healthy_rmse_s0_nm=m.get("rmse_post_S0"),
                                   rmse_ratio_s0=m.get("rmse_ratio_S0"),
                                   loc_cf_top1=m.get("loc_cf_top1_ALL"), loc_cf_distance=m.get("loc_cf_dist_ALL"),
                                   auroc_all_by_seed=json.dumps({str(k): v for k, v in by_seed_auroc.items()}),
                                   val_rmse_by_seed=json.dumps({str(k): v for k, v in by_seed_rmse.items()}),
                                   n_seeds=len(seeds),
                                   units="AUROC dimensionless; RMSE in N m; chain distance in links"))
        for k, rowsk in tables.items():
            if rowsk:
                write_csv(st.layout.sub("p4_healthy") / f"stage2b_{scale}_{k}.csv", rowsk)
        write_json(st.layout.sub("p4_healthy") / f"stage2b_{scale}_summary.json", summary)

    # ---------------------------------------------------------------- monotonicity
    import pandas as pd

    lc = pd.DataFrame(lc_rows).sort_values("n_healthy_train_episodes")
    mono = {}
    for col in ("auroc_all", "auroc_s1", "auroc_f4", "healthy_rmse_s0_nm"):
        if col not in lc:
            continue
        v = lc[col].astype(float).to_numpy()
        better = np.diff(v) < 0 if "rmse" in col else np.diff(v) > 0
        mono[col] = {"values": v.tolist(), "scales": lc["scale"].tolist(),
                     "monotone_improving": bool(better.all()), "n_improving_steps": int(better.sum()),
                     "n_steps": int(len(better))}
    write_json(st.layout.results / "stage2b_healthy_expansion_manifest.json",
               {"manifest": {k: v for k, v in man.items() if k != "episode_sha256"},
                "nested": nested, "seed_disjointness": disjoint, "scales": scales, "seeds": seeds,
                "monotonicity": mono,
                "requirement": he["monotonicity_requirement"],
                "extrapolation_beyond_h160": "forbidden"})
    st.write_table("stage2b_healthy_learning_curve.csv", lc_rows,
                   units="AUROC dimensionless; RMSE in N m; one row per training-set size, seed-averaged",
                   schema={"scale": "H40 | H80 | H160", "n_healthy_train_episodes": "training-set size"})
    st.log(f"learning curve: {json.dumps({k: v['values'] for k, v in mono.items()})}")
    st.finish({"scales": scales, "seeds": seeds})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
