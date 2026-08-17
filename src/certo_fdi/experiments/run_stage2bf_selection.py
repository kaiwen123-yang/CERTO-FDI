"""Stage 2B-F Phase 3/E: reproduce the Stage 2B F4_CAL localizer selection under canonical names.

The selection is replayed with the frozen helpers -- ``_aligned_stats``, ``_episode_records``,
``_loc_metrics`` and ``selective_localization.select_feature_and_threshold`` are imported from the
Stage 2B modules, not reimplemented -- so the only thing this file supplies is the frozen inputs
and the canonical naming.

Two deliberate choices:

* the F4_CAL episode list is rebuilt from the **historical manifest CSV**, never by calling
  ``contact_calibration.generate_partition``. Regenerating an episode is forbidden, and a
  generator that happens to be idempotent is not a licence to run it.
* the ridge is scored on F4_CAL for the audit table only and is flagged
  ``is_selection_candidate = false``. The candidate set stays exactly Stage 2B's five. A selection
  that could see the ridge would not be a reproduction of Stage 2B's selection.

F4_TEST is not opened anywhere in this file.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from certo_fdi.data.windows import load_episode_arrays
from certo_fdi.experiments.common import load_config, write_json
from certo_fdi.experiments.run_stage2b_localization import _aligned_stats, _episode_records, _loc_metrics
from certo_fdi.experiments.stage2a_pathway_pipeline import (
    WindowGrid,
    episode_windows,
    fit_whiteners,
    load_pathways,
    stack_window_residual,
)
from certo_fdi.experiments.stage2b_common import ensure_model_cfg
from certo_fdi.pathways.jacobians import candidate_points
from certo_fdi.stage2b import rank_aware_scores as RS
from certo_fdi.stage2b import selective_localization as SL
from certo_fdi.stage2bf import estimator_identity as EI


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2B-F F4_CAL selection reproduction")
    ap.add_argument("--config", required=True)
    ap.add_argument("--stage2b-config", required=True)
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import load_bundle, load_checkpoint

    fcfg = yaml.safe_load(Path(args.config).read_text())
    cfg, _sha = load_config(args.stage2b_config)
    cfg = ensure_model_cfg(cfg)
    root = Path(args.run_root)
    res = root / "results"
    res.mkdir(parents=True, exist_ok=True)
    log: list[str] = []

    def say(m: str) -> None:
        line = f"[{utc_now()}] {m}"
        print(line, flush=True)
        log.append(line)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "logs" / "stage2bf_selection.log").write_text("\n".join(log) + "\n", encoding="utf-8")

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    stage2b_run = Path(fcfg["paths"]["stage2b_run_root"])
    data_root = Path(fcfg["paths"]["data_root"]) / \
        f"{cfg['frozen_inputs']['dataset_profile']}_seed{cfg['frozen_inputs']['dataset_seed']}"
    cal_cache = stage2b_run / "p2_localization" / "cache"
    test_cache = stage2b_run / "p1_loadpath" / "cache"
    seeds = [int(s) for s in cfg["seed_list"]]
    loc_cfg = cfg["localization"]
    n_pert = int(loc_cfg["perturbation_replicates"])
    coverages = [float(c) for c in loc_cfg["selective_coverages"]]
    min_cov = float(cfg["decision"]["go"]["selective_coverage_min"])

    say("Stage 2B-F F4_CAL selection reproduction start")

    # ---- F4_CAL episode list: rebuilt from the historical manifest, never regenerated
    man_csv = stage2b_run / "results" / "stage2b_contact_calibration_manifest.csv"
    with man_csv.open(newline="", encoding="utf-8") as f:
        man_rows = list(csv.DictReader(f))
    # `family`/`kind` are not manifest columns: the manifest records the family as `fault_family`
    # and every F4_CAL episode is a fault by construction (contact_calibration generates only faults)
    cal_rows = [{**r, "seed": int(r["seed"]), "truth_link": int(r["truth_link"]),
                 "family": r.get("fault_family") or "F4_contact", "kind": "fault"} for r in man_rows]
    cal_index = {r["episode_id"]: r for r in cal_rows}
    missing = [r["episode_id"] for r in cal_rows if not Path(r["path"]).is_file()]
    say(f"F4_CAL from frozen manifest: {len(cal_rows)} episodes, {len(missing)} missing on disk")
    if missing:
        say(f"BLOCKED: F4_CAL episodes absent: {missing[:5]}")
        return 4

    bundle = load_bundle(cfg, data_root)
    chain = bundle.base_chain
    n_links = bundle.n_links
    grid = WindowGrid.build(int(cfg["simulation"]["window_samples"]), int(cfg["pathway"]["window_time_points"]))
    d = n_links * grid.n_points
    tc = TorchChain.from_chain(chain, dtype=torch.float32, device=device)
    cpoints = candidate_points(chain)
    healthy_ids = list(bundle.train_ids) + list(bundle.val_ids)

    hist = json.loads((stage2b_run / "results" / "stage2b_localizer_selection.json").read_text())
    selection, rows, gate = {}, [], {"per_seed": {}, "all_pass": True}

    for seed in seeds:
        t0 = time.time()
        fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
        ck = stage2b_run / "checkpoints" / f"chain_gnn_aug_{fc['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        model = load_checkpoint("chain_gnn_aug", ck, bundle, cfg, device)["model"]
        healthy_w = [episode_windows(model, bundle.episodes[e], bundle, tc, grid, device) for e in healthy_ids]
        win_wh, _ = fit_whiteners(healthy_w, cfg)
        W = win_wh.whitener

        # healthy-validation acceptance thresholds (frozen recipe, healthy only)
        rss_h = []
        for h in healthy_w[-len(bundle.val_ids):]:
            zh = win_wh.transform(stack_window_residual(h.resid), h.ctx)
            pw = load_pathways(test_cache, h.episode_id)
            rss_h.append(_aligned_stats(pw, h.rows, zh, cpoints, W, n_links, d).rss)
        acceptance = RS.healthy_acceptance_thresholds(
            np.concatenate(rss_h), float(loc_cfg["minimal_consistent_link_quantile"]))

        # score F4_CAL
        recs, parts = {k: [] for k in ("episode", "split", "label", "target")}, []
        for r in cal_rows:
            ea = load_episode_arrays(cal_index[r["episode_id"]], chain)
            pw = load_pathways(cal_cache, r["episode_id"])
            ew = episode_windows(model, ea, bundle, tc, grid, device)
            z = win_wh.transform(stack_window_residual(ew.resid), ew.ctx)
            parts.append(_aligned_stats(pw, ew.rows, z, cpoints, W, n_links, d))
            nw = ew.resid.shape[0]
            recs["episode"].append(np.full(nw, r["episode_id"], dtype=object))
            recs["split"].append(np.full(nw, ea.split, dtype=object))
            recs["label"].append(ew.label)
            recs["target"].append(ew.target)
        cal_rec = {k: np.concatenate(v) for k, v in recs.items()}
        cal_S = RS.ProjectionStats(
            rss=np.concatenate([s.rss for s in parts]), ess=np.concatenate([s.ess for s in parts]),
            rank=np.concatenate([s.rank for s in parts]),
            z_energy=np.concatenate([s.z_energy for s in parts]), dimension=d)
        say(f"[seed {seed}] F4_CAL scored ({time.time() - t0:.0f}s)")

        # the five Stage 2B candidates -- the ridge is NOT among them
        cal_by_score = {}
        for score in RS.SCORES:
            conf = _episode_records(cal_S, cal_rec, score, acceptance, d, n_pert, seed)
            cal_by_score[score] = {"conf": conf, **_loc_metrics(conf)}
        best = sorted(RS.SCORES, key=lambda s: (-cal_by_score[s]["top1"],
                                                cal_by_score[s]["chain_distance"], s))[0]
        rej = SL.select_feature_and_threshold(cal_by_score[best]["conf"], coverages, min_cov)

        h = hist["per_seed"][str(seed)]
        ok_score = EI.canonical_name(best) == EI.canonical_name(h["score"])
        ok_top1 = cal_by_score[best]["top1"] == h["calibration_top1"]
        ok_cd = cal_by_score[best]["chain_distance"] == h["calibration_chain_distance"]
        ok_thr = bool(np.allclose(acceptance, np.array(h["acceptance_thresholds"]), rtol=0, atol=0))
        hr = h.get("reject") or {}
        sr = rej.get("selected") or {}
        ok_rej = (sr.get("feature") == hr.get("feature")
                  and float(sr.get("threshold", np.nan)) == float(hr.get("threshold", np.nan))
                  and float(sr.get("calibration_selective_top1", np.nan))
                  == float(hr.get("calibration_selective_top1", np.nan)))
        ok_all = all([ok_score, ok_top1, ok_cd, ok_thr, ok_rej])
        gate["all_pass"] &= ok_all
        gate["per_seed"][str(seed)] = {
            "selected_score_exact": ok_score, "calibration_top1_exact": ok_top1,
            "calibration_chain_distance_exact": ok_cd, "acceptance_thresholds_bit_exact": ok_thr,
            "reject_rule_exact": ok_rej,
            "replay_selected_canonical": EI.canonical_name(best),
            "historical_selected_canonical": EI.canonical_name(h["score"]),
            "replay_calibration_top1": cal_by_score[best]["top1"],
            "historical_calibration_top1": h["calibration_top1"]}
        say(f"[seed {seed}] selected {EI.canonical_name(best)} (cal top1 {cal_by_score[best]['top1']:.4f}) "
            f"-> {'PASS' if ok_all else 'FAIL ' + str([k for k, v in {'score': ok_score, 'top1': ok_top1, 'cd': ok_cd, 'thr': ok_thr, 'rej': ok_rej}.items() if not v])}")

        selection[str(seed)] = {
            "canonical_score": EI.canonical_name(best),
            "calibration_top1": cal_by_score[best]["top1"],
            "calibration_chain_distance": cal_by_score[best]["chain_distance"],
            "reject": sr, "reject_rule": rej.get("rule"),
            "acceptance_thresholds": acceptance.tolist(),
            "all_scores": {EI.canonical_name(s): {k: v for k, v in cal_by_score[s].items() if k != "conf"}
                           for s in RS.SCORES}}
        for s in RS.SCORES:
            rows.append({"seed": seed, "partition": "F4_CAL",
                         "canonical_score": EI.canonical_name(s),
                         "estimator_family": "truncated_svd" if s == RS.AUDIT_CONTROL_SCORE
                         else "truncated_svd_rank_aware",
                         "episode_top1": cal_by_score[s]["top1"],
                         "mean_chain_distance": cal_by_score[s]["chain_distance"],
                         "n_episodes": cal_by_score[s]["n_episodes"],
                         "selected": bool(s == best),
                         "is_selection_candidate": True, "is_audit_baseline": False})
        rows.append({"seed": seed, "partition": "F4_CAL",
                     "canonical_score": EI.RIDGE_CANONICAL, "estimator_family": "ridge",
                     "episode_top1": None, "mean_chain_distance": None, "n_episodes": None,
                     "selected": False, "is_selection_candidate": False, "is_audit_baseline": True})

    out = {"generated_utc": utc_now(), "selection_partition": "F4_CAL",
           "rule": "highest episode top-1 on F4_CAL; ties -> lower chain distance, then alphabetical",
           "final_test_untouched_at_selection_time": True,
           "candidates_considered": [EI.canonical_name(s) for s in RS.SCORES],
           "ridge_excluded_from_selection": True,
           "audit_control_canonical": EI.canonical_name(RS.AUDIT_CONTROL_SCORE),
           "per_seed": selection, "reproduction_gate": gate}
    EI.assert_no_legacy_names(out)
    write_json(res / "stage2bf_f4cal_selection_reproduction.json", out)
    EI.assert_no_legacy_names(rows)
    with (res / "stage2bf_f4cal_selection.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    say(f"F4_CAL selection reproduction: {'PASS' if gate['all_pass'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
