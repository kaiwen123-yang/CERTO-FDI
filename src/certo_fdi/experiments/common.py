from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

import jax
import numpy as np
import pandas as pd
import scipy

from certo_fdi.closed_loop.model import simulate_constant_fault
from certo_fdi.config import build_closed_loop_params, load_yaml
from certo_fdi.faults.layout import zeros
from certo_fdi.operators.linearize import linearize_nominal_trajectory
from certo_fdi.paths import require_external_run_root


def load_experiment(config_path: str | Path):
    config_path = Path(config_path)
    config = load_yaml(config_path)
    params = build_closed_loop_params(config)
    return config_path, config, params


def prepare_nominal(config: dict[str, Any], params):
    times, states, residuals = simulate_constant_fault(
        params,
        np.asarray(zeros()),
        int(config["horizon_steps"]),
    )
    linearizations = linearize_nominal_trajectory(states, times, params)
    return times, states, residuals, linearizations


def window_starts(config: dict[str, Any]) -> list[int]:
    horizon = int(config["horizon_steps"])
    w = int(config["window_length"])
    stride = int(config["window_stride"])
    return list(range(0, horizon - w + 1, stride))


def ensure_output_dir(config: dict[str, Any]) -> Path:
    output_dir = require_external_run_root() / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def run_metadata(config_path: str | Path, config: dict[str, Any]) -> dict[str, Any]:
    run_root = require_external_run_root()
    return {
        "run_id": run_root.name,
        "seed": int(config["seed"]),
        "git_sha": git_sha(),
        "config_sha256": sha256_file(Path(config_path)),
    }


def status_metadata(
    metadata: dict[str, Any],
    *,
    strict_certificate: bool,
    empirical_screening: bool,
    provisional: bool,
) -> dict[str, Any]:
    return {
        **metadata,
        "strict_certificate": strict_certificate,
        "empirical_screening": empirical_screening,
        "provisional": provisional,
    }


def write_csv_with_schema(
    rows: list[dict[str, Any]],
    path: Path,
    *,
    units: dict[str, str] | None = None,
    descriptions: dict[str, str] | None = None,
) -> Path:
    frame = pd.DataFrame(rows)
    frame.to_csv(path, index=False)
    schema = {
        "file": path.name,
        "row_count": len(frame),
        "columns": {
            column: {
                "dtype": str(frame[column].dtype),
                "unit": (units or {}).get(column, "dimensionless_or_not_applicable"),
                "description": (descriptions or {}).get(column, column.replace("_", " ")),
            }
            for column in frame.columns
        },
    }
    path.with_suffix(".schema.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8"
    )
    return path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_run_manifest(
    output_dir: Path,
    config_path: Path,
    produced_files: list[Path],
    extra: dict[str, Any] | None = None,
) -> Path:
    manifest = {
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "jax": jax.__version__,
        "files": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in produced_files
        },
    }
    if extra:
        manifest["extra"] = extra
    path = output_dir / "stage1_run_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path
