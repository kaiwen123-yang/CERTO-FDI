from __future__ import annotations

import numpy as np


def local_condition_lower_bound(signature_jacobian: np.ndarray, error: float) -> float:
    singular_values = np.linalg.svd(np.asarray(signature_jacobian, dtype=float), compute_uv=False)
    nominal = float(singular_values[-1]) if singular_values.size else 0.0
    return max(0.0, nominal - float(error))
