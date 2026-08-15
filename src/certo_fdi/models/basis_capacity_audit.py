"""Stage 1R-B Phase A: capacity / conditioning audit of the LiGRA-v1 12-column covariant basis.

Three instruments, all gauge-invariant by construction:

* **Gram audit** — ``G_i = B_i^T I_i^{-1} B_i`` (12x12) for the analytic basis of every
  (sample, link); rank, spectrum, condition numbers, nullity, normalized correlations, and
  explicit checks of the algebraic dependencies that the basis carries by construction
  (``F_body = I A + ad*_V I V`` etc.). ``G`` is invariant under legal per-link frame changes.
* **Oracle A** — regularized least-squares torque-correction ceilings on healthy windows for
  the old basis (per-link, per-time coefficients ``alpha`` through the exact chain projection)
  and for a free 6-D local wrench, with fixed Tikhonov + first-difference temporal smoothness
  penalties. The per-window problems are block-tridiagonal in time and are solved exactly
  (batched block-Thomas recursion) together with the effective degrees of freedom
  ``tr(H) = tr(M A^{-1} M^T)`` (diagonal blocks of the inverse via the two-sided Schur
  recursion). Regularization strengths are selected on healthy *validation* windows only, by
  held-out-timestep prediction error; fault data never enters.
* **Oracle B** — projection residual of the analytic truth-vs-nominal inertial mismatch
  wrench ``dF_i = dI_i A_i + ad*_{V_i} dI_i V_i`` onto the basis in the ``I^{-1}`` metric.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch

from certo_fdi.dynamics.rnea_torch import TorchChain, TypedBatch
from certo_fdi.geometry import torch_ops as T
from certo_fdi.models.covariant_basis import ANALYTIC_BASIS_DIM, BASIS_NAMES, covariant_basis

# Algebraic dependencies of the v1 basis (column indices refer to BASIS_NAMES):
#   dep_Fbody:  b4 (F_body) = b0 (I A) + b1 (ad*_V I V)              — every link, every sample
#   dep_accel:  b0 (I A) = b7 (I X A_p) + qdd_i b2 (I S) + qd_i b10 (I ad_V S) — every link
#   dep_leaf:   b5 (F) = b4 (F_body)                                  — leaf links only
#   dep_root:   b6 (I X V_p) = 0 and b7 (I X A_p) = -b11 (I X g)      — root link only
DEPENDENCY_NAMES = ("dep_Fbody_eq_IA_plus_adstarV_IV", "dep_IA_eq_IXAp_plus_qdd_IS_plus_qd_IadVS", "dep_leaf_F_eq_Fbody", "dep_root_IXVp_zero", "dep_root_IXAp_eq_minus_IXg")


def _quad(v: torch.Tensor, m: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
    return (v[..., None, :] @ m @ w[..., :, None])[..., 0, 0]


def invariant_column_scale(tc: TorchChain, tb: TypedBatch) -> torch.Tensor:
    """Per-column gauge-invariant RMS ``sqrt(E[b_k^T I^{-1} b_k])`` pooled over links/samples (12,)."""
    B = covariant_basis(tc, tb)  # (N,n,6,12)
    I_inv = torch.linalg.inv(tb.inertia)  # (N,n,6,6)
    e = torch.einsum("bnik,bnij,bnjk->bnk", B, I_inv, B)  # (N,n,12) b_k^T I^{-1} b_k
    return e.reshape(-1, ANALYTIC_BASIS_DIM).mean(0).clamp_min(1e-30).sqrt()


@dataclass
class GramStats:
    evals: torch.Tensor  # (N,n,12) ascending
    rank: torch.Tensor  # (N,n) int
    nullity: torch.Tensor  # (N,n)
    sigma_min_plus: torch.Tensor  # (N,n) smallest eigenvalue above tolerance
    cond_full: torch.Tensor  # (N,n) lambda_max / lambda_min (all 12)
    cond_plus: torch.Tensor  # (N,n) lambda_max / sigma_min_plus (nonzero spectrum)
    corr: torch.Tensor  # (N,n,12,12) normalized correlations
    dependency_relative_residuals: dict[str, torch.Tensor] = field(default_factory=dict)  # (N,n)
    gram: torch.Tensor | None = None


def gram_audit(tc: TorchChain, tb: TypedBatch, column_scale: torch.Tensor | None = None, *, rank_tol: float = 1e-10, keep_gram: bool = False) -> GramStats:
    """Gauge-invariant Gram audit of the analytic basis on a typed batch (float64 recommended)."""
    B = covariant_basis(tc, tb)
    if column_scale is not None:
        B = B / column_scale.to(B.dtype)
    I_inv = torch.linalg.inv(tb.inertia)
    G = B.transpose(-1, -2) @ I_inv @ B  # (N,n,12,12)
    G = 0.5 * (G + G.transpose(-1, -2))
    evals = torch.linalg.eigvalsh(G)  # ascending
    lam_max = evals[..., -1].clamp_min(1e-300)
    thresh = rank_tol * lam_max
    above = evals > thresh[..., None]
    rank = above.sum(-1)
    big = torch.where(above, evals, torch.full_like(evals, float("inf")))
    sigma_min_plus = big.amin(-1)
    cond_full = lam_max / evals[..., 0].clamp_min(1e-300)
    cond_plus = lam_max / sigma_min_plus
    d = torch.diagonal(G, dim1=-2, dim2=-1).clamp_min(1e-300).sqrt()
    corr = G / (d[..., :, None] * d[..., None, :])
    # explicit dependency residuals in the I^{-1} metric (relative to the left-hand column)
    n = tb.V.shape[1]
    b = lambda k: B[..., k]  # (N,n,6)

    def rel(lhs: torch.Tensor, rhs: torch.Tensor) -> torch.Tensor:
        num = _quad(lhs - rhs, I_inv, lhs - rhs).clamp_min(0).sqrt()
        den = _quad(lhs, I_inv, lhs).clamp_min(0).sqrt()
        return num / den.clamp_min(1e-12)

    if column_scale is None:
        s = torch.ones(ANALYTIC_BASIS_DIM, dtype=B.dtype, device=B.device)
    else:
        s = column_scale.to(B.dtype)
    # scale factors undo the column normalization so that the physical identities hold
    qdd = tb.qdd[..., None]
    qd = tb.qd[..., None]
    deps = {
        DEPENDENCY_NAMES[0]: rel(b(4) * s[4], b(0) * s[0] + b(1) * s[1]),
        DEPENDENCY_NAMES[1]: rel(b(0) * s[0], b(7) * s[7] + qdd * b(2) * s[2] + qd * b(10) * s[10]),
    }
    leaf = torch.tensor([len(tc.children[i]) == 0 for i in range(n)], device=B.device)
    root = torch.tensor([tc.parent[i] < 0 for i in range(n)], device=B.device)
    nan = torch.full(rel(b(5), b(4)).shape, float("nan"), dtype=B.dtype, device=B.device)
    deps[DEPENDENCY_NAMES[2]] = torch.where(leaf[None, :], rel(b(5) * s[5], b(4) * s[4]), nan)
    zero6 = torch.zeros_like(b(6))
    b6_norm = _quad(b(6) * s[6], I_inv, b(6) * s[6]).clamp_min(0).sqrt()
    b7_norm = _quad(b(7) * s[7], I_inv, b(7) * s[7]).clamp_min(0).sqrt()
    deps[DEPENDENCY_NAMES[3]] = torch.where(root[None, :], b6_norm / b7_norm.clamp_min(1e-12), nan)
    deps[DEPENDENCY_NAMES[4]] = torch.where(root[None, :], rel(b(7) * s[7], -b(11) * s[11]), nan)
    return GramStats(evals=evals, rank=rank, nullity=ANALYTIC_BASIS_DIM - rank, sigma_min_plus=sigma_min_plus, cond_full=cond_full, cond_plus=cond_plus, corr=corr, dependency_relative_residuals=deps, gram=G if keep_gram else None)


def stable_nullspace(G: torch.Tensor, rank_tol: float = 1e-10) -> tuple[torch.Tensor, torch.Tensor]:
    """Average null-space projector over the leading batch axis: (P_mean eigenvalues desc, eigenvectors).

    ``G`` (N,12,12). Eigenvalues of the mean projector close to 1 identify null directions that
    are shared by (almost) all samples — i.e. *stable* exact redundancies."""
    evals, evecs = torch.linalg.eigh(G)
    lam_max = evals[..., -1:].clamp_min(1e-300)
    null = (evals <= rank_tol * lam_max).to(G.dtype)  # (N,12)
    P = (evecs * null[..., None, :]) @ evecs.transpose(-1, -2)  # V diag(null) V^T
    Pm = P.mean(0)
    pe, pv = torch.linalg.eigh(Pm)
    return pe.flip(0), pv.flip(1)


# ---------------------------------------------------------------------- chain projection
def chain_projection(tc: TorchChain, X: torch.Tensor, S: torch.Tensor) -> torch.Tensor:
    """P (N, n, n*6): delta_tau_j = sum_i P[j, i-block] w_i for local wrenches w_i in link frames.

    ``P[j, i] = S_j^T X_{i<-j}^T`` for ``i`` in the subtree of ``j`` (exact coadjoint transport of
    the child message through the chain), zero otherwise. ``X`` (N,n,6,6) = X_{i<-p}."""
    N, n = X.shape[0], X.shape[1]
    P = torch.zeros(N, n, n * 6, dtype=X.dtype, device=X.device)
    for i in range(n):
        # transport from link i up to each ancestor j: Xt_{i<-j}^T = X_{j+1<-j}^T ... X_{i<-i-1}^T
        acc = torch.eye(6, dtype=X.dtype, device=X.device).expand(N, 6, 6)
        j = i
        while j >= 0:
            P[:, j, i * 6:(i + 1) * 6] = (S[:, j][:, None, :] @ acc)[:, 0, :]  # S_j^T (X_{i<-j})^T
            p = tc.parent[j]
            if p < 0:
                break
            acc = X[:, j].transpose(-1, -2) @ acc  # X_{i<-p}^T = X_{j<-p}^T X_{i<-j}^T (transport one level up)
            j = p
    return P


def oracle_operators(tc: TorchChain, tb: TypedBatch, column_scale: torch.Tensor, keep_columns: list[int] | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Return (M_basis (N,n,n*K), M_free (N,n,n*6)) mapping coefficients / whitened free wrenches to delta_tau.

    Free wrenches are parameterized as ``w_i = I_i^{1/2} u_i`` so that the Tikhonov penalty
    ``|u|^2 = w^T I^{-1} w`` is gauge-invariant."""
    N, n = tb.V.shape[0], tb.V.shape[1]
    P = chain_projection(tc, tb.X, tb.S)  # (N,n,6n)
    B = covariant_basis(tc, tb) / column_scale.to(tb.V.dtype)  # (N,n,6,12)
    if keep_columns is not None:
        B = B[..., keep_columns]
    K = B.shape[-1]
    # M_basis[:, j, i*K:(i+1)*K] = P[:, j, i-block] @ B[:, i]
    Mb = torch.einsum("bjik,bikl->bjil", P.reshape(N, n, n, 6), B).reshape(N, n, n * K)
    # symmetric square root of the inertia
    ev, evec = torch.linalg.eigh(tb.inertia)
    I_half = (evec * ev.clamp_min(1e-12).sqrt()[..., None, :]) @ evec.transpose(-1, -2)  # (N,n,6,6)
    Mf = torch.einsum("bjik,bikl->bjil", P.reshape(N, n, n, 6), I_half).reshape(N, n, n * 6)
    return Mb, Mf


