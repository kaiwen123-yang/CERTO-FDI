from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from certo_fdi.certificates.set_distance import detection_distance


@dataclass(frozen=True)
class ScalarFaultDistanceResult:
    distance: float
    fault_parameter: float
    healthy_difference: np.ndarray
    residual_vector: np.ndarray
    solver_status: int
    solver_message: str


def scalar_fault_to_healthy_difference_distance(
    fault_signature: np.ndarray,
    fault_interval: tuple[float, float],
    healthy_basis: np.ndarray,
    healthy_half_widths: np.ndarray,
) -> ScalarFaultDistanceResult:
    """Compute dist(s*K+, G*(Z-Z)) by one joint bounded least-squares solve.

    The healthy set is ``G Z`` with symmetric half-widths ``b``. The difference
    set is therefore ``G [-2b, 2b]``. The optimization is joint across every
    healthy direction; no one-dimensional approximation is used.
    """

    s = np.asarray(fault_signature, dtype=float).reshape(-1, 1)
    g = np.asarray(healthy_basis, dtype=float)
    b = np.asarray(healthy_half_widths, dtype=float).reshape(-1)
    if g.shape[0] != s.shape[0]:
        raise ValueError("fault signature and healthy basis must share output dimension")
    if g.shape[1] != b.size:
        raise ValueError("healthy basis width and half-width vector differ")
    a_min, a_max = map(float, fault_interval)
    if not (0.0 <= a_min <= a_max):
        raise ValueError("fault interval must satisfy 0 <= min <= max")

    checked = detection_distance(s, a_min, a_max, g, b)
    solution = checked.scipy
    vector = solution.residual
    return ScalarFaultDistanceResult(
        distance=float(np.linalg.norm(vector)),
        fault_parameter=float(solution.parameters[0]),
        healthy_difference=np.asarray(solution.parameters[1:]),
        residual_vector=np.asarray(vector),
        solver_status=1,
        solver_message=(
            f"{solution.status}; cross_solver_diff={checked.absolute_solver_difference:.3e}"
        ),
    )
