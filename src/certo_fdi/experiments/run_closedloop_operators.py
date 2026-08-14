from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi.experiments.common import (
    ensure_output_dir,
    load_experiment,
    prepare_nominal,
    window_starts,
    write_run_manifest,
)
from certo_fdi.faults.layout import SCALAR_MODES
from certo_fdi.operators.direct_signature import direct_filtered_signature
from certo_fdi.operators.window import (
    assemble_window_operator,
    constant_profile_operator,
    spectral_summary,
)


def run(config_path: str | Path) -> Path:
    config_path, config, params = load_experiment(config_path)
    output_dir = ensure_output_dir(config)
    times, states, residuals, linearizations = prepare_nominal(config, params)

    rows: list[dict[str, float | int | str | bool]] = []
    w = int(config["window_length"])
    npz_payload: dict[str, np.ndarray] = {}

    for start in window_starts(config):
        end = start + w
        lin_window = linearizations[start:end]
        state_window = states[start:end]
        time_window = times[start:end]

        for mode_name, (index, provisional) in SCALAR_MODES.items():
            stepwise = assemble_window_operator(lin_window, [index])
            constant = constant_profile_operator(stepwise, parameter_dim=1)
            summary = spectral_summary(constant)
            direct = direct_filtered_signature(mode_name, state_window, time_window, params)
            if direct is None:
                direct_norm = float("nan")
                relative_difference = float("nan")
                cosine = float("nan")
            else:
                closed = constant[:, 0]
                direct_norm = float(np.linalg.norm(direct))
                denom = max(float(np.linalg.norm(closed)), 1e-15)
                relative_difference = float(np.linalg.norm(closed - direct) / denom)
                cosine = float(
                    abs(np.dot(closed, direct))
                    / max(np.linalg.norm(closed) * np.linalg.norm(direct), 1e-15)
                )

            key = f"window_{start:04d}__{mode_name}"
            npz_payload[key] = constant
            rows.append(
                {
                    "experiment": config["experiment_name"],
                    "window_start": start,
                    "window_end": end,
                    "window_length": w,
                    "mode": mode_name,
                    "provisional": provisional,
                    "operator_rows": constant.shape[0],
                    "operator_cols": constant.shape[1],
                    **summary,
                    "closed_operator_norm": float(np.linalg.norm(constant)),
                    "direct_signature_norm": direct_norm,
                    "closed_vs_direct_relative_error": relative_difference,
                    "closed_vs_direct_abs_cosine": cosine,
                    "nominal_residual_rms": float(np.sqrt(np.mean(residuals[start:end] ** 2))),
                }
            )

    csv_path = output_dir / "stage1_closedloop_operators.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    npz_path = output_dir / "stage1_closedloop_operators.npz"
    np.savez_compressed(npz_path, **npz_payload)
    write_run_manifest(
        output_dir,
        config_path,
        [csv_path, npz_path],
        extra={"status": "stage1_started", "decision": "NOT_EVALUATED"},
    )
    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    path = run(args.config)
    print(path)


if __name__ == "__main__":
    main()
