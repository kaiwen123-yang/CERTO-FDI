"""Oracle closed-loop sensitivities through the **frozen truth simulator** (validation only).

A deployed detector cannot resimulate the true plant, so these are never inputs to a Stage 2A
head. They exist to answer one question: *is the deployed dictionary column the right
direction?* Each sensitivity replays a frozen episode from its stored seed with one physical
fault parameter perturbed and differences the resulting residual, so it propagates the full
closed loop -- controller feedback, plant response, acceleration estimator and residual.

The replay is bit-for-bit faithful (Phase 0 checks this to the float32 storage round-trip), so
the difference really is the parameter's effect and not a re-seeding artefact.

Sidedness. Symmetric differences are used wherever the parameter is signed and the frozen
injector accepts both signs (F1 efficiency, F2 friction, F5 encoder bias/velocity). A
**forward** difference is used where a negative value is not representable: the command-delay
hook indexes an integer command buffer (a negative delay would read the wrong tap) and a
negative payload mass is unphysical. That choice is recorded per row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from certo_fdi.data.schema import EpisodeContext, FaultSpec


@dataclass(frozen=True)
class OracleProbe:
    """One perturbable physical parameter of the frozen simulator."""

    key: str
    family: str
    kind: str
    target: int
    delta: float
    symmetric: bool
    units: str
    dictionary_key: str
    dictionary_column: int


def probes_for(n_joints: int, *, encoder_delta: float = 2e-3, gain_delta: float = 0.02,
               viscous_delta: float = 0.2, coulomb_delta: float = 0.2,
               delay_delta: float = 4e-3, payload_delta: float = 0.05) -> list[OracleProbe]:
    """The probe set used by the Phase 4 dictionary-correctness audit."""
    p: list[OracleProbe] = []
    for j in range(n_joints):
        p.append(OracleProbe(f"F1_actuator_j{j}", "F1_actuator", "efficiency", j, gain_delta, True, "efficiency-loss fraction", "F1_actuator", j))
        p.append(OracleProbe(f"F2_viscous_j{j}", "F2_friction", "viscous", j, viscous_delta, True, "relative viscous increment", "F2_viscous", j))
        p.append(OracleProbe(f"F2_coulomb_j{j}", "F2_friction", "coulomb", j, coulomb_delta, True, "relative Coulomb increment", "F2_coulomb", j))
        p.append(OracleProbe(f"F5_encoder_bias_j{j}", "F5_encoder", "bias", j, encoder_delta, True, "rad", "F5_encoder_q", j))
    p.append(OracleProbe("F6_delay", "F6_command", "delay", -1, delay_delta, False, "s", "F6_delay", 0))
    p.append(OracleProbe("F3_payload_mass", "F3_payload", "mass", n_joints - 1, payload_delta, False, "kg", "F3_payload", 0))
    return p


def _spec(probe: OracleProbe, severity: float) -> FaultSpec:
    """A *persistent, from-t=0* version of the probe's fault (no onset ramp, no duration)."""
    return FaultSpec(family=probe.family, kind=probe.kind, target=probe.target, severity=float(severity),
                     onset_s=0.0, duration_s=-1.0, profile="abrupt", ramp_s=0.0)


def _residual(ep) -> np.ndarray:
    """Pre-correction joint residual ``tau_meas - tau_nom`` of a generated episode."""
    return ep.signals["tau_meas"].astype(np.float64) - ep.signals["tau_nominal"].astype(np.float64)


