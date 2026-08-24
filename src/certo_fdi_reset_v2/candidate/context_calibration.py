"""CC-FDI core: context-conditioned calibration of window anomaly scores.

Pure decision layer. Inputs: per-window scores s, per-window context ids c,
plus a healthy calibration set (s_cal, c_cal). Outputs: transformed scores
whose healthy distribution is homogenized across contexts.

Two frozen calibrators (16_candidate_collision_matrix.md):
  - "z":        s' = (s - mu_c) / sd_c            (CFAR-style standardization)
  - "quantile": s' = ecdf_c(s) = rank of s within the context's healthy
                calibration scores (a split-conformal p-value complement)

Small-cell rule (frozen): contexts with < MIN_CELL healthy calibration windows
fall back to the marginal statistics. The context-PERMUTED control shuffles the
calibration-set context labels within the healthy set (fit-side permutation),
destroying the context-score association while keeping cell sizes identical.
"""

from __future__ import annotations

import numpy as np

MIN_CELL = 40


class ContextCalibrator:
    def __init__(self, mode: str = "z", min_cell: int = MIN_CELL):
        assert mode in ("z", "quantile")
        self.mode = mode
        self.min_cell = min_cell
        self.stats: dict = {}
        self.marginal: tuple | np.ndarray | None = None

    def fit(self, s_cal: np.ndarray, c_cal: np.ndarray) -> "ContextCalibrator":
        s_cal = np.asarray(s_cal, dtype=np.float64)
        c_cal = np.asarray(c_cal)
        if self.mode == "z":
            self.marginal = (float(s_cal.mean()), float(s_cal.std() + 1e-12))
        else:
            self.marginal = np.sort(s_cal)
        for c in np.unique(c_cal):
            sc = s_cal[c_cal == c]
            if len(sc) < self.min_cell:
                continue
            if self.mode == "z":
                self.stats[c] = (float(sc.mean()), float(sc.std() + 1e-12))
            else:
                self.stats[c] = np.sort(sc)
        return self

    def transform(self, s: np.ndarray, c: np.ndarray) -> np.ndarray:
        s = np.asarray(s, dtype=np.float64)
        c = np.asarray(c)
        out = np.empty_like(s)
        for ci in np.unique(c):
            m = c == ci
            ref = self.stats.get(ci, self.marginal)
            if self.mode == "z":
                mu, sd = ref
                out[m] = (s[m] - mu) / sd
            else:
                out[m] = np.searchsorted(ref, s[m], side="right") / (len(ref) + 1.0)
        return out


def permute_contexts(c_cal: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.permutation(np.asarray(c_cal))


def episode_scores(window_scores: np.ndarray, episode_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Frozen aggregator: episode score = MEAN over its windows."""
    eps = np.unique(episode_ids)
    return eps, np.array([window_scores[episode_ids == e].mean() for e in eps])
