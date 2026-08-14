from __future__ import annotations

import numpy as np

from certo_fdi.operators.linearize import StepLinearization
from certo_fdi.operators.window import (
    assemble_healthy_window_operator,
    constant_profile_operator,
)


HEALTHY_PARAMETER_NAMES = ("viscous_j1", "viscous_j2", "payload_mass")


def build_physical_healthy_basis(
    linearizations: list[StepLinearization],
    parameter_names: list[str] | tuple[str, ...] = HEALTHY_PARAMETER_NAMES,
) -> np.ndarray:
    indices = [HEALTHY_PARAMETER_NAMES.index(name) for name in parameter_names]
    stepwise = assemble_healthy_window_operator(linearizations, indices)
    return constant_profile_operator(stepwise, len(indices))
