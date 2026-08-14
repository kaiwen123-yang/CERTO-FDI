from __future__ import annotations

import numpy as np

from certo_fdi.dynamics.two_link import ee_jacobian
from certo_fdi.experiments.adversarial import (
    covariance_bound_trial,
    figure_eight_response,
    nearest_centroid_error,
    subspace_external_energy,
)


def test_t3_breaks_archived_generic_covariance_bound_more_often() -> None:
    seeds = range(12)
    gaussian = [covariance_bound_trial("gaussian", 20, 400, seed)["violation"] for seed in seeds]
    t3 = [covariance_bound_trial("t3", 20, 400, seed)["violation"] for seed in seeds]
    assert sum(t3) > sum(gaussian)
    assert sum(t3) >= 4


def test_pure_quotient_erases_fault_inside_healthy_span() -> None:
    healthy = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    fault = np.array([0.4, -0.2, 0.0])
    assert subspace_external_energy(fault, healthy) < 1e-14


def test_static_payload_and_contact_have_an_exact_equivalence(params) -> None:
    q = np.array([0.4, -0.7])
    jacobian = np.asarray(ee_jacobian(q, params.plant))
    payload_torque = jacobian.T @ np.array([0.0, params.plant.gravity])
    matching_force = np.linalg.solve(jacobian.T, payload_torque)
    np.testing.assert_allclose(matching_force, [0.0, params.plant.gravity], atol=1e-12)


def test_singular_configuration_has_unobservable_contact_direction(params) -> None:
    jacobian = np.asarray(ee_jacobian(np.array([0.3, 0.0]), params.plant))
    _, _, vh = np.linalg.svd(jacobian.T)
    force_null = vh[-1]
    assert np.linalg.norm(jacobian.T @ force_null) < 1e-12


def test_figure_eight_is_locally_regular_but_globally_self_intersects() -> None:
    h = 1e-6
    local_derivative = (
        figure_eight_response(np.array([h])) - figure_eight_response(np.array([-h]))
    ) / (2.0 * h)
    assert np.linalg.norm(local_derivative) > 1.0
    values = figure_eight_response(np.array([0.0, np.pi]))
    np.testing.assert_allclose(values[0], values[1], atol=1e-12)


def test_positive_geometric_separation_can_still_classify_near_random() -> None:
    error = nearest_centroid_error(separation=0.0169, noise_scale=1.0, trials=40_000, seed=7)
    assert 0.47 < error < 0.51


def test_per_joint_friction_shape_can_leave_average_linear_span() -> None:
    phase = np.linspace(-2.0, 2.0, 100)
    average_columns = np.column_stack([phase, np.tanh(phase / 0.2)])
    per_joint_shape = np.exp(-(phase / 0.35) ** 2) * np.sign(phase)
    assert subspace_external_energy(per_joint_shape, average_columns) > 0.05
