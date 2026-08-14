from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HealthyBox:
    parameter_names: tuple[str, ...]
    half_widths: np.ndarray
    provenance: str

    def __post_init__(self) -> None:
        widths = np.asarray(self.half_widths, dtype=float)
        if widths.shape != (len(self.parameter_names),):
            raise ValueError("one healthy half-width is required per parameter")
        if np.any(widths < 0.0):
            raise ValueError("healthy half-widths must be nonnegative")
        object.__setattr__(self, "half_widths", widths)

    @property
    def difference_lower(self) -> np.ndarray:
        return -2.0 * self.half_widths

    @property
    def difference_upper(self) -> np.ndarray:
        return 2.0 * self.half_widths
