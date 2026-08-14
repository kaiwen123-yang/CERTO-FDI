from __future__ import annotations

from typing import NamedTuple

import jax.numpy as jnp


class TwoLinkParams(NamedTuple):
    gravity: float
    m1: float
    m2: float
    l1: float
    l2: float
    lc1: float
    lc2: float
    I1: float
    I2: float
    viscous: jnp.ndarray
    coulomb: jnp.ndarray
    friction_eps: float


class ControllerParams(NamedTuple):
    kp: jnp.ndarray
    kd: jnp.ndarray


class ObserverParams(NamedTuple):
    ko: jnp.ndarray


class ClosedLoopParams(NamedTuple):
    plant: TwoLinkParams
    controller: ControllerParams
    observer: ObserverParams
    dt: float
