"""Model-free physics baselines: generalized-momentum-observer residual with a fixed
threshold and with a state-dependent (dynamic) threshold, both calibrated on healthy
validation windows only. Rows are appended to the event/OOD detection tables."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from certo_fdi.anomaly.calibration import healthy_quantile_threshold
from certo_fdi.data.windows import WindowSet
from certo_fdi.experiments.evaluation import _detection_rows
from certo_fdi.experiments.pipeline import DataBundle


def _window_arrays(ws: WindowSet, device: str = "cpu"):
    """Per-window: max|r_gmo| per joint, mean|qd|, mean|qdd|, labels/meta (no model)."""
    r_max, qd_mean, qdd_mean, label, family, target, ep, start, ctx = ([] for _ in range(9))
    for batch in ws.iterate(512, False, device=device):
        r_max.append(batch["r_gmo"].abs().amax(1).cpu().numpy())
        qd_mean.append(batch["qd"].abs().mean(1).cpu().numpy())
        qdd_mean.append(batch["qdd"].abs().mean(1).cpu().numpy())
        label.append(batch["active"][:, -1].cpu().numpy())
        family.append(batch["family"].cpu().numpy())
        target.append(batch["target"][:, -1].cpu().numpy())
        ep.append(batch["episode_index"].numpy())
        start.append(batch["start"].numpy())
        ctx.append(batch["ctx"].cpu().numpy())
    return {k: np.concatenate(v) for k, v in dict(r_max=r_max, qd_mean=qd_mean, qdd_mean=qdd_mean, label=label, family=family, target=target, episode=ep, start=start, ctx=ctx).items()}


class _F:
    """Minimal WindowFeatures stand-in for _detection_rows (needs label/family/target/episode/start/ctx)."""

    def __init__(self, d):
        self.label, self.family, self.target, self.episode, self.start, self.ctx = d["label"], d["family"], d["target"], d["episode"], d["start"], d["ctx"]


def gmo_baseline_rows(bundle: DataBundle, cfg: dict, base: dict, quantile: float, device: str = "cpu") -> tuple[list[dict], list[dict]]:
    dt = float(cfg["simulation"]["control_dt_s"])
    ws_val = WindowSet(bundle.subset(bundle.val_ids), bundle.window, bundle.stride_train, device, min_start=bundle.eval_min_start)
    ws_test = WindowSet(bundle.subset(bundle.test_ids), bundle.window, bundle.stride_eval, device, min_start=bundle.eval_min_start)
    va, te = _window_arrays(ws_val, device), _window_arrays(ws_test, device)
    n = va["r_max"].shape[1]
    det_rows, ood_rows = [], []
    # fixed threshold: score = max_j |r_j|_max / sigma_j (sigma from healthy val)
    sigma = va["r_max"].mean(0) + 1e-9
    s_va = (va["r_max"] / sigma).max(1)
    s_te = (te["r_max"] / sigma).max(1)
    thr = healthy_quantile_threshold(s_va, quantile)
    d, o = _detection_rows({**base, "n_params": 0}, "gmo_fixed", "gmo_norm", None, thr, ws_test, _F(te), s_te, dt, s_va)
    det_rows += d
    ood_rows += o
    # dynamic threshold: per joint, |r_j| scale predicted from (1, mean|qd_j|, mean|qdd_j|) by ridge on healthy val
    coef = np.zeros((n, 3))
    for j in range(n):
        X = np.c_[np.ones(len(va["r_max"])), va["qd_mean"][:, j], va["qdd_mean"][:, j]]
        coef[j] = np.linalg.solve(X.T @ X + 1e-3 * np.eye(3), X.T @ va["r_max"][:, j])
    def dyn_score(a):
        out = np.zeros((len(a["r_max"]), n))
        for j in range(n):
            X = np.c_[np.ones(len(a["r_max"])), a["qd_mean"][:, j], a["qdd_mean"][:, j]]
            out[:, j] = a["r_max"][:, j] / np.maximum(X @ coef[j], 1e-6)
        return out.max(1)
    s_va2, s_te2 = dyn_score(va), dyn_score(te)
    thr2 = healthy_quantile_threshold(s_va2, quantile)
    d, o = _detection_rows({**base, "n_params": 0}, "gmo_dynamic", "gmo_dynamic_norm", None, thr2, ws_test, _F(te), s_te2, dt, s_va2)
    det_rows += d
    ood_rows += o
    return det_rows, ood_rows
