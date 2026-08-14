from __future__ import annotations

import numpy as np

from certo_fdi.certificates import set_distance
from certo_fdi.certificates.set_distance import detection_distance, isolation_distance
from certo_fdi.sets.tube import scalar_fault_to_healthy_difference_distance


def test_joint_multidirection_tube_solver():
    s = np.array([1.0, 0.0, 0.0])
    g = np.array([[0.8, 0.2], [0.0, 1.0], [0.0, 0.0]])
    result = scalar_fault_to_healthy_difference_distance(
        fault_signature=s,
        fault_interval=(0.5, 0.8),
        healthy_basis=g,
        healthy_half_widths=np.array([0.2, 0.2]),
    )
    # Joint healthy directions can cancel more than either direction alone.
    assert result.distance >= 0.0
    assert 0.5 <= result.fault_parameter <= 0.8
    assert np.all(np.abs(result.healthy_difference) <= 0.4 + 1e-10)


def test_joint_qp_is_cross_checked_by_scipy_and_osqp():
    signature = np.array([1.0, 0.0])
    healthy = np.array([[0.8, 0.8], [0.6, -0.6]])
    widths = np.array([0.2, 0.2])
    joint = detection_distance(signature, 0.8, 1.0, healthy, widths)
    single_1 = detection_distance(signature, 0.8, 1.0, healthy[:, [0]], widths[[0]])
    single_2 = detection_distance(signature, 0.8, 1.0, healthy[:, [1]], widths[[1]])
    assert joint.absolute_solver_difference < 1e-7
    assert joint.distance < 0.5 * min(single_1.distance, single_2.distance)


def test_isolation_distance_uses_joint_difference_set():
    sj = np.array([1.0, 0.0, 0.0])
    sk = np.array([0.0, 1.0, 0.0])
    healthy = np.array([[0.1], [0.1], [1.0]])
    result = isolation_distance(sj, 0.5, 0.8, sk, 0.5, 0.8, healthy, np.array([0.1]))
    assert result.distance > 0.5
    assert result.absolute_solver_difference < 1e-7


def test_near_zero_solver_differences_use_explicit_absolute_tolerance():
    signature = np.array([1e-6, 0.0])
    healthy = np.array([[1e-6], [1e-6]])
    result = detection_distance(signature, 0.2, 0.4, healthy, np.array([0.1]))
    assert result.absolute_solver_difference <= 1e-6
    assert result.distance == min(result.scipy.distance, result.osqp.distance)


def test_badly_scaled_joint_qp_is_normalized_before_secondary_solve():
    signature = np.array([1e6, 1e-6, 1.0])
    healthy = np.array([[1e6, -1e6], [2e-6, 1e-6], [0.5, -0.25]])
    result = detection_distance(
        signature,
        1e-3,
        2e-3,
        healthy,
        np.array([1e-3, 1e-3]),
        agreement_tolerance=1e-5,
    )
    assert np.isfinite(result.distance)
    assert result.osqp.solver in {
        "cvxpy_osqp",
        "cvxpy_clarabel_fallback",
        "cvxpy_clarabel_after_osqp_disagreement",
    }


def test_clarabel_arbitrates_osqp_disagreement(monkeypatch):
    def disagreeing_osqp(design, lower, upper):
        reference = set_distance._scipy_distance(design, lower, upper)
        return set_distance.SolverResult(
            distance=reference.distance + 1e-3,
            parameters=reference.parameters,
            residual=reference.residual,
            status="synthetic_disagreement",
            solver="synthetic_osqp",
        )

    def agreeing_clarabel(design, lower, upper):
        reference = set_distance._scipy_distance(design, lower, upper)
        return set_distance.SolverResult(
            distance=reference.distance,
            parameters=reference.parameters,
            residual=reference.residual,
            status="synthetic_agreement",
            solver="cvxpy_clarabel_after_osqp_disagreement",
        )

    monkeypatch.setattr(set_distance, "_osqp_distance", disagreeing_osqp)
    monkeypatch.setattr(set_distance, "_clarabel_distance", agreeing_clarabel)
    result = detection_distance(
        np.array([1.0, 0.0]),
        0.8,
        1.0,
        np.array([[0.8, 0.8], [0.6, -0.6]]),
        np.array([0.2, 0.2]),
    )
    assert result.osqp.solver == "cvxpy_clarabel_after_osqp_disagreement"
    assert result.absolute_solver_difference == 0.0
