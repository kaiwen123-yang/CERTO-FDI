"""Stage 2A Phase 5: the geometry ablations.

Every ablation uses the **same** conditional-Gaussian healthy density head, the same
leave-one-episode-out candidate selection on healthy validation windows and the same 0.995
healthy-validation threshold as the frozen Stage 1R-B baseline. Only the feature vector
changes, so a detection difference is a difference in representation -- not in head capacity,
training data or calibration. No fault window, label, severity or location enters any primary
decision.

Per seed the runner writes ``p5_ablations/scores_seed<seed>.npz`` holding, for every
evaluation window: the score of every ablation, the zero-shot link prediction and rejection
flags, the coarse-class evidence, the diagnosability map and the episode bookkeeping. Phase 6
turns those into the metric tables.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from certo_fdi.anomaly.calibration import healthy_quantile_threshold
from certo_fdi.experiments.common import write_json
from certo_fdi.experiments.evaluation import fit_head_loo
from certo_fdi.experiments.stage2a_common import Stage, common_parser, ensure_model_cfg
from certo_fdi.experiments.stage2a_pathway_pipeline import (
    WindowGrid,
    episode_windows,
    fit_whiteners,
    fit_whiteners_pre,
    load_pathways,
    stack_window_residual,
    truth_contact_point,
)
from certo_fdi.pathways.fusion import ABLATION_BLOCKS, assemble, block_dimensions, geometry_blocks_from, per_link_slices, zero_shot_coarse_class
from certo_fdi.pathways.jacobians import candidate_points, end_effector_point
from certo_fdi.pathways.localization import RejectionCalibration, localize
from certo_fdi.pathways.window_features import FAMILY_KEYS, episode_geometry, feature_block_names

DIAG_KEYS = ("contact_observability", "contact_observability_best_link", "fisher_min_eigenvalue",
             "link_min_angle", "fault_family_min_angle", "predicted_ambiguity", "entropy", "ee_jacobian_sigma_min")


def _geometry_for(ep_arrays, pw, ew, win_wh, inst_wh, cfg, chain, rng, *, pre: bool = False):
    """Window geometry of one episode, on the corrected (or pre-correction) residual."""
    z_win = win_wh.transform(stack_window_residual(ew.resid_pre if pre else ew.resid), ew.ctx)
    z_inst = inst_wh.transform((ew.resid_pre if pre else ew.resid)[:, -1, :], ew.ctx)
    shuffle = None if pre else rng.permutation(ew.rows.reshape(-1)).reshape(ew.rows.shape)
    return z_win, z_inst, episode_geometry(
        pw, ew.rows, z_win, z_inst, win_wh, inst_wh,
        candidate_points=candidate_points(chain), ee_link=chain.n_links - 1, ee_point=end_effector_point(chain),
        truth_contact=None if pre else truth_contact_point(ep_arrays),
        shuffle_rows=shuffle, with_families=True, with_angles=not pre, with_instantaneous=not pre,
    )


def main() -> int:
    ap = common_parser("Stage 2A Phase 5: geometry ablations")
    ap.add_argument("--seeds", default="")
    args = ap.parse_args()
    st = Stage(args, "ablations")
    if not st.require_freeze():
        return 3
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import load_checkpoint

    cfg = st.cfg
    bundle = st.bundle
    chain = bundle.base_chain
    grid = WindowGrid.build(int(cfg["simulation"]["window_samples"]), int(cfg["pathway"]["window_time_points"]))
    cache_root = st.layout.sub("p3_dictionaries") / "cache"
    out_dir = st.layout.sub("p5_ablations")
    quantile = float(cfg["anomaly"]["threshold_quantile"])
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [int(s) for s in cfg["seed_list"]]
    tc = TorchChain.from_chain(chain, dtype=torch.float32, device=st.device)
    n_links = bundle.n_links
    coarse_map = {k: list(v) for k, v in cfg["coarse_classes"].items()}
    ee_only = ("residual", "end_effector")

    write_json(st.layout.results / "stage2a_feature_block_manifest.json", {
        "blocks": feature_block_names(n_links),
        "block_dimensions": block_dimensions(n_links),
        "residual_block": [f"link{i}_{s}" for i in range(n_links) for s in ("mean", "std", "absmax")],
        "ablations": {k: list(v) for k, v in ABLATION_BLOCKS.items()},
        "head": "conditional Gaussian, LOO-selected on healthy validation windows, threshold = 0.995 LOO quantile",
        "note": "identical head for every ablation; only the feature vector changes",
    })

    for seed in seeds:
        t_seed = time.time()
        fc = cfg["models"]["frozen_best_config"]
        ck = st.layout.sub("checkpoints") / f"chain_gnn_aug_{fc['chain_gnn_aug']['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        ck_gru = st.layout.sub("checkpoints") / f"rnea_gru_{fc['rnea_gru']['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        if not ck.exists():
            st.log(f"BLOCKED: missing checkpoint {ck}")
            return 4
        mcfg = ensure_model_cfg(cfg)
        model = load_checkpoint("chain_gnn_aug", ck, bundle, mcfg, st.device)["model"]
        model_gru = load_checkpoint("rnea_gru", ck_gru, bundle, mcfg, st.device)["model"] if ck_gru.exists() else None
        rng = np.random.default_rng(seed)

        # ---------------- residuals and whiteners (healthy train+val only)
        t0 = time.time()
        healthy_ids = bundle.train_ids + bundle.val_ids
        healthy_w = [episode_windows(model, bundle.episodes[e], bundle, tc, grid, st.device) for e in healthy_ids]
        win_wh, inst_wh = fit_whiteners(healthy_w, cfg)
        win_wh_pre, inst_wh_pre = fit_whiteners_pre(healthy_w, cfg)
        st.log(f"[seed {seed}] whiteners fitted ({time.time() - t0:.0f}s)")

        val_ids, test_ids = list(bundle.val_ids), list(bundle.test_ids)
        gru_windows = {}
        if model_gru is not None:
            for e in val_ids + test_ids:
                gru_windows[e] = episode_windows(model_gru, bundle.episodes[e], bundle, tc, grid, st.device)

        # ---------------- one pass per episode: residual windows + window geometry
        feat: dict[str, dict[str, list]] = {"val": {}, "test": {}}
        meta: dict[str, dict[str, list]] = {"val": {}, "test": {}}
        n_total = len(val_ids) + len(test_ids)
        n_done = 0
        for part, ids in (("val", val_ids), ("test", test_ids)):
            for e_i, eid in enumerate(ids):
                ea = bundle.episodes[eid]
                pw = load_pathways(cache_root, eid)
                if pw is None:
                    st.log(f"BLOCKED: pathway cache missing for {eid}")
                    return 5
                ew = episode_windows(model, ea, bundle, tc, grid, st.device)
                nw = ew.resid.shape[0]
                z_win, z_inst, g = _geometry_for(ea, pw, ew, win_wh, inst_wh, cfg, chain, rng)
                _, _, gp = _geometry_for(ea, pw, ew, win_wh_pre, inst_wh_pre, cfg, chain, rng, pre=True)
                gb, gbp = geometry_blocks_from(g), geometry_blocks_from(gp)
                blocks = {"residual": ew.resid_pooled, "residual_pre": ew.resid_pre_pooled,
                          "contact_window_pre": gbp["contact_window"], "families_pre": gbp["families"], **gb}
                if eid in gru_windows:
                    blocks["residual_gru"] = gru_windows[eid].resid_pooled
                for name, arr in blocks.items():
                    feat[part].setdefault(name, []).append(arr)

                loc = localize(g.contact_window, g.diagnosability, None)
                m = meta[part]
                m.setdefault("ctx", []).append(ew.ctx)
                m.setdefault("episode_index", []).append(np.full(nw, e_i))
                m.setdefault("episode", []).append(np.full(nw, eid, dtype=object))
                m.setdefault("split", []).append(np.full(nw, ea.split, dtype=object))
                m.setdefault("family", []).append(np.full(nw, ea.family, dtype=object))
                m.setdefault("kind", []).append(np.full(nw, ea.kind, dtype=object))
                m.setdefault("controller", []).append(np.full(nw, str(ea.context["controller"]), dtype=object))
                m.setdefault("label", []).append(ew.label)
                m.setdefault("target", []).append(ew.target)
                m.setdefault("severity", []).append(np.full(nw, ew.severity))
                m.setdefault("onset_s", []).append(np.full(nw, ew.onset_s))
                m.setdefault("t_end", []).append(ew.t_end)
                m.setdefault("start", []).append(ew.starts)
                m.setdefault("predicted_link", []).append(loc["predicted_link"])
                m.setdefault("rank_order", []).append(loc["rank_order"])
                m.setdefault("margin_explained", []).append(loc["margin_explained"])
                m.setdefault("margin_residual", []).append(loc["margin_residual"])
                m.setdefault("min_projection_residual", []).append(loc["min_projection_residual"])
                m.setdefault("best_point", []).append(g.contact_window["best_point"][np.arange(nw), loc["predicted_link"]])
                m.setdefault("contact_best_explained", []).append(g.contact_window["best_explained"])
                m.setdefault("contact_residual", []).append(g.contact_window["projection_residual"])
                m.setdefault("contact_energy", []).append(g.contact_window["projection_energy"])
                m.setdefault("wrench_residual", []).append(g.contact_wrench["projection_residual"])
                m.setdefault("instant_residual", []).append(
                    g.contact_instant["projection_residual"] if g.contact_instant else np.full((nw, n_links), np.nan))
                m.setdefault("shuffled_residual", []).append(
                    g.contact_shuffled["projection_residual"] if g.contact_shuffled else np.full((nw, n_links), np.nan))
                m.setdefault("oracle_residual", []).append(
                    g.contact_oracle["truth_point_projection_residual"] if g.contact_oracle else np.full((nw, n_links), np.nan))
                m.setdefault("oracle_explained", []).append(
                    g.contact_oracle["explained_fraction"] if g.contact_oracle else np.full(nw, np.nan))
                m.setdefault("oracle_projection_energy", []).append(
                    g.contact_oracle["projection_energy"] if g.contact_oracle else np.full(nw, np.nan))
                m.setdefault("oracle_predicted_link", []).append(
                    g.contact_oracle["truth_point_predicted_link"] if g.contact_oracle else np.full(nw, -1, dtype=int))
                for k in DIAG_KEYS:
                    m.setdefault(k, []).append(g.diagnosability[k])
                for k in FAMILY_KEYS:
                    m.setdefault(f"fam_{k}", []).append(g.families[k]["explained_fraction"])
                n_done += 1
                if n_done % 25 == 0:
                    st.log(f"[seed {seed}] geometry {n_done}/{n_total} episodes ({time.time() - t_seed:.0f}s)")

        cat = {p: {k: np.concatenate(v) for k, v in feat[p].items()} for p in feat}
        md = {p: {k: np.concatenate(v) for k, v in meta[p].items()} for p in meta}
        rec = md["test"]

        # ---------------- rejection calibration on healthy validation windows only
        rc = cfg["localization"]["rejection"]
        calib = RejectionCalibration.fit(md["val"]["margin_explained"], md["val"]["min_projection_residual"],
                                         md["val"]["fisher_min_eigenvalue"], md["val"]["link_min_angle"], rc)
        r_margin = rec["margin_explained"] < calib.margin_threshold
        r_resid = rec["min_projection_residual"] > calib.residual_threshold
        r_fisher = rec["fisher_min_eigenvalue"] < calib.fisher_threshold
        r_angle = rec["link_min_angle"] < calib.angle_threshold
        rec["reject"] = r_margin | r_resid | r_fisher | r_angle
        reason = np.array(["none"] * len(rec["reject"]), dtype=object)
        reason[r_angle] = "link_dictionaries_indistinguishable"
        reason[r_fisher] = "low_contact_observability"
        reason[r_resid] = "no_link_explains_the_residual"
        reason[r_margin] = "ambiguous_link_margin"
        rec["reject_reason"] = reason

        # ---------------- zero-shot coarse attribution (healthy-standardised evidence)
        healthy_ref = {k: (float(md["val"][f"fam_{k}"].mean()), float(md["val"][f"fam_{k}"].std())) for k in FAMILY_KEYS}
        healthy_ref["F4_contact"] = (float(md["val"]["contact_best_explained"].mean()), float(md["val"]["contact_best_explained"].std()))
        coarse_pred, coarse_scores, coarse_classes = zero_shot_coarse_class(
            {k: {"explained_fraction": rec[f"fam_{k}"]} for k in FAMILY_KEYS},
            {"best_explained": rec["contact_best_explained"]}, healthy_ref, coarse_map)
        rec["coarse_pred"] = coarse_pred

        # ---------------- heads (identical form and protocol for every ablation)
        head_rows, scores = [], {}
        ctx_val, ctx_test = md["val"]["ctx"], md["test"]["ctx"]
        ep_val = md["val"]["episode_index"]
        for name, block_names in ABLATION_BLOCKS.items():
            bn = tuple("residual_gru" if (name == "rnea_gru" and b == "residual") else b for b in block_names)
            missing = [b for b in bn if b not in cat["val"]]
            if missing:
                st.log(f"[seed {seed}] skipping {name}: missing block(s) {missing}")
                continue
            z_val, sl = assemble({k: cat["val"][k] for k in bn}, bn)
            z_test, _ = assemble({k: cat["test"][k] for k in bn}, bn)
            slices = per_link_slices(n_links) if len(bn) == 1 else sl
            head, hinfo, loo, _ = fit_head_loo(z_val, ctx_val, ep_val, slices)
            s_test = head.nll(z_test, ctx_test)
            thr = healthy_quantile_threshold(loo, quantile)
            scores[name] = s_test
            head_rows.append({"ablation": name, "blocks": list(bn), "z_dim": int(z_val.shape[1]), "threshold": float(thr),
                              "val_loo_nll_mean": hinfo["loo_val_nll_mean"], "chosen_conditional": hinfo["conditional"],
                              "chosen_covariance": hinfo["covariance"], "chosen_rank": hinfo["rank"],
                              "n_val_windows": int(len(z_val)), "n_val_episodes": hinfo["n_val_episodes"], "seed": seed})
            st.log(f"[seed {seed}] head {name:52s} dim={z_val.shape[1]:3d} thr={thr:9.2f} loo_nll={hinfo['loo_val_nll_mean']:.2f}")

        np.savez_compressed(
            out_dir / f"scores_seed{seed}.npz",
            ablations=np.array(list(scores)), **{f"score__{k}": v for k, v in scores.items()},
            thresholds=np.array([r["threshold"] for r in head_rows]), head_order=np.array([r["ablation"] for r in head_rows]),
            coarse_classes=np.array(coarse_classes), coarse_scores=coarse_scores,
            **{k: (v.astype(str) if v.dtype == object else v) for k, v in rec.items()},
        )
        # secondary, clearly separated: a fault-label-trained coarse fuser on the calib partition
        write_json(out_dir / f"heads_seed{seed}.json", {
            "heads": head_rows, "rejection_calibration": calib.to_dict(),
            "healthy_reference_for_coarse_evidence": healthy_ref,
            "whitening": {"window": win_wh.to_dict(), "instantaneous": inst_wh.to_dict(),
                          "window_pre_correction": win_wh_pre.to_dict()},
            "n_test_windows": int(len(rec["label"])), "seed": seed,
        })
        st.log(f"[seed {seed}] done ({time.time() - t_seed:.0f}s), {len(scores)} heads, {len(rec['label'])} test windows")

    st.finish({"seeds": seeds})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
