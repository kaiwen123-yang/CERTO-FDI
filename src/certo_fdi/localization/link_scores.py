"""Unsupervised link/joint localization from per-link healthy NLL excess."""

from __future__ import annotations

import numpy as np


def localization_metrics(pred: np.ndarray, target: np.ndarray, n_links: int, k: int = 2) -> dict[str, float]:
    pred = np.asarray(pred)
    target = np.asarray(target)
    top1 = float((pred[:, 0] == target).mean()) if len(target) else float("nan")
    topk = float(np.mean([t in p[:k] for p, t in zip(pred, target)])) if len(target) else float("nan")
    dist = float(np.mean(np.abs(pred[:, 0] - target))) if len(target) else float("nan")
    conf = np.zeros((n_links, n_links), dtype=int)
    for p, t in zip(pred[:, 0], target):
        conf[int(t), int(p)] += 1
    return {"top1": top1, f"top{k}": topk, "mean_chain_distance": dist, "confusion": conf.tolist(), "n": int(len(target))}


def rank_links(excess: np.ndarray) -> np.ndarray:
    """excess (N, n_links) -> ranking indices per row (descending)."""
    return np.argsort(-np.asarray(excess), axis=1)
