from __future__ import annotations

import numpy as np

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
