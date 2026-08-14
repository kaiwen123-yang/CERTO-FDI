from __future__ import annotations

from pathlib import Path
from typing import Any

import jax.numpy as jnp
import yaml

from certo_fdi.types import ClosedLoopParams, ControllerParams, ObserverParams, TwoLinkParams


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("configuration root must be a mapping")
    return data


def build_closed_loop_params(config: dict[str, Any]) -> ClosedLoopParams:
    p = config["plant"]
    c = config["controller"]
    o = config["observer"]
    plant = TwoLinkParams(
        gravity=float(p["gravity"]),
        m1=float(p["m1"]),
        m2=float(p["m2"]),
        l1=float(p["l1"]),
        l2=float(p["l2"]),
        lc1=float(p["lc1"]),
        lc2=float(p["lc2"]),
        I1=float(p["I1"]),
        I2=float(p["I2"]),
        viscous=jnp.asarray(p["viscous"], dtype=jnp.float64),
        coulomb=jnp.asarray(p["coulomb"], dtype=jnp.float64),
        friction_eps=float(p["friction_eps"]),
    )
    controller = ControllerParams(
        kp=jnp.asarray(c["kp"], dtype=jnp.float64),
        kd=jnp.asarray(c["kd"], dtype=jnp.float64),
    )
    observer = ObserverParams(ko=jnp.asarray(o["ko"], dtype=jnp.float64))
    return ClosedLoopParams(
        plant=plant,
        controller=controller,
        observer=observer,
        dt=float(config["dt"]),
    )
