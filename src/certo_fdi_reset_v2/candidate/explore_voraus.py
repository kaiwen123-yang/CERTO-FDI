"""E1: CC-FDI exploration on voraus-AD (official split, official metric).

Front-ends {gru_pred, ocsvm, window_ae} fitted on 80% of official train
episodes; calibration on the held-out 20% healthy episodes; context = official
per-sample `action` (15 phases) at window centers; calibrators z / quantile vs
marginal and context-PERMUTED control. Metric: official per-category AUROC
mean + FPR@TPR90 (episode = window-mean aggregation, frozen).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

GPU_CHECKOUT = Path.home() / "research/CERTO-FDI-BASELINES/voraus-ad-dataset-gpu"
DATASET = Path.home() / "Downloads/voraus-ad-dataset-100hz.parquet"
RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/explore"
)
W, STRIDE = 50, 25
SEEDS = (260824, 260825, 260826)

sys.path.insert(0, str(GPU_CHECKOUT))

from certo_fdi_reset_v2.benchmarks.models import fit_model  # noqa: E402
from certo_fdi_reset_v2.candidate.context_calibration import (  # noqa: E402
    ContextCalibrator, permute_contexts,
)


def load_actions() -> dict[int, np.ndarray]:
    df = pd.read_parquet(DATASET, columns=["sample", "action"])
    return {int(s): g["action"].to_numpy() for s, g in df.groupby("sample")}


def episode_windows(ep: np.ndarray) -> np.ndarray:
    idx = np.arange(0, max(len(ep) - W + 1, 1), STRIDE)
    if len(ep) < W:
        ep = np.concatenate([ep, np.zeros((W - len(ep), ep.shape[1]), ep.dtype)], 0)
        idx = np.array([0])
    return np.stack([ep[i : i + W] for i in idx])


def window_contexts(action_series: np.ndarray, n_padded: int) -> np.ndarray:
    a = action_series
    if len(a) < n_padded:
        a = np.concatenate([a, np.full(n_padded - len(a), -1)])
    idx = np.arange(0, max(n_padded - W + 1, 1), STRIDE)
    return np.array([int(a[min(i + W // 2, len(a) - 1)]) for i in idx])


def per_category_metrics(meta: list[dict], ep_scores: np.ndarray) -> dict:
    from sklearn import metrics as M
    from voraus_ad import ANOMALY_CATEGORIES

    df = pd.DataFrame(meta)
    df["score"] = ep_scores
    aurocs, fprs = [], []
    per = {}
    for cat in ANOMALY_CATEGORIES:
        dfn = df[(df["category"] == cat.name) | (~df["anomaly"])]
        y = dfn["anomaly"].astype(bool).values
        fpr, tpr, _ = M.roc_curve(y, dfn["score"].values, pos_label=True)
        auroc = M.auc(fpr, tpr)
        i = int(np.searchsorted(tpr, 0.9, side="left"))
        per[cat.name] = round(float(auroc), 4)
        aurocs.append(auroc)
        fprs.append(float(fpr[min(i, len(fpr) - 1)]))
    return {"auroc_mean": float(np.mean(aurocs)), "fpr_at_tpr90_mean": float(np.mean(fprs)),
            "per_category": per}


def main() -> int:
    from voraus_ad import Signals, load_torch_dataloaders

    actions = load_actions()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUN_DIR / "e1_voraus.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}

    for seed in SEEDS:
        train_ds, _, _, test_dl = load_torch_dataloaders(
            dataset=DATASET, batch_size=32, columns=Signals.groups()["machine"],
            seed=seed, frequency_divider=1, train_gain=1.0, normalize=True, pad=True,
        )
        train_eps = [t[0].numpy() for t in train_ds]
        train_ids = [int(t[1]["sample"]) for t in train_ds]
        test_eps, test_meta = [], []
        for tensors, labels in test_dl:
            arr = tensors.float().numpy()
            for j in range(arr.shape[0]):
                test_eps.append(arr[j])
                test_meta.append({k: (v[j].item() if hasattr(v, "shape") else v[j])
                                  for k, v in labels.items()})
        rng = np.random.default_rng(seed)
        order = rng.permutation(len(train_eps))
        n_fit = int(0.8 * len(train_eps))
        fit_idx, cal_idx = order[:n_fit], order[n_fit:]

        n_padded = train_eps[0].shape[0]
        def wins_and_ctx(eps, ids):
            ws, cs, eids = [], [], []
            for k, (ep, sid) in enumerate(zip(eps, ids)):
                w = episode_windows(ep)
                ws.append(w)
                cs.append(window_contexts(actions[sid], n_padded))
                eids.append(np.full(len(w), k))
            return np.concatenate(ws), np.concatenate(cs), np.concatenate(eids)

        fit_w, _, _ = wins_and_ctx([train_eps[i] for i in fit_idx], [train_ids[i] for i in fit_idx])
        cal_w, cal_c, _ = wins_and_ctx([train_eps[i] for i in cal_idx], [train_ids[i] for i in cal_idx])
        test_ids = [int(m["sample"]) for m in test_meta]
        test_w, test_c, test_e = wins_and_ctx(test_eps, test_ids)

        for fe in ("gru_pred", "ocsvm", "window_ae"):
            key = f"{fe}_seed{seed}"
            if key in results:
                print(f"[skip] {key}", flush=True)
                continue
            t0 = time.time()
            score = fit_model(fe, fit_w, seed)
            s_cal, s_test = score(cal_w), score(test_w)
            variants = {}
            def agg(ws):
                return np.array([ws[test_e == k].mean() for k in range(len(test_eps))])
            variants["marginal"] = per_category_metrics(test_meta, agg(s_test))
            for mode in ("z", "quantile"):
                calib = ContextCalibrator(mode).fit(s_cal, cal_c)
                variants[f"ctx_{mode}"] = per_category_metrics(test_meta, agg(calib.transform(s_test, test_c)))
                pcal = ContextCalibrator(mode).fit(s_cal, permute_contexts(cal_c, seed))
                variants[f"permuted_{mode}"] = per_category_metrics(
                    test_meta, agg(pcal.transform(s_test, test_c)))
            results[key] = {"variants": variants, "wall_seconds": round(time.time() - t0, 1),
                            "n_contexts_calibrated": len(ContextCalibrator("z").fit(s_cal, cal_c).stats)}
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(f"[done] {key}: marginal={variants['marginal']['auroc_mean']:.4f} "
                  f"ctx_z={variants['ctx_z']['auroc_mean']:.4f} "
                  f"ctx_q={variants['ctx_quantile']['auroc_mean']:.4f} "
                  f"perm_z={variants['permuted_z']['auroc_mean']:.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
