"""Geometric statistics of the whitened fault-pathway dictionaries.

All statistics live in the *same* whitened residual coordinates ``z_W = W_0 (E_W - mu_0(C_W))``
and use the *same* window, so projections, principal angles and Fisher information are
directly comparable across fault families and links.

Ridge rule (declared before any result was produced, uses **no** data at all -- only the
numerical conditioning of the dictionary itself, contract §4.1):

    lambda_j = max( LAMBDA_RELATIVE * sigma_max(Dbar_j)^2 ,
                    sigma_max(Dbar_j)^2 / CONDITION_MAX )

so that ``cond(Dbar^T Dbar + lambda I) <= CONDITION_MAX`` and the ridge is never larger than
``LAMBDA_RELATIVE`` of the leading direction's energy. No fault label, severity or test
statistic enters the choice.
"""

from __future__ import annotations

import numpy as np

LAMBDA_RELATIVE = 1e-6
CONDITION_MAX = 1e6
RANK_TOLERANCE = 1e-10
# Absolute floor so the normal equations are positive definite even for an identically zero
# dictionary. That case is physical, not pathological: a point force applied ON a joint axis
# exerts no moment about it, so link 0's proximal candidate point has an all-zero dictionary.
# With the floor the fit returns theta = 0 and zero explained energy, which is the right answer.
LAMBDA_ABSOLUTE_FLOOR = 1e-12


def ridge_lambda(D: np.ndarray) -> np.ndarray:
    """Declared ridge for a (d,p) or (N,d,p) whitened dictionary -> scalar or (N,)."""
    D = np.asarray(D, dtype=float)
    s = np.linalg.svd(D, compute_uv=False)
    smax2 = (s[..., 0] ** 2) if s.ndim > 1 else (s[0] ** 2)
    return np.maximum(np.maximum(LAMBDA_RELATIVE * smax2, smax2 / CONDITION_MAX), LAMBDA_ABSOLUTE_FLOOR)


def dictionary_spectrum(D: np.ndarray) -> dict[str, float]:
    """Rank, singular values, condition number and nullspace dimension of one (d,p) block."""
    D = np.asarray(D, dtype=float)
    s = np.linalg.svd(D, compute_uv=False)
    smax = float(s[0]) if s.size else 0.0
    tol = smax * max(D.shape) * np.finfo(float).eps
    pos = s[s > max(tol, RANK_TOLERANCE * max(smax, 1e-300))]
    return {
        "n_rows": int(D.shape[0]),
        "n_columns": int(D.shape[1]),
        "rank": int(pos.size),
        "nullspace_dimension": int(D.shape[1] - pos.size),
        "singular_value_max": smax,
        "singular_value_min_positive": float(pos[-1]) if pos.size else float("nan"),
        "condition_number": float(pos[0] / pos[-1]) if pos.size else float("inf"),
        "frobenius_norm": float(np.linalg.norm(D)),
        "singular_values": [float(v) for v in s],
    }


def batched_projection(D: np.ndarray, z: np.ndarray, lam: np.ndarray | float | None = None) -> dict[str, np.ndarray]:
    """Ridge weighted-least-squares projection of ``z`` (N,d) on ``D`` (N,d,p) or (d,p).

    Returns per-window ``theta``, ``projection_residual`` (norm), ``explained_energy``
    (absolute, i.e. ``||D theta||^2``), ``explained_fraction`` and ``coefficient_norm``.
    """
    D = np.asarray(D, dtype=float)
    z = np.asarray(z, dtype=float)
    if D.ndim == 2:
        D = np.broadcast_to(D, (z.shape[0],) + D.shape)
    lam = ridge_lambda(D) if lam is None else lam
    lam = np.broadcast_to(np.asarray(lam, dtype=float), (D.shape[0],))
    G = np.einsum("ndp,ndq->npq", D, D)
    b = np.einsum("ndp,nd->np", D, z)
    p = D.shape[2]
    A = G + lam[:, None, None] * np.eye(p)[None]
    theta = np.linalg.solve(A, b[..., None])[..., 0]
    fit_energy = np.einsum("np,npq,nq->n", theta, G, theta)
    z_energy = (z**2).sum(1)
    resid2 = np.maximum(z_energy - 2.0 * (theta * b).sum(1) + fit_energy, 0.0)
    return {
        "theta": theta,
        "projection_residual": np.sqrt(resid2),
        "projection_residual_energy": resid2,
        "explained_energy": fit_energy,
        "explained_fraction": fit_energy / np.maximum(z_energy, 1e-12),
        "coefficient_norm": np.linalg.norm(theta, axis=1),
        "z_energy": z_energy,
        "ridge_lambda": lam,
    }


