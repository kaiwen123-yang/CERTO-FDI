from __future__ import annotations

from dataclasses import dataclass

import jax.numpy as jnp
import numpy as np


@dataclass(frozen=True)
class FaultSpec:
    name: str
    indices: tuple[int, ...]
    parameter_names: tuple[str, ...]
    provisional: bool = False


ACTUATOR_GAIN = slice(0, 2)
VISCOUS_FRICTION = slice(2, 4)
COULOMB_FRICTION = slice(4, 6)
FRICTION_SHAPE = slice(6, 8)
PAYLOAD_MASS = slice(8, 9)
LINK1_CONTACT_FORCE = slice(9, 11)
CONTACT_FORCE = slice(11, 13)
ENCODER_BIAS = slice(13, 15)
COMMAND_DELAY = slice(15, 16)
FAULT_DIM = 16

FAULT_SPECS: tuple[FaultSpec, ...] = (
    FaultSpec("actuator_gain", (0, 1), ("gamma_j1", "gamma_j2")),
    FaultSpec("viscous_friction", (2, 3), ("delta_bv_j1", "delta_bv_j2")),
    FaultSpec("coulomb_friction", (4, 5), ("delta_bc_j1", "delta_bc_j2")),
    FaultSpec("friction_shape", (6, 7), ("delta_eps_j1", "delta_eps_j2")),
    FaultSpec("payload_mass", (8,), ("delta_payload_mass",)),
    FaultSpec("link1_contact_force", (9, 10), ("link1_fx", "link1_fy")),
    FaultSpec("contact_force", (11, 12), ("ee_contact_fx", "ee_contact_fy")),
    FaultSpec("encoder_bias", (13, 14), ("encoder_bias_j1", "encoder_bias_j2")),
    FaultSpec("command_delay", (15,), ("delay_seconds",), provisional=True),
)

SCALAR_MODES: dict[str, tuple[int, bool]] = {
    "actuator_gain_j1": (0, False),
    "actuator_gain_j2": (1, False),
    "viscous_j1": (2, False),
    "viscous_j2": (3, False),
    "coulomb_j1": (4, False),
    "coulomb_j2": (5, False),
    "friction_shape_j1": (6, False),
    "friction_shape_j2": (7, False),
    "payload_mass": (8, False),
    "link1_contact_fx": (9, False),
    "link1_contact_fy": (10, False),
    "contact_fx": (11, False),
    "contact_fy": (12, False),
    "encoder_bias_j1": (13, False),
    "encoder_bias_j2": (14, False),
    "command_delay": (15, True),
}


def zeros(dtype=jnp.float64) -> jnp.ndarray:
    return jnp.zeros(FAULT_DIM, dtype=dtype)


def scalar_fault(index: int, value: float, dtype=jnp.float64) -> jnp.ndarray:
    return zeros(dtype).at[index].set(value)


def select_columns(matrix: np.ndarray, spec: FaultSpec) -> np.ndarray:
    return np.asarray(matrix)[:, list(spec.indices)]
