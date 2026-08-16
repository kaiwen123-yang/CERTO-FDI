"""Stage 2B Phase 2: F4_CAL generation, rank-aware localizer selection and accept/defer.

Order of operations matters here and is enforced by the code, not by discipline:

1. generate the ``F4_CAL`` partition with disjoint seeds and verify the disjointness;
2. score all five pre-registered localizers on ``F4_CAL`` **only** and select one;
3. calibrate the accept/defer feature and threshold on ``F4_CAL`` **only**;
4. *then* evaluate the selected localizer -- and, for the audit trail, all five -- on the
   untouched final F4 test episodes, applying the frozen threshold unchanged.

The final F4 test set is never read before the selection is written to disk.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from certo_fdi.experiments.common import write_csv, write_json
from certo_fdi.experiments.stage2a_pathway_pipeline import (
    WindowGrid,
    build_cache_parallel,
    episode_windows,
    fit_whiteners,
    load_pathways,
    stack_window_residual,
)
from certo_fdi.experiments.stage2b_common import (
    Stage,
    common_parser,
    ensure_model_cfg,
    episode_seed_map,
    paired_episode_bootstrap,
    episode_cluster_bootstrap,
    seedwise,
    truth_parameters,
)
from certo_fdi.pathways.jacobians import candidate_points
from certo_fdi.stage2b import contact_calibration as CC
from certo_fdi.stage2b import rank_aware_scores as RS
from certo_fdi.stage2b import selective_localization as SL


def _aligned_stats(pw, rows, z, cpoints, W, n_links, d):
    per_link = []
    for l in range(n_links):
        hyp = [np.einsum("de,nep->ndp", W, CC_contact(pw, rows, l, rl)) for _, rl in cpoints[l]]
        per_link.append(RS.best_hypothesis_stats(hyp, z))
    return RS.stack_links(per_link, z, d)


def CC_contact(pw, rows, link, r_link):
    from certo_fdi.pathways.dictionaries import contact_columns_batched

    return contact_columns_batched(pw, rows, link, r_link)


def _episode_records(stats: RS.ProjectionStats, rec: dict, score: str, acceptance, dimension: int,
                     n_pert: int, seed: int) -> list[SL.EpisodeConfidence]:
    """Collapse windows to one accept/defer record per fault episode."""
    pred_w = RS.predict_link(stats, score, acceptance)
    margin = RS.score_margin(stats, score, acceptance)
    evid = RS.normalized_link_evidence(stats, score, acceptance)
    out = []
    for e in np.unique(rec["episode"]):
        m = (rec["episode"] == e) & (rec["label"] == 1)
        if m.sum() == 0:
            continue
        t = int(rec["target"][m][0])
        if t < 0:
            continue
        pw_ = pred_w[m]
        v = int(np.bincount(pw_[pw_ >= 0], minlength=7).argmax()) if (pw_ >= 0).any() else -1
        adequacy = float(np.median(stats.ess[m, v] / np.maximum(stats.z_energy[m], 1e-12))) if v >= 0 else 0.0
        out.append(SL.EpisodeConfidence(
            episode_id=str(e), predicted_link=v, target_link=t, n_windows=int(m.sum()),
            split=str(rec["split"][m][0]),
            features={
                "best_second_margin": float(np.median(margin[m])),
                "subwindow_stability": SL.subwindow_stability(pw_),
                "perturbation_stability": SL.perturbation_stability(
                    stats.rss[m], stats.rank[m], stats.ess[m], dimension, score, acceptance, n_pert, seed),
                "normalized_link_evidence": float(np.median(evid[m].max(1))),
                "absolute_fit_adequacy": adequacy,
            }))
    return out


def _loc_metrics(conf: list[SL.EpisodeConfidence]) -> dict:
    if not conf:
        return {"top1": float("nan"), "chain_distance": float("nan"), "n_episodes": 0}
    P = np.array([c.predicted_link for c in conf])
    T = np.array([c.target_link for c in conf])
    return {"top1": float((P == T).mean()), "chain_distance": float(np.abs(P - T).mean()),
            "n_episodes": int(len(conf))}


def main() -> int:
    ap = common_parser("Stage 2B Phase 2: F4_CAL, rank-aware localizer selection, accept/defer")
    ap.add_argument("--seeds", default="")
    args = ap.parse_args()
    st = Stage(args, "localization")
    if not st.require_freeze():
        return 3
    import torch
    import yaml

    from certo_fdi.data.windows import load_episode_arrays
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import load_checkpoint

    cfg = ensure_model_cfg(st.cfg)
    bundle = st.bundle
    chain = bundle.base_chain
    n_links = bundle.n_links
    grid = WindowGrid.build(int(cfg["simulation"]["window_samples"]), int(cfg["pathway"]["window_time_points"]))
    d = n_links * grid.n_points
    cpoints = candidate_points(chain)
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [int(s) for s in cfg["seed_list"]]
    tc = TorchChain.from_chain(chain, dtype=torch.float32, device=st.device)
    loc_cfg = cfg["localization"]
    n_pert = int(loc_cfg["perturbation_replicates"])
    coverages = [float(c) for c in loc_cfg["selective_coverages"]]
    min_cov = float(cfg["decision"]["go"]["selective_coverage_min"])

    # ---------------------------------------------------------------- 1. F4_CAL generation
    cal_root = Path(cfg["paths"]["stage2b_data_root"]) / "contact_calibration_F4"
    frozen_cfg = yaml.safe_load((st.repo_root / "configs" / "frozen_dataset_protocol.yaml").read_text())
    specs = CC.design_table({**cfg, "faults": frozen_cfg.get("faults", {})})
    frozen_seeds = set(episode_seed_map(st.data_root).values())
    disjoint = CC.seeds_are_disjoint(specs, frozen_seeds)
    st.log(f"F4_CAL seed disjointness: {disjoint['disjoint']} (cal range {disjoint['cal_seed_range']}, frozen range {disjoint['frozen_seed_range']})")
    if not disjoint["disjoint"]:
        st.log("BLOCKED: F4_CAL seeds collide with frozen episode seeds")
        return 5
    truth = truth_parameters(st.data_root)
    rows = CC.generate_partition(frozen_cfg, str(cfg["paths"]["mjcf_path"]), truth, specs, cal_root,
                                 log=st.log, workers=args.workers)
    # r_gmo is required by the frozen episode reader
    from certo_fdi.experiments.precompute_gmo import main as gmo_main

    gmo_main(["--config", str(st.repo_root / "configs" / "frozen_dataset_protocol.yaml"),
              "--data-root", str(cal_root), "--workers", str(args.workers)])
    man = CC.write_manifest(cal_root, specs, rows, cfg, disjoint,
                            {"run_id": st.layout.run_id, "generated_by": "run_stage2b_localization"})
    st.log(f"F4_CAL ready: {man['n_episodes']} episodes, content manifest {man['content_manifest_sha256'][:16]}")
    cal_rows = [{**r} for r in rows]
    cal_index = {r["episode_id"]: r for r in cal_rows}
    build_cache_parallel(cal_rows, {r["episode_id"]: int(r["seed"]) for r in cal_rows}, cfg, grid,
                         cal_root, st.layout.sub("p2_localization") / "cache", n_workers=args.workers, log=st.log)
    st.write_table("stage2b_contact_calibration_manifest.csv",
                   [st.base_row(method="F4_CAL", partition="F4_CAL", split=r["split"], seed=r["seed"],
                                fault_family="F4_contact", episode_id=r["episode_id"], truth_link=r["truth_link"],
                                replicate=r["replicate"], path=r["path"], exists=r["exists"],
                                sha256=man["episode_sha256"].get(r["episode_id"], ""),
                                controller=r.get("ctx_controller", ""), speed_scale=r.get("ctx_speed_scale", ""),
                                tool_id=r.get("ctx_tool_id", ""), severity=r.get("fault_severity", ""),
                                onset_s=r.get("fault_onset_s", ""),
                                units="one row per generated calibration episode") for r in cal_rows],
                   units="F4_CAL partition manifest",
                   schema={"partition": "always F4_CAL", "note": "selection-only; never enters a final metric"})

    # ---------------------------------------------------------------- 2/3. selection on F4_CAL only
    f4_test = [e for e in bundle.test_ids if bundle.episodes[e].family == "F4_contact"]
    healthy_ids = list(bundle.train_ids) + list(bundle.val_ids)
    sel_rows, test_rows, rc_rows = [], [], []
    selection: dict[int, dict] = {}
    cal_cache = st.layout.sub("p2_localization") / "cache"
    test_cache = st.layout.sub("p1_loadpath") / "cache"

    for seed in seeds:
        t0 = time.time()
        fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
        ck = st.layout.sub("checkpoints") / f"chain_gnn_aug_{fc['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        model = load_checkpoint("chain_gnn_aug", ck, bundle, cfg, st.device)["model"]
        healthy_w = [episode_windows(model, bundle.episodes[e], bundle, tc, grid, st.device) for e in healthy_ids]
        win_wh, _ = fit_whiteners(healthy_w, cfg)
        W = win_wh.whitener

        # healthy-validation acceptance thresholds for minimal_consistent_link (healthy only)
        rss_h = []
        for h in healthy_w[-len(bundle.val_ids):]:
            zh = win_wh.transform(stack_window_residual(h.resid), h.ctx)
            pw = load_pathways(test_cache, h.episode_id)
            s = _aligned_stats(pw, h.rows, zh, cpoints, W, n_links, d)
            rss_h.append(s.rss)
        acceptance = RS.healthy_acceptance_thresholds(np.concatenate(rss_h), float(loc_cfg["minimal_consistent_link_quantile"]))

        def collect(ids, cache_root, get_ea):
            recs, stats_parts = {k: [] for k in ("episode", "split", "label", "target")}, []
            for eid in ids:
                ea = get_ea(eid)
                pw = load_pathways(cache_root, eid)
                ew = episode_windows(model, ea, bundle, tc, grid, st.device)
                z = win_wh.transform(stack_window_residual(ew.resid), ew.ctx)
                stats_parts.append(_aligned_stats(pw, ew.rows, z, cpoints, W, n_links, d))
                nw = ew.resid.shape[0]
                recs["episode"].append(np.full(nw, eid, dtype=object))
                recs["split"].append(np.full(nw, ea.split, dtype=object))
                recs["label"].append(ew.label)
                recs["target"].append(ew.target)
            rec = {k: np.concatenate(v) for k, v in recs.items()}
            S = RS.ProjectionStats(rss=np.concatenate([s.rss for s in stats_parts]),
                                   ess=np.concatenate([s.ess for s in stats_parts]),
                                   rank=np.concatenate([s.rank for s in stats_parts]),
                                   z_energy=np.concatenate([s.z_energy for s in stats_parts]), dimension=d)
            return rec, S

        cal_rec, cal_S = collect([r["episode_id"] for r in cal_rows], cal_cache,
                                 lambda e: load_episode_arrays(cal_index[e], chain))
        st.log(f"[seed {seed}] F4_CAL scored ({time.time() - t0:.0f}s)")

        # --- select the localizer score on F4_CAL only
        cal_by_score = {}
        for score in RS.SCORES:
            conf = _episode_records(cal_S, cal_rec, score, acceptance, d, n_pert, seed)
            m = _loc_metrics(conf)
            cal_by_score[score] = {"conf": conf, **m}
            sel_rows.append(st.base_row(method=score, partition="F4_CAL", split="ALL", seed=seed,
                                        fault_family="F4_contact", episode_top1=m["top1"],
                                        mean_chain_distance=m["chain_distance"], n_episodes=m["n_episodes"],
                                        selected=False,
                                        units="episode-level top-1 on the calibration partition only"))
        best_score = sorted(RS.SCORES, key=lambda s: (-cal_by_score[s]["top1"], cal_by_score[s]["chain_distance"], s))[0]
        for r in sel_rows:
            if r["seed"] == seed and r["method"] == best_score and r["partition"] == "F4_CAL":
                r["selected"] = True
        # --- select the accept/defer feature and threshold on F4_CAL only
        rej = SL.select_feature_and_threshold(cal_by_score[best_score]["conf"], coverages, min_cov)
        selection[seed] = {"score": best_score, "calibration_top1": cal_by_score[best_score]["top1"],
                           "calibration_chain_distance": cal_by_score[best_score]["chain_distance"],
                           "reject": rej.get("selected"), "reject_rule": rej.get("rule"),
                           "acceptance_thresholds": acceptance.tolist(),
                           "all_scores": {s: {k: v for k, v in cal_by_score[s].items() if k != "conf"} for s in RS.SCORES}}
        st.log(f"[seed {seed}] selected score={best_score} (cal top1 {cal_by_score[best_score]['top1']:.4f}); "
               f"reject={rej.get('selected')}")
        for row in rej["rows"]:
            rc_rows.append(st.base_row(method=best_score, partition="F4_CAL", split="ALL", seed=seed,
                                       fault_family="F4_contact", **row,
                                       units="risk-coverage on the calibration partition"))

    # the selection must be written before the final test set is touched
    write_json(st.layout.results / "stage2b_localizer_selection.json",
               {"selection_partition": "F4_CAL", "per_seed": selection,
                "rule": "highest episode top-1 on F4_CAL; ties -> lower chain distance, then alphabetical",
                "final_test_untouched_at_selection_time": True,
                "scores_considered": list(RS.SCORES),
                "audit_control_score": RS.AUDIT_CONTROL_SCORE})
    st.write_table("stage2b_localizer_selection.csv", sel_rows,
                   units="episode-level localization on the F4_CAL partition",
                   schema={"selected": "True for the score chosen for that seed"})

    # ---------------------------------------------------------------- 4. final F4 test evaluation
    for seed in seeds:
        fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
        ck = st.layout.sub("checkpoints") / f"chain_gnn_aug_{fc['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        model = load_checkpoint("chain_gnn_aug", ck, bundle, cfg, st.device)["model"]
        healthy_w = [episode_windows(model, bundle.episodes[e], bundle, tc, grid, st.device) for e in healthy_ids]
        win_wh, _ = fit_whiteners(healthy_w, cfg)
        W = win_wh.whitener
        acceptance = np.array(selection[seed]["acceptance_thresholds"])
        recs = {k: [] for k in ("episode", "split", "label", "target")}
        parts = []
        for eid in f4_test:
            ea = bundle.episodes[eid]
            pw = load_pathways(test_cache, eid)
            ew = episode_windows(model, ea, bundle, tc, grid, st.device)
            z = win_wh.transform(stack_window_residual(ew.resid), ew.ctx)
            parts.append(_aligned_stats(pw, ew.rows, z, cpoints, W, n_links, d))
            nw = ew.resid.shape[0]
            recs["episode"].append(np.full(nw, eid, dtype=object))
            recs["split"].append(np.full(nw, ea.split, dtype=object))
            recs["label"].append(ew.label)
            recs["target"].append(ew.target)
        rec = {k: np.concatenate(v) for k, v in recs.items()}
        S = RS.ProjectionStats(rss=np.concatenate([s.rss for s in parts]), ess=np.concatenate([s.ess for s in parts]),
                               rank=np.concatenate([s.rank for s in parts]),
                               z_energy=np.concatenate([s.z_energy for s in parts]), dimension=d)
        sel = selection[seed]
        for score in RS.SCORES:
            conf = _episode_records(S, rec, score, acceptance, d, n_pert, seed)
            m = _loc_metrics(conf)
            P = np.array([c.predicted_link for c in conf])
            T = np.array([c.target_link for c in conf])
            per_link = {int(l): float((P[T == l] == l).mean()) for l in np.unique(T)}
            row = st.base_row(method=score, partition="F4_TEST", split="ALL", seed=seed,
                              fault_family="F4_contact", episode_top1=m["top1"],
                              mean_chain_distance=m["chain_distance"], n_episodes=m["n_episodes"],
                              is_selected=bool(score == sel["score"]),
                              is_audit_control=bool(score == RS.AUDIT_CONTROL_SCORE),
                              n_links_recall_ge_040=int(sum(1 for v in per_link.values() if v >= 0.40)),
                              **{f"recall_link{l}": v for l, v in per_link.items()},
                              units="episode-level top-1 and chain distance on the untouched final F4 test set")
            if score == sel["score"] and sel.get("reject"):
                acc = SL.apply_threshold(conf, sel["reject"]["feature"], float(sel["reject"]["threshold"]))
                row.update({f"selective_{k}": v for k, v in SL.selective_metrics(conf, acc).items()})
                row["reject_feature"] = sel["reject"]["feature"]
                row["reject_threshold"] = float(sel["reject"]["threshold"])
                for r in SL.risk_coverage(conf, sel["reject"]["feature"], coverages):
                    rc_rows.append(st.base_row(method=score, partition="F4_TEST", split="ALL", seed=seed,
                                               fault_family="F4_contact", **r,
                                               units="risk-coverage on the final F4 test set (threshold frozen on F4_CAL)"))
            test_rows.append(row)
        st.log(f"[seed {seed}] final F4 test evaluated for all {len(RS.SCORES)} scores")

    st.write_table("stage2b_localization_metrics.csv", test_rows,
                   units="episode-level localization; per-link recall; selective metrics where applicable",
                   schema={"is_selected": "the score chosen on F4_CAL", "is_audit_control": "the frozen Stage 2A score"})
    st.write_table("stage2b_selective_risk.csv", rc_rows,
                   units="risk-coverage curves; thresholds frozen on F4_CAL and applied unchanged to F4_TEST",
                   schema={"partition": "F4_CAL for selection, F4_TEST for the reported result"})
    st.finish({"seeds": seeds})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
