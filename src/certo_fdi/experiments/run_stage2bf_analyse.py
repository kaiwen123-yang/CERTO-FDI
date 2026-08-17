"""Stage 2B-F Phases 2-5: hard reproduction gates, the 2x5 matrix, contrasts and CIs.

Consumes the dual-estimator arrays written by ``run_stage2bf_replay`` and:

* **Phase 2** checks the ridge replay against Stage 2A's frozen ``contact_residual`` at score,
  candidate-point, window-label, episode-vote, episode-label, confusion and per-seed metric level.
  Every one of those must hold; a mean agreeing to 2 % is explicitly not sufficient.
* **Phase 3** checks the SVD replay against Stage 2B's frozen per-window arrays and its published
  F4_TEST load-path metrics for all five controls.
* **Phase 4** builds the 2x5 estimator/control matrix on identical residuals and dictionaries.
* **Phase 5** forms the four mechanism contrasts with paired episode-cluster CIs and labels each
  for estimator robustness.

The random control's 16 replicates are aggregated the way the frozen code does it -- mean over
replicates -- and are carried per replicate first, so ``name#k`` is never mistaken for missing.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from certo_fdi.experiments.common import write_json
from certo_fdi.experiments.stage2b_common import episode_cluster_bootstrap, paired_episode_bootstrap
from certo_fdi.experiments.run_stage2bf_replay import (
    METHOD_ORDER,
    N_LINKS,
    confusion,
    episode_localization,
    window_labels,
)
from certo_fdi.stage2bf import estimator_identity as EI

ESTIMATORS = {"ridge": EI.RIDGE_CANONICAL, "svd": EI.SVD_CANONICAL}
#: score key inside the replay arrays for each estimator. Ridge ranks by the residual NORM (its
#: native unit, and the one Stage 2A used); SVD ranks by the residual ENERGY. Both are argmin and
#: the difference is monotone, so it cannot reorder links -- but the unit is reported honestly.
SCORE_KEY = {"ridge": "ridge_norm", "svd": "svd_rss"}


def _nanmean(vals) -> float:
    """Mean ignoring NaN; a link with no episodes in any replicate stays NaN without warning."""
    v = [x for x in vals if x == x]
    return float(np.mean(v)) if v else float("nan")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_csv_checked(path: Path, rows: list[dict]) -> None:
    """Write a table, refusing any renamed legacy estimator name."""
    EI.assert_no_legacy_names(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def load_replay(arrays: Path, seed: int) -> dict:
    z = np.load(arrays / f"stage2bf_dual_scores_seed{seed}.npz", allow_pickle=False)
    rec = {k: z[k] for k in ("episode", "split", "family", "kind", "label", "target", "start")}
    n_rep = int(z["n_replicates"])
    stats: dict[str, dict[str, np.ndarray]] = {}
    for m in METHOD_ORDER:
        if m == "random_within_support_rankmatched":
            continue
        stats[m] = {k: z[f"{m}__{k}"] for k in
                    ("svd_rss", "svd_ess", "svd_rank", "svd_best",
                     "ridge_norm", "ridge_energy", "ridge_lambda", "ridge_best")}
    rnd = [{k: z[f"random{r}__{k}"] for k in
            ("svd_rss", "svd_ess", "svd_rank", "svd_best",
             "ridge_norm", "ridge_energy", "ridge_lambda", "ridge_best")} for r in range(n_rep)]
    # residual energy is recoverable from any link: RSS + ESS
    z_energy = (stats["time_aligned_jacobian"]["svd_rss"][:, 0]
                + stats["time_aligned_jacobian"]["svd_ess"][:, 0])
    return {"rec": rec, "stats": stats, "random": rnd, "n_rep": n_rep, "z_energy": z_energy}


def evidence_auroc(rec: dict, explained: np.ndarray) -> float:
    """Head-free contact-evidence AUROC: max-over-links explained energy, F4 faulty vs healthy."""
    from certo_fdi.anomaly.event_detection import safe_auroc

    ev = np.asarray(explained).max(1)
    pos = (rec["label"] == 1) & (rec["family"] == "F4_contact")
    neg = rec["label"] == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    return float(safe_auroc(np.r_[np.ones(pos.sum()), np.zeros(neg.sum())], np.r_[ev[pos], ev[neg]]))


def explained_for(est: str, s: dict, z_energy: np.ndarray) -> np.ndarray:
    """Per-link explained energy, in the same unit for both estimators."""
    if est == "svd":
        return s["svd_ess"]
    return z_energy[:, None] - s["ridge_energy"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2B-F phases 2-5")
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()

    fcfg = yaml.safe_load(Path(args.config).read_text())
    root = Path(args.run_root)
    res, arrays = root / "results", root / "arrays"
    res.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in fcfg["seed_list"]]
    stage2a_run = Path(fcfg["paths"]["stage2a_run_root"])
    stage2b_run = Path(fcfg["paths"]["stage2b_run_root"])
    tol_abs = float(fcfg["reproduction"]["score_abs_tolerance"])
    tol_rel = float(fcfg["reproduction"]["score_rel_tolerance"])
    nb = int(fcfg["statistics"]["bootstrap_resamples"])
    alpha = float(fcfg["statistics"]["bootstrap_alpha"])

    log: list[str] = []

    def say(m: str) -> None:
        line = f"[{utc_now()}] {m}"
        print(line, flush=True)
        log.append(line)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "logs" / "stage2bf_analyse.log").write_text("\n".join(log) + "\n", encoding="utf-8")

    say("Stage 2B-F analysis start")
    data = {s: load_replay(arrays, s) for s in seeds}

    # ================================================================ Phase 2: ridge hard gates
    say("Phase 2: Stage 2A ridge reproduction")
    ridge_rows, conf_rows = [], []
    gate2 = {"per_seed": {}, "all_pass": True}
    for seed in seeds:
        d = data[seed]
        rec = d["rec"]
        al = d["stats"]["time_aligned_jacobian"]
        A = np.load(stage2a_run / "p5_ablations" / f"scores_seed{seed}.npz", allow_pickle=False)

        kn = np.char.add(np.char.add(rec["episode"].astype(str), "|"), rec["start"].astype(str))
        ka = np.char.add(np.char.add(A["episode"].astype(str), "|"), A["start"].astype(str))
        ia = {k: i for i, k in enumerate(ka.tolist())}
        keep = np.array([k in ia for k in kn.tolist()])
        idx_a = np.array([ia[k] for k in kn[keep].tolist()])
        unique_ok = len(set(kn.tolist())) == len(kn) and len(set(ka.tolist())) == len(ka)

        ours = al["ridge_norm"][keep]
        ref = A["contact_residual"][idx_a]
        adiff = np.abs(ours - ref)
        within = bool(np.all(adiff <= tol_abs + tol_rel * np.abs(ref)))
        bit = int((ours == ref).sum())

        # candidate-point index: Stage 2A stored the winning point of the predicted link
        pred_ours = window_labels(ours)
        pred_ref = window_labels(ref)
        cand_ours = al["ridge_best"][keep][np.arange(len(pred_ours)), np.maximum(pred_ours, 0)]
        cand_ref = A["best_point"][idx_a]
        cand_exact = bool(np.array_equal(cand_ours, cand_ref))
        label_exact = bool(np.array_equal(pred_ours, pred_ref))

        # episode level, on the F4 faulty windows of the test episodes
        sub = {k: v[keep] for k, v in rec.items()}
        loc_ours = episode_localization(sub, ours)
        loc_ref = episode_localization(sub, ref)
        votes_exact = bool(np.array_equal(loc_ours["votes"], loc_ref["votes"]))
        eplabel_exact = bool(np.array_equal(loc_ours["pred"], loc_ref["pred"]))
        c_ours = confusion(loc_ours["pred"], loc_ours["target"])
        c_ref = confusion(loc_ref["pred"], loc_ref["target"])
        conf_exact = bool(np.array_equal(c_ours, c_ref))
        top1_exact = loc_ours["top1"] == loc_ref["top1"]
        cd_exact = loc_ours["chain_distance"] == loc_ref["chain_distance"]

        gates = {"join_complete_unique": bool(unique_ok and keep.sum() > 0),
                 "score_within_tolerance": within, "candidate_index_exact": cand_exact,
                 "window_label_exact": label_exact, "episode_votes_exact": votes_exact,
                 "episode_label_exact": eplabel_exact, "confusion_exact": conf_exact,
                 "top1_exact": bool(top1_exact), "chain_distance_exact": bool(cd_exact)}
        gate2["per_seed"][str(seed)] = {
            **gates, "n_windows_joined": int(keep.sum()), "n_score_pairs": int(ours.size),
            "n_bit_identical": bit, "max_abs_diff": float(adiff.max()),
            "max_rel_diff": float((adiff / np.maximum(np.abs(ref), 1e-300)).max()),
            "episode_top1": loc_ours["top1"], "reference_top1": loc_ref["top1"],
            "mean_chain_distance": loc_ours["chain_distance"],
            "reference_chain_distance": loc_ref["chain_distance"], "n_episodes": loc_ours["n_episodes"]}
        gate2["all_pass"] &= all(gates.values())
        say(f"  seed {seed}: bit-identical {bit}/{ours.size}, max|abs| {adiff.max():.3e}, "
            f"all gates {'PASS' if all(gates.values()) else 'FAIL ' + str([k for k, v in gates.items() if not v])}")

        for i, e in enumerate(loc_ours["episodes"]):
            ridge_rows.append({
                "seed": seed, "episode_id": str(e), "truth_link": int(loc_ours["target"][i]),
                "estimator": EI.RIDGE_CANONICAL,
                "replay_predicted_link": int(loc_ours["pred"][i]),
                "stage2a_reference_predicted_link": int(loc_ref["pred"][i]),
                "label_matches": bool(loc_ours["pred"][i] == loc_ref["pred"][i]),
                "replay_votes": "|".join(map(str, loc_ours["votes"][i])),
                "reference_votes": "|".join(map(str, loc_ref["votes"][i])),
                "votes_match": bool(np.array_equal(loc_ours["votes"][i], loc_ref["votes"][i]))})
        for t in range(N_LINKS):
            for p in range(N_LINKS):
                if c_ours[t, p] or c_ref[t, p]:
                    conf_rows.append({"seed": seed, "truth_link": t, "predicted_link": p,
                                      "replay_count": int(c_ours[t, p]),
                                      "stage2a_reference_count": int(c_ref[t, p]),
                                      "delta": int(c_ours[t, p] - c_ref[t, p])})
    write_csv_checked(res / "stage2bf_stage2a_ridge_reproduction.csv", ridge_rows)
    write_csv_checked(res / "stage2bf_stage2a_ridge_confusion_diff.csv", conf_rows)
    say(f"Phase 2 verdict: {'PASS' if gate2['all_pass'] else 'FAIL'}")

    # ================================================================ Phase 3: SVD hard gates
    say("Phase 3: Stage 2B truncated-SVD reproduction")
    # The historical table stores the random control as one row per replicate, named
    # `random_within_support_rankmatched#k`. Looking it up under the bare name finds nothing and
    # reads as a reproduction failure, so the key is (base_name, seed, replicate).
    hist = {}
    with (stage2b_run / "results" / "stage2b_loadpath_controls.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            if r.get("partition") != "F4_TEST":
                continue
            base = r["method"].split("#")[0]
            rep = int(r["method"].split("#")[1]) if "#" in r["method"] else -1
            hist[(base, int(r["seed"]), rep)] = r
    svd_rows = []
    gate3 = {"per_seed": {}, "all_pass": True}
    for seed in seeds:
        d = data[seed]
        rec = d["rec"]
        B = np.load(stage2b_run / "p1_loadpath" / f"controls_seed{seed}.npz", allow_pickle=False)
        kn = np.char.add(np.char.add(rec["episode"].astype(str), "|"), rec["start"].astype(str))
        kb = np.char.add(np.char.add(B["episode"].astype(str), "|"), B["start"].astype(str))
        order_same = bool(np.array_equal(kn, kb))
        per_method = {}
        for m in METHOD_ORDER:
            if m == "random_within_support_rankmatched":
                # every replicate is compared against its own historical row, which is stricter
                # than comparing the aggregate and is what the `#k` naming exists to permit
                adiffs, ok_top1, ok_cd, ok_rank = [], True, True, True
                tops, cds = [], []
                for r_i in range(d["n_rep"]):
                    o, rf = d["random"][r_i]["svd_rss"], B[f"random{r_i}__rss"]
                    adiffs.append(np.abs(o - rf))
                    ok_rank &= bool(np.array_equal(d["random"][r_i]["svd_rank"], B[f"random{r_i}__rank"]))
                    lr = episode_localization(rec, o)
                    tops.append(lr["top1"])
                    cds.append(lr["chain_distance"])
                    hr = hist.get((m, seed, r_i))
                    ok_top1 &= hr is not None and lr["top1"] == float(hr["episode_top1"])
                    ok_cd &= hr is not None and lr["chain_distance"] == float(hr["mean_chain_distance"])
                adiff = np.concatenate([a.ravel() for a in adiffs])
                ref_rss = np.concatenate([B[f"random{r_i}__rss"].ravel() for r_i in range(d["n_rep"])])
                ours_rss = np.concatenate([d["random"][r_i]["svd_rss"].ravel() for r_i in range(d["n_rep"])])
                ok_score = bool(np.all(adiff <= tol_abs + tol_rel * np.abs(ref_rss)))
                loc = {"top1": float(np.mean(tops)), "chain_distance": float(np.mean(cds))}
                h_top1 = float(np.mean([float(hist[(m, seed, r_i)]["episode_top1"])
                                        for r_i in range(d["n_rep"])]))
                h_cd = float(np.mean([float(hist[(m, seed, r_i)]["mean_chain_distance"])
                                      for r_i in range(d["n_rep"])]))
            else:
                ours_rss, ref_rss = d["stats"][m]["svd_rss"], B[f"{m}__rss"]
                adiff = np.abs(ours_rss - ref_rss)
                ok_score = bool(np.all(adiff <= tol_abs + tol_rel * np.abs(ref_rss)))
                ok_rank = bool(np.array_equal(d["stats"][m]["svd_rank"], B[f"{m}__rank"]))
                loc = episode_localization(rec, ours_rss)
                h = hist.get((m, seed, -1))
                ok_top1 = h is not None and loc["top1"] == float(h["episode_top1"])
                ok_cd = h is not None and loc["chain_distance"] == float(h["mean_chain_distance"])
                h_top1 = float(h["episode_top1"]) if h else None
                h_cd = float(h["mean_chain_distance"]) if h else None
            per_method[m] = {"score_within_tolerance": ok_score, "rank_exact": bool(ok_rank),
                             "published_top1_exact": bool(ok_top1),
                             "published_chain_distance_exact": bool(ok_cd),
                             "n_bit_identical": int((ours_rss == ref_rss).sum()),
                             "n_pairs": int(ours_rss.size), "max_abs_diff": float(adiff.max()),
                             "replay_top1": loc["top1"], "published_top1": h_top1,
                             "replay_chain_distance": loc["chain_distance"],
                             "published_chain_distance": h_cd}
            gate3["all_pass"] &= all([ok_score, ok_rank, ok_top1, ok_cd])
            svd_rows.append({"seed": seed, "control": m, "estimator": EI.SVD_CANONICAL,
                             **{k: v for k, v in per_method[m].items()}})
        gate3["per_seed"][str(seed)] = {"window_key_order_identical": order_same, "methods": per_method}
        bad = [m for m, v in per_method.items() if not all(
            [v["score_within_tolerance"], v["rank_exact"], v["published_top1_exact"],
             v["published_chain_distance_exact"]])]
        say(f"  seed {seed}: key order identical {order_same}; "
            f"{'all 5 controls PASS' if not bad else 'FAIL ' + str(bad)}")
    write_csv_checked(res / "stage2bf_stage2b_svd_reproduction.csv", svd_rows)
    say(f"Phase 3 verdict: {'PASS' if gate3['all_pass'] else 'FAIL'}")

    # ================================================================ Phase 4: 2x5 matrix
    say("Phase 4: 2x5 estimator/control matrix")
    matrix_rows, per_ep_rows, per_link_rows = [], [], []
    cell: dict[tuple[str, str, int], dict] = {}
    for seed in seeds:
        d = data[seed]
        rec = d["rec"]
        for est in ("ridge", "svd"):
            for m in METHOD_ORDER:
                if m == "random_within_support_rankmatched":
                    reps = []
                    for r_i, r in enumerate(d["random"]):
                        locr = episode_localization(rec, r[SCORE_KEY[est]])
                        reps.append(locr)
                        matrix_rows.append({
                            "seed": seed, "estimator": ESTIMATORS[est], "control": m,
                            "replicate": r_i, "is_replicate_row": True,
                            "episode_top1": locr["top1"], "mean_chain_distance": locr["chain_distance"],
                            "n_episodes": locr["n_episodes"],
                            "contact_evidence_auroc": evidence_auroc(rec, explained_for(est, r, d["z_energy"])),
                            "score_unit": "residual_norm" if est == "ridge" else "residual_energy",
                            "is_audit_baseline": est == "ridge", "is_selection_candidate": False})
                    loc = {"top1": float(np.mean([x["top1"] for x in reps])),
                           "chain_distance": float(np.mean([x["chain_distance"] for x in reps])),
                           "n_episodes": reps[0]["n_episodes"],
                           "episodes": reps[0]["episodes"], "target": reps[0]["target"],
                           "correct": np.mean([x["correct"] for x in reps], axis=0),
                           "distance": np.mean([x["distance"] for x in reps], axis=0),
                           "per_link_recall": {l: _nanmean([x["per_link_recall"][l] for x in reps])
                                               for l in range(N_LINKS)}}
                    auroc = float(np.mean([evidence_auroc(rec, explained_for(est, r, d["z_energy"]))
                                           for r in d["random"]]))
                    mean_rank = float(np.mean([r["svd_rank"].mean() for r in d["random"]]))
                    cand_use = float(np.mean([len(np.unique(r[f"{est}_best"])) for r in d["random"]]))
                else:
                    s = d["stats"][m]
                    loc = episode_localization(rec, s[SCORE_KEY[est]])
                    auroc = evidence_auroc(rec, explained_for(est, s, d["z_energy"]))
                    mean_rank = float(s["svd_rank"].mean())
                    cand_use = float(len(np.unique(s[f"{est}_best"])))
                cell[(est, m, seed)] = loc
                matrix_rows.append({
                    "seed": seed, "estimator": ESTIMATORS[est], "control": m, "replicate": -1,
                    "is_replicate_row": False,
                    "episode_top1": loc["top1"], "mean_chain_distance": loc["chain_distance"],
                    "n_episodes": loc["n_episodes"], "contact_evidence_auroc": auroc,
                    "mean_dictionary_rank": mean_rank, "n_candidate_points_used": cand_use,
                    "score_unit": "residual_norm" if est == "ridge" else "residual_energy",
                    "is_audit_baseline": est == "ridge", "is_selection_candidate": False,
                    "orthonormalised_control": m in fcfg["orthonormalised_controls"],
                    **{f"recall_link{l}": loc["per_link_recall"][l] for l in range(N_LINKS)}})
                for l in range(N_LINKS):
                    per_link_rows.append({"seed": seed, "estimator": ESTIMATORS[est], "control": m,
                                          "link": l, "recall": loc["per_link_recall"][l]})
                for i, e in enumerate(loc["episodes"]):
                    per_ep_rows.append({"seed": seed, "estimator": ESTIMATORS[est], "control": m,
                                        "episode_id": str(e), "truth_link": int(loc["target"][i]),
                                        "correct": float(loc["correct"][i]),
                                        "chain_distance": float(loc["distance"][i])})
    write_csv_checked(res / "stage2bf_estimator_control_matrix.csv", matrix_rows)
    write_csv_checked(res / "stage2bf_per_episode_localization.csv", per_ep_rows)
    write_csv_checked(res / "stage2bf_per_link_metrics.csv", per_link_rows)
    say(f"Phase 4: {len(matrix_rows)} matrix rows ({len(seeds)} seeds x 2 estimators x 5 controls "
        f"+ {fcfg.get('n_rep', 16)} replicate rows each for the random control)")

    # ================================================================ Phase 5: contrasts
    say("Phase 5: mechanism contrasts with paired episode-cluster CIs")
    contrast_rows = []
    for name, (a, b) in fcfg["mechanism_contrasts"].items():
        for est in ("ridge", "svd"):
            eps, ca, cb, da, db = [], [], [], [], []
            for seed in seeds:
                A, B_ = cell[(est, a, seed)], cell[(est, b, seed)]
                assert list(map(str, A["episodes"])) == list(map(str, B_["episodes"])), \
                    f"{name}/{est}/{seed}: contrast is not paired on the same episodes"
                eps.append(np.array([f"{seed}:{e}" for e in A["episodes"]]))
                ca.append(A["correct"]); cb.append(B_["correct"])
                da.append(A["distance"]); db.append(B_["distance"])
            eps = np.concatenate(eps)
            t1 = paired_episode_bootstrap(eps, np.concatenate(ca), np.concatenate(cb), nb, alpha)
            cd = paired_episode_bootstrap(eps, np.concatenate(db), np.concatenate(da), nb, alpha)
            contrast_rows.append({
                "contrast": name, "estimator": ESTIMATORS[est], "a": a, "b": b,
                "unit": "episode", "n_episodes": int(t1["n_episodes"]),
                "top1_delta": t1["point"], "top1_ci_low": t1["ci_low"], "top1_ci_high": t1["ci_high"],
                "top1_ci_excludes_zero": bool(t1.get("ci_excludes_zero", False)),
                "chain_distance_reduction": cd["point"], "cd_ci_low": cd["ci_low"],
                "cd_ci_high": cd["ci_high"], "cd_ci_excludes_zero": bool(cd.get("ci_excludes_zero", False)),
                "bootstrap_resamples": nb, "alpha": alpha})
    # robustness labels
    labelled = []
    for name in fcfg["mechanism_contrasts"]:
        r = {x["estimator"]: x for x in contrast_rows if x["contrast"] == name}
        rr, ss = r[EI.RIDGE_CANONICAL], r[EI.SVD_CANONICAL]
        for metric, key, exc in (("top1", "top1_delta", "top1_ci_excludes_zero"),
                                 ("chain_distance", "chain_distance_reduction", "cd_ci_excludes_zero")):
            a_v, b_v = rr[key], ss[key]
            if not (np.isfinite(a_v) and np.isfinite(b_v)):
                lab = "NOT_IDENTIFIABLE"
            elif np.sign(a_v) != np.sign(b_v) and abs(a_v) > 1e-12 and abs(b_v) > 1e-12:
                lab = "ESTIMATOR_SENSITIVE"
            elif rr[exc] and ss[exc]:
                lab = "ROBUST_BOTH_ESTIMATORS"
            else:
                lab = "DIRECTIONALLY_CONSISTENT"
            labelled.append({"contrast": name, "metric": metric,
                             "ridge_value": a_v, "svd_value": b_v,
                             "ridge_ci_excludes_zero": rr[exc], "svd_ci_excludes_zero": ss[exc],
                             "robustness": lab,
                             "orthonormalised_pair": bool(
                                 fcfg["mechanism_contrasts"][name][0] in fcfg["orthonormalised_controls"]
                                 and fcfg["mechanism_contrasts"][name][1] in fcfg["orthonormalised_controls"])})
    write_csv_checked(res / "stage2bf_estimator_contrast_ci.csv", contrast_rows)
    write_csv_checked(res / "stage2bf_mechanism_robustness.csv", labelled)
    for x in labelled:
        say(f"  {x['contrast']:18s} {x['metric']:15s} ridge {x['ridge_value']:+.4f} "
            f"svd {x['svd_value']:+.4f} -> {x['robustness']}")

    write_json(res / "stage2bf_reproduction_gates.json", {
        "generated_utc": utc_now(),
        "phase2_stage2a_ridge": gate2,
        "phase3_stage2b_svd": gate3,
        "tolerances": {"abs": tol_abs, "rel": tol_rel},
        "estimators": ESTIMATORS,
        "note": ("both estimators were computed inside one loop on the same z and the same "
                 "dictionaries; the ridge is an audit baseline and never a selection candidate"),
    })
    say(f"gates: phase2 {'PASS' if gate2['all_pass'] else 'FAIL'}, "
        f"phase3 {'PASS' if gate3['all_pass'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
