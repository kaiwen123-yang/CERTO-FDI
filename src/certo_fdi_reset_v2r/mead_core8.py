"""M2: ME-AD CORE-8 matrix over the 7 OFFICIAL tasks (frozen protocol).

Per task: fit on train cycles 0-14, calibration = train cycles 15-19 (healthy
threshold source), test = official healthy (50) vs faulty (50) cycles.
Cycle score = window-mean. Metrics: AUROC/AUPRC/FPR@TPR90 (cycle level),
plus P/R/F1 and false alarms per 1000 healthy cycles at the healthy-cal
threshold (= max cycle score over the 5 calibration cycles).
Deterministic models 1 fit + 2000-resample cycle bootstrap CI on AUROC;
stochastic models seeds 260824-26. B8 = mvt_flow_adapted (official
architecture/loss; labeled ADAPTED). No faulty data touches any fit or
threshold. Emits mead_core8_metrics.{json,csv} + per-seed cycle scores.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from certo_fdi_reset_v2.benchmarks.models import fit_model
from certo_fdi_reset_v2r.mead_common import (
    SEEDS, TASKS, W, cycle_windows, fit_mvt_flow_adapted, fit_stats, load_task,
)

RUN = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r/mead")
DET = ("mahalanobis", "pca_spe")
STOCH = ("iforest", "ocsvm", "window_ae", "gru_ae", "tcn_ae", "gru_pred")


def cycle_scores(score_fn, cycles, mu, sd):
    return np.array([float(np.mean(score_fn(cycle_windows(c, mu, sd)))) for c in cycles])


def task_metrics(s_heal, s_fault, thr):
    from sklearn import metrics as M
    y = np.concatenate([np.zeros(len(s_heal)), np.ones(len(s_fault))])
    s = np.concatenate([s_heal, s_fault])
    fpr, tpr, _ = M.roc_curve(y, s)
    i = int(np.searchsorted(tpr, 0.9, side="left"))
    pred = s > thr
    tp = int((pred[y == 1]).sum()); fp = int((pred[y == 0]).sum())
    fn = int(len(s_fault) - tp)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "auroc": float(M.auc(fpr, tpr)),
        "auprc": float(M.average_precision_score(y, s)),
        "fpr_at_tpr90": float(fpr[min(i, len(fpr) - 1)]),
        "precision_at_cal_thr": prec, "recall_at_cal_thr": rec,
        "f1_at_cal_thr": (2 * prec * rec / (prec + rec)) if prec + rec else 0.0,
        "false_alarms_per_1000_healthy_cycles": 1000.0 * fp / len(s_heal),
    }


def bootstrap_auroc_ci(s_heal, s_fault, n=2000, seed=260824):
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        h = rng.choice(s_heal, len(s_heal), replace=True)
        f = rng.choice(s_fault, len(s_fault), replace=True)
        y = np.concatenate([np.zeros(len(h)), np.ones(len(f))])
        vals.append(roc_auc_score(y, np.concatenate([h, f])))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def main(models=None, tasks=None):
    RUN.mkdir(parents=True, exist_ok=True)
    out_path = RUN / "mead_core8_metrics.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}
    results["_protocol"] = {"summary": "official 7 tasks; fit=train[0:15], cal=train[15:20] (thr=max cycle score); cycle=window-mean W=100 s50; RAW24 channels"}
    scores_dir = RUN / "cycle_scores"; scores_dir.mkdir(exist_ok=True)

    for task in (tasks or TASKS):
        data = load_task(task)
        fit_c, cal_c = data["train"][:15], data["train"][15:20]
        mu, sd = fit_stats(fit_c)
        train_w = np.concatenate([cycle_windows(c, mu, sd) for c in fit_c], 0)
        for m in (models or (DET + STOCH + ("mvt_flow_adapted",))):
            seeds = (SEEDS[0],) if m in DET else SEEDS
            for seed in seeds:
                key = f"{task}_{m}_seed{seed}"
                if key in results:
                    print(f"[skip] {key}", flush=True); continue
                t0 = time.time()
                if m == "mvt_flow_adapted":
                    score = fit_mvt_flow_adapted(train_w, seed)
                else:
                    score = fit_model(m, train_w, seed)
                s_cal = cycle_scores(score, cal_c, mu, sd)
                s_heal = cycle_scores(score, data["healthy"], mu, sd)
                s_fault = cycle_scores(score, data["faulty"], mu, sd)
                np.savez(scores_dir / f"{key}.npz", cal=s_cal, healthy=s_heal, faulty=s_fault)
                entry = task_metrics(s_heal, s_fault, thr=float(s_cal.max()))
                if m in DET:
                    entry["auroc_ci95_cycle_bootstrap"] = bootstrap_auroc_ci(s_heal, s_fault)
                entry["seed_semantics"] = "deterministic_1fit" if m in DET else "stochastic_seed"
                entry["wall_s"] = round(time.time() - t0, 1)
                results[key] = entry
                out_path.write_text(json.dumps(results, indent=2))
                print(f"[done] {key}: AUROC={entry['auroc']:.3f} AUPRC={entry['auprc']:.3f} "
                      f"FA/1000={entry['false_alarms_per_1000_healthy_cycles']:.0f} ({entry['wall_s']}s)",
                      flush=True)

    # csv + macro
    rows = []
    for k, v in results.items():
        if k.startswith("_"):
            continue
        task, rest = k.split("_", 1)
        m, s = rest.rsplit("_seed", 1)
        rows.append(dict(task=task, model=m, seed=s, **{kk: vv for kk, vv in v.items()
                                                        if not isinstance(vv, list)}))
    with (RUN / "mead_core8_metrics.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # dataset-level macro for the unified matrix: mean over 7 tasks per model/seed
    macro = {}
    for r in rows:
        macro.setdefault((r["model"], r["seed"]), []).append(r)
    uni = {}
    for (m, s), rs in macro.items():
        if len(rs) == len(TASKS):
            uni[f"{m}_seed{s}"] = {"macro": {
                "auroc": float(np.mean([r["auroc"] for r in rs])),
                "auprc": float(np.mean([r["auprc"] for r in rs])),
                "fpr_at_tpr90": float(np.mean([r["fpr_at_tpr90"] for r in rs]))}}
    uni["_protocol"] = results["_protocol"]
    (RUN / "mead_core8_macro.json").write_text(json.dumps(uni, indent=2))
    print("macro rows:", len(uni) - 1)


if __name__ == "__main__":
    import sys
    main(tasks=sys.argv[1].split(",") if len(sys.argv) > 1 else None)
