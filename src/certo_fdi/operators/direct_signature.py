from __future__ import annotations

import numpy as np

from certo_fdi.control.computed_torque import (
    computed_torque_command,
    nominal_command_derivative,
)
from certo_fdi.dynamics.two_link import ee_jacobian, link1_jacobian, payload_torque_per_kg
from certo_fdi.faults.layout import SCALAR_MODES
from certo_fdi.types import ClosedLoopParams


def observer_filter(force_sequence: np.ndarray, params: ClosedLoopParams) -> np.ndarray:
    """Exact ZOH filter for r_dot=-K_o r+K_o d with diagonal K_o."""
    forces = np.asarray(force_sequence, dtype=float)
    phi = np.exp(-np.asarray(params.observer.ko, dtype=float) * params.dt)
    gamma = 1.0 - phi
    residual = np.zeros(2, dtype=float)
    output = []
    for force in forces:
        residual = phi * residual + gamma * force
        output.append(residual.copy())
    return np.asarray(output)


def direct_raw_torque_sequence(
    mode_name: str,
    states: np.ndarray,
    times: np.ndarray,
    params: ClosedLoopParams,
) -> np.ndarray | None:
    """Archived direct trajectory-conditioned signature used only as a comparator.

    It deliberately omits closed-loop state propagation. Encoder bias has no
    meaningful direct generalized-torque signature and returns ``None``.
    """
    if mode_name not in SCALAR_MODES:
        raise KeyError(mode_name)
    result = []
    for x, t in zip(states, times):
        q = np.asarray(x[0:2], dtype=float)
        v = np.asarray(x[2:4], dtype=float)
        tau_cmd = np.asarray(
            computed_torque_command(q, v, float(t), params.plant, params.controller)
        )
        if mode_name == "actuator_gain_j1":
            force = np.array([-tau_cmd[0], 0.0])
        elif mode_name == "actuator_gain_j2":
            force = np.array([0.0, -tau_cmd[1]])
        elif mode_name == "viscous_j1":
            force = np.array([-v[0], 0.0])
        elif mode_name == "viscous_j2":
            force = np.array([0.0, -v[1]])
        elif mode_name == "coulomb_j1":
            force = np.array([-np.tanh(v[0] / params.plant.friction_eps), 0.0])
        elif mode_name == "coulomb_j2":
            force = np.array([0.0, -np.tanh(v[1] / params.plant.friction_eps)])
        elif mode_name.startswith("friction_shape"):
            joint = 0 if mode_name.endswith("j1") else 1
            z = v[joint] / params.plant.friction_eps
            derivative = (
                params.plant.coulomb[joint]
                * v[joint]
                / params.plant.friction_eps**2
                / np.cosh(z) ** 2
            )
            force = np.zeros(2)
            force[joint] = derivative
        elif mode_name == "payload_mass":
            # A positive physical payload appears on the nominal-model RHS as -Y_L dm.
            # Desired acceleration is used for the archived pre-specified-trajectory comparator.
            from certo_fdi.control.computed_torque import reference_trajectory

            _, _, qdd_ref = reference_trajectory(float(t))
            force = -np.asarray(payload_torque_per_kg(q, v, qdd_ref, params.plant))
        elif mode_name == "contact_fx":
            force = np.asarray(ee_jacobian(q, params.plant).T @ np.array([1.0, 0.0]))
        elif mode_name == "contact_fy":
            force = np.asarray(ee_jacobian(q, params.plant).T @ np.array([0.0, 1.0]))
        elif mode_name == "link1_contact_fx":
            force = np.asarray(link1_jacobian(q, params.plant).T @ np.array([1.0, 0.0]))
        elif mode_name == "link1_contact_fy":
            force = np.asarray(link1_jacobian(q, params.plant).T @ np.array([0.0, 1.0]))
        elif mode_name.startswith("encoder_bias"):
            return None
        elif mode_name == "command_delay":
            force = -np.asarray(
                nominal_command_derivative(float(t), params.plant, params.controller)
            )
        else:
            raise KeyError(mode_name)
        result.append(force)
    return np.asarray(result)


def direct_filtered_signature(
    mode_name: str,
    states: np.ndarray,
    times: np.ndarray,
    params: ClosedLoopParams,
) -> np.ndarray | None:
    raw = direct_raw_torque_sequence(mode_name, states, times, params)
    if raw is None:
        return None
    return observer_filter(raw, params).reshape(-1)
