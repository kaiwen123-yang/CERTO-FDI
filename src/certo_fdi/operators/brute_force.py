from __future__ import annotations

import numpy as np

from certo_fdi.operators.linearize import StepLinearization


def brute_force_linear_recursion(
    linearizations: list[StepLinearization],
    input_sequence: np.ndarray,
    *,
    state_field: str = "e",
    output_field: str = "d_bar",
    column_indices: tuple[int, ...] | list[int] | None = None,
) -> np.ndarray:
    """Independent interval-end recursion for operator validation."""

    inputs = np.asarray(input_sequence, dtype=float)
    if inputs.ndim != 2 or inputs.shape[0] != len(linearizations):
        raise ValueError("input_sequence must have one row per interval")
    columns = list(range(inputs.shape[1])) if column_indices is None else list(column_indices)
    nx = linearizations[0].a.shape[0]
    state = np.zeros(nx)
    outputs = []
    for step, value in zip(linearizations, inputs):
        direct = getattr(step, output_field)
        state_input = getattr(step, state_field)
        if direct is None or state_input is None:
            raise ValueError(f"linearization lacks {state_field}/{output_field}")
        outputs.append(step.c_bar @ state + direct[:, columns] @ value)
        state = step.a @ state + state_input[:, columns] @ value
    return np.asarray(outputs)
