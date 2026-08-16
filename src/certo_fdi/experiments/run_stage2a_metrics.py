"""Stage 2A Phase 6: detection, event, localization, coarse-attribution and diagnosability metrics.

Reads the per-seed score archives written by Phase 5 and produces the contract's metric tables.
Metric definitions are the frozen Stage 1R-B ones (``certo_fdi.anomaly.event_detection``), so
every number is directly comparable with the reproduced baseline.

Localization is evaluated **per episode** (a vote over that episode's faulty windows), which is
how the frozen Stage 1R-B localizer was scored; the per-window numbers are reported alongside.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi.anomaly.event_detection import event_metrics, safe_auprc, safe_auroc, window_metrics
from certo_fdi.experiments.common import write_csv, write_json
from certo_fdi.experiments.stage2a_common import COARSE_CLASS_OF_FAMILY, Stage, bootstrap_ci, common_parser, spearman

SPLITS = ("S0", "S1", "S2", "S3", "S4", "OOD", "ALL")
FAMILIES = ("F1_actuator", "F2_friction", "F3_payload", "F4_contact", "F5_encoder", "F6_command")
LOCALIZABLE = ("F1_actuator", "F2_friction", "F3_payload", "F4_contact", "F5_encoder")
LOCALIZERS = {
    "contact_projection_residual": "contact_residual",
    "contact_projection_residual_body_wrench": "wrench_residual",
    "contact_projection_residual_instantaneous": "instant_residual",
    "contact_projection_residual_shuffled_control": "shuffled_residual",
    "contact_projection_residual_oracle_truth_point": "oracle_residual",
}
DIAG_METRICS = ("contact_observability", "fisher_min_eigenvalue", "link_min_angle",
                "fault_family_min_angle", "predicted_ambiguity", "entropy", "ee_jacobian_sigma_min")


def _split_mask(split: np.ndarray, tag: str) -> np.ndarray:
    if tag == "ALL":
        return np.ones(len(split), dtype=bool)
    if tag == "OOD":
        return np.isin(split, ["S1", "S2", "S3", "S4"])
    return split == tag


def _sequences(d: dict, scores: np.ndarray, mask: np.ndarray) -> list[dict]:
    """Per-episode time-ordered score sequences for the frozen event metrics."""
    out = []
    idx = np.where(mask)[0]
    for eid in np.unique(d["episode"][idx]):
        m = idx[d["episode"][idx] == eid]
        order = m[np.argsort(d["start"][m])]
        out.append({"scores": scores[order], "labels": d["label"][order].astype(int), "t_end": d["t_end"][order],
                    "is_fault_episode": d["kind"][order][0] == "fault", "onset_s": float(d["onset_s"][order][0]),
                    "family": d["family"][order][0], "split": d["split"][order][0]})
    return out


def _episode_vote(pred: np.ndarray) -> int:
    return int(np.bincount(pred[pred >= 0], minlength=7).argmax()) if (pred >= 0).any() else -1


def main() -> int:
    ap = common_parser("Stage 2A Phase 6: metric tables")
    ap.add_argument("--supervised-calib-episodes", type=int, default=20, help="per family, for the SECONDARY supervised experiment")
    args = ap.parse_args()
    st = Stage(args, "metrics")
    if not st.require_freeze():
        return 3
    cfg = st.cfg
    seeds = [int(s) for s in cfg["seed_list"]]
    src = st.layout.sub("p5_ablations")
    dt = float(cfg["simulation"]["control_dt_s"])
    window_dt = int(cfg["simulation"]["window_stride_eval"]) * dt
    persist = int(cfg["anomaly"]["persistence_windows"])
    n_links = 7

    data, heads = {}, {}
    for seed in seeds:
        f = src / f"scores_seed{seed}.npz"
        if not f.exists():
            st.log(f"BLOCKED: missing {f}")
            return 4
        z = np.load(f, allow_pickle=False)
        data[seed] = {k: z[k] for k in z.files}
        heads[seed] = json.loads((src / f"heads_seed{seed}.json").read_text())
    ablations = [str(a) for a in data[seeds[0]]["ablations"]]
    thr_by = {s: {r["ablation"]: float(r["threshold"]) for r in heads[s]["heads"]} for s in seeds}
    st.log(f"loaded {len(seeds)} seeds x {len(ablations)} ablations x {len(data[seeds[0]]['label'])} test windows")

    # ---------------------------------------------------------------- detection + event
    det_rows, ev_rows = [], []
    for seed in seeds:
        d = data[seed]
        for ab in ablations:
            s = d[f"score__{ab}"]
            thr = thr_by[seed][ab]
            for split in SPLITS:
                in_split = _split_mask(d["split"], split)
                neg = in_split & (d["label"] == 0)
                if neg.sum() == 0:
                    continue
                for fam in ("ALL",) + FAMILIES:
                    pos = in_split & (d["label"] == 1) & ((d["family"] == fam) if fam != "ALL" else True)
                    if pos.sum() == 0:
                        continue
                    y = np.r_[np.ones(pos.sum()), np.zeros(neg.sum())]
                    sc = np.r_[s[pos], s[neg]]
                    wm = window_metrics(y, sc, thr)
                    det_rows.append({**st.base_row(model=ab, split=split, fault_family=fam, seed=seed),
                                     "threshold": thr, **wm,
                                     "n_pos_windows": int(pos.sum()), "n_neg_windows": int(neg.sum())})
                    seqs = _sequences(d, s, pos | neg)
                    em = event_metrics(seqs, thr, window_dt)
                    em3 = {f"p{persist}_{k}": v for k, v in event_metrics(seqs, thr, window_dt, persistence=persist).items()}
                    rej = float(d["reject"][pos].mean()) if pos.sum() else float("nan")
                    ev_rows.append(st.base_row(model=ab, split=split, fault_family=fam, seed=seed, threshold=thr,
                                               **em, **em3, rejection_rate_on_fault_windows=rej,
                                               rejection_rate_on_healthy_windows=float(d["reject"][neg].mean()),
                                               units="delay in s; false alarms per hour; p3_* = 3-window persistence rule"))
    st.write_table("stage2a_detection_metrics.csv", det_rows,
                   units="AUROC/AUPRC dimensionless; FPR at TPR 90; threshold in score units (-log p0)",
                   schema={"model": "ablation name", "n_pos/n_neg": "window counts"})
    st.write_table("stage2a_event_metrics.csv", ev_rows,
                   units="event_tpr/f1 dimensionless; false_alarms_per_hour 1/h; detection delay s",
                   schema={"p3_*": "3-consecutive-window persistence rule"})

    # ---------------------------------------------------------------- selective risk / coverage
    sel_rows = []
    for seed in seeds:
        d = data[seed]
        for ab in ablations:
            s, thr = d[f"score__{ab}"], thr_by[seed][ab]
            for split in ("ALL", "S0", "OOD"):
                m = _split_mask(d["split"], split)
                if m.sum() == 0:
                    continue
                keep = m & ~d["reject"]
                err = (s > thr) != (d["label"] == 1)
                sel_rows.append(st.base_row(model=ab, split=split, fault_family="ALL", seed=seed,
                                            coverage=float(keep.sum() / max(m.sum(), 1)),
                                            selective_error=float(err[keep].mean()) if keep.sum() else float("nan"),
                                            full_error=float(err[m].mean()),
                                            selective_risk_reduction=float(err[m].mean() - err[keep].mean()) if keep.sum() else float("nan"),
                                            units="coverage and error are window fractions"))
    write_csv(st.layout.sub("p6_metrics") / "stage2a_selective_risk.csv", sel_rows)

    # ---------------------------------------------------------------- localization (episode level)
    loc_rows, conf_out = [], {}
    for seed in seeds:
        d = data[seed]
        for lname, key in LOCALIZERS.items():
            if key not in d:
                continue
            resid = d[key]
            valid = np.isfinite(resid).all(1)
            pred_w = np.where(valid, np.argmin(np.where(np.isfinite(resid), resid, np.inf), axis=1), -1)
            for split_tag in ("S0", "OOD", "ALL"):
                for fam in ("ALL",) + LOCALIZABLE:
                    preds, targets, cov, chain_d = [], [], [], []
                    for eid in np.unique(d["episode"]):
                        m = (d["episode"] == eid) & (d["label"] == 1)
                        if m.sum() == 0:
                            continue
                        f0, s0, t0 = d["family"][m][0], d["split"][m][0], int(d["target"][m][0])
                        if d["kind"][m][0] != "fault" or f0 not in LOCALIZABLE or t0 < 0:
                            continue
                        if fam != "ALL" and f0 != fam:
                            continue
                        if split_tag == "S0" and s0 != "S0":
                            continue
                        if split_tag == "OOD" and s0 == "S0":
                            continue
                        pw = pred_w[m]
                        if (pw < 0).all():
                            continue
                        v = _episode_vote(pw)
                        preds.append(v)
                        targets.append(t0)
                        acc = m & ~d["reject"]
                        cov.append(float((~d["reject"][m]).mean()))
                        va = _episode_vote(pred_w[acc]) if acc.sum() else -1
                        chain_d.append((v, va, t0))
                    if not targets:
                        continue
                    P, T = np.asarray(preds), np.asarray(targets)
                    acc_pred = np.array([c[1] for c in chain_d])
                    ok_acc = acc_pred >= 0
                    row = st.base_row(model=lname, split=split_tag, fault_family=fam, seed=seed,
                                      n_episodes=int(len(T)), top1=float((P == T).mean()),
                                      mean_chain_distance=float(np.abs(P - T).mean()),
                                      coverage=float(np.mean(cov)),
                                      conditional_top1_after_rejection=float((acc_pred[ok_acc] == T[ok_acc]).mean()) if ok_acc.any() else float("nan"),
                                      units="episode-level vote over the faulty windows; chain distance in links")
                    loc_rows.append(row)
                    if fam == "F4_contact" and split_tag == "ALL":
                        c = np.zeros((n_links, n_links), dtype=int)
                        for t, p in zip(T, P):
                            c[t, p] += 1
                        conf_out.setdefault(lname, {})[str(seed)] = c.tolist()
    # the frozen Stage 1R-B counterfactual localizer, for comparability
    base_loc = st.layout.sub("p2_baseline") / "stage2a_baseline_localization.csv"
    if base_loc.exists():
        bl = pd.read_csv(base_loc)
        bl = bl[(bl.method == "counterfactual_link_masking") & (bl.training_fraction >= 1.0)]
        for _, r in bl.iterrows():
            loc_rows.append(st.base_row(model="counterfactual_link_masking_baseline", split=str(r["split"]),
                                        fault_family=str(r["family"]), seed=int(r["seed"]), n_episodes=int(r["n_episodes"]),
                                        top1=float(r["top1"]), top2=float(r["top2"]), mean_chain_distance=float(r["mean_chain_distance"]),
                                        coverage=1.0, conditional_top1_after_rejection=float(r["top1"]),
                                        units="frozen Stage 1R-B localizer on the reproduced baseline (no rejection option)"))
    st.write_table("stage2a_localization_metrics.csv", loc_rows,
                   units="top-1 accuracy; chain distance in links; coverage = fraction of windows not rejected",
                   schema={"model": "localizer variant", "conditional_top1_after_rejection": "top-1 among accepted windows"})
    write_json(st.layout.sub("p6_metrics") / "stage2a_link_confusion.json", conf_out)

    # ---------------------------------------------------------------- coarse attribution (zero-shot)
    coarse_rows = []
    classes = [str(c) for c in data[seeds[0]]["coarse_classes"]]
    for seed in seeds:
        d = data[seed]
        true_class = np.array([COARSE_CLASS_OF_FAMILY.get(f, "") for f in d["family"]])
        for split_tag in ("S0", "OOD", "ALL"):
            m = _split_mask(d["split"], split_tag) & (d["label"] == 1) & (true_class != "")
            if m.sum() == 0:
                continue
            pred, truth = d["coarse_pred"][m], true_class[m]
            per_class = {c: float((pred[truth == c] == c).mean()) for c in classes if (truth == c).any()}
            coarse_rows.append(st.base_row(model="zero_shot_pathway_evidence", split=split_tag, fault_family="ALL", seed=seed,
                                           n_windows=int(m.sum()), accuracy=float((pred == truth).mean()),
                                           balanced_accuracy=float(np.mean(list(per_class.values()))),
                                           n_classes=len(classes), chance=1.0 / len(classes),
                                           **{f"recall_{c}": v for c, v in per_class.items()},
                                           units="window-level; zero-shot argmax of healthy-standardised pathway evidence"))
            for fam in FAMILIES:
                mf = m & (d["family"] == fam)
                if mf.sum() == 0:
                    continue
                c_true = COARSE_CLASS_OF_FAMILY[fam]
                coarse_rows.append(st.base_row(model="zero_shot_pathway_evidence", split=split_tag, fault_family=fam, seed=seed,
                                               n_windows=int(mf.sum()), accuracy=float((d["coarse_pred"][mf] == c_true).mean()),
                                               balanced_accuracy=float("nan"), n_classes=len(classes), chance=1.0 / len(classes),
                                               true_coarse_class=c_true, units="window-level recall of this family's coarse class"))
    st.write_table("stage2a_coarse_attribution_metrics.csv", coarse_rows,
                   units="accuracy fractions; chance = 1/5",
                   schema={"model": "zero_shot_pathway_evidence uses no fault labels"})

    # ---------------------------------------------------------------- diagnosability correlations
    diag_rows = []
    nb = int(cfg["diagnosability"]["bootstrap_resamples"])
    alpha = float(cfg["diagnosability"]["bootstrap_alpha"])
    nbins = int(cfg["diagnosability"]["reliability_bins"])
    prim = cfg["primary_geometry_head"]
    for seed in seeds:
        d = data[seed]
        s, thr = d[f"score__{prim}"], thr_by[seed][prim]
        resid = d["contact_residual"]
        pred_link = np.argmin(resid, axis=1)
        errors = {
            "link_localization_error": ((pred_link != d["target"]) & (d["label"] == 1) & (d["family"] == "F4_contact")).astype(float),
            "link_chain_distance": np.where((d["label"] == 1) & (d["family"] == "F4_contact"), np.abs(pred_link - d["target"]), np.nan),
            "missed_detection": ((s <= thr) & (d["label"] == 1)).astype(float),
            "rejection": d["reject"].astype(float),
            "false_alarm": ((s > thr) & (d["label"] == 0)).astype(float),
        }
        for metric in DIAG_METRICS:
            if metric not in d:
                continue
            x = d[metric]
            for ename, e in errors.items():
                m = np.isfinite(x) & np.isfinite(e)
                if ename.startswith("link_"):
                    m &= (d["label"] == 1) & (d["family"] == "F4_contact")
                elif ename == "missed_detection":
                    m &= d["label"] == 1
                elif ename == "false_alarm":
                    m &= d["label"] == 0
                if m.sum() < 30:
                    continue
                pair = np.stack([x[m], e[m]], 1)
                rho, lo, hi = bootstrap_ci(pair, lambda a: spearman(a[:, 0], a[:, 1]), nb, alpha, seed=seed)
                q = np.nanquantile(x[m], np.linspace(0, 1, nbins + 1))
                q[-1] += 1e-12
                b = np.clip(np.digitize(x[m], q[1:-1]), 0, nbins - 1)
                bins = [{"bin": int(k), "x_median": float(np.median(x[m][b == k])), "error_rate": float(np.mean(e[m][b == k])), "n": int((b == k).sum())} for k in range(nbins) if (b == k).any()]
                lowq, highq = np.nanquantile(x[m], [0.25, 0.75])
                diag_rows.append(st.base_row(model=prim, split="ALL", fault_family="F4_contact" if ename.startswith("link_") else "ALL",
                                             seed=seed, diagnosability_metric=metric, error_metric=ename,
                                             n=int(m.sum()), spearman_rho=rho, abs_spearman_rho=abs(rho) if rho == rho else float("nan"),
                                             ci_low=lo, ci_high=hi, ci_excludes_zero=bool(lo == lo and hi == hi and (lo > 0 or hi < 0)),
                                             error_low_diagnosability_quartile=float(np.mean(e[m][x[m] <= lowq])),
                                             error_high_diagnosability_quartile=float(np.mean(e[m][x[m] >= highq])),
                                             reliability_bins=json.dumps(bins),
                                             units="Spearman rho with a percentile bootstrap CI; error rates are fractions"))
    st.write_table("stage2a_diagnosability_error_correlation.csv", diag_rows,
                   units="Spearman rho dimensionless; CI from a percentile bootstrap",
                   schema={"error_metric": "the actual error the geometry metric is asked to predict"})

    # ---------------------------------------------------------------- geometry score summary
    geo_rows = []
    for seed in seeds:
        d = data[seed]
        for split in SPLITS:
            for fam in ("healthy",) + FAMILIES:
                m = _split_mask(d["split"], split) & (d["family"] == fam)
                if fam != "healthy":
                    m &= d["label"] == 1
                if m.sum() == 0:
                    continue
                row = st.base_row(model=prim, split=split, fault_family=fam, seed=seed, n_windows=int(m.sum()),
                                  contact_best_explained_median=float(np.median(d["contact_best_explained"][m])),
                                  contact_min_residual_median=float(np.median(d["min_projection_residual"][m])),
                                  contact_margin_median=float(np.median(d["margin_residual"][m])),
                                  oracle_explained_median=float(np.nanmedian(d["oracle_explained"][m])) if np.isfinite(d["oracle_explained"][m]).any() else float("nan"),
                                  rejection_rate=float(d["reject"][m].mean()),
                                  units="explained fractions dimensionless; residuals in whitened units")
                for k in DIAG_METRICS:
                    if k in d:
                        row[f"{k}_median"] = float(np.nanmedian(d[k][m]))
                for k in [c for c in d if c.startswith("fam_")]:
                    row[f"{k}_median"] = float(np.nanmedian(d[k][m]))
                geo_rows.append(row)
    st.write_table("stage2a_geometry_scores.csv", geo_rows,
                   units="medians over the selected windows; whitened residual units",
                   schema={"fam_*": "explained fraction of that family's dictionary"})

    write_json(st.layout.results / "stage2a_metrics_summary.json", {
        "seeds": seeds, "ablations": ablations, "thresholds": thr_by,
        "n_detection_rows": len(det_rows), "n_event_rows": len(ev_rows), "n_localization_rows": len(loc_rows),
        "n_coarse_rows": len(coarse_rows), "n_diagnosability_rows": len(diag_rows),
        "localizers": list(LOCALIZERS), "diagnosability_metrics": list(DIAG_METRICS),
        "localization_protocol": "episode-level vote over the faulty windows (the frozen Stage 1R-B protocol)",
    })
    st.finish({"n_rows": len(det_rows) + len(ev_rows) + len(loc_rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
