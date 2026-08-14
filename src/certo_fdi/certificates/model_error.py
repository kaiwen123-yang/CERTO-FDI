from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EmpiricalModelError:
    grid_max: float
    relative_grid_max: float
    grid_cover_term: float
    hessian_bound: float
    validated_upper_bound: float
    status: str


def empirical_error_summary(
    errors: np.ndarray,
    predicted_norms: np.ndarray,
    *,
    hessian_norm_at_zero: float = float("nan"),
    maximum_severity: float = float("nan"),
) -> EmpiricalModelError:
    errors = np.asarray(errors, dtype=float)
    predicted_norms = np.asarray(predicted_norms, dtype=float)
    relative = errors / np.maximum(predicted_norms, 1e-15)
    hessian_bound = (
        0.5 * hessian_norm_at_zero * maximum_severity**2
        if np.isfinite(hessian_norm_at_zero) and np.isfinite(maximum_severity)
        else float("nan")
    )
    return EmpiricalModelError(
        grid_max=float(np.max(errors)),
        relative_grid_max=float(np.max(relative)),
        grid_cover_term=float("nan"),
        hessian_bound=float(hessian_bound),
        validated_upper_bound=float("nan"),
        status="EMPIRICAL_ONLY",
    )
