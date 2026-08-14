from __future__ import annotations

import math

import numpy as np
from scipy.stats import chi2


def gaussian_oracle_radius(dimension: int, sigma: float, alpha: float) -> float:
    if dimension <= 0 or sigma <= 0.0 or not 0.0 < alpha < 1.0:
        raise ValueError("invalid Gaussian radius arguments")
    return float(sigma * math.sqrt(chi2.ppf(1.0 - alpha, dimension)))


def empirical_norm_radius(samples: np.ndarray, alpha: float) -> float:
    values = np.linalg.norm(np.asarray(samples, dtype=float), axis=1)
    try:
        return float(np.quantile(values, 1.0 - alpha, method="higher"))
    except TypeError:
        return float(np.quantile(values, 1.0 - alpha, interpolation="higher"))


def whiten(values: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    covariance = np.asarray(covariance, dtype=float)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    if np.min(eigenvalues) <= 0.0:
        raise ValueError("covariance must be SPD")
    inverse_square_root = eigenvectors @ np.diag(eigenvalues**-0.5) @ eigenvectors.T
    return np.asarray(values, dtype=float) @ inverse_square_root.T
