"""7-DoF episode generator: MuJoCo truth plant + nominal-model controllers + faults.

Documented truth-vs-nominal mismatch (configs/stage1r_pilot.yaml::plant_mismatch):
inertial parameters perturbed once per dataset (one physical robot), truth friction has a
Stribeck term absent from the nominal model, truth viscous/Coulomb differ from nominal by
a dataset-fixed factor and a per-episode declared temperature proxy, measurements are
noisy, and the acceleration is a causal estimate.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from certo_fdi.data.controllers import make_controller
from certo_fdi.data.episode_io import Episode
from certo_fdi.data.fault_injection import FaultInjector
from certo_fdi.data.schema import CONTEXT_FIELDS, FAULT_FAMILY_ID, TOOLS, EpisodeContext, FaultSpec
from certo_fdi.data.trajectories import make_trajectory
from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.dynamics.mujoco_backend import MujocoPlant, PlantParams, chain_from_mujoco
from certo_fdi.dynamics.nominal_model import NominalModel
from certo_fdi.geometry.se3 import quat_to_rot


class CausalDerivative:
    """Causal Savitzky–Golay first derivative (quadratic fit over the last ``window`` samples)."""

    def __init__(self, n: int, dt: float, window: int = 21):
        self.n = n
        self.dt = dt
        self.window = window
        self.buf = np.zeros((window, n))
        self.count = 0
        k = np.arange(window) - (window - 1)  # ..., -1, 0  (0 = newest)
        a = np.stack([np.ones_like(k), k, k**2], 1).astype(float)
        # derivative at newest point of the LS quadratic fit: d/dk (c0 + c1 k + c2 k^2) at k=0 = c1
        pinv = np.linalg.pinv(a)
        self.w = pinv[1] / dt

    def update(self, x: np.ndarray) -> np.ndarray:
        self.buf = np.roll(self.buf, -1, axis=0)
        self.buf[-1] = x
        self.count += 1
        if self.count < self.window:
            self.buf[: self.window - self.count] = x
        return self.w @ self.buf


def make_truth_params(cfg: dict, n: int, dataset_rng: np.random.Generator) -> dict[str, Any]:
    pm = cfg["plant_mismatch"]
    nominal_v = np.asarray(pm["nominal_viscous_nms"], dtype=float)[:n]
    nominal_c = np.asarray(pm["nominal_coulomb_nm"], dtype=float)[:n]
    v_scale = dataset_rng.uniform(*pm["truth_viscous_scale_range"], size=n)
    c_scale = dataset_rng.uniform(*pm["truth_coulomb_scale_range"], size=n)
    rel = float(pm["inertial_param_relative_perturbation"])
    return {
        "nominal_viscous": nominal_v.tolist(),
        "nominal_coulomb": nominal_c.tolist(),
        "truth_viscous": (nominal_v * v_scale).tolist(),
        "truth_coulomb": (nominal_c * c_scale).tolist(),
        "truth_stribeck": np.asarray(pm["truth_stribeck_nm"], dtype=float)[:n].tolist(),
        "truth_stribeck_velocity": float(pm["truth_stribeck_velocity"]),
        "inertial_mass_scale": dataset_rng.uniform(1 - rel, 1 + rel, size=n).tolist(),
        "inertial_inertia_scale": dataset_rng.uniform(1 - rel, 1 + rel, size=n).tolist(),
        "inertial_com_shift_m": (dataset_rng.uniform(-rel, rel, size=(n, 3)) * 0.05).tolist(),
        "temperature_friction_gain": 0.15,
    }


def apply_truth_inertials(plant: MujocoPlant, truth: dict[str, Any]) -> None:
    for k, b in enumerate(plant.link_body_ids):
        plant.model.body_mass[b] *= truth["inertial_mass_scale"][k]
        plant.model.body_inertia[b] *= truth["inertial_inertia_scale"][k]
        plant.model.body_ipos[b] += np.asarray(truth["inertial_com_shift_m"][k])
    plant.recompute_constants()
    plant.chain = chain_from_mujoco(plant.model)


_REFERENCE_CHAIN: dict[str, ChainModel] = {}


def reference_chain(xml_path: str | Path) -> ChainModel:
    """Datasheet (unperturbed) chain extracted once from the frozen MJCF."""
    key = str(xml_path)
    if key not in _REFERENCE_CHAIN:
        _REFERENCE_CHAIN[key] = MujocoPlant(xml_path).chain
    return _REFERENCE_CHAIN[key].copy()


def nominal_chain_with_tool(base_chain: ChainModel, tool_id: int, nominal_v: np.ndarray, nominal_c: np.ndarray) -> ChainModel:
    ch = base_chain.copy()
    ch.damping = np.asarray(nominal_v, dtype=float)
    ch.coulomb = np.asarray(nominal_c, dtype=float)
    ch.coulomb_eps = 0.05
    tool = TOOLS[tool_id]
    if tool["mass_kg"] > 0:
        ch = ch.with_payload(tool["mass_kg"], np.asarray(tool["com"]), np.diag(tool["inertia_diag"]))
    return ch


def generate_episode(
    cfg: dict,
    xml_path: str | Path,
    truth: dict[str, Any],
    context: EpisodeContext,
    fault: FaultSpec,
    seed: int,
    episode_id: str,
    *,
    duration_s: float | None = None,
) -> Episode:
    rng = np.random.default_rng(seed)
    sim = cfg["simulation"]
    dt_p = float(sim["physics_dt_s"])
    dt_c = float(sim["control_dt_s"])
    substeps = int(round(dt_c / dt_p))
    T = float(duration_s or sim["episode_duration_s"])
    steps = int(round(T / dt_c))
    plant = MujocoPlant(xml_path, timestep=dt_p)
    apply_truth_inertials(plant, truth)
    n = plant.n
    tool = TOOLS[context.tool_id]
    if tool["mass_kg"] > 0:
        plant.payload_variant(tool["mass_kg"], np.asarray(tool["com"]), np.diag(tool["inertia_diag"]))
    # The *nominal* chain uses the datasheet (unperturbed) parameters plus the declared tool.
    nominal = nominal_chain_with_tool(reference_chain(xml_path), context.tool_id, truth["nominal_viscous"], truth["nominal_coulomb"])
    controller = make_controller(context.controller, nominal)
    temp_gain = 1.0 + truth["temperature_friction_gain"] * context.temperature_proxy
    truth_params = PlantParams(
        viscous=np.asarray(truth["truth_viscous"]) * temp_gain,
        coulomb=np.asarray(truth["truth_coulomb"]) * temp_gain,
        stribeck=np.asarray(truth["truth_stribeck"]) * temp_gain,
        stribeck_velocity=float(truth["truth_stribeck_velocity"]),
    )
    noise = cfg["plant_mismatch"]["measurement_noise"]
    noise_std = (float(noise["q_std_rad"]) * context.noise_level, float(noise["qd_std_rad_s"]) * context.noise_level)
    tau_noise = float(noise["tau_std_nm"]) * context.noise_level

    t_grid = np.arange(steps) * dt_c
    traj = make_trajectory(context.trajectory_family, t_grid, context.region_id, rng, context.speed_scale, nominal.joint_lower, nominal.joint_upper, nominal.velocity_limit)
    injector = FaultInjector(fault, n, dt_c, rng)
    deriv = CausalDerivative(n, dt_c, window=int(cfg["plant_mismatch"].get("acceleration_window_samples", 21)))
    torque_limit = nominal.torque_limit

    plant.reset(traj.q[0], np.zeros(n))
    sig = {k: np.zeros((steps, n)) for k in ("q_meas", "qd_meas", "qdd_est", "tau_meas", "tau_cmd", "tau_applied", "q_true", "qd_true", "qdd_true", "q_ref", "tau_nominal")}
    sig["t"] = t_grid.copy()
    sig["ext_wrench_link"] = np.zeros((steps, n, 6))
    lab = {"fault_active": np.zeros(steps, dtype=np.int8), "fault_family_id": np.zeros(steps, dtype=np.int8), "fault_target": np.full(steps, -1, dtype=np.int8), "severity": np.zeros(steps, dtype=np.float32)}
    tau_prev_cmd = np.zeros(n)
    tau_prev_applied = np.zeros(n)
    for k in range(steps):
        t = float(t_grid[k])
        q_true, qd_true = plant.q, plant.qd
        q_meas, qd_meas = injector.sensor(t, q_true, qd_true, noise_std)
        qdd_est = deriv.update(qd_meas)
        tau_cmd = controller(q_meas, qd_meas, traj.q[k], traj.qd[k], traj.qdd[k])
        tau_cmd = np.clip(tau_cmd, -torque_limit, torque_limit)
        tau_path = injector.command_path(t, tau_cmd)
        tau_applied = injector.actuator_gain(t) * tau_path
        payload = injector.payload_event(t)
        if payload is not None:
            plant.payload_variant(payload["mass"], payload["com"], payload["inertia_com"])
        v_s, c_s, s_s = injector.friction_scales(t)
        wrench = injector.external_wrench_world(t, plant.link_pose_world)
        # log (torque columns hold the command active over the interval ending at t_k)
        sig["q_meas"][k] = q_meas
        sig["qd_meas"][k] = qd_meas
        sig["qdd_est"][k] = qdd_est
        sig["tau_meas"][k] = tau_prev_cmd + rng.normal(scale=tau_noise, size=n)
        sig["tau_cmd"][k] = tau_prev_cmd
        sig["tau_applied"][k] = tau_prev_applied
        sig["q_true"][k] = q_true
        sig["qd_true"][k] = qd_true
        sig["qdd_true"][k] = plant.qdd
        sig["q_ref"][k] = traj.q[k]
        if wrench:
            for i, w in wrench.items():
                pose = plant.link_pose_world(i)
                f_link = pose.R.T @ w[:3]
                n_link = pose.R.T @ w[3:]
                sig["ext_wrench_link"][k, i] = np.concatenate([n_link, f_link])
        act = injector.active(t)
        lab["fault_active"][k] = int(act)
        lab["fault_family_id"][k] = FAULT_FAMILY_ID[fault.family] if act else 0
        lab["fault_target"][k] = fault.target if act else -1
        lab["severity"][k] = fault.severity if act else 0.0
        # physics substeps
        for _ in range(substeps):
            qd_now = plant.qd
            sgn = np.tanh(qd_now / truth_params.coulomb_eps)
            fric = truth_params.viscous * v_s * qd_now + truth_params.coulomb * c_s * sgn + truth_params.stribeck * s_s * np.exp(-((qd_now / truth_params.stribeck_velocity) ** 2)) * sgn
            plant.step(tau_applied - fric, link_wrench_world=wrench)
        tau_prev_cmd = tau_cmd
        tau_prev_applied = tau_applied
        if not np.all(np.isfinite(plant.q)) or np.max(np.abs(plant.qd)) > 20.0:
            raise RuntimeError(f"simulation diverged at t={t:.3f}s in {episode_id}")
    # nominal torque with measured inputs (declared context)
    nominal_model = NominalModel(nominal)
    for k in range(steps):
        sig["tau_nominal"][k] = nominal_model.torque(sig["q_meas"][k], sig["qd_meas"][k], sig["qdd_est"][k])
    tracking_rms = float(np.sqrt(np.mean((sig["q_true"] - sig["q_ref"]) ** 2)))
    return Episode(
        episode_id=episode_id,
        signals=sig,
        labels=lab,
        context=context.to_dict(),
        context_vector=np.asarray(context.vector()),
        fault=fault.to_dict(),
        meta={
            "seed": seed,
            "duration_s": T,
            "control_dt_s": dt_c,
            "physics_dt_s": dt_p,
            "trajectory_meta": traj.meta,
            "tracking_rms_rad": tracking_rms,
            "truth_temperature_gain": temp_gain,
            "context_fields": list(CONTEXT_FIELDS),
            "nominal_tool_id": context.tool_id,
        },
    )
