"""Episode schema: signals, units, labels, contexts, fault families (machine-readable)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

FAULT_FAMILIES = ("healthy", "F1_actuator", "F2_friction", "F3_payload", "F4_contact", "F5_encoder", "F6_command")
FAULT_FAMILY_ID = {name: i for i, name in enumerate(FAULT_FAMILIES)}

SIGNALS: dict[str, tuple[str, str]] = {
    # name: (unit, description)
    "t": ("s", "log time from episode start"),
    "q_meas": ("rad", "measured joint positions (encoder incl. faults/noise)"),
    "qd_meas": ("rad/s", "measured joint velocities (incl. faults/noise)"),
    "qdd_est": ("rad/s^2", "causal acceleration estimate from qd_meas"),
    "tau_meas": ("N m", "torque signal available to the detector (= commanded/current-based estimate)"),
    "tau_cmd": ("N m", "controller command before command-path faults"),
    "tau_applied": ("N m", "torque actually applied by the truth plant (hidden)"),
    "q_true": ("rad", "truth joint positions (hidden)"),
    "qd_true": ("rad/s", "truth joint velocities (hidden)"),
    "qdd_true": ("rad/s^2", "truth joint accelerations (hidden)"),
    "q_ref": ("rad", "reference trajectory"),
    "tau_nominal": ("N m", "nominal RNEA torque with declared context (measured inputs)"),
    "ext_wrench_link": ("[N m, N]", "truth external wrench per link in link frame [n; f] (hidden)"),
}

LABELS: dict[str, tuple[str, str]] = {
    "fault_active": ("bool", "1 when the injected fault is active at this sample"),
    "fault_family_id": ("int", "index into FAULT_FAMILIES (0 = healthy)"),
    "fault_target": ("int", "0-based joint/link index of the fault (-1 = none/global)"),
    "severity": ("family-specific", "scalar severity (gain loss, scale, kg, N, rad, s)"),
}

CONTEXT_FIELDS: tuple[str, ...] = (
    "controller_id",  # 0 computed_torque, 1 pd_gravity
    "speed_scale",  # dimensionless multiplier on trajectory speed
    "tool_id",  # declared tool identity index
    "tool_mass_kg",
    "tool_com_z_m",
    "temperature_proxy",  # [-1,1] scales truth friction (declared)
    "noise_level",  # multiplier on measurement noise std
    "region_id",  # configuration region index (0 A, 1 B, 2 C)
    "trajectory_family_id",  # 0 multisine, 1 minjerk_p2p, 2 periodic
)


@dataclass
class EpisodeContext:
    controller: str
    speed_scale: float
    tool_id: int
    tool_mass_kg: float
    tool_com_z_m: float
    temperature_proxy: float
    noise_level: float
    region_id: int
    trajectory_family: str
    speed_band: str
    region_name: str
    tool_name: str

    def vector(self) -> list[float]:
        return [
            0.0 if self.controller == "computed_torque" else 1.0,
            float(self.speed_scale),
            float(self.tool_id),
            float(self.tool_mass_kg),
            float(self.tool_com_z_m),
            float(self.temperature_proxy),
            float(self.noise_level),
            float(self.region_id),
            float({"multisine": 0, "minjerk_p2p": 1, "periodic": 2}[self.trajectory_family]),
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FaultSpec:
    family: str = "healthy"
    kind: str = "none"  # sub-type within the family
    target: int = -1  # joint/link index
    severity: float = 0.0
    onset_s: float = 0.0
    duration_s: float = -1.0  # -1 = persistent until end
    profile: str = "abrupt"  # abrupt | ramp | pulse
    ramp_s: float = 2.0
    direction: list[float] = field(default_factory=list)  # for contact force
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def family_id(self) -> int:
        return FAULT_FAMILY_ID[self.family]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TOOLS: dict[int, dict[str, Any]] = {
    0: {"name": "none", "mass_kg": 0.0, "com": [0.0, 0.0, 0.0], "inertia_diag": [0.0, 0.0, 0.0]},
    1: {"name": "tool_A", "mass_kg": 0.30, "com": [0.0, 0.0, 0.08], "inertia_diag": [4e-4, 4e-4, 2e-4]},
    2: {"name": "tool_B", "mass_kg": 0.60, "com": [0.02, 0.0, 0.10], "inertia_diag": [1e-3, 1e-3, 5e-4]},
    3: {"name": "tool_C", "mass_kg": 0.90, "com": [0.0, 0.03, 0.12], "inertia_diag": [2e-3, 2e-3, 8e-4]},  # held out (S2)
}

REGIONS: dict[int, dict[str, Any]] = {
    # centers of motion; joint index -> [lo, hi] for the trajectory center
    0: {"name": "A", "q1": [-2.4, -0.9], "q2": [-1.2, 0.3]},
    1: {"name": "B", "q1": [-0.7, 0.7], "q2": [-1.2, 0.3]},
    2: {"name": "C", "q1": [0.9, 2.4], "q2": [0.4, 1.4]},  # held out (S1)
}
OTHER_JOINT_CENTER_RANGES = {2: [-0.8, 0.8], 3: [-2.5, -0.9], 4: [-0.8, 0.8], 5: [0.9, 2.5], 6: [-1.5, 0.5]}

SPEED_BANDS: dict[str, list[float]] = {"slow": [0.45, 0.65], "medium": [0.75, 1.0], "fast": [1.15, 1.45]}  # fast held out (S3)