# ---------------------------------------------------------------------- block-tridiagonal solver
@torch.no_grad()
def solve_regularized(M: torch.Tensor, e: torch.Tensor, lam1: float, lam2: float, *, row_mask: torch.Tensor | None = None, want_edf: bool = True) -> dict[str, torch.Tensor]:
    """Solve  min_x sum_t |e_t - M_t x_t|^2 + lam1 sum_t |x_t|^2 + lam2 sum_t |x_t - x_{t-1}|^2  per window.

    ``M`` (W,T,m,d), ``e`` (W,T,m). ``row_mask`` (W,T) optional 0/1 mask removing whole time
    steps from the data term (held-out-timestep selection). Returns the fitted prediction
    ``M x`` (W,T,m), the coefficients (W,T,d), and the effective degrees of freedom
    ``tr(M A^{-1} M^T)`` per window (W,). Exact block-Thomas recursion; float64 advised.
    """
    W, Tn, m, d = M.shape
    dt, dev = M.dtype, M.device
    if row_mask is None:
        Mm = M
        em = e
    else:
        Mm = M * row_mask[..., None, None].to(dt)
        em = e * row_mask[..., None].to(dt)
    MtM = Mm.transpose(-1, -2) @ Mm  # (W,T,d,d)
    r = (Mm.transpose(-1, -2) @ em[..., None])[..., 0]  # (W,T,d)
    eye = torch.eye(d, dtype=dt, device=dev)
    c = torch.full((Tn,), 2.0, dtype=dt, device=dev)
    c[0] = 1.0
    c[-1] = 1.0
    if Tn == 1:
        c[0] = 0.0
    D = MtM + (lam1 + lam2 * c)[None, :, None, None] * eye  # (W,T,d,d)
    lam2sq = lam2 * lam2
    # forward sweep: F_t = D_t - lam2^2 F_{t-1}^{-1};  y_t = r_t + lam2 F_{t-1}^{-1} y_{t-1}   (E = -lam2 I)
    F_inv = torch.empty_like(D)
    y = torch.empty_like(r)
    Fi = torch.linalg.inv(D[:, 0])
    F_inv[:, 0] = Fi
    y[:, 0] = r[:, 0]
    for t in range(1, Tn):
        Ft = D[:, t] - lam2sq * Fi
        Fi = torch.linalg.inv(Ft)
        F_inv[:, t] = Fi
        y[:, t] = r[:, t] + lam2 * (F_inv[:, t - 1] @ y[:, t - 1][..., None])[..., 0]
    # back substitution: x_t = F_t^{-1} (y_t + lam2 x_{t+1})
    x = torch.empty_like(r)
    x[:, Tn - 1] = (F_inv[:, Tn - 1] @ y[:, Tn - 1][..., None])[..., 0]
    for t in range(Tn - 2, -1, -1):
        x[:, t] = (F_inv[:, t] @ (y[:, t] + lam2 * x[:, t + 1])[..., None])[..., 0]
    out = {"coeffs": x, "pred": (M @ x[..., None])[..., 0]}
    if want_edf:
        # backward Schur recursion G_t = D_t - lam2^2 G_{t+1}^{-1}; (A^{-1})_tt = (F_t + G_t - D_t)^{-1}
        # F_t - D_t = -lam2^2 F_{t-1}^{-1} (t>=1), = 0 (t=0)
        edf = torch.zeros(W, dtype=dt, device=dev)
        Gi = None
        for t in range(Tn - 1, -1, -1):
            Gt = D[:, t] if Gi is None else D[:, t] - lam2sq * Gi
            Ainv_tt = torch.linalg.inv(Gt if t == 0 else Gt - lam2sq * F_inv[:, t - 1])
            edf = edf + torch.einsum("wij,wji->w", Ainv_tt, MtM[:, t])
            Gi = torch.linalg.inv(Gt)
        out["edf"] = edf
    return out


