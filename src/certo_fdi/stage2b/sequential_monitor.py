"""Sequential wrappers around a calibrated per-window alarm (kickoff §05.6).

A per-window threshold alone alarms far too often: Stage 2A produced ~1650 event false alarms
per hour. Requiring temporal consistency is the classical fix, so five wrappers are compared,
all with parameters chosen on **healthy validation episodes only**:

``none``                 the raw per-window decision
``persistence_k_of_n``   alarm when k of the last n windows are above threshold (3-of-3, and the
                         frozen grid (2,3), (3,4), (3,5))
``hysteresis``           a two-threshold latch: raise at the high threshold, hold until the score
                         falls below a lower one
``one_sided_cusum``      a one-sided CUSUM on the calibrated exceedance, with drift and threshold
                         from a frozen grid

Every wrapper resets at an episode boundary; sequential state never leaks between episodes.
Fault data selects none of these parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

METHODS = ("none", "persistence_3_of_3", "persistence_2_of_3", "persistence_3_of_4",
           "persistence_3_of_5", "hysteresis", "one_sided_cusum")


def k_of_n(above: np.ndarray, k: int, n: int) -> np.ndarray:
    """Causal k-of-n persistence over a single episode's time-ordered windows.

    Vectorised with a cumulative sum: window ``i`` alarms when at least ``k`` of the ``n`` most
    recent windows (including itself) are above threshold. Before ``n`` windows have elapsed the
    partial history is used, so the rule never looks into the future.
    """
    above = np.asarray(above, dtype=bool)
    if n <= 1:
        return above.copy()
    c = np.cumsum(np.concatenate([[0], above.astype(int)]))
    i = np.arange(len(above))
    lo = np.maximum(0, i + 1 - n)
    return (c[i + 1] - c[lo]) >= k


def hysteresis(score: np.ndarray, high, low) -> np.ndarray:
    """Two-threshold latch: rise above ``high`` to alarm, stay alarmed until below ``low``.

    ``high`` and ``low`` may be scalars or **per-window** arrays, because a context-calibrated
    threshold varies within an episode; broadcasting keeps the latch context-aware instead of
    silently reverting to a global level.
    """
    score = np.asarray(score, dtype=float)
    high = np.broadcast_to(np.asarray(high, dtype=float), score.shape)
    low = np.broadcast_to(np.asarray(low, dtype=float), score.shape)
    out = np.zeros(len(score), dtype=bool)
    on = False
    for i in range(len(score)):
        if not on and score[i] > high[i]:
            on = True
        elif on and score[i] < low[i]:
            on = False
        out[i] = on
    return out


def one_sided_cusum(excess: np.ndarray, drift: float, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """One-sided CUSUM ``S_i = max(0, S_{i-1} + excess_i - drift)``, alarming at ``threshold``.

    ``excess`` is the calibrated exceedance (score minus its context threshold, in units of the
    healthy scale), so the statistic is comparable across contexts. The statistic resets to zero
    after an alarm so a single excursion cannot latch the rest of the episode.
    """
    excess = np.asarray(excess, dtype=float)
    S = np.zeros(len(excess))
    alarm = np.zeros(len(excess), dtype=bool)
    s = 0.0
    for i, e in enumerate(excess):
        s = max(0.0, s + e - drift)
        if s > threshold:
            alarm[i] = True
            s = 0.0
        S[i] = s
    return alarm, S


@dataclass
class SequentialSpec:
    """One fully specified wrapper, selected on healthy validation only."""

    method: str
    params: dict

    def apply(self, score: np.ndarray, threshold: np.ndarray, scale: float = 1.0) -> np.ndarray:
        score = np.asarray(score, dtype=float)
        threshold = np.asarray(threshold, dtype=float)
        above = score > threshold
        if self.method == "none":
            return above
        if self.method.startswith("persistence_"):
            return k_of_n(above, int(self.params["k"]), int(self.params["n"]))
        if self.method == "hysteresis":
            # thresholds are expressed relative to the calibrated per-window threshold, so the
            # latch stays context-aware rather than reverting to a global level
            return hysteresis(score, threshold, threshold * float(self.params["low_ratio"]))
        if self.method == "one_sided_cusum":
            excess = (score - threshold) / max(scale, 1e-12)
            a, _ = one_sided_cusum(excess, float(self.params["drift"]), float(self.params["threshold"]))
            return a
        raise ValueError(self.method)

    def to_dict(self) -> dict[str, Any]:
        return {"method": self.method, "params": dict(self.params)}


def candidate_specs(cfg: dict) -> list[SequentialSpec]:
    """The frozen candidate grid. Nothing outside this grid may be tried after seeing results."""
    s = cfg["sequential"]
    out = [SequentialSpec("none", {})]
    out.append(SequentialSpec("persistence_3_of_3", {"k": 3, "n": 3}))
    for k, n in s["persistence_grid"]:
        out.append(SequentialSpec(f"persistence_{k}_of_{n}", {"k": int(k), "n": int(n)}))
    for lr in s["hysteresis_high_low_ratio_grid"]:
        out.append(SequentialSpec("hysteresis", {"low_ratio": float(lr)}))
    for drift in s["cusum_drift_grid"]:
        for thr in s["cusum_threshold_grid"]:
            out.append(SequentialSpec("one_sided_cusum", {"drift": float(drift), "threshold": float(thr)}))
    return out


def family_of(spec: SequentialSpec) -> str:
    """The contract's five families, for reporting one representative per family."""
    if spec.method == "none":
        return "none"
    if spec.method == "persistence_3_of_3":
        return "persistence_3_of_3"
    if spec.method.startswith("persistence_"):
        return "persistence_grid"
    return spec.method
