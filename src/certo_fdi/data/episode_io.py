"""HDF5 episode storage (one file per episode) with JSON attributes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import h5py
import numpy as np


@dataclass
class Episode:
    episode_id: str
    signals: dict[str, np.ndarray]
    labels: dict[str, np.ndarray]
    context: dict[str, Any]
    context_vector: np.ndarray
    fault: dict[str, Any]
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n_samples(self) -> int:
        return int(self.signals["t"].shape[0])


def write_episode(path: str | Path, ep: Episode) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        g = f.create_group("signals")
        for k, v in ep.signals.items():
            g.create_dataset(k, data=np.asarray(v, dtype=np.float32 if k != "t" else np.float64), compression="gzip", compression_opts=4)
        l = f.create_group("labels")
        for k, v in ep.labels.items():
            l.create_dataset(k, data=np.asarray(v), compression="gzip", compression_opts=4)
        f.attrs["episode_id"] = ep.episode_id
        f.attrs["context_json"] = json.dumps(ep.context, default=float)
        f.attrs["context_vector"] = np.asarray(ep.context_vector, dtype=np.float64)
        f.attrs["fault_json"] = json.dumps(ep.fault, default=float)
        f.attrs["meta_json"] = json.dumps(ep.meta, default=_default)
    return str(path)


def _default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return str(o)


def read_episode(path: str | Path, signals: tuple[str, ...] | None = None) -> Episode:
    with h5py.File(path, "r") as f:
        sig = {}
        for k in f["signals"].keys():
            if signals is None or k in signals or k == "t":
                sig[k] = f["signals"][k][()]
        lab = {k: f["labels"][k][()] for k in f["labels"].keys()}
        return Episode(
            episode_id=str(f.attrs["episode_id"]),
            signals=sig,
            labels=lab,
            context=json.loads(str(f.attrs["context_json"])),
            context_vector=np.asarray(f.attrs["context_vector"], dtype=float),
            fault=json.loads(str(f.attrs["fault_json"])),
            meta=json.loads(str(f.attrs["meta_json"])),
        )


def read_attrs(path: str | Path) -> dict[str, Any]:
    with h5py.File(path, "r") as f:
        return {
            "episode_id": str(f.attrs["episode_id"]),
            "context": json.loads(str(f.attrs["context_json"])),
            "context_vector": np.asarray(f.attrs["context_vector"], dtype=float).tolist(),
            "fault": json.loads(str(f.attrs["fault_json"])),
            "meta": json.loads(str(f.attrs["meta_json"])),
            "n_samples": int(f["signals"]["t"].shape[0]),
        }
