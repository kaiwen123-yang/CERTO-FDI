"""The separate ``F4_CAL`` contact-calibration partition (kickoff §04.7).

Stage 2A selected nothing on contact data -- its localizer was pre-registered. Stage 2B *does*
select: one score out of five, and an accept/defer threshold. Doing that on the final F4 test
episodes would invalidate every number that follows, so a **new** contact partition is generated
with disjoint seeds and used for exactly two things:

1. choosing one of the five pre-registered localization scores;
2. calibrating the accept/defer thresholds.

It may never train or tune the healthy encoder, and never move a detection threshold. The final
F4 test episodes stay byte-for-byte untouched -- Phase 0 re-hashes all 590 of them, so any
modification would surface as a content-manifest mismatch and a `BLOCKED`.

Design. 12 episodes per truth link over links (1, 3, 5, 6) = 48 episodes, with contexts laid out
on a deterministic table that mirrors the frozen split structure (S0 plus the four OOD splits)
so the calibration distribution is not narrower than deployment. Everything derives from
``seed_root`` and the link/replicate index, so the partition is reproducible from the manifest
alone and its seeds provably cannot collide with the frozen dataset's.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from certo_fdi.data.schema import REGIONS, SPEED_BANDS, TOOLS, EpisodeContext, FaultSpec

#: split allocation of the 12 replicates per link: mirrors the frozen fault design
#: (half in-distribution, the rest spread over the four OOD splits)
SPLIT_CYCLE = ("S0", "S0", "S0", "S0", "S0", "S0", "S1", "S2", "S3", "S4", "S1", "S2")
CONTROLLERS = ("computed_torque", "pd_gravity")
ID_REGIONS = (0, 1)
OOD_REGION = 2
ID_TOOLS = (0, 1, 2)
OOD_TOOL = 3
ID_SPEEDS = ("slow", "medium")
OOD_SPEED = "fast"
TRAJ_FAMILIES = ("multisine", "minjerk_p2p", "periodic")


@dataclass
class CalEpisodeSpec:
    episode_id: str
    seed: int
    link: int
    replicate: int
    split: str
    context: dict
    fault: dict

    def row(self) -> dict[str, Any]:
        r = {"episode_id": self.episode_id, "seed": self.seed, "kind": "fault", "partition": "F4_CAL",
             "split": self.split, "family": "F4_contact", "truth_link": self.link, "replicate": self.replicate}
        r.update({f"ctx_{k}": v for k, v in self.context.items()})
        r.update({f"fault_{k}": (v if not isinstance(v, (list, dict)) else json.dumps(v)) for k, v in self.fault.items()})
        return r


def _context_for(split: str, rng: np.random.Generator) -> EpisodeContext:
    """Same context law as the frozen protocol, so F4_CAL is not a narrower distribution."""
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
        controller=str(rng.choice(CONTROLLERS)),
        speed_scale=float(rng.uniform(*SPEED_BANDS[speed])),
        tool_id=tool, tool_mass_kg=float(t["mass_kg"]), tool_com_z_m=float(t["com"][2]),
        temperature_proxy=float(rng.uniform(-1.0, 1.0)),
        noise_level=float(rng.choice([0.7, 1.0, 1.3])),
        region_id=region, trajectory_family=str(rng.choice(TRAJ_FAMILIES)),
        speed_band=speed, region_name=REGIONS[region]["name"], tool_name=t["name"],
    )


def _fault_for(link: int, rng: np.random.Generator, contact_force_grid: list[float]) -> FaultSpec:
    """A contact fault on a *forced* truth link, otherwise identical to the frozen F4 law."""
    kind = str(rng.choice(["soft", "soft", "impact"]))
    d = rng.normal(size=3)
    d /= np.linalg.norm(d)
    onset = float(rng.uniform(3.0, 6.0))
    dur = float(rng.uniform(1.5, 4.0)) if kind == "soft" else float(rng.uniform(3.0, 5.0))
    return FaultSpec(family="F4_contact", kind=kind, target=int(link),
                     severity=float(rng.choice(contact_force_grid)), onset_s=onset, duration_s=dur,
                     profile="abrupt", ramp_s=0.0, direction=d.tolist(),
                     extra={"point_link": [0.0, 0.0, float(rng.uniform(0.03, 0.10))], "pulse_s": 0.08})


def design_table(cfg: dict) -> list[CalEpisodeSpec]:
    """The deterministic F4_CAL design. Reproducible from ``seed_root`` alone."""
    cc = cfg["contact_calibration"]
    links = [int(l) for l in cc["truth_links"]]
    per_link = int(cc["episodes_per_truth_link"])
    seed_root = int(cc["seed_root"])
    grid = [float(x) for x in cfg.get("faults", {}).get("contact_force_n", [2.0, 5.0, 10.0])]
    specs: list[CalEpisodeSpec] = []
    for li, link in enumerate(links):
        for k in range(per_link):
            seed = seed_root + 1000 * li + k
            rng = np.random.default_rng(seed)
            split = SPLIT_CYCLE[k % len(SPLIT_CYCLE)]
            ctx = _context_for(split, rng)
            fault = _fault_for(link, rng, grid)
            specs.append(CalEpisodeSpec(episode_id=f"F4CAL_link{link}_{k:03d}", seed=seed, link=link,
                                        replicate=k, split=split, context=ctx.to_dict(), fault=fault.to_dict()))
    return specs


def seeds_are_disjoint(specs: list[CalEpisodeSpec], frozen_seeds: set[int]) -> dict[str, Any]:
    """Hard check: no F4_CAL seed may coincide with a frozen episode seed."""
    cal = {s.seed for s in specs}
    overlap = sorted(cal & set(frozen_seeds))
    return {"n_cal_seeds": len(cal), "n_frozen_seeds": len(frozen_seeds), "n_overlap": len(overlap),
            "overlap": overlap[:20], "disjoint": len(overlap) == 0,
            "cal_seed_range": [min(cal), max(cal)] if cal else [],
            "frozen_seed_range": [min(frozen_seeds), max(frozen_seeds)] if frozen_seeds else []}


def generate_partition(cfg_frozen: dict, xml: str, truth: dict, specs: list[CalEpisodeSpec],
                       out_root: Path, log=print, workers: int = 8) -> list[dict]:
    """Generate the F4_CAL episodes with the frozen generator and write the partition index."""
    import multiprocessing as mp

    out_root = Path(out_root)
    (out_root / "episodes").mkdir(parents=True, exist_ok=True)
    todo = [s for s in specs if not (out_root / "episodes" / f"{s.episode_id}.h5").exists()]
    log(f"F4_CAL: {len(specs)} episodes, {len(todo)} to generate with {workers} workers")
    if todo:
        args = [(asdict(s), cfg_frozen, xml, truth, str(out_root / "episodes")) for s in todo]
        done = 0
        with mp.get_context("spawn").Pool(workers) as pool:
            for _ in pool.imap_unordered(_generate_one, args, chunksize=1):
                done += 1
                if done % 12 == 0:
                    log(f"  F4_CAL {done}/{len(todo)}")
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


def _generate_one(args):
    spec_d, cfg_frozen, xml, truth, out_dir = args
    from certo_fdi.data.episode_io import write_episode
    from certo_fdi.data.franka_generator import generate_episode
    from certo_fdi.data.schema import EpisodeContext, FaultSpec

    ctx = EpisodeContext(**spec_d["context"])
    fault = FaultSpec(**spec_d["fault"])
    ep = generate_episode(cfg_frozen, xml, truth, ctx, fault, int(spec_d["seed"]), spec_d["episode_id"])
    write_episode(Path(out_dir) / f"{spec_d['episode_id']}.h5", ep)
    return spec_d["episode_id"]


def write_manifest(out_root: Path, specs: list[CalEpisodeSpec], rows: list[dict], cfg: dict,
                   disjoint: dict, extra: dict | None = None) -> dict:
    """Manifest + per-episode content hashes, so the partition is auditable and replayable."""
    import hashlib

    from certo_fdi.experiments.common import sha256_file

    out_root = Path(out_root)
    hashes = {}
    for r in rows:
        p = Path(r["path"])
        hashes[r["episode_id"]] = sha256_file(p) if p.exists() else "MISSING"
    joint = hashlib.sha256("\n".join(f"{k},{v}" for k, v in sorted(hashes.items())).encode()).hexdigest()
    man = {
        "partition": "F4_CAL",
        "purpose": ["select one of the five pre-registered localization scores",
                    "calibrate the accept/defer thresholds"],
        "forbidden_uses": ["training or tuning the healthy encoder",
                           "moving any detection threshold",
                           "entering any final F4 test metric"],
        "n_episodes": len(rows),
        "episodes_per_truth_link": int(cfg["contact_calibration"]["episodes_per_truth_link"]),
        "truth_links": [int(l) for l in cfg["contact_calibration"]["truth_links"]],
        "seed_root": int(cfg["contact_calibration"]["seed_root"]),
        "split_cycle": list(SPLIT_CYCLE),
        "seed_disjointness": disjoint,
        "episode_sha256": hashes,
        "content_manifest_sha256": joint,
        "generator": "frozen certo_fdi.data.franka_generator.generate_episode",
        "frozen_truth_parameters": "reused unchanged from the frozen dataset manifest",
        "replayable": "every episode is reproducible from (seed, context, fault spec) in this manifest",
    }
    if extra:
        man.update(extra)
    (out_root / "manifest.json").write_text(json.dumps(man, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return man
