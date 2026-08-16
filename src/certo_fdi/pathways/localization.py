"""Zero-shot per-link contact localization with an explicit rejection option.

The primary localizer is **never trained on fault labels**: it ranks links by how well a
constant contact wrench on that link explains the whitened window residual,

    score_l = -||z_W - Dbar_contact_l,W theta_hat_l||   (equivalently: explained energy),

and predicts ``argmax_l score_l``. It may also **reject** -- decline to localize -- when the
window is geometrically uninformative. All four rejection thresholds are calibrated on
**healthy validation windows only**, before any fault window is scored:

* the best/second-best margin is below the healthy ``margin_quantile``;
* every link's projection residual exceeds the healthy ``residual_quantile``;
* the best link's Fisher minimum eigenvalue is below the healthy ``fisher_quantile``;
* the link dictionaries are nearly indistinguishable (minimum principal angle below the
  healthy ``margin_quantile`` of the angle distribution).

Rejecting on healthy windows is not an error; the rate is reported as coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class RejectionCalibration:
    """Thresholds fitted on healthy validation windows (no fault data)."""

    margin_threshold: float = 0.0
    residual_threshold: float = float("inf")
    fisher_threshold: float = 0.0
    angle_threshold: float = 0.0
    quantiles: dict = field(default_factory=dict)
    n_healthy_windows: int = 0

    @staticmethod
    def fit(margin: np.ndarray, min_residual: np.ndarray, fisher: np.ndarray, angle: np.ndarray, cfg: dict) -> "RejectionCalibration":
        q = {k: float(cfg[k]) for k in ("margin_quantile", "residual_quantile", "fisher_quantile")}
        return RejectionCalibration(
            margin_threshold=float(np.nanquantile(margin, q["margin_quantile"])),
            residual_threshold=float(np.nanquantile(min_residual, q["residual_quantile"])),
            fisher_threshold=float(np.nanquantile(fisher, q["fisher_quantile"])),
            angle_threshold=float(np.nanquantile(angle, q["margin_quantile"])),
            quantiles=q,
            n_healthy_windows=int(len(margin)),
        )

    def to_dict(self) -> dict:
        return {"margin_threshold": self.margin_threshold, "residual_threshold": self.residual_threshold,
                "fisher_threshold": self.fisher_threshold, "angle_threshold": self.angle_threshold,
                "quantiles": self.quantiles, "n_healthy_windows": self.n_healthy_windows,
                "calibrated_on": "healthy validation windows only"}


def localize(block: dict[str, np.ndarray], diagnosability: dict[str, np.ndarray], calib: RejectionCalibration | None) -> dict[str, np.ndarray]:
    """Predicted link, margin and rejection flags for a batch of windows."""
    explained = block["explained_fraction"]
    residual = block["projection_residual"]
    pred = np.argmin(residual, axis=1)  # score_l = -projection_residual
    order = np.argsort(residual, axis=1)
    idx = np.arange(len(pred))
    margin_resid = residual[idx, order[:, 1]] - residual[idx, order[:, 0]] if residual.shape[1] > 1 else np.zeros(len(pred))
    out = {
        "predicted_link": pred.astype(int),
        "rank_order": order.astype(int),
        "margin_explained": block["margin"],
        "margin_residual": margin_resid,
        "min_projection_residual": residual[idx, order[:, 0]],
        "best_explained": explained[idx, pred],
    }
    if calib is None:
        out["reject"] = np.zeros(len(pred), dtype=bool)
        out["reject_reason"] = np.array(["none"] * len(pred))
        return out
    fisher = diagnosability["fisher_min_eigenvalue"]
    angle = diagnosability["link_min_angle"]
    r_margin = out["margin_explained"] < calib.margin_threshold
    r_resid = out["min_projection_residual"] > calib.residual_threshold
    r_fisher = fisher < calib.fisher_threshold
    r_angle = angle < calib.angle_threshold
    reject = r_margin | r_resid | r_fisher | r_angle
    reason = np.array(["none"] * len(pred), dtype=object)
    reason[r_angle] = "link_dictionaries_indistinguishable"
    reason[r_fisher] = "low_contact_observability"
    reason[r_resid] = "no_link_explains_the_residual"
    reason[r_margin] = "ambiguous_link_margin"
    out.update({"reject": reject, "reject_reason": reason.astype(str),
                "reject_margin": r_margin, "reject_residual": r_resid, "reject_fisher": r_fisher, "reject_angle": r_angle})
    return out


def localization_scores(pred: np.ndarray, target: np.ndarray, n_links: int, ranks: np.ndarray | None = None, keep: np.ndarray | None = None) -> dict[str, float]:
    """top-1 / top-2 / mean chain distance, optionally restricted to accepted windows."""
    pred = np.asarray(pred, dtype=int)
    target = np.asarray(target, dtype=int)
    m = np.ones(len(pred), dtype=bool) if keep is None else np.asarray(keep, dtype=bool)
    if m.sum() == 0:
        return {"n": 0, "top1": float("nan"), "top2": float("nan"), "mean_chain_distance": float("nan"), "coverage": 0.0}
    top1 = float((pred[m] == target[m]).mean())
    if ranks is not None:
        r = np.asarray(ranks, dtype=int)[m]
        top2 = float(np.mean([target[m][i] in r[i, :2] for i in range(m.sum())]))
    else:
        top2 = float("nan")
    return {"n": int(m.sum()), "top1": top1, "top2": top2,
            "mean_chain_distance": float(np.abs(pred[m] - target[m]).mean()),
            "coverage": float(m.mean())}


def confusion(pred: np.ndarray, target: np.ndarray, n_links: int, keep: np.ndarray | None = None) -> np.ndarray:
    """(n_links, n_links) confusion matrix ``[true, predicted]``."""
    m = np.ones(len(pred), dtype=bool) if keep is None else np.asarray(keep, dtype=bool)
    c = np.zeros((n_links, n_links), dtype=int)
    for t, p in zip(np.asarray(target, dtype=int)[m], np.asarray(pred, dtype=int)[m]):
        if 0 <= t < n_links and 0 <= p < n_links:
            c[t, p] += 1
    return c
