"""E3: CC-FDI exploration on RoAD — event-level with per-context thresholds.

Context = official `action` column (0-9) at window centers. Thresholds =
per-context quantiles of healthy-VALIDATION scores (3 held-out recordings),
falling back to marginal for small cells (<40). Dev anomaly = collision
recordings only (weight/velocity sealed). Metrics on the R5 grid: event recall
+ false alarms per hour, marginal vs per-context vs permuted-context control.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from certo_fdi_reset_v2.benchmarks.road_reverify import (
    Road, WINDOW, STRIDE, SAMPLE_HZ, fit_scaler, apply_scaler, model_scores,
    split_recordings, SEEDS,
)

RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/explore"
)
MIN_CELL = 40
ACTION_COL = 0  # verified: columns[0] == 'action'


def windows_with_ctx(arr: np.ndarray):
    feats = arr[:, :86]
    label = arr[:, 86] if arr.shape[1] > 86 else np.zeros(len(arr))
    idx = np.arange(0, len(arr) - WINDOW + 1, STRIDE)
    w = np.stack([feats[i : i + WINDOW] for i in idx])
    y = np.array([label[i : i + WINDOW].max() for i in idx])
    c = np.array([int(arr[i + WINDOW // 2, ACTION_COL]) for i in idx])
    return w, y, c, idx


def main() -> int:
    road = Road.load()
    assert road.columns[ACTION_COL] == "action"
    train_ids, val_ids = split_recordings(len(road.training), 3, SEEDS[0])
    train_arrays = [road.training[i] for i in train_ids]
    val_arrays = [road.training[i] for i in val_ids]
    mn, span = fit_scaler(train_arrays)

    def prep(arr):
        return windows_with_ctx(apply_scaler(arr, mn, span))

    train_w = np.concatenate([prep(a)[0] for a in train_arrays], 0)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUN_DIR / "e3_road.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}

    for m in ("pca_spe", "gru_ae"):
        key = m
        if key in results:
            print(f"[skip] {key}", flush=True)
            continue
        t0 = time.time()
        val_s, val_c = [], []
        for a in val_arrays:
            w, _, c, _ = prep(a)
            val_s.append(model_scores(m, train_w, w, SEEDS[0]))
            val_c.append(c)
        val_s, val_c = np.concatenate(val_s), np.concatenate(val_c)
        rng = np.random.default_rng(SEEDS[1])
        val_c_perm = rng.permutation(val_c)

        entry = {}
        for q in (0.99, 0.999, 1.0):
            def thresholds(ctx_labels):
                marg = float(np.quantile(val_s, q)) if q < 1.0 else float(val_s.max())
                th = {}
                for cv in np.unique(ctx_labels):
                    sc = val_s[ctx_labels == cv]
                    if len(sc) >= MIN_CELL:
                        th[int(cv)] = float(np.quantile(sc, q)) if q < 1.0 else float(sc.max())
                return th, marg

            variants = {"marginal": ({}, float(np.quantile(val_s, q)) if q < 1.0 else float(val_s.max())),
                        "ctx": thresholds(val_c),
                        "permuted": thresholds(val_c_perm)}
            qent = {}
            for vname, (th, marg) in variants.items():
                events_total = events_hit = 0
                fp = 0
                hours = 0.0
                for rec in road.anomalies["collision"]:
                    w, y, c, idx = prep(rec)
                    s = model_scores(m, train_w, w, SEEDS[0])
                    thr = np.array([th.get(int(cv), marg) for cv in c])
                    alarm = s > thr
                    lab = rec[:, 86]
                    edges = np.flatnonzero(np.diff(np.concatenate([[0], lab > 0, [0]])))
                    for st, en in zip(edges[::2], edges[1::2]):
                        events_total += 1
                        touching = (idx + WINDOW > st) & (idx < en)
                        if alarm[touching].any():
                            events_hit += 1
                    fp += int((alarm & (y == 0)).sum())
                    hours += float((y == 0).sum()) * STRIDE / SAMPLE_HZ / 3600.0
                for a in val_arrays:
                    w, _, c, _ = prep(a)
                    s = model_scores(m, train_w, w, SEEDS[0])
                    thr = np.array([th.get(int(cv), marg) for cv in c])
                    fp += int((s > thr).sum())
                    hours += len(w) * STRIDE / SAMPLE_HZ / 3600.0
                qent[vname] = {
                    "event_recall": events_hit / events_total if events_total else float("nan"),
                    "events_total": events_total,
                    "false_alarms_per_hour": fp / hours if hours else float("nan"),
                    "n_ctx_cells": len(th),
                }
            entry[f"q{q}"] = qent
        results[key] = {"grid": entry, "wall_seconds": round(time.time() - t0, 1)}
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        for q, qent in entry.items():
            print(f"[done] {m} {q}: " + " | ".join(
                f"{v}: rec={d['event_recall']:.2f} FA/h={d['false_alarms_per_hour']:.1f}"
                for v, d in qent.items()), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
