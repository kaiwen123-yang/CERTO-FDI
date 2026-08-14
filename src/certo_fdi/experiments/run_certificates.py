from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi.experiments.common import ensure_output_dir, load_experiment, write_run_manifest
from certo_fdi.sets.tube import scalar_fault_to_healthy_difference_distance


def run(config_path: str | Path) -> Path:
    config_path, config, _ = load_experiment(config_path)
    output_dir = ensure_output_dir(config)
    operator_csv = output_dir / "stage1_closedloop_operators.csv"
    operator_npz = output_dir / "stage1_closedloop_operators.npz"
    eps_csv = output_dir / "stage1_epsA_sweep.csv"
    for path in (operator_csv, operator_npz, eps_csv):
        if not path.exists():
            raise FileNotFoundError(f"required prior-stage output missing: {path}")

    operators = np.load(operator_npz)
    eps = pd.read_csv(eps_csv)
    starts = sorted(eps["window_start"].unique())
    tube_modes = list(config["healthy_tube"]["basis_modes"])
    tube_half_widths = np.asarray(config["healthy_tube"]["half_widths"], dtype=float)
    basis_error = float(config["healthy_tube"].get("basis_error", 0.0))

    rows: list[dict[str, float | int | str | bool]] = []
    for start in starts:
        healthy_columns = [
            np.asarray(operators[f"window_{int(start):04d}__{mode}"])[:, 0]
            for mode in tube_modes
        ]
        healthy_basis = np.column_stack(healthy_columns)

        for mode, severities in config["fault_sweeps"].items():
            signature = np.asarray(operators[f"window_{int(start):04d}__{mode}"])[:, 0]
            interval = (float(min(severities)), float(max(severities)))
            result = scalar_fault_to_healthy_difference_distance(
                signature,
                interval,
                healthy_basis,
                tube_half_widths,
            )
            subset = eps[(eps["window_start"] == start) & (eps["mode"] == mode)]
            empirical_abs_error = float(subset["absolute_model_error"].max())
            empirical_rel_error = float(subset["relative_model_error"].max())
            screening_lower = max(
                0.0,
                result.distance - basis_error - empirical_abs_error,
            )
            rows.append(
                {
                    "experiment": config["experiment_name"],
                    "window_start": int(start),
                    "window_length": int(config["window_length"]),
                    "mode": mode,
                    "fault_min": interval[0],
                    "fault_max": interval[1],
                    "geometric_distance": result.distance,
                    "optimizer_fault_parameter": result.fault_parameter,
                    "healthy_basis_error_assumed": basis_error,
                    "empirical_absolute_model_error_max": empirical_abs_error,
                    "empirical_relative_model_error_max": empirical_rel_error,
                    "deterministic_screening_lower_bound": screening_lower,
                    "noise_radius": float("nan"),
                    "deployment_lower_bound": float("nan"),
                    "deployment_certified": False,
                    "status": "UNCALIBRATED_SCREENING_ONLY",
                    "solver_status": result.solver_status,
                }
            )

    csv_path = output_dir / "stage1_certificates.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    write_run_manifest(
        output_dir,
        config_path,
        [operator_csv, operator_npz, eps_csv, csv_path],
        extra={
            "status": "stage1_started",
            "decision": "NOT_EVALUATED",
            "certificate_status": "UNCALIBRATED_SCREENING_ONLY",
        },
    )
    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
