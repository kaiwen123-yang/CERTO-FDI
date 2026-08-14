from __future__ import annotations


def detection_lower_bound(
    estimated_distance: float,
    healthy_set_error: float,
    absolute_fault_model_error: float,
) -> float:
    return max(0.0, float(estimated_distance - healthy_set_error - absolute_fault_model_error))


def isolation_lower_bound(
    estimated_distance: float,
    healthy_set_error: float,
    fault_error_j: float,
    fault_error_k: float,
) -> float:
    return max(
        0.0,
        float(estimated_distance - healthy_set_error - fault_error_j - fault_error_k),
    )


def noise_separation_ratio(certified_distance: float, noise_radius: float) -> float:
    if noise_radius <= 0.0:
        raise ValueError("noise_radius must be positive")
    return float(certified_distance / (2.0 * noise_radius))
