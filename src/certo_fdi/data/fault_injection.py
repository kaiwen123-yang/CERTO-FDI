"""Fault families F1–F6 (04_7DOF_DATA_AND_FAULT_PROTOCOL.md §6) as simulator hooks.

Every fault acts on the *physics*, the *command path* or the *sensing path* of the truth
plant. None of them touches the coordinate laws: a faulty episode is still described by
typed quantities that transform exactly like healthy ones (verified in R0).
"""

from __future__ import annotations

from collections import deque

import numpy as np

from certo_fdi.data.schema import FaultSpec


def _profile(spec: FaultSpec, t: float) -> float:
    """Activation in [0,1] at time ``t``."""
    if t < spec.onset_s:
        return 0.0
    if spec.duration_s > 0 and t > spec.onset_s + spec.duration_s:
        return 0.0
    if spec.profile == "ramp":
        return float(min(1.0, (t - spec.onset_s) / max(spec.ramp_s, 1e-6)))
    return 1.0


class FaultInjector:
    """Stateful hooks used by the generator loop for one episode."""

    def __init__(self, spec: FaultSpec, n: int, control_dt: float, rng: np.random.Generator):
        self.spec = spec
        self.n = n
        self.dt = control_dt
        self.rng = rng
        self._cmd_history: deque[np.ndarray] = deque(maxlen=64)
        self._meas_history: deque[tuple[np.ndarray, np.ndarray]] = deque(maxlen=16)
        self._hold_until = -1.0
        self._held_cmd: np.ndarray | None = None
        self._stuck_until = -1.0
        self._stuck_value: tuple[np.ndarray, np.ndarray] | None = None
        self._next_pulse = spec.onset_s
        self.payload_applied = False

    # ------------------------------------------------------------ status
    def activation(self, t: float) -> float:
        if self.spec.family == "healthy":
            return 0.0
        return _profile(self.spec, t)

    def active(self, t: float) -> bool:
        return self.activation(t) > 0.0

    # ------------------------------------------------------------ F1 actuator efficiency
    def actuator_gain(self, t: float) -> np.ndarray:
        g = np.ones(self.n)
        if self.spec.family == "F1_actuator":
            g[self.spec.target] = 1.0 - self.spec.severity * self.activation(t)
        return g

    # ------------------------------------------------------------ F2 friction
    def friction_scales(self, t: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Multipliers on truth (viscous, coulomb, stribeck) per joint."""
        v = np.ones(self.n)
        c = np.ones(self.n)
        s = np.ones(self.n)
        if self.spec.family == "F2_friction":
            a = self.activation(t)
            j = self.spec.target
            if self.spec.kind == "viscous":
                v[j] = 1.0 + self.spec.severity * a
            elif self.spec.kind == "coulomb":
                c[j] = 1.0 + self.spec.severity * a
            elif self.spec.kind == "stribeck":
                s[j] = 1.0 + 3.0 * self.spec.severity * a
        return v, c, s

    # ------------------------------------------------------------ F3 payload
    def payload_event(self, t: float) -> dict | None:
        """Return payload parameters to attach (once) at onset; None otherwise."""
        if self.spec.family != "F3_payload" or self.payload_applied or t < self.spec.onset_s:
            return None
        self.payload_applied = True
        if self.spec.kind == "mass":
            return {"mass": self.spec.severity, "com": np.array([0.0, 0.0, 0.11]), "inertia_com": np.diag([5e-4, 5e-4, 2e-4]) * self.spec.severity}
        if self.spec.kind == "com_shift":
            # unannounced CoM shift: model as adding a small mass far off-axis
            return {"mass": 0.15, "com": np.array([self.spec.severity, 0.0, 0.10]), "inertia_com": np.zeros((3, 3))}
        if self.spec.kind == "inertia":
            return {"mass": 0.05, "com": np.array([0.0, 0.0, 0.05]), "inertia_com": np.diag([1.0, 1.0, 0.5]) * self.spec.severity * 1e-2}
        return None

    # ------------------------------------------------------------ F4 external contact
    def external_wrench_world(self, t: float, link_pose_world) -> dict[int, np.ndarray]:
        """World-frame ``[force; torque]`` at the link body origin (MuJoCo xfrc order)."""
        if self.spec.family != "F4_contact":
            return {}
        a = self.activation(t)
        if self.spec.kind == "impact":
            # short pulses repeated every 1.5-2.5 s while active
            if t >= self._next_pulse and self.active(t):
                self._pulse_end = t + self.spec.extra.get("pulse_s", 0.08)
                self._next_pulse = t + self.rng.uniform(1.5, 2.5)
            a = 1.0 if (self.active(t) and t < getattr(self, "_pulse_end", -1.0)) else 0.0
            if a == 0.0:
                return {}
        elif a == 0.0:
            return {}
        i = self.spec.target
        pose = link_pose_world(i)
        direction = np.asarray(self.spec.direction, dtype=float)
        direction = direction / np.linalg.norm(direction)
        force_world = self.spec.severity * a * direction * (3.0 if self.spec.kind == "impact" else 1.0)
        # slow drift of the persistent force magnitude (soft contact)
        if self.spec.kind == "soft":
            force_world = force_world * (1.0 + 0.2 * np.sin(2 * np.pi * 0.3 * (t - self.spec.onset_s)))
        r_link = np.asarray(self.spec.extra.get("point_link", [0.0, 0.0, 0.05]), dtype=float)
        r_world = pose.R @ r_link
        torque_world = np.cross(r_world, force_world)
        return {i: np.concatenate([force_world, torque_world])}

    # ------------------------------------------------------------ F5 encoder / sensing
    def sensor(self, t: float, q_true: np.ndarray, qd_true: np.ndarray, noise_std: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
        q = q_true.copy()
        qd = qd_true.copy()
        self._meas_history.append((q_true.copy(), qd_true.copy()))
        if self.spec.family == "F5_encoder":
            a = self.activation(t)
            j = self.spec.target
            if self.spec.kind == "bias":
                q[j] += self.spec.severity * a
            elif self.spec.kind == "drift":
                if a > 0:
                    q[j] += self.spec.severity * (t - self.spec.onset_s) / max(self.spec.duration_s if self.spec.duration_s > 0 else 6.0, 1e-3)
            elif self.spec.kind == "stuck":
                if a > 0:
                    if t >= self._stuck_until and self.rng.uniform() < 0.25 * self.dt / 0.002:
                        self._stuck_until = t + self.rng.uniform(0.02, 0.10)
                        self._stuck_value = (q_true.copy(), qd_true.copy())
                    if t < self._stuck_until and self._stuck_value is not None:
                        q[j] = self._stuck_value[0][j]
                        qd[j] = 0.0
            elif self.spec.kind == "timestamp":
                if a > 0:
                    k = int(round(self.spec.severity / self.dt))
                    if len(self._meas_history) > k:
                        old = self._meas_history[-1 - k]
                        q[j] = old[0][j]
                        qd[j] = old[1][j]
            elif self.spec.kind == "velocity":
                if a > 0:
                    qd[j] += self.rng.normal(scale=8.0 * noise_std[1]) + self.spec.severity
        # measurement noise
        q += self.rng.normal(scale=noise_std[0], size=self.n)
        qd += self.rng.normal(scale=noise_std[1], size=self.n)
        return q, qd

    # ------------------------------------------------------------ F6 command / communication
    def command_path(self, t: float, tau_cmd: np.ndarray) -> np.ndarray:
        self._cmd_history.append(tau_cmd.copy())
        if self.spec.family != "F6_command" or not self.active(t):
            return tau_cmd
        if self.spec.kind == "delay":
            k = int(round(self.spec.severity / self.dt))
            if len(self._cmd_history) > k:
                return self._cmd_history[-1 - k].copy()
            return self._cmd_history[0].copy()
        if self.spec.kind == "scale":
            return tau_cmd * (1.0 + self.spec.severity)
        if self.spec.kind == "hold":
            if t >= self._hold_until and self.rng.uniform() < 0.3 * self.dt / 0.002:
                self._hold_until = t + self.rng.uniform(0.004, self.spec.severity)
                self._held_cmd = tau_cmd.copy()
            if t < self._hold_until and self._held_cmd is not None:
                return self._held_cmd.copy()
            return tau_cmd
        return tau_cmd


def sample_fault_spec(family: str, cfg_faults: dict, rng: np.random.Generator, n: int, episode_s: float) -> FaultSpec:
    """Sample one fault specification for ``family`` from the pilot severity grids."""
    onset = float(rng.uniform(3.0, 6.0))
    if family == "healthy":
        return FaultSpec()
    if family == "F1_actuator":
        return FaultSpec(family, "efficiency", int(rng.integers(0, n)), float(rng.choice(cfg_faults["actuator_efficiency"])), onset, -1.0, str(rng.choice(["abrupt", "ramp"])), 2.0)
    if family == "F2_friction":
        kind = str(rng.choice(["viscous", "coulomb", "stribeck"]))
        grid = cfg_faults["viscous_scale"] if kind == "viscous" else cfg_faults["coulomb_scale"]
        return FaultSpec(family, kind, int(rng.integers(0, n)), float(rng.choice(grid)), onset, -1.0, str(rng.choice(["abrupt", "ramp"])), 2.0)
    if family == "F3_payload":
        kind = str(rng.choice(["mass", "mass", "com_shift", "inertia"]))
        if kind == "mass":
            sev = float(rng.choice(cfg_faults["payload_mass_kg"]))
        elif kind == "com_shift":
            sev = float(rng.choice([0.03, 0.05, 0.08]))
        else:
            sev = float(rng.choice([0.5, 1.0, 2.0]))
        return FaultSpec(family, kind, n - 1, sev, onset, -1.0, "abrupt")
    if family == "F4_contact":
        kind = str(rng.choice(["soft", "soft", "impact"]))
        link = int(rng.choice(cfg_faults["contact_links"]))
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        dur = float(rng.uniform(1.5, 4.0)) if kind == "soft" else float(rng.uniform(3.0, 5.0))
        return FaultSpec(family, kind, link, float(rng.choice(cfg_faults["contact_force_n"])), onset, dur, "abrupt", 0.0, d.tolist(), {"point_link": [0.0, 0.0, float(rng.uniform(0.03, 0.10))], "pulse_s": 0.08})
    if family == "F5_encoder":
        kind = str(rng.choice(["bias", "drift", "stuck", "timestamp", "velocity"]))
        j = int(rng.integers(0, n))
        if kind == "bias":
            return FaultSpec(family, kind, j, float(rng.choice(cfg_faults["encoder_bias_rad"])), onset, -1.0, "abrupt")
        if kind == "drift":
            return FaultSpec(family, kind, j, float(rng.choice([0.01, 0.02])), onset, 6.0, "abrupt")
        if kind == "stuck":
            return FaultSpec(family, kind, j, 0.05, onset, -1.0, "abrupt")
        if kind == "timestamp":
            return FaultSpec(family, kind, j, float(rng.choice([0.002, 0.004])), onset, -1.0, "abrupt")
        return FaultSpec(family, kind, j, float(rng.choice([0.02, 0.05])), onset, -1.0, "abrupt")
    if family == "F6_command":
        kind = str(rng.choice(["delay", "delay", "scale", "hold"]))
        if kind == "delay":
            return FaultSpec(family, kind, -1, float(rng.choice(cfg_faults["command_delay_s"])), onset, -1.0, "abrupt")
        if kind == "scale":
            return FaultSpec(family, kind, -1, float(rng.choice([-0.15, 0.15, 0.25])), onset, -1.0, "abrupt")
        return FaultSpec(family, kind, -1, float(rng.choice([0.012, 0.02])), onset, -1.0, "abrupt")
    raise ValueError(family)
