"""Shared plumbing for the Stage 2A phase runners: run layout, logging, data bundle, rows."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from certo_fdi.experiments.common import capture_environment, load_config, sha256_file, utc_now, write_csv, write_json
from certo_fdi.paths import RunLayout, create_or_resume_run, git_sha

# every Stage 2A result CSV carries these columns (contract §9)
REQUIRED_COLUMNS = (
    "run_id", "git_sha", "config_sha", "dataset_manifest_sha", "controller", "split", "seed",
    "model", "fault_family", "status", "provisional", "strict", "empirical",
)

COARSE_CLASS_OF_FAMILY = {
    "F1_actuator": "internal_actuation_friction",
    "F2_friction": "internal_actuation_friction",
    "F3_payload": "load_inertia",
    "F4_contact": "external_contact",
    "F5_encoder": "sensor",
    "F6_command": "command_timing",
}


def common_parser(desc: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--config", required=True)
    ap.add_argument("--storage-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--device", default=None)
    return ap


class Stage:
    """Run context: config, layout, provenance, logging, lazily loaded data bundle."""

    def __init__(self, args, phase: str):
        import torch

        self.args = args
        self.cfg, self.cfg_sha = load_config(args.config)
        self.repo_root = Path(args.repo_root).resolve()
        self.layout: RunLayout = create_or_resume_run(args.storage_root, args.run_id, stage=self.cfg["stage"])
        self.phase = phase
        self.lines: list[str] = []
        (self.layout.sub("config") / Path(args.config).name).write_bytes(Path(args.config).read_bytes())
        capture_environment(self.layout, self.repo_root, f"stage2a_{phase}_start", {"config_sha256": self.cfg_sha})
        fi = self.cfg["frozen_inputs"]
        self.data_root = Path(args.data_root or self.cfg["paths"]["data_root"]) / f"{fi['dataset_profile']}_seed{fi['dataset_seed']}"
        self.device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
        freeze = self.layout.results / "stage2a_input_freeze.json"
        self.freeze = json.loads(freeze.read_text()) if freeze.exists() else {}
        self.manifest_sha = self.freeze.get("episode_manifest_sha256", "")
        self._bundle = None
        self.log(f"phase {phase} start (git {git_sha(self.repo_root)[:8]}, config {self.cfg_sha[:8]}, device {self.device})")

    # ------------------------------------------------------------------ logging
    def log(self, msg: str) -> None:
        line = f"[{utc_now()}] {msg}"
        print(line, flush=True)
        self.lines.append(line)
        (self.layout.sub("logs") / f"stage2a_{self.phase}.log").write_text("\n".join(self.lines) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ gates
    def require_freeze(self) -> bool:
        ok = self.freeze.get("gate") == "PASS" and bool(self.manifest_sha)
        if not ok:
            self.log("BLOCKED: the Phase 0 input freeze has not passed in this run")
        return ok

    # ------------------------------------------------------------------ data
    @property
    def bundle(self):
        from certo_fdi.experiments.pipeline import load_bundle

        if self._bundle is None:
            t0 = time.time()
            self._bundle = load_bundle(self.cfg, self.data_root)
            b = self._bundle
            self.log(f"data bundle loaded: train={len(b.train_ids)} val={len(b.val_ids)} test={len(b.test_ids)} calib={len(b.calib_ids)} ({time.time() - t0:.0f}s)")
        return self._bundle

    # ------------------------------------------------------------------ rows
    def base_row(self, **kw) -> dict[str, Any]:
        row = {
            "run_id": self.layout.run_id,
            "git_sha": git_sha(self.repo_root),
            "config_sha": self.cfg_sha,
            "dataset_manifest_sha": self.manifest_sha,
            "controller": "ALL",
            "split": "",
            "seed": "",
            "model": "",
            "fault_family": "",
            "status": "OK",
            "provisional": False,
            "strict": False,
            "empirical": True,
        }
        row.update(kw)
        return row

    def write_table(self, name: str, rows: list[dict], *, units: str = "", schema: dict | None = None) -> Path:
        """Write ``<results>/<name>.csv`` and its schema sidecar, checking the required columns."""
        path = self.layout.results / name
        if rows:
            missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
            if missing:
                raise ValueError(f"{name} is missing required columns: {missing}")
        write_csv(path, rows)
        meta = {"table": name, "n_rows": len(rows), "required_columns": list(REQUIRED_COLUMNS), "units": units, "columns": schema or {}, "written_utc": utc_now()}
        write_json(self.layout.results / (name.replace(".csv", "") + ".schema.json"), meta)
        self.log(f"wrote {name} ({len(rows)} rows)")
        return path

    def finish(self, extra: dict | None = None) -> None:
        capture_environment(self.layout, self.repo_root, f"stage2a_{self.phase}_end", extra or {})


# ---------------------------------------------------------------------- helpers
def model_cfg(cfg: dict) -> dict:
    m = cfg["models"]
    return {
        "scalar_hidden_dim": int(m.get("scalar_hidden_dim", 64)),
        "scalar_layers": int(m.get("scalar_layers", 2)),
        "baseline_gru_hidden": int(m.get("baseline_gru_hidden", 80)),
    }


def ensure_model_cfg(cfg: dict) -> dict:
    if "model" not in cfg:
        cfg = dict(cfg)
        cfg["model"] = model_cfg(cfg)
    return cfg


def train_cfg(cfg: dict) -> dict:
    t = cfg["training"]
    return {
        "epochs": int(t.get("epochs", 40)),
        "min_epochs": int(t.get("min_epochs", 15)),
        "patience": int(t.get("patience", 10)),
        "batch_size": int(t.get("batch_size", 64)),
        "weight_decay": float(t.get("weight_decay", 1e-6)),
        "grad_clip": float(t.get("grad_clip", 1.0)),
    }


def episode_seed_map(data_root: Path) -> dict[str, int]:
    """episode_id -> generator seed (needed to replay an episode deterministically)."""
    import csv

    with (Path(data_root) / "episode_index.csv").open(newline="", encoding="utf-8") as f:
        return {r["episode_id"]: int(r["seed"]) for r in csv.DictReader(f)}


def truth_parameters(data_root: Path) -> dict:
    """The dataset-level hidden truth parameters (oracle replay only, never a deployed input)."""
    return json.loads((Path(data_root) / "dataset_manifest.json").read_text())["truth_parameters_hidden_from_models"]


def bootstrap_ci(values: np.ndarray, statistic, n_resamples: int, alpha: float, seed: int = 20260816) -> tuple[float, float, float]:
    """Percentile bootstrap CI of ``statistic(values)`` over the first axis."""
    values = np.asarray(values)
    rng = np.random.default_rng(seed)
    n = values.shape[0]
    point = float(statistic(values))
    if n < 3:
        return point, float("nan"), float("nan")
    draws = np.empty(n_resamples)
    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        draws[b] = statistic(values[idx])
    lo, hi = np.nanpercentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    from scipy.stats import rankdata

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return float("nan")
    rx, ry = rankdata(x[m]), rankdata(y[m])
    if rx.std() < 1e-12 or ry.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])
