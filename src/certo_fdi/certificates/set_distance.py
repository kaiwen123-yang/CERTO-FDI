from __future__ import annotations

from dataclasses import dataclass

import cvxpy as cp
import numpy as np
from scipy.optimize import lsq_linear
import warnings


@dataclass(frozen=True)
class SolverResult:
    distance: float
    parameters: np.ndarray
    residual: np.ndarray
    status: str
    solver: str


@dataclass(frozen=True)
class CrossCheckedDistance:
    distance: float
    scipy: SolverResult
    osqp: SolverResult
    absolute_solver_difference: float


def _validate_bounds(lower: np.ndarray, upper: np.ndarray) -> None:
    if lower.shape != upper.shape or np.any(lower > upper):
        raise ValueError("invalid optimization bounds")


def _scipy_distance(design: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> SolverResult:
    solution = lsq_linear(
        design,
        np.zeros(design.shape[0]),
        bounds=(lower, upper),
        tol=1e-12,
        lsmr_tol=1e-12,
        max_iter=500,
    )
    residual = design @ solution.x
    return SolverResult(
        distance=float(np.linalg.norm(residual)),
        parameters=np.asarray(solution.x),
        residual=np.asarray(residual),
        status=str(solution.message),
        solver="scipy_lsq_linear",
    )


def _osqp_distance(design: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> SolverResult:
    center = 0.5 * (lower + upper)
    half_range = 0.5 * (upper - lower)
    if np.any(half_range <= 0.0):
        raise ValueError("strictly positive variable ranges are required")
    normalized = cp.Variable(design.shape[1])
    variable = center + cp.multiply(half_range, normalized)
    problem = cp.Problem(
        cp.Minimize(cp.sum_squares(design @ variable)),
        [normalized >= -1.0, normalized <= 1.0],
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        problem.solve(
            solver=cp.OSQP,
            eps_abs=1e-10,
            eps_rel=1e-10,
            max_iter=100_000,
            polishing=True,
            verbose=False,
        )
    solver_name = "cvxpy_osqp"
    if normalized.value is None or problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
        problem.solve(
            solver=cp.CLARABEL,
            tol_gap_abs=1e-10,
            tol_feas=1e-10,
            max_iter=10_000,
            verbose=False,
        )
        solver_name = "cvxpy_clarabel_fallback"
    if normalized.value is None or problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
        raise RuntimeError(f"CVXPY distance solve failed: {problem.status}")
    parameters = center + half_range * np.asarray(normalized.value).reshape(-1)
    residual = design @ parameters
    return SolverResult(
        distance=float(np.linalg.norm(residual)),
        parameters=parameters,
        residual=np.asarray(residual),
        status=str(problem.status),
        solver=solver_name,
    )


def _cross_checked(
    design: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    agreement_tolerance: float,
) -> CrossCheckedDistance:
    design = np.asarray(design, dtype=float)
    lower = np.asarray(lower, dtype=float).reshape(-1)
    upper = np.asarray(upper, dtype=float).reshape(-1)
    _validate_bounds(lower, upper)
    scipy_result = _scipy_distance(design, lower, upper)
    osqp_result = _osqp_distance(design, lower, upper)
    difference = abs(scipy_result.distance - osqp_result.distance)
    scale = max(1.0, scipy_result.distance, osqp_result.distance)
    if difference > agreement_tolerance * scale:
        raise RuntimeError(
            f"independent QP solvers disagree: scipy={scipy_result.distance}, "
            f"osqp={osqp_result.distance}"
        )
    return CrossCheckedDistance(
        # The smaller independently reproduced value is conservative for a
        # downstream separation lower bound.
        distance=min(scipy_result.distance, osqp_result.distance),
        scipy=scipy_result,
        osqp=osqp_result,
        absolute_solver_difference=difference,
    )


def detection_distance(
    fault_signature: np.ndarray,
    fault_lower: np.ndarray | float,
    fault_upper: np.ndarray | float,
    healthy_basis: np.ndarray,
    healthy_half_widths: np.ndarray,
    agreement_tolerance: float = 1e-6,
) -> CrossCheckedDistance:
    signature = np.asarray(fault_signature, dtype=float)
    if signature.ndim == 1:
        signature = signature[:, None]
    healthy = np.asarray(healthy_basis, dtype=float)
    widths = np.asarray(healthy_half_widths, dtype=float).reshape(-1)
    lower_fault = np.broadcast_to(np.asarray(fault_lower, dtype=float), (signature.shape[1],))
    upper_fault = np.broadcast_to(np.asarray(fault_upper, dtype=float), (signature.shape[1],))
    design = np.column_stack([signature, healthy])
    lower = np.concatenate([lower_fault, -2.0 * widths])
    upper = np.concatenate([upper_fault, 2.0 * widths])
    return _cross_checked(design, lower, upper, agreement_tolerance)


def isolation_distance(
    signature_j: np.ndarray,
    lower_j: np.ndarray | float,
    upper_j: np.ndarray | float,
    signature_k: np.ndarray,
    lower_k: np.ndarray | float,
    upper_k: np.ndarray | float,
    healthy_basis: np.ndarray,
    healthy_half_widths: np.ndarray,
    agreement_tolerance: float = 1e-6,
) -> CrossCheckedDistance:
    sj = np.asarray(signature_j, dtype=float)
    sk = np.asarray(signature_k, dtype=float)
    if sj.ndim == 1:
        sj = sj[:, None]
    if sk.ndim == 1:
        sk = sk[:, None]
    healthy = np.asarray(healthy_basis, dtype=float)
    widths = np.asarray(healthy_half_widths, dtype=float).reshape(-1)
    low_j = np.broadcast_to(np.asarray(lower_j, dtype=float), (sj.shape[1],))
    high_j = np.broadcast_to(np.asarray(upper_j, dtype=float), (sj.shape[1],))
    low_k = np.broadcast_to(np.asarray(lower_k, dtype=float), (sk.shape[1],))
    high_k = np.broadcast_to(np.asarray(upper_k, dtype=float), (sk.shape[1],))
    design = np.column_stack([sj, -sk, healthy])
    lower = np.concatenate([low_j, low_k, -2.0 * widths])
    upper = np.concatenate([high_j, high_k, 2.0 * widths])
    return _cross_checked(design, lower, upper, agreement_tolerance)
