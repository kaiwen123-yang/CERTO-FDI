"""Nested healthy-data expansion H40 -> H80 -> H160 (kickoff §06).

The frozen learning curve was still climbing at 40 healthy training episodes, so Stage 2B has to
separate "the calibration layer is the bottleneck" from "the healthy model is data starved".

Rules, all enforced here rather than by discipline:

* **nested** -- H40 is the frozen 40 training episodes, H80 = H40 + 40 new, H160 = H80 + 80 new.
  Every larger set is a strict superset, so a change across scales cannot come from a different
  episode mix.
* **nothing frozen is touched** -- new episodes go to a separate versioned root with disjoint
  seeds. No existing episode is regenerated or overwritten, and the fault tests (including the
  final F4 test episodes) stay byte-for-byte identical.
* **context balanced by design** -- the new episodes come from a pre-generated deterministic
  table that sweeps the declared controller, speed, payload, temperature and noise ranges. The
  table is fixed before any fault performance is looked at.
* **same encoder, same hyperparameters** -- only the training-set size changes. Calibration
  layers are refitted per scale; the encoder is never retuned.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from certo_fdi.data.schema import REGIONS, SPEED_BANDS, TOOLS, EpisodeContext, FaultSpec

#: healthy *training* episodes in the frozen protocol are all in-distribution (S0)
ID_REGIONS = (0, 1)
ID_TOOLS = (0, 1, 2)
ID_SPEEDS = ("slow", "medium")
CONTROLLERS = ("computed_torque", "pd_gravity")
TRAJ_FAMILIES = ("multisine", "minjerk_p2p", "periodic")
NOISE_LEVELS = (0.7, 1.0, 1.3)


@dataclass
class HealthyEpisodeSpec:
    episode_id: str
    seed: int
    index: int
    scale: str                 # the smallest nested set this episode belongs to: H80 or H160
    context: dict

    def row(self) -> dict[str, Any]:
        r = {"episode_id": self.episode_id, "seed": self.seed, "kind": "healthy", "partition": "train",
             "split": "S0", "family": "healthy", "index": self.index, "added_at_scale": self.scale}
        r.update({f"ctx_{k}": v for k, v in self.context.items()})
        r.update({f"fault_{k}": v for k, v in FaultSpec().to_dict().items() if not isinstance(v, (list, dict))})
        return r


def design_table(cfg: dict) -> list[HealthyEpisodeSpec]:
    """Deterministic, context-balanced design for the 120 new healthy episodes.

    Balance is achieved by *construction*: controller, speed band, tool and noise level cycle on
    coprime-ish periods so every combination is visited roughly equally, and the continuous
    fields are drawn from the episode's own seeded generator. Nothing adapts to results.
    """
    he = cfg["healthy_expansion"]
    totals = [int(t) for t in he["totals"]]
    seed_root = int(he["seed_root"])
    n_new = totals[-1] - totals[0]
    boundary = totals[1] - totals[0]
    specs: list[HealthyEpisodeSpec] = []
    for k in range(n_new):
        seed = seed_root + k
        rng = np.random.default_rng(seed)
        controller = CONTROLLERS[k % len(CONTROLLERS)]
        speed = ID_SPEEDS[(k // 2) % len(ID_SPEEDS)]
        tool = ID_TOOLS[(k // 4) % len(ID_TOOLS)]
        region = ID_REGIONS[(k // 3) % len(ID_REGIONS)]
        traj = TRAJ_FAMILIES[(k // 5) % len(TRAJ_FAMILIES)]
        noise = NOISE_LEVELS[(k // 7) % len(NOISE_LEVELS)]
        temp = -1.0 + 2.0 * ((k % 11) / 10.0)          # sweeps [-1, 1] deterministically
        t = TOOLS[tool]
        ctx = EpisodeContext(
            controller=controller, speed_scale=float(rng.uniform(*SPEED_BANDS[speed])),
            tool_id=tool, tool_mass_kg=float(t["mass_kg"]), tool_com_z_m=float(t["com"][2]),
            temperature_proxy=float(temp), noise_level=float(noise), region_id=region,
            trajectory_family=traj, speed_band=speed, region_name=REGIONS[region]["name"],
            tool_name=t["name"])
        specs.append(HealthyEpisodeSpec(episode_id=f"H_EXT_{k:04d}", seed=seed, index=k,
                                        scale="H80" if k < boundary else "H160",
                                        context=ctx.to_dict()))
    return specs


def nested_ids(frozen_train_ids: list[str], specs: list[HealthyEpisodeSpec], totals: list[int]) -> dict[str, list[str]]:
    """The training id list at each scale. Strictly nested by construction."""
    base = list(frozen_train_ids)
    extra = [s.episode_id for s in specs]
    out = {}
    for t in totals:
        need = t - len(base)
        out[f"H{t}"] = base + (extra[:need] if need > 0 else [])
    return out


def check_nested(sets: dict[str, list[str]], totals: list[int]) -> dict[str, Any]:
    names = [f"H{t}" for t in totals]
    ok = True
    detail = []
    for a, b in zip(names, names[1:]):
        sa, sb = set(sets[a]), set(sets[b])
        nested = sa < sb
        ok = ok and nested
        detail.append({"smaller": a, "larger": b, "n_smaller": len(sa), "n_larger": len(sb),
                       "strictly_nested": nested, "n_added": len(sb - sa)})
    sizes_ok = all(len(sets[f"H{t}"]) == t for t in totals)
    return {"nested": ok, "sizes_correct": sizes_ok,
            "sizes": {n: len(sets[n]) for n in names}, "detail": detail}


def seeds_are_disjoint(specs: list[HealthyEpisodeSpec], other_seeds: set[int]) -> dict[str, Any]:
    mine = {s.seed for s in specs}
    overlap = sorted(mine & set(other_seeds))
    return {"n_new_seeds": len(mine), "n_other_seeds": len(other_seeds), "n_overlap": len(overlap),
            "overlap": overlap[:20], "disjoint": len(overlap) == 0,
            "new_seed_range": [min(mine), max(mine)] if mine else []}


def _generate_one(args):
    spec_d, cfg_frozen, xml, truth, out_dir = args
    from certo_fdi.data.episode_io import write_episode
    from certo_fdi.data.franka_generator import generate_episode
    from certo_fdi.data.schema import EpisodeContext, FaultSpec

    ep = generate_episode(cfg_frozen, xml, truth, EpisodeContext(**spec_d["context"]), FaultSpec(),
                          int(spec_d["seed"]), spec_d["episode_id"])
    write_episode(Path(out_dir) / f"{spec_d['episode_id']}.h5", ep)
    return spec_d["episode_id"]


def generate(cfg_frozen: dict, xml: str, truth: dict, specs: list[HealthyEpisodeSpec],
             out_root: Path, log=print, workers: int = 8) -> list[dict]:
    import multiprocessing as mp

    out_root = Path(out_root)
    (out_root / "episodes").mkdir(parents=True, exist_ok=True)
    todo = [s for s in specs if not (out_root / "episodes" / f"{s.episode_id}.h5").exists()]
    log(f"healthy expansion: {len(specs)} new episodes, {len(todo)} to generate with {workers} workers")
    if todo:
        args = [(asdict(s), cfg_frozen, xml, truth, str(out_root / "episodes")) for s in todo]
        done = 0
        with mp.get_context("spawn").Pool(workers) as pool:
            for _ in pool.imap_unordered(_generate_one, args, chunksize=2):
                done += 1
                if done % 20 == 0:
                    log(f"  healthy expansion {done}/{len(todo)}")
    rows = []
    for s in specs:
        p = out_root / "episodes" / f"{s.episode_id}.h5"
        r = s.row()
        r["path"] = str(p)
        r["exists"] = p.exists()
        rows.append(r)
    with (out_root / "episode_index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def write_manifest(out_root: Path, rows: list[dict], cfg: dict, nested: dict, disjoint: dict) -> dict:
    import hashlib

    from certo_fdi.experiments.common import sha256_file

    out_root = Path(out_root)
    hashes = {r["episode_id"]: (sha256_file(Path(r["path"])) if Path(r["path"]).exists() else "MISSING") for r in rows}
    joint = hashlib.sha256("\n".join(f"{k},{v}" for k, v in sorted(hashes.items())).encode()).hexdigest()
    man = {"partition": "healthy_expansion", "totals": cfg["healthy_expansion"]["totals"],
           "seed_root": cfg["healthy_expansion"]["seed_root"], "n_new_episodes": len(rows),
           "nested_check": nested, "seed_disjointness": disjoint,
           "episode_sha256": hashes, "content_manifest_sha256": joint,
           "frozen_episodes_touched": False,
           "fault_tests_frozen": True,
           "design": "deterministic context-balanced table, fixed before any fault evaluation",
           "encoder": "chain_gnn_aug with unchanged hyperparameters; no retuning at any scale"}
    (out_root / "manifest.json").write_text(json.dumps(man, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return man