def closed_loop_sensitivity(cfg_frozen: dict, xml: str, truth: dict, context: EpisodeContext,
                            seed: int, episode_id: str, probe: OracleProbe) -> dict[str, Any]:
    """``d (tau_meas - tau_nom) / d theta`` (T, n) through the frozen truth simulator."""
    from certo_fdi.data.franka_generator import generate_episode

    d = float(probe.delta)
    if probe.symmetric:
        plus = generate_episode(cfg_frozen, xml, truth, context, _spec(probe, +d), seed, f"{episode_id}__{probe.key}_p")
        minus = generate_episode(cfg_frozen, xml, truth, context, _spec(probe, -d), seed, f"{episode_id}__{probe.key}_m")
        sens = (_residual(plus) - _residual(minus)) / (2 * d)
        scheme = "symmetric"
    else:
        base = generate_episode(cfg_frozen, xml, truth, context, FaultSpec(), seed, f"{episode_id}__{probe.key}_0")
        plus = generate_episode(cfg_frozen, xml, truth, context, _spec(probe, +d), seed, f"{episode_id}__{probe.key}_p")
        sens = (_residual(plus) - _residual(base)) / d
        scheme = "forward"
    return {"key": probe.key, "family": probe.family, "kind": probe.kind, "target": probe.target,
            "delta": d, "scheme": scheme, "units": probe.units, "sensitivity": sens,
            "dictionary_key": probe.dictionary_key, "dictionary_column": probe.dictionary_column}


def contact_oracle_sensitivity(cfg_frozen: dict, xml: str, truth: dict, context: EpisodeContext,
                               seed: int, episode_id: str, link: int, r_link: np.ndarray,
                               direction: np.ndarray, force_n: float = 2.0) -> dict[str, Any]:
    """``d (tau_meas - tau_nom) / d |f|`` for a constant contact force on ``link`` at ``r_link``."""
    from certo_fdi.data.franka_generator import generate_episode

    dirn = np.asarray(direction, dtype=float)
    dirn = dirn / np.linalg.norm(dirn)
    spec = FaultSpec(family="F4_contact", kind="soft_constant", target=int(link), severity=float(force_n),
                     onset_s=0.0, duration_s=-1.0, profile="abrupt", ramp_s=0.0,
                     direction=dirn.tolist(), extra={"point_link": [float(v) for v in np.asarray(r_link, dtype=float)]})
    base = generate_episode(cfg_frozen, xml, truth, context, FaultSpec(), seed, f"{episode_id}__contact_0")
    plus = generate_episode(cfg_frozen, xml, truth, context, spec, seed, f"{episode_id}__contact_p")
    return {"key": f"F4_contact_link{link}", "family": "F4_contact", "link": int(link), "force_n": float(force_n),
            "direction": dirn.tolist(), "r_link": np.asarray(r_link, dtype=float).tolist(), "scheme": "forward",
            "sensitivity": (_residual(plus) - _residual(base)) / float(force_n), "units": "N m per N"}


# --------------------------------------------------------------------------- comparison
def direction_agreement(oracle: np.ndarray, deployed: np.ndarray, weight: np.ndarray | None = None) -> dict[str, float]:
    """Angle, cosine and norm ratio between an oracle sensitivity and a deployed column.

    Both arrays are ``(T, n)`` (or already flattened); ``weight`` optionally restricts the
    comparison to a subset of samples (e.g. after the settle period).
    """
    a = np.asarray(oracle, dtype=float)
    b = np.asarray(deployed, dtype=float)
    if weight is not None:
        a, b = a[weight], b[weight]
    a, b = a.reshape(-1), b.reshape(-1)
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na < 1e-15 or nb < 1e-15:
        return {"cosine": float("nan"), "angle_deg": float("nan"), "norm_ratio_deployed_over_oracle": float("nan"),
                "relative_error": float("nan"), "oracle_norm": na, "deployed_norm": nb}
    cos = float(np.clip(a @ b / (na * nb), -1.0, 1.0))
    scale = float(a @ b / (nb * nb))  # best least-squares rescale of the deployed column
    return {
        "cosine": cos,
        "angle_deg": float(np.degrees(np.arccos(abs(cos)))),  # sign-agnostic: the two sign conventions differ
        "norm_ratio_deployed_over_oracle": nb / na,
        "relative_error": float(np.linalg.norm(a - scale * b) / na),
        "oracle_norm": na,
        "deployed_norm": nb,
    }
