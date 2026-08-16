"""G0 conditional Gaussian healthy density on pooled invariant window features.

``z | C ~ N(mu(C), Sigma)`` with ``mu(C) = W C + b`` (ridge least squares) and ``Sigma``
either diagonal or low-rank-plus-diagonal (probabilistic PCA of the healthy residuals).
The head is fitted on healthy *training* windows only; the score is ``-log p0(z|C)``.
The same head (form and capacity) is used for every representation so that gains can be
attributed to the representation rather than to density-model capacity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ConditionalGaussian:
    conditional: bool = True
    covariance: str = "lowrank"  # diag | lowrank
    rank: int = 8
    ridge: float = 1e-2
    W: np.ndarray | None = None
    b: np.ndarray | None = None
    z_mean: np.ndarray | None = None
    z_std: np.ndarray | None = None
    c_mean: np.ndarray | None = None
    c_std: np.ndarray | None = None
    c_min: np.ndarray | None = None
    c_max: np.ndarray | None = None
    diag_var: np.ndarray | None = None
    U: np.ndarray | None = None  # (D, r) factor loadings scaled by sqrt(eigval - noise)
    logdet: float = 0.0
    prec: np.ndarray | None = None
    block_slices: dict[str, slice] = field(default_factory=dict)

    # ------------------------------------------------------------------ fit
    def _prep(self, z: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        zs = (z - self.z_mean) / self.z_std
        if self.conditional:
            # clip to the healthy training range: the conditional mean is never extrapolated
            c = np.clip(c, self.c_min, self.c_max)
            cs = (c - self.c_mean) / self.c_std
        else:
            cs = np.zeros((z.shape[0], 0))
        return zs, cs

    def fit(self, z: np.ndarray, c: np.ndarray, block_slices: dict[str, slice] | None = None) -> "ConditionalGaussian":
        z = np.asarray(z, dtype=float)
        c = np.asarray(c, dtype=float)
        self.block_slices = block_slices or {}
        self.z_mean = z.mean(0)
        self.z_std = np.where(z.std(0) < 1e-8, 1.0, z.std(0))
        self.c_min = c.min(0)
        self.c_max = c.max(0)
        self.c_mean = c.mean(0)
        self.c_std = np.where(c.std(0) < 1e-8, 1.0, c.std(0))
        zs, cs = self._prep(z, c)
        n, d = zs.shape
        if self.conditional and cs.shape[1] > 0:
            X = np.concatenate([cs, np.ones((n, 1))], 1)
            A = X.T @ X + self.ridge * np.eye(X.shape[1])
            A[-1, -1] -= self.ridge
            coef = np.linalg.solve(A, X.T @ zs)
            self.W, self.b = coef[:-1], coef[-1]
            resid = zs - X @ coef
        else:
            self.W, self.b = np.zeros((cs.shape[1], d)), zs.mean(0)
            resid = zs - self.b
        cov = resid.T @ resid / max(n - 1, 1)
        if self.covariance == "diag" or self.rank <= 0 or self.rank >= d:
            var = np.diag(cov) + 1e-6
            self.diag_var = var
            self.U = None
            self.prec = np.diag(1.0 / var)
            self.logdet = float(np.log(var).sum())
        else:
            evals, evecs = np.linalg.eigh(cov)
            evals, evecs = evals[::-1], evecs[:, ::-1]
            r = int(self.rank)
            noise = float(max(evals[r:].mean(), 1e-6))
            self.U = evecs[:, :r] * np.sqrt(np.maximum(evals[:r] - noise, 0.0))
            self.diag_var = np.full(d, noise)
            sigma = self.U @ self.U.T + np.diag(self.diag_var)
            self.prec = np.linalg.inv(sigma)
            self.logdet = float(np.linalg.slogdet(sigma)[1])
        return self

    # ------------------------------------------------------------------ score
    def residual(self, z: np.ndarray, c: np.ndarray) -> np.ndarray:
        zs, cs = self._prep(np.asarray(z, dtype=float), np.asarray(c, dtype=float))
        mu = (cs @ self.W + self.b) if (self.conditional and cs.shape[1] > 0) else self.b
        return zs - mu

    def nll(self, z: np.ndarray, c: np.ndarray) -> np.ndarray:
        r = self.residual(z, c)
        d = r.shape[1]
        maha = np.einsum("nd,de,ne->n", r, self.prec, r)
        return 0.5 * (maha + self.logdet + d * np.log(2 * np.pi))

    def block_nll(self, z: np.ndarray, c: np.ndarray) -> dict[str, np.ndarray]:
        """Per-block (e.g. per-link) diagonal-Gaussian NLL for localization."""
        r = self.residual(z, c)
        var = self.diag_var if self.U is None else (self.diag_var + (self.U**2).sum(1))
        out = {}
        for name, sl in self.block_slices.items():
            rr = r[:, sl]
            vv = var[sl]
            out[name] = 0.5 * ((rr**2 / vv).sum(1) + np.log(vv).sum() + rr.shape[1] * np.log(2 * np.pi))
        return out

    def to_dict(self) -> dict:
        return {"conditional": self.conditional, "covariance": self.covariance, "rank": self.rank, "dim": int(self.z_mean.size), "ctx_dim": int(self.c_mean.size), "logdet": self.logdet}


def pooled_window_features(x: np.ndarray, stats: tuple[str, ...] = ("mean", "std", "absmax")) -> np.ndarray:
    """Temporal pooling of (N, T, ...) -> (N, prod(...) * len(stats)) invariant window statistics."""
    n = x.shape[0]
    flat = x.reshape(n, x.shape[1], -1)
    parts = []
    for s in stats:
        if s == "mean":
            parts.append(flat.mean(1))
        elif s == "std":
            parts.append(flat.std(1))
        elif s == "absmax":
            parts.append(np.abs(flat).max(1))
        elif s == "last":
            parts.append(flat[:, -1])
    return np.concatenate(parts, 1)
