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


def decode_localization(excess: np.ndarray, rule: str, *, sig: float = 2.0, rho: float = 0.25) -> np.ndarray:
    """Unsupervised link decoding from a per-link excess profile ``excess`` (n_links,) in healthy z-score units.

    * ``argmax``: peaked-pattern assumption (joint-local faults);
    * ``distal``: load-path assumption — the most distal link whose excess is significant
      (``>= max(sig, rho * max)``): a wrench applied to link i loads every joint j <= i;
    * ``pattern``: choose ``distal`` when the profile is cumulative (all links proximal to the distal
      candidate are significant), otherwise ``argmax``.
    Returns a ranking (descending preference) of link indices.
    """
    e = np.asarray(excess, dtype=float)
    n = e.size
    order_desc = np.argsort(-e)
    if rule == "argmax":
        return order_desc
    thr = max(sig, rho * float(e.max()))
    significant = np.where(e >= thr)[0]
    distal = int(significant.max()) if significant.size else int(order_desc[0])
    if rule == "distal":
        rest = [i for i in order_desc if i != distal]
        return np.array([distal] + rest)
    if rule == "pattern":
        proximal = e[: distal + 1]
        cumulative = bool(np.all(proximal >= thr)) and distal != int(order_desc[0])
        if cumulative:
            rest = [i for i in order_desc if i != distal]
            return np.array([distal] + rest)
        return order_desc
    raise ValueError(rule)
