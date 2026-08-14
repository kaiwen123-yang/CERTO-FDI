from __future__ import annotations

import numpy as np

from certo_fdi.operators.linearize import StepLinearization


def assemble_window_operator(
    linearizations: list[StepLinearization],
    column_indices: tuple[int, ...] | list[int],
) -> np.ndarray:
    """Assemble the interval-end block-lower-triangular fault operator.

    Row block ``a`` is residual ``r_{k0+a+1}``; column block ``b`` is the
    fault applied on interval ``[k0+b, k0+b+1]``.
    """

    return _assemble_input_operator(linearizations, column_indices, "e", "d_bar")


def assemble_healthy_window_operator(
    linearizations: list[StepLinearization],
    column_indices: tuple[int, ...] | list[int],
) -> np.ndarray:
    return _assemble_input_operator(linearizations, column_indices, "g", "h_bar")


def _assemble_input_operator(
    linearizations: list[StepLinearization],
    column_indices: tuple[int, ...] | list[int],
    state_field: str,
    output_field: str,
) -> np.ndarray:
    w = len(linearizations)
    if w == 0:
        raise ValueError("window must contain at least one step")
    cols = list(column_indices)
    first_output = getattr(linearizations[0], output_field)
    if first_output is None:
        raise ValueError(f"linearization does not contain {output_field}")
    ny = first_output.shape[0]
    nx = linearizations[0].a.shape[0]
    p = len(cols)
    operator = np.zeros((ny * w, p * w), dtype=float)

    for b in range(w):
        row_b = slice(b * ny, (b + 1) * ny)
        col_b = slice(b * p, (b + 1) * p)
        direct = getattr(linearizations[b], output_field)
        state_input = getattr(linearizations[b], state_field)
        if direct is None or state_input is None:
            raise ValueError(f"linearization lacks {state_field}/{output_field}")
        operator[row_b, col_b] = direct[:, cols]

        state_effect = state_input[:, cols]
        for a in range(b + 1, w):
            row_a = slice(a * ny, (a + 1) * ny)
            operator[row_a, col_b] = linearizations[a].c_bar @ state_effect
            state_effect = linearizations[a].a @ state_effect

    return operator


def constant_profile_matrix(window_length: int, parameter_dim: int) -> np.ndarray:
    return np.kron(np.ones((window_length, 1)), np.eye(parameter_dim))


def constant_profile_operator(stepwise_operator: np.ndarray, parameter_dim: int) -> np.ndarray:
    if stepwise_operator.shape[1] % parameter_dim != 0:
        raise ValueError("stepwise operator width is not divisible by parameter_dim")
    window_length = stepwise_operator.shape[1] // parameter_dim
    return stepwise_operator @ constant_profile_matrix(window_length, parameter_dim)


def numerical_rank(matrix: np.ndarray, rtol: float = 1e-10) -> int:
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    if singular_values.size == 0 or singular_values[0] == 0.0:
        return 0
    return int(np.sum(singular_values > rtol * singular_values[0]))


def spectral_summary(matrix: np.ndarray) -> dict[str, float | int]:
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    if singular_values.size == 0:
        return {
            "rank": 0,
            "sigma_max": 0.0,
            "sigma_min_positive": 0.0,
            "condition_number_positive": float("inf"),
        }
    rank = numerical_rank(matrix)
    positive = singular_values[:rank]
    sigma_max = float(singular_values[0])
    sigma_min_positive = float(positive[-1]) if rank else 0.0
    condition = sigma_max / sigma_min_positive if sigma_min_positive > 0.0 else float("inf")
    return {
        "rank": rank,
        "sigma_max": sigma_max,
        "sigma_min_positive": sigma_min_positive,
        "condition_number_positive": condition,
    }
