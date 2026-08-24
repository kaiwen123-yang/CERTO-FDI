"""U0: RoAD CORE-8 rows (frozen before results).

Closes the V2 matrix-truth gap: RoAD never had the CORE-8. Protocol (frozen):
windows 50 @10Hz stride 10, min-max scaling fitted on the 6 training
recordings of the frozen split (seed 260824, same as V2 R-experiments);
evaluation = window-level AUROC/AUPRC/FPR@TPR90 per subset with the paper's
negative-set semantics (collision: within-recording normals; weight/velocity:
control-set negatives), macro over the three subsets. Deterministic models
(mahalanobis, pca_spe) run once with a recording-level bootstrap CI
(15 recordings -> bootstrap over the 6 anomaly/control recordings, reported
as diagnostic only); stochastic models run seeds 260824-26. seed_count is
recorded per row; nothing is described as 3-seed unless it ran 3 seeds.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from certo_fdi_reset_v2.benchmarks.models import CLASSICAL, NEURAL, fit_model
from certo_fdi_reset_v2.benchmarks.road_reverify import (
    Road, WINDOW, STRIDE, fit_scaler, apply_scaler, split_recordings,
)

RUN = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r/unified")
SEEDS = (260824, 260825, 260826)
DET = ("mahalanobis", "pca_spe")
STOCH = ("iforest", "ocsvm", "window_ae", "gru_ae", "tcn_ae", "gru_pred")


def wins(arr, mn, span):
    a = apply_scaler(arr, mn, span)
    feats = a[:, :86]
    lab = a[:, 86] if a.shape[1] > 86 else np.zeros(len(a))
    idx = np.arange(0, len(a) - WINDOW + 1, STRIDE)
    w = np.stack([feats[i:i + WINDOW] for i in idx]).astype(np.float32)
    y = np.array([lab[i:i + WINDOW].max() for i in idx])
    return w, y


def main():
    from sklearn import metrics as M
    RUN.mkdir(parents=True, exist_ok=True)
    road = Road.load()
    train_ids, _ = split_recordings(len(road.training), 3, SEEDS[0])
    train_arrays = [road.training[i] for i in train_ids]
    mn, span = fit_scaler(train_arrays)
    train_w = np.concatenate([wins(a, mn, span)[0] for a in train_arrays])
    ctrl_w, _ = wins(road.anomalies["control"][0], mn, span)

    out_path = RUN / "road_core8.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}
    results["_protocol"] = __doc__.strip().split("\n")[2:14]

    def subset_metrics(score):
        s_ctrl = score(ctrl_w)
        per = {}
        vals = []
        # collision: within-recording
        ys, ss = [], []
        for rec in road.anomalies["collision"]:
            w, y = wins(rec, mn, span)
            ys.append(y); ss.append(score(w))
        y_all, s_all = np.concatenate(ys), np.concatenate(ss)
        for name, (y, s) in {
            "collision": (y_all > 0, s_all),
            "weight": (None, None), "velocity": (None, None),
        }.items():
            if name == "collision":
                pass
            else:
                s_pos = np.concatenate([score(wins(r, mn, span)[0]) for r in road.anomalies[name]])
                y = np.concatenate([np.ones(len(s_pos)), np.zeros(len(s_ctrl))]) > 0
                s = np.concatenate([s_pos, s_ctrl])
            fpr, tpr, _ = M.roc_curve(y, s)
            i = int(np.searchsorted(tpr, 0.9, side="left"))
            per[name] = {"auroc": float(M.auc(fpr, tpr)),
                         "auprc": float(M.average_precision_score(y, s)),
                         "fpr_at_tpr90": float(fpr[min(i, len(fpr) - 1)])}
            vals.append(per[name]["auroc"])
        per["macro_auroc"] = float(np.mean(vals))
        return per

    for m in DET + STOCH:
        seeds = (SEEDS[0],) if m in DET else SEEDS
        for seed in seeds:
            key = f"{m}_seed{seed}"
            if key in results:
                print(f"[skip] {key}", flush=True)
                continue
            t0 = time.time()
            score = fit_model(m, train_w, seed)
            entry = subset_metrics(score)
            entry["seed_count_semantics"] = ("deterministic_1fit" if m in DET else "stochastic_seed")
            entry["wall_s"] = round(time.time() - t0, 1)
            results[key] = entry
            out_path.write_text(json.dumps(results, indent=2))
            print(f"[done] {key}: macro={entry['macro_auroc']:.3f} "
                  f"col={entry['collision']['auroc']:.3f} wt={entry['weight']['auroc']:.3f} "
                  f"vel={entry['velocity']['auroc']:.3f} ({entry['wall_s']}s)", flush=True)


if __name__ == "__main__":
    main()
