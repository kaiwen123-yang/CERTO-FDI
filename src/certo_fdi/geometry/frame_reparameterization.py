"""Legal per-link frame reparameterization and covariance-residual bookkeeping.

The local gauge group is ``prod_i SE(3)_i``: each link frame may be redefined by an
arbitrary rigid transform. Nothing physical changes — joint trajectories, torques,
faults, and contexts are untouched — only the coordinates in which link-level typed
quantities are expressed. Sampling always produces SE(3) elements (rotation + translation);
arbitrary ``GL(6)`` matrices are never used as frame changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.dynamics.rnea import TypedRNEAState
from certo_fdi.geometry.se3 import SE3, random_se3
from certo_fdi.geometry.spatial_types import SpatialType, transform_typed


def sample_link_frames(
    chain: ChainModel,
    rng: np.random.Generator,
    *,
    rotation_angle_max_deg: float = 180.0,
    translation_fraction_of_link_length: float = 0.25,
    identity_links: tuple[int, ...] = (),
) -> list[SE3]:
    """Sample one legal ``H_i`` per link (pose of old frame in new frame)."""
    frames: list[SE3] = []
    for i in range(chain.n_links):
        if i in identity_links:
            frames.append(SE3.identity())
            continue
        max_t = translation_fraction_of_link_length * float(chain.link_length[i])
        frames.append(
            random_se3(rng, max_angle_rad=np.deg2rad(rotation_angle_max_deg), max_translation=max_t)
        )
    return frames


@dataclass
class CovarianceReport:
    """Per-quantity max-abs residuals between predicted and observed transformed values."""

    residuals: dict[str, float] = field(default_factory=dict)
    scales: dict[str, float] = field(default_factory=dict)

    @property
    def max_residual(self) -> float:
        return max(self.residuals.values()) if self.residuals else 0.0

    def relative(self, name: str) -> float:
        return self.residuals[name] / max(self.scales.get(name, 1.0), 1e-12)


def compare_typed_states(
    chain: ChainModel,
    before: TypedRNEAState,
    after: TypedRNEAState,
    adjoints: np.ndarray,
) -> CovarianceReport:
    """Check that ``after`` equals the exact transformation law applied to ``before``."""
    n = chain.n_links
    report = CovarianceReport()
    for name, kind in TypedRNEAState.TYPES.items():
        b = getattr(before, name)
        a = getattr(after, name)
        worst = 0.0
        scale = float(np.max(np.abs(b))) if np.size(b) else 0.0
        if kind == SpatialType.SCALAR:
            worst = float(np.max(np.abs(a - b)))
        else:
            for i in range(n):
                p = chain.parent[i]
                a_parent = np.eye(6) if p < 0 else adjoints[p]
                pred = transform_typed(kind, b[i], adjoints[i], a_parent)
                worst = max(worst, float(np.max(np.abs(a[i] - pred))))
        report.residuals[name] = worst
        report.scales[name] = scale
    return report
