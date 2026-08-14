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
PAYLOAD_MASS = slice(4, 5)
CONTACT_FORCE = slice(5, 7)
ENCODER_BIAS = slice(7, 9)
COMMAND_DELAY = slice(9, 10)
FAULT_DIM = 10

FAULT_SPECS: tuple[FaultSpec, ...] = (
    FaultSpec("actuator_gain", (0, 1), ("gamma_j1", "gamma_j2")),
    FaultSpec("viscous_friction", (2, 3), ("delta_bv_j1", "delta_bv_j2")),
    FaultSpec("payload_mass", (4,), ("delta_payload_mass",)),
    FaultSpec("contact_force", (5, 6), ("contact_fx", "contact_fy")),
    FaultSpec("encoder_bias", (7, 8), ("encoder_bias_j1", "encoder_bias_j2")),
    FaultSpec("command_delay", (9,), ("small_delay",), provisional=True),
)

SCALAR_MODES: dict[str, tuple[int, bool]] = {
    "actuator_gain_j1": (0, False),
    "actuator_gain_j2": (1, False),
    "viscous_j1": (2, False),
    "viscous_j2": (3, False),
    "payload_mass": (4, False),
    "contact_fx": (5, False),
    "contact_fy": (6, False),
    "encoder_bias_j1": (7, False),
    "encoder_bias_j2": (8, False),
    "command_delay": (9, True),
}


def zeros(dtype=jnp.float64) -> jnp.ndarray:
    return jnp.zeros(FAULT_DIM, dtype=dtype)


def scalar_fault(index: int, value: float, dtype=jnp.float64) -> jnp.ndarray:
    return zeros(dtype).at[index].set(value)


def select_columns(matrix: np.ndarray, spec: FaultSpec) -> np.ndarray:
    return np.asarray(matrix)[:, list(spec.indices)]
