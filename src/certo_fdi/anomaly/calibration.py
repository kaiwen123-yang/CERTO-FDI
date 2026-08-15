"""Healthy-only threshold calibration."""

from __future__ import annotations

import numpy as np


def healthy_quantile_threshold(healthy_val_scores: np.ndarray, quantile: float = 0.995) -> float:
    s = np.asarray(healthy_val_scores, dtype=float)
    return float(np.quantile(s, quantile))


def dynamic_threshold_fit(features: np.ndarray, scores: np.ndarray, quantile: float = 0.995, ridge: float = 1e-3) -> np.ndarray:
    """State-dependent threshold: linear regression of |score| on features (healthy val only),
    scaled so that ``quantile`` of healthy val scores fall below it. Returns [coef..., bias, scale]."""
    X = np.concatenate([features, np.ones((features.shape[0], 1))], 1)
    coef = np.linalg.solve(X.T @ X + ridge * np.eye(X.shape[1]), X.T @ scores)
    pred = X @ coef
    ratio = scores / np.maximum(pred, 1e-9)
    scale = float(np.quantile(ratio, quantile))
    return np.concatenate([coef, [scale]])


def dynamic_threshold_apply(params: np.ndarray, features: np.ndarray) -> np.ndarray:
    coef, scale = params[:-1], params[-1]
    X = np.concatenate([features, np.ones((features.shape[0], 1))], 1)
    return np.maximum(X @ coef, 1e-9) * scale
