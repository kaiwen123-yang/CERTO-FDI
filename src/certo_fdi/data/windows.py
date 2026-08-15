"""In-memory windowed dataset over HDF5 episodes (windows never cross episodes)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import h5py
import numpy as np
import torch

from certo_fdi.data.episode_io import read_attrs
from certo_fdi.data.schema import FAULT_FAMILIES, TOOLS
from certo_fdi.data.splits import window_index
from certo_fdi.dynamics.chain_model import ChainModel

SIGNAL_KEYS = ("q_meas", "qd_meas", "qdd_est", "tau_meas", "tau_nominal", "r_gmo")
# Declared *physical* context given to models and density heads: controller id, speed scale,
# tool mass, tool CoM z, temperature proxy, noise level. Configuration-region and
# trajectory-family ids are deliberately excluded: unseen configurations must be handled by
# the representation, not by extrapolating a categorical id (S1/S4 protocol).
MODEL_CONTEXT_INDICES = (0, 1, 3, 4, 5, 6)
MODEL_CONTEXT_NAMES = ("controller_id", "speed_scale", "tool_mass_kg", "tool_com_z_m", "temperature_proxy", "noise_level")


@dataclass
class EpisodeArrays:
    episode_id: str
    partition: str
    split: str
    family: str
    kind: str
    signals: dict[str, np.ndarray]  # (T,n) float32
    ctx: np.ndarray  # (C,)
    inertia: np.ndarray  # (n,6,6) nominal with declared tool
    tool_id: int
    labels: dict[str, np.ndarray]
    fault: dict[str, Any]
    context: dict[str, Any]

    @property
    def n_samples(self) -> int:
        return int(self.signals["q_meas"].shape[0])


def load_index(data_root: Path) -> list[dict[str, Any]]:
    import csv

    with (Path(data_root) / "episode_index.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nominal_inertia_with_tool(base_chain: ChainModel, tool_id: int) -> np.ndarray:
    tool = TOOLS[int(tool_id)]
    ch = base_chain
    if tool["mass_kg"] > 0:
        ch = base_chain.with_payload(tool["mass_kg"], np.asarray(tool["com"]), np.diag(tool["inertia_diag"]))
    return ch.spatial_inertias()


def load_episode_arrays(row: dict[str, Any], base_chain: ChainModel) -> EpisodeArrays:
    path = row["path"]
    with h5py.File(path, "r") as f:
        sig = {k: f["signals"][k][()].astype(np.float32) for k in SIGNAL_KEYS if k in f["signals"]}
        if "r_gmo" not in sig:
            raise RuntimeError(f"r_gmo missing in {path}; run precompute_gmo first")
        labels = {k: f["labels"][k][()] for k in f["labels"].keys()}
        ctx_vec = np.asarray(f.attrs["context_vector"], dtype=np.float32)
        context = json.loads(str(f.attrs["context_json"]))
        fault = json.loads(str(f.attrs["fault_json"]))
    tool_id = int(context["tool_id"])
    return EpisodeArrays(
        episode_id=row["episode_id"], partition=row["partition"], split=row["split"], family=row["family"], kind=row["kind"],
        signals=sig, ctx=ctx_vec, inertia=nominal_inertia_with_tool(base_chain, tool_id).astype(np.float32), tool_id=tool_id,
        labels=labels, fault=fault, context=context,
    )


class WindowSet:
    """A collection of windows over a list of episodes; yields tensors for the models."""

    def __init__(self, episodes: list[EpisodeArrays], window: int, stride: int, device: str = "cpu"):
        self.episodes = episodes
        self.window = window
        self.stride = stride
        self.device = device
        self.index: list[tuple[int, int]] = []
        for e_i, ep in enumerate(episodes):
            for s in window_index(ep.n_samples, window, stride):
                self.index.append((e_i, int(s)))
        self._stack()

    def _stack(self) -> None:
        # Pre-stack per-episode arrays into torch tensors for fast slicing.
        self._sig = {k: [torch.as_tensor(ep.signals[k]) for ep in self.episodes] for k in SIGNAL_KEYS}
        self._ctx = torch.stack([torch.as_tensor(ep.ctx[list(MODEL_CONTEXT_INDICES)]) for ep in self.episodes])
        self._inertia = torch.stack([torch.as_tensor(ep.inertia) for ep in self.episodes])
        self._active = [torch.as_tensor(ep.labels["fault_active"].astype(np.float32)) for ep in self.episodes]
        self._target = [torch.as_tensor(ep.labels["fault_target"].astype(np.int64)) for ep in self.episodes]
        self._family = torch.as_tensor([FAULT_FAMILIES.index(ep.family) for ep in self.episodes])

    def __len__(self) -> int:
        return len(self.index)

    def batch(self, ids: Iterable[int], device: str | None = None) -> dict[str, torch.Tensor]:
        ids = list(ids)
        dev = device or self.device
        W = self.window
        out: dict[str, Any] = {k: [] for k in ("q", "qd", "qdd", "tau_meas", "tau_nom", "r_gmo", "active", "target")}
        ep_ids, starts = [], []
        for i in ids:
            e, s = self.index[i]
            out["q"].append(self._sig["q_meas"][e][s : s + W])
            out["qd"].append(self._sig["qd_meas"][e][s : s + W])
            out["qdd"].append(self._sig["qdd_est"][e][s : s + W])
            out["tau_meas"].append(self._sig["tau_meas"][e][s : s + W])
            out["tau_nom"].append(self._sig["tau_nominal"][e][s : s + W])
            out["r_gmo"].append(self._sig["r_gmo"][e][s : s + W])
            out["active"].append(self._active[e][s : s + W])
            out["target"].append(self._target[e][s : s + W])
            ep_ids.append(e)
            starts.append(s)
        batch = {k: torch.stack(v).to(dev) for k, v in out.items()}
        e_idx = torch.as_tensor(ep_ids)
        batch["ctx"] = self._ctx[e_idx].to(dev)
        batch["inertia"] = self._inertia[e_idx].to(dev)
        batch["family"] = self._family[e_idx].to(dev)
        batch["episode_index"] = e_idx
        batch["start"] = torch.as_tensor(starts)
        return batch

    def iterate(self, batch_size: int, shuffle: bool, rng: np.random.Generator | None = None, device: str | None = None):
        order = np.arange(len(self))
        if shuffle:
            (rng or np.random.default_rng()).shuffle(order)
        for k in range(0, len(order), batch_size):
            yield self.batch(order[k : k + batch_size].tolist(), device)


def select_episodes(index_rows: list[dict[str, Any]], *, partition: str | None = None, split: str | None = None, kind: str | None = None, family: str | None = None) -> list[dict[str, Any]]:
    rows = index_rows
    if partition is not None:
        rows = [r for r in rows if r["partition"] == partition]
    if split is not None:
        rows = [r for r in rows if r["split"] == split]
    if kind is not None:
        rows = [r for r in rows if r["kind"] == kind]
    if family is not None:
        rows = [r for r in rows if r["family"] == family]
    return rows
