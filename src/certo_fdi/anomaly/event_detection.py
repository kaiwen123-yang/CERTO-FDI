"""Window- and event-level detection metrics from raw per-window scores.

Definitions (fixed before any fault result is seen):
* window label = fault active at the window's last sample (causal detection at time t);
* event = the faulty segment of a fault episode; detected if any window in the segment
  exceeds the threshold; detection delay = time from onset to the first alarm;
* false alarms/hour = number of alarm *onsets* (below->above threshold transitions) on
  healthy windows divided by the healthy time covered;
* FPR@TPR90 = healthy-window false-positive rate at the threshold achieving 90% TPR.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve


def safe_auroc(y: np.ndarray, s: np.ndarray) -> float:
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return float("nan")
    return float(roc_auc_score(y, s))


def safe_auprc(y: np.ndarray, s: np.ndarray) -> float:
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return float("nan")
    return float(average_precision_score(y, s))


def fpr_at_tpr(y: np.ndarray, s: np.ndarray, tpr_target: float = 0.9) -> float:
    y = np.asarray(y).astype(int)
    if y.min() == y.max():
        return float("nan")
    fpr, tpr, _ = roc_curve(y, s)
    idx = np.searchsorted(tpr, tpr_target, side="left")
    idx = min(idx, len(fpr) - 1)
    return float(fpr[idx])


def window_metrics(y: np.ndarray, s: np.ndarray, threshold: float) -> dict[str, float]:
    y = np.asarray(y).astype(int)
    s = np.asarray(s, dtype=float)
    alarm = s > threshold
    out = {
        "auroc": safe_auroc(y, s),
        "auprc": safe_auprc(y, s),
        "fpr_at_tpr90": fpr_at_tpr(y, s, 0.9),
        "tpr_at_threshold": float(alarm[y == 1].mean()) if (y == 1).any() else float("nan"),
        "fpr_at_threshold": float(alarm[y == 0].mean()) if (y == 0).any() else float("nan"),
        "n_pos": int((y == 1).sum()),
        "n_neg": int((y == 0).sum()),
    }
    return out


def persistence_filter(alarm: np.ndarray, k: int) -> np.ndarray:
    """Alarm only when ``k`` consecutive windows exceed the threshold (causal)."""
    if k <= 1:
        return alarm
    out = np.zeros_like(alarm, dtype=bool)
    run = 0
    for i, a in enumerate(alarm):
        run = run + 1 if a else 0
        out[i] = run >= k
    return out


def event_metrics(episodes: list[dict], threshold: float, window_dt: float, persistence: int = 1) -> dict[str, float]:
    """``episodes``: list of dicts with keys ``scores`` (per window, time ordered), ``labels``
    (window labels), ``t_end`` (window end times), ``is_fault_episode``, ``onset_s``.
    ``persistence``: number of consecutive above-threshold windows required for an alarm."""
    detected, delays, n_events = 0, [], 0
    fa_onsets, healthy_seconds = 0, 0.0
    tp = fp = fn = 0
    for ep in episodes:
        s = np.asarray(ep["scores"], dtype=float)
        y = np.asarray(ep["labels"]).astype(int)
        t = np.asarray(ep["t_end"], dtype=float)
        alarm = persistence_filter(s > threshold, persistence)
        healthy_mask = y == 0
        if healthy_mask.any():
            a = alarm[healthy_mask]
            onsets = int(a[0]) + int(np.sum(a[1:] & ~a[:-1]))
            fa_onsets += onsets
            healthy_seconds += float(healthy_mask.sum()) * window_dt
            fp += onsets
        if ep["is_fault_episode"] and (y == 1).any():
            n_events += 1
            hit = alarm & (y == 1)
            if hit.any():
                detected += 1
                tp += 1
                delays.append(float(t[hit][0] - ep["onset_s"]))
            else:
                fn += 1
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    return {
        "n_events": n_events,
        "event_tpr": detected / max(n_events, 1),
        "false_alarms_per_hour": fa_onsets / max(healthy_seconds / 3600.0, 1e-9),
        "healthy_hours": healthy_seconds / 3600.0,
        "detection_delay_median_s": float(np.median(delays)) if delays else float("nan"),
        "detection_delay_mean_s": float(np.mean(delays)) if delays else float("nan"),
        "event_f1": 2 * prec * rec / max(prec + rec, 1e-9),
        "event_precision": prec,
        "event_recall": rec,
    }


def episode_level_auroc(episodes: list[dict]) -> float:
    """Event-level AUROC: positives = max score over the faulty segment of each fault
    episode; negatives = max score over each healthy episode (and pre-onset segments)."""
    pos, neg = [], []
    for ep in episodes:
        s = np.asarray(ep["scores"], dtype=float)
        y = np.asarray(ep["labels"]).astype(int)
        if (y == 1).any():
            pos.append(s[y == 1].max())
        if (y == 0).any():
            neg.append(s[y == 0].max())
    if not pos or not neg:
        return float("nan")
    return safe_auroc(np.r_[np.ones(len(pos)), np.zeros(len(neg))], np.r_[pos, neg])
