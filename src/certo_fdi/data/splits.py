"""Episode-level plan and S0–S5 splits with automated leakage checks."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np

from certo_fdi.data.fault_injection import sample_fault_spec
from certo_fdi.data.schema import FAULT_FAMILIES, REGIONS, SPEED_BANDS, TOOLS, EpisodeContext, FaultSpec

ID_REGIONS = (0, 1)
OOD_REGION = 2
ID_TOOLS = (0, 1, 2)
OOD_TOOL = 3
ID_SPEEDS = ("slow", "medium")
OOD_SPEED = "fast"
TRAJ_FAMILIES = ("multisine", "minjerk_p2p", "periodic")


@dataclass
class PlannedEpisode:
    episode_id: str
    kind: str  # healthy | fault
    partition: str  # train | val | test | calib
    split: str  # S0..S4 (context split)
    family: str
    context: EpisodeContext
    fault: FaultSpec
    seed: int

    def to_row(self) -> dict[str, Any]:
        row = {
            "episode_id": self.episode_id, "kind": self.kind, "partition": self.partition, "split": self.split,
            "family": self.family, "seed": self.seed,
        }
        row.update({f"ctx_{k}": v for k, v in asdict(self.context).items()})
        row.update({f"fault_{k}": (v if not isinstance(v, (list, dict)) else str(v)) for k, v in asdict(self.fault).items()})
        return row


def _sample_context(rng: np.random.Generator, split: str, controllers: list[str]) -> EpisodeContext:
    if split == "S0":
        region, tool, speed = int(rng.choice(ID_REGIONS)), int(rng.choice(ID_TOOLS)), str(rng.choice(ID_SPEEDS))
    elif split == "S1":
        region, tool, speed = OOD_REGION, int(rng.choice(ID_TOOLS)), str(rng.choice(ID_SPEEDS))
    elif split == "S2":
        region, tool, speed = int(rng.choice(ID_REGIONS)), OOD_TOOL, str(rng.choice(ID_SPEEDS))
    elif split == "S3":
        region, tool, speed = int(rng.choice(ID_REGIONS)), int(rng.choice(ID_TOOLS)), OOD_SPEED
    elif split == "S4":
        region, tool, speed = OOD_REGION, OOD_TOOL, OOD_SPEED
    else:
        raise ValueError(split)
    t = TOOLS[tool]
    return EpisodeContext(
        controller=str(rng.choice(controllers)),
        speed_scale=float(rng.uniform(*SPEED_BANDS[speed])),
        tool_id=tool,
        tool_mass_kg=float(t["mass_kg"]),
        tool_com_z_m=float(t["com"][2]),
        temperature_proxy=float(rng.uniform(-1.0, 1.0)),
        noise_level=float(rng.choice([0.7, 1.0, 1.3])),
        region_id=region,
        trajectory_family=str(rng.choice(TRAJ_FAMILIES)),
        speed_band=speed,
        region_name=REGIONS[region]["name"],
        tool_name=t["name"],
    )


def build_plan(cfg: dict, profile: str, dataset_seed: int) -> list[PlannedEpisode]:
    """Deterministic episode plan for ``profile`` in {smoke, pilot}."""
    rng = np.random.default_rng(dataset_seed)
    p = cfg[profile]
    controllers = list(p["controllers"])
    n_healthy = int(p["healthy_episodes"])
    n_fault = int(p["fault_episodes_per_family"])
    n_calib = int(p["attribution_calibration_episodes_per_family"])
    n = int(cfg["robot"]["dof"])
    T = float(cfg["simulation"]["episode_duration_s"])
    plan: list[PlannedEpisode] = []
    seed_counter = [dataset_seed * 1000]

    def next_seed() -> int:
        seed_counter[0] += 1
        return seed_counter[0]

    # healthy: 2/3 ID, 1/3 OOD (spread over S1..S4)
    n_ood_each = max(1, n_healthy // 12)
    n_id = n_healthy - 4 * n_ood_each
    n_train = int(round(0.625 * n_id))
    n_val = int(round(0.1875 * n_id))
    idx = 0
    for k in range(n_id):
        partition = "train" if k < n_train else ("val" if k < n_train + n_val else "test")
        ctx = _sample_context(rng, "S0", controllers)
        plan.append(PlannedEpisode(f"healthy_{idx:04d}", "healthy", partition, "S0", "healthy", ctx, FaultSpec(), next_seed()))
        idx += 1
    for split in ("S1", "S2", "S3", "S4"):
        for _ in range(n_ood_each):
            ctx = _sample_context(rng, split, controllers)
            plan.append(PlannedEpisode(f"healthy_{idx:04d}", "healthy", "test", split, "healthy", ctx, FaultSpec(), next_seed()))
            idx += 1
    # faults: half ID (S0), rest spread across S1..S4
    for fam in FAULT_FAMILIES[1:]:
        n_id_f = max(1, n_fault // 2)
        splits = ["S0"] * n_id_f
        rest = n_fault - n_id_f
        for i in range(rest):
            splits.append(("S1", "S2", "S3", "S4")[i % 4])
        for k, split in enumerate(splits):
            ctx = _sample_context(rng, split, controllers)
            spec = sample_fault_spec(fam, cfg["faults"], rng, n, T)
            plan.append(PlannedEpisode(f"{fam}_{k:04d}", "fault", "test", split, fam, ctx, spec, next_seed()))
        # attribution calibration partition (ID contexts only; strictly separated from test)
        for k in range(n_calib):
            ctx = _sample_context(rng, "S0", controllers)
            spec = sample_fault_spec(fam, cfg["faults"], rng, n, T)
            plan.append(PlannedEpisode(f"calib_{fam}_{k:04d}", "fault", "calib", "S0", fam, ctx, spec, next_seed()))
    # healthy calibration episodes for the few-shot head (class 'healthy'), ID contexts
    for k in range(n_calib):
        ctx = _sample_context(rng, "S0", controllers)
        plan.append(PlannedEpisode(f"calib_healthy_{k:04d}", "healthy", "calib", "S0", "healthy", ctx, FaultSpec(), next_seed()))
    return plan


def leakage_report(plan: list[PlannedEpisode]) -> dict[str, Any]:
    """Automated leakage tests on the plan (episode-level; windows never cross episodes)."""
    ids = [p.episode_id for p in plan]
    checks: dict[str, bool] = {}
    checks["unique_episode_ids"] = len(ids) == len(set(ids))
    train_val = [p for p in plan if p.partition in ("train", "val")]
    checks["train_val_healthy_only"] = all(p.kind == "healthy" and p.family == "healthy" for p in train_val)
    checks["train_val_in_distribution_only"] = all(p.split == "S0" for p in train_val)
    train_regions = {p.context.region_id for p in train_val}
    train_tools = {p.context.tool_id for p in train_val}
    train_speeds = {p.context.speed_band for p in train_val}
    checks["ood_region_absent_from_train"] = OOD_REGION not in train_regions
    checks["ood_tool_absent_from_train"] = OOD_TOOL not in train_tools
    checks["ood_speed_absent_from_train"] = OOD_SPEED not in train_speeds
    checks["s1_episodes_use_ood_region"] = all(p.context.region_id == OOD_REGION for p in plan if p.split == "S1")
    checks["s2_episodes_use_ood_tool"] = all(p.context.tool_id == OOD_TOOL for p in plan if p.split == "S2")
    checks["s3_episodes_use_ood_speed"] = all(p.context.speed_band == OOD_SPEED for p in plan if p.split == "S3")
    checks["s4_combined_shift"] = all(p.context.region_id == OOD_REGION and p.context.tool_id == OOD_TOOL and p.context.speed_band == OOD_SPEED for p in plan if p.split == "S4")
    calib = {p.episode_id for p in plan if p.partition == "calib"}
    test = {p.episode_id for p in plan if p.partition == "test"}
    checks["calib_disjoint_from_test"] = not (calib & test)
    checks["partitions_disjoint"] = all(sum(1 for q in plan if q.episode_id == pid) == 1 for pid in ids)
    checks["all_faults_in_test_or_calib"] = all(p.partition in ("test", "calib") for p in plan if p.kind == "fault")
    # region overlap check on the actual center ranges
    ida = REGIONS[ID_REGIONS[0]]["q1"]
    idb = REGIONS[ID_REGIONS[1]]["q1"]
    ood = REGIONS[OOD_REGION]["q1"]
    checks["ood_region_q1_disjoint_from_id_regions"] = (ood[0] > max(ida[1], idb[1])) or (ood[1] < min(ida[0], idb[0]))
    return {"checks": checks, "all_pass": all(checks.values()), "n_episodes": len(plan), "n_train": sum(1 for p in plan if p.partition == "train"), "n_val": sum(1 for p in plan if p.partition == "val"), "n_test": sum(1 for p in plan if p.partition == "test"), "n_calib": sum(1 for p in plan if p.partition == "calib")}


def window_index(n_samples: int, window: int, stride: int) -> np.ndarray:
    """Start indices of windows fully inside one episode (never crossing episode boundaries)."""
    if n_samples < window:
        return np.zeros(0, dtype=int)
    return np.arange(0, n_samples - window + 1, stride, dtype=int)