def exact_projection_energy(D: np.ndarray, z: np.ndarray, rtol: float = 1e-8) -> np.ndarray:
    """``||P_D z||^2`` with the *exact* orthogonal projector (rank-truncated SVD).

    Used to cross-check the ridge projection (contract §7.2 item 4).
    """
    D = np.asarray(D, dtype=float)
    z = np.asarray(z, dtype=float)
    if D.ndim == 2:
        D = np.broadcast_to(D, (z.shape[0],) + D.shape)
    out = np.zeros(z.shape[0])
    for i in range(z.shape[0]):
        U, s, _ = np.linalg.svd(D[i], full_matrices=False)
        keep = s > (s[0] * rtol if s.size else 0.0)
        out[i] = float(((U[:, keep].T @ z[i]) ** 2).sum())
    return out


def orthonormal_basis(A: np.ndarray, rtol: float | None = None) -> np.ndarray:
    """Orthonormal basis of ``range(A)`` from the SVD, with the LAPACK default rank tolerance.

    An unpivoted QR cannot estimate rank (``|diag(R)|`` is not a singular-value proxy), and the
    per-link contact dictionaries are frequently rank deficient -- link ``l`` loads only joints
    ``0..l``, and nearby window samples are almost collinear. This is the same criterion
    ``scipy.linalg.orth`` uses, so the principal angles match SciPy exactly.
    """
    A = np.asarray(A, dtype=float)
    U, s, _ = np.linalg.svd(A, full_matrices=False)
    if s.size == 0:
        return U[:, :0]
    tol = (rtol if rtol is not None else max(A.shape) * np.finfo(float).eps) * s[0]
    return U[:, s > tol]


def principal_angles(A: np.ndarray, B: np.ndarray, rtol: float | None = None) -> np.ndarray:
    """Principal angles (radians, ascending) between ``range(A)`` and ``range(B)``.

    Returns ``min(rank(A), rank(B))`` angles; if either subspace is numerically trivial the
    result is a single right angle (maximally distinguishable, which is the conservative
    reading for an unobservable dictionary).
    """
    Qa = orthonormal_basis(A, rtol)
    Qb = orthonormal_basis(B, rtol)
    if Qa.shape[1] == 0 or Qb.shape[1] == 0:
        return np.array([np.pi / 2])
    s = np.linalg.svd(Qa.T @ Qb, compute_uv=False)
    return np.arccos(np.clip(s, -1.0, 1.0))


def subspace_overlap(A: np.ndarray, B: np.ndarray) -> float:
    """Mean squared cosine of the principal angles (1 = identical, 0 = orthogonal)."""
    th = principal_angles(A, B)
    return float((np.cos(th) ** 2).mean())


def fisher_information(D: np.ndarray) -> dict[str, float]:
    """``I = Dbar^T Dbar`` summary for a contact dictionary (whitened units)."""
    D = np.asarray(D, dtype=float)
    I = D.T @ D
    ev = np.linalg.eigvalsh(0.5 * (I + I.T))
    ev = np.maximum(ev, 0.0)
    tol = float(ev.max()) * D.shape[1] * np.finfo(float).eps if ev.size else 0.0
    pos = ev[ev > max(tol, RANK_TOLERANCE * max(float(ev.max()) if ev.size else 0.0, 1e-300))]
    return {
        "fisher_trace": float(ev.sum()),
        "fisher_eigenvalue_max": float(ev.max()) if ev.size else 0.0,
        "fisher_eigenvalue_min_positive": float(pos.min()) if pos.size else 0.0,
        "fisher_rank": int(pos.size),
        "fisher_log_det_positive": float(np.log(pos).sum()) if pos.size else float("-inf"),
    }


def batched_fisher_min_eigenvalue(D: np.ndarray) -> np.ndarray:
    """(N,) smallest eigenvalue of ``Dbar^T Dbar`` for a batch of (N,d,p) dictionaries."""
    G = np.einsum("ndp,ndq->npq", np.asarray(D, dtype=float), np.asarray(D, dtype=float))
    return np.linalg.eigvalsh(0.5 * (G + np.swapaxes(G, 1, 2)))[:, 0]


def ee_null_decomposition(D_ee: np.ndarray, z: np.ndarray) -> dict[str, np.ndarray]:
    """Split ``z`` into the part explainable by a single end-effector wrench and the rest.

    ``P_ee`` projects on ``Im(Jbar_ee^T)``; ``P_null = I - P_ee``. A large
    ``joint_null_energy`` only means "not explainable by one end-effector wrench" -- it is
    **not** evidence of an actuator fault (contract §4.3).
    """
    e = exact_projection_energy(D_ee, z)
    total = (np.asarray(z, dtype=float) ** 2).sum(1)
    return {
        "end_effector_explainable_energy": e,
        "joint_null_energy": np.maximum(total - e, 0.0),
        "end_effector_explainable_fraction": e / np.maximum(total, 1e-12),
    }
