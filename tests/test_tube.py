from __future__ import annotations

import numpy as np

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