@torch.no_grad()
def solve_min_norm(M: torch.Tensor, e: torch.Tensor) -> dict[str, torch.Tensor]:
    """Zero-regularization limit: per-time-step minimum-norm least squares (upper bound only)."""
    x = (torch.linalg.pinv(M) @ e[..., None])[..., 0]
    rank = torch.linalg.matrix_rank(M)
    return {"coeffs": x, "pred": (M @ x[..., None])[..., 0], "rank": rank}


# ---------------------------------------------------------------------- oracle B
def mismatch_wrench(delta_inertia: torch.Tensor, tb: TypedBatch) -> torch.Tensor:
    """Per-link analytic mismatch local wrench ``dF_i = dI_i A_i + ad*_{V_i} dI_i V_i`` (N,n,6).

    ``delta_inertia`` (n,6,6) = I_truth - I_nominal in the canonical link frames."""
    dI = delta_inertia.to(tb.V.dtype)[None]
    return (dI @ tb.A[..., None])[..., 0] + (T.ad_star(tb.V) @ (dI @ tb.V[..., None]))[..., 0]


def projection_residual(target: torch.Tensor, B: torch.Tensor, I_inv: torch.Tensor, rtol: float = 1e-10) -> tuple[torch.Tensor, torch.Tensor]:
    """min_alpha |target - B alpha|_{I^{-1}} (minimum-norm alpha): returns (relative residual (N,n), alpha (N,n,K))."""
    G = B.transpose(-1, -2) @ I_inv @ B
    G = 0.5 * (G + G.transpose(-1, -2))
    rhs = (B.transpose(-1, -2) @ I_inv @ target[..., None])[..., 0]
    alpha = (torch.linalg.pinv(G, rtol=rtol, hermitian=True) @ rhs[..., None])[..., 0]
    res = target - (B @ alpha[..., None])[..., 0]
    num = _quad(res, I_inv, res).clamp_min(0).sqrt()
    den = _quad(target, I_inv, target).clamp_min(0).sqrt()
    return num / den.clamp_min(1e-15), alpha


__all__ = ["ANALYTIC_BASIS_DIM", "BASIS_NAMES", "DEPENDENCY_NAMES", "GramStats", "gram_audit", "stable_nullspace", "invariant_column_scale", "chain_projection", "oracle_operators", "solve_regularized", "solve_min_norm", "mismatch_wrench", "projection_residual"]
