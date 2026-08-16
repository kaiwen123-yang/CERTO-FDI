"""Fast nominal-model evaluator (Pinocchio backend when available, NumPy RNEA otherwise).

Used by controllers and by the generator's ``tau_nominal`` column. Both backends implement
the same nominal torque ``RNEA_rigid + armature*qdd + damping*qd + coulomb*tanh(qd/eps)``
and are cross-checked in R0/unit tests.
"""

from __future__ import annotations

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.dynamics.rnea import joint_friction_torque, rnea


class NominalModel:
    def __init__(self, chain: ChainModel, backend: str = "auto"):
        self.chain = chain
        self.n = chain.n_links
        self.backend = "numpy"
        self._pin = None
        if backend in ("auto", "pinocchio"):
            try:
                import pinocchio as pin

                from certo_fdi.dynamics.pinocchio_backend import build_pinocchio_model, pin_rnea_includes_armature

                self._pin = pin
                self._model = build_pinocchio_model(chain)
                self._data = self._model.createData()
                self._includes_armature = pin_rnea_includes_armature(self._model)
                self.backend = "pinocchio"
            except Exception:  # pragma: no cover - fallback
                if backend == "pinocchio":
                    raise
                self._pin = None

    def rigid_torque(self, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> np.ndarray:
        """Rigid-body torque including armature (no friction)."""
        if self._pin is not None:
            tau = np.array(self._pin.rnea(self._model, self._data, np.asarray(q, float), np.asarray(qd, float), np.asarray(qdd, float)), dtype=float)
            if not self._includes_armature:
                tau = tau + self.chain.armature * np.asarray(qdd, float)
            return tau
        return rnea(self.chain, q, qd, qdd, include_joint_terms=False).tau + self.chain.armature * np.asarray(qdd, float)

    def torque(self, q, qd, qdd) -> np.ndarray:
        return self.rigid_torque(q, qd, qdd) + joint_friction_torque(self.chain, np.asarray(qd, float))

    def gravity(self, q) -> np.ndarray:
        z = np.zeros(self.n)
        return self.rigid_torque(q, z, z)

    def friction(self, qd) -> np.ndarray:
        return joint_friction_torque(self.chain, np.asarray(qd, float))
