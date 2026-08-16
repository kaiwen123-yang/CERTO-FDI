"""Shared plumbing for the Stage 2B phase runners.

The one rule that differs from Stage 2A and is enforced here: **the episode is the independent
statistical unit**. :func:`episode_cluster_bootstrap` resamples whole episodes; there is no
window-level IID bootstrap anywhere in Stage 2B (kickoff §07.1 makes using one an integrity
failure, i.e. `BLOCKED`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from certo_fdi.experiments.common import capture_environment, load_config, utc_now, write_csv, write_json
from certo_fdi.paths import RunLayout, create_or_resume_run, git_sha

# every Stage 2B result CSV carries these columns
REQUIRED_COLUMNS = (
    "run_id", "git_sha", "config_sha", "dataset_manifest_sha", "partition", "split", "seed",
    "method", "fault_family", "status", "provisional", "strict", "empirical",
)

# partitions Stage 2B is allowed to *select* on, and the one it may never select on
SELECTION_PARTITIONS = ("healthy_train", "healthy_val", "F4_CAL")
FINAL_TEST_PARTITION = "F4_TEST"


def common_parser(desc: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--config", required=True)
    ap.add_argument("--storage-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--device", default=None)
    ap.add_argument("--workers", type=int, default=8)
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
        capture_environment(self.layout, self.repo_root, f"stage2b_{phase}_start", {"config_sha256": self.cfg_sha})
        fi = self.cfg["frozen_inputs"]
        self.data_root = Path(args.data_root or self.cfg["paths"]["data_root"]) / f"{fi['dataset_profile']}_seed{fi['dataset_seed']}"
        self.device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
        freeze = self.layout.results / "stage2b_input_freeze.json"
        self.freeze = json.loads(freeze.read_text()) if freeze.exists() else {}
        self.manifest_sha = self.freeze.get("dataset_content_manifest_sha256", "")
        self._bundle = None
        self.log(f"phase {phase} start (git {git_sha(self.repo_root)[:8]}, config {self.cfg_sha[:8]}, device {self.device})")

    # ------------------------------------------------------------------ logging
    def log(self, msg: str) -> None:
        line = f"[{utc_now()}] {msg}"
        print(line, flush=True)
        self.lines.append(line)
        (self.layout.sub("logs") / f"stage2b_{self.phase}.log").write_text("\n".join(self.lines) + "\n", encoding="utf-8")

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
            self._bundle = load_bundle(self.cfg, self.data_root)
            b = self._bundle
            self.log(f"data bundle loaded: train={len(b.train_ids)} val={len(b.val_ids)} test={len(b.test_ids)} calib={len(b.calib_ids)}")
        return self._bundle

    # ------------------------------------------------------------------ rows
    def base_row(self, **kw) -> dict[str, Any]:
        row = {
            "run_id": self.layout.run_id,
            "git_sha": git_sha(self.repo_root),
            "config_sha": self.cfg_sha,
            "dataset_manifest_sha": self.manifest_sha,
            "partition": "",
            "split": "",
            "seed": "",
            "method": "",
            "fault_family": "",
            "status": "OK",
            "provisional": False,
            "strict": False,
            "empirical": True,
        }
        row.update(kw)
        return row

    def write_table(self, name: str, rows: list[dict], *, units: str = "", schema: dict | None = None) -> Path:
        path = self.layout.results / name
        if rows:
            missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
            if missing:
                raise ValueError(f"{name} is missing required columns: {missing}")
        write_csv(path, rows)
        write_json(self.layout.results / (name.replace(".csv", "") + ".schema.json"),
                   {"table": name, "n_rows": len(rows), "required_columns": list(REQUIRED_COLUMNS),
                    "units": units, "columns": schema or {}, "written_utc": utc_now(),
                    "independent_unit": "episode"})
        self.log(f"wrote {name} ({len(rows)} rows)")
        return path

    def finish(self, extra: dict | None = None) -> None:
        capture_environment(self.layout, self.repo_root, f"stage2b_{self.phase}_end", extra or {})


# ---------------------------------------------------------------------- config helpers
def model_cfg(cfg: dict) -> dict:
    m = cfg["models"]
    return {"scalar_hidden_dim": int(m.get("scalar_hidden_dim", 64)),
            "scalar_layers": int(m.get("scalar_layers", 2)),
            "baseline_gru_hidden": int(m.get("baseline_gru_hidden", 80))}


def ensure_model_cfg(cfg: dict) -> dict:
    if "model" not in cfg:
        cfg = dict(cfg)
        cfg["model"] = model_cfg(cfg)
    return cfg


def train_cfg(cfg: dict) -> dict:
    t = cfg["training"]
    return {"epochs": int(t.get("epochs", 40)), "min_epochs": int(t.get("min_epochs", 15)),
            "patience": int(t.get("patience", 10)), "batch_size": int(t.get("batch_size", 64)),
            "weight_decay": float(t.get("weight_decay", 1e-6)), "grad_clip": float(t.get("grad_clip", 1.0))}


# ---------------------------------------------------------------------- statistics
def episode_cluster_bootstrap(
    episode_ids: Sequence, values: np.ndarray, statistic: Callable[[np.ndarray], float],
    n_resamples: int = 2000, alpha: float = 0.05, seed: int = 20260816,
) -> dict[str, float]:
    """Percentile bootstrap that resamples **whole episodes**, not windows.

    ``values`` is aligned with ``episode_ids``; every row belonging to a drawn episode is taken
    together, so overlapping windows inside an episode never contribute independent evidence.
    Window-level IID bootstrap is an integrity failure in this stage, so it is simply not
    implemented anywhere.
    """
    episode_ids = np.asarray(episode_ids)
    values = np.asarray(values)
    uniq = np.unique(episode_ids)
    by_ep = {e: np.where(episode_ids == e)[0] for e in uniq}
    point = float(statistic(values))
    if len(uniq) < 3:
        return {"point": point, "ci_low": float("nan"), "ci_high": float("nan"),
                "n_episodes": int(len(uniq)), "n_rows": int(len(values)), "unit": "episode"}
    rng = np.random.default_rng(seed)
    draws = np.empty(n_resamples)
    for b in range(n_resamples):
        pick = rng.integers(0, len(uniq), size=len(uniq))
        idx = np.concatenate([by_ep[uniq[k]] for k in pick])
        draws[b] = statistic(values[idx])
    lo, hi = np.nanpercentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"point": point, "ci_low": float(lo), "ci_high": float(hi),
            "ci_excludes_zero": bool(lo > 0 or hi < 0),
            "n_episodes": int(len(uniq)), "n_rows": int(len(values)),
            "n_resamples": int(n_resamples), "alpha": float(alpha), "unit": "episode"}


def paired_episode_bootstrap(
    episode_ids: Sequence, a: np.ndarray, b: np.ndarray,
    n_resamples: int = 2000, alpha: float = 0.05, seed: int = 20260816,
) -> dict[str, float]:
    """Episode-cluster CI for the paired difference ``mean(a) - mean(b)`` on the same episodes."""
    pair = np.stack([np.asarray(a, dtype=float), np.asarray(b, dtype=float)], 1)
    return episode_cluster_bootstrap(episode_ids, pair, lambda v: float(np.nanmean(v[:, 0]) - np.nanmean(v[:, 1])),
                                     n_resamples=n_resamples, alpha=alpha, seed=seed)


def seedwise(values_by_seed: dict[int, float]) -> dict[str, Any]:
    v = np.array([x for x in values_by_seed.values() if x == x], dtype=float)
    return {"by_seed": {str(k): (None if x != x else float(x)) for k, x in values_by_seed.items()},
            "mean": float(v.mean()) if v.size else float("nan"),
            "std": float(v.std(ddof=1)) if v.size > 1 else float("nan"),
            "n_seeds": int(v.size),
            "n_seeds_positive": int((v > 0).sum()),
            "n_seeds_negative": int((v < 0).sum())}


def episode_seed_map(data_root: Path) -> dict[str, int]:
    import csv

    with (Path(data_root) / "episode_index.csv").open(newline="", encoding="utf-8") as f:
        return {r["episode_id"]: int(r["seed"]) for r in csv.DictReader(f)}


def truth_parameters(data_root: Path) -> dict:
    """Dataset-level hidden truth parameters (episode replay only; never a deployed input)."""
    return json.loads((Path(data_root) / "dataset_manifest.json").read_text())["truth_parameters_hidden_from_models"]
