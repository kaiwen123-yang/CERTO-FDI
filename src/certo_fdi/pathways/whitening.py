"""Context-conditional whitening of the window residual (healthy data only).

``E_W`` is the stacked window residual (``n * M`` entries; the frozen 128-sample window is
sub-sampled to ``M`` time points so that a full ``(nM) x (nM)`` covariance is estimable from
the healthy train+validation windows -- see ``WINDOW_SUBSAMPLE_RATIONALE``).

The healthy model is

    E_W | C_W ~ N( mu_0(C_W), Sigma_0 ),   mu_0(C) = W C + b   (ridge least squares),
    z_W = Sigma_0^{-1/2} ( E_W - mu_0(C_W) ),   W_0 = Sigma_0^{-1/2}.

``C_W`` contains only *declared physical* context: controller id, speed scale, tool mass,
tool CoM z, temperature proxy, noise level. Configuration-region id and trajectory-family id
are never inputs (Stage 2A contract §3.2). Fitting uses healthy train + validation windows
only; no fault window, label, severity or location is touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

WINDOW_SUBSAMPLE_RATIONALE = (
    "The frozen evaluation window is 128 samples at 500 Hz. Stacking all of them would make "
    "E_W a 896-vector and Sigma_0 an 896x896 covariance, which ~8.8k healthy windows cannot "
    "estimate. Stage 2A therefore sub-samples the window on a fixed stride so that E_W has "
    "n*M entries with M=8 (56 for the 7-DoF arm), giving >150 healthy windows per covariance "
    "dimension. The sub-sample stride is a pre-registered numerical choice made on healthy "
    "data only; it is applied identically to the residual and to every dictionary column, so "
    "no geometry is discarded relative to the residual it is fitted against."
)


@dataclass
class ConditionalWhitener:
    """Healthy conditional mean + whitening of the stacked window residual."""

    ridge_mean: float = 1e-2
    shrinkage: float = 1e-6  # relative to trace(Sigma)/d
    W: np.ndarray | None = None
    b: np.ndarray | None = None
    c_mean: np.ndarray | None = None
    c_std: np.ndarray | None = None
    c_min: np.ndarray | None = None
    c_max: np.ndarray | None = None
    whitener: np.ndarray | None = None  # (d,d) Sigma^{-1/2}
    dewhitener: np.ndarray | None = None  # (d,d) Sigma^{+1/2}
    eigenvalues: np.ndarray | None = None
    diagnostics: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ fit
    def fit(self, E: np.ndarray, C: np.ndarray) -> "ConditionalWhitener":
        E = np.asarray(E, dtype=float)
        C = np.asarray(C, dtype=float)
        n, d = E.shape
        self.c_min, self.c_max = C.min(0), C.max(0)
        self.c_mean = C.mean(0)
        self.c_std = np.where(C.std(0) < 1e-8, 1.0, C.std(0))
        Cs = (C - self.c_mean) / self.c_std
        X = np.concatenate([Cs, np.ones((n, 1))], 1)
        A = X.T @ X + self.ridge_mean * np.eye(X.shape[1])
        A[-1, -1] -= self.ridge_mean
        coef = np.linalg.solve(A, X.T @ E)
        self.W, self.b = coef[:-1], coef[-1]
        R = E - X @ coef
        S = R.T @ R / max(n - X.shape[1], 1)
        S = 0.5 * (S + S.T)
        lam = self.shrinkage * float(np.trace(S)) / d
        S_reg = S + lam * np.eye(d)
        evals, evecs = np.linalg.eigh(S_reg)
        evals = np.maximum(evals, lam * 1e-6)
        self.eigenvalues = evals[::-1].copy()
        self.whitener = (evecs / np.sqrt(evals)) @ evecs.T
        self.dewhitener = (evecs * np.sqrt(evals)) @ evecs.T
        raw = np.linalg.eigvalsh(S)
        tol = float(raw.max()) * d * np.finfo(float).eps
        self.diagnostics = {
            "n_windows": int(n),
            "dimension": int(d),
            "ridge_mean": float(self.ridge_mean),
            "shrinkage_relative": float(self.shrinkage),
            "shrinkage_absolute": float(lam),
            "eigenvalue_max": float(self.eigenvalues[0]),
            "eigenvalue_min": float(self.eigenvalues[-1]),
            "condition_number": float(self.eigenvalues[0] / self.eigenvalues[-1]),
            "condition_number_unregularised": float(raw.max() / max(raw.min(), np.finfo(float).tiny)),
            "effective_rank_numeric": int((raw > tol).sum()),
            "effective_rank_participation": float(raw.sum() ** 2 / max((raw**2).sum(), 1e-300)),
            "context_clipped_to_healthy_range": True,
            "fitted_on": "healthy train + validation windows only",
        }
        return self

    # ------------------------------------------------------------------ apply
    def mean(self, C: np.ndarray) -> np.ndarray:
        C = np.clip(np.asarray(C, dtype=float), self.c_min, self.c_max)
        return ((C - self.c_mean) / self.c_std) @ self.W + self.b

    def transform(self, E: np.ndarray, C: np.ndarray) -> np.ndarray:
        """(N,d) whitened residuals ``z_W``."""
        return (np.asarray(E, dtype=float) - self.mean(C)) @ self.whitener

    def whiten_dictionary(self, D: np.ndarray) -> np.ndarray:
        """``Dbar = W_0 D`` for a (d,p) or (N,d,p) dictionary."""
        D = np.asarray(D, dtype=float)
        if D.ndim == 2:
            return self.whitener @ D
        return np.einsum("de,nep->ndp", self.whitener, D)

    def to_dict(self) -> dict:
        return dict(self.diagnostics)


def window_time_offsets(window: int, n_points: int) -> np.ndarray:
    """Fixed within-window sample offsets (last sample always included, uniform stride)."""
    if n_points < 1 or n_points > window:
        raise ValueError("n_points must be in [1, window]")
    stride = window // n_points
    return np.arange(window - 1, -1, -stride)[::-1][-n_points:].copy()


def stack_window_residual(resid: np.ndarray, offsets: np.ndarray) -> np.ndarray:
    """(N, T, n) per-sample residuals -> (N, n*M) stacked window residual on ``offsets``."""
    return np.asarray(resid, dtype=float)[:, offsets, :].reshape(resid.shape[0], -1)
