from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi.closed_loop.model import simulate_constant_fault
from certo_fdi.experiments.common import (
    ensure_output_dir,
    load_experiment,
    prepare_nominal,
    window_starts,
    write_run_manifest,
)
from certo_fdi.faults.layout import SCALAR_MODES, scalar_fault, zeros
from certo_fdi.operators.window import assemble_window_operator, constant_profile_operator


def run(config_path: str | Path) -> Path:
    config_path, config, params = load_experiment(config_path)
    output_dir = ensure_output_dir(config)
    times, states, _, linearizations = prepare_nominal(config, params)
    w = int(config["window_length"])

    rows: list[dict[str, float | int | str | bool]] = []
    for start in window_starts(config):
        end = start + w
        x0 = states[start]
        start_time = float(times[start])
        _, _, residual_zero = simulate_constant_fault(
            params, np.asarray(zeros()), w, x0=x0, start_time=start_time
        )
        lin_window = linearizations[start:end]

        for mode_name, severities in config["fault_sweeps"].items():
            index, provisional = SCALAR_MODES[mode_name]
            stepwise = assemble_window_operator(lin_window, [index])
            signature = constant_profile_operator(stepwise, 1)[:, 0]

            for severity in severities:
                fault = np.asarray(scalar_fault(index, float(severity)))
                _, _, residual_fault = simulate_constant_fault(
                    params, fault, w, x0=x0, start_time=start_time
                )
                actual = (residual_fault - residual_zero).reshape(-1)
                predicted = signature * float(severity)
                error = actual - predicted
                predicted_norm = float(np.linalg.norm(predicted))
                actual_norm = float(np.linalg.norm(actual))
                absolute_error = float(np.linalg.norm(error))
                relative_error = absolute_error / max(predicted_norm, 1e-15)
                cosine = float(
                    abs(np.dot(actual, predicted))
                    / max(actual_norm * predicted_norm, 1e-15)
                )
                rows.append(
                    {
                        "experiment": config["experiment_name"],
                        "window_start": start,
                        "window_end": end,
                        "window_length": w,
                        "mode": mode_name,
                        "provisional": provisional,
                        "severity": float(severity),
                        "actual_delta_residual_norm": actual_norm,
                        "linear_prediction_norm": predicted_norm,
                        "absolute_model_error": absolute_error,
                        "relative_model_error": relative_error,
                        "actual_vs_prediction_abs_cosine": cosine,
                    }
                )

    csv_path = output_dir / "stage1_epsA_sweep.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    operator_csv = output_dir / "stage1_closedloop_operators.csv"
    produced = [csv_path] + ([operator_csv] if operator_csv.exists() else [])
    write_run_manifest(
        output_dir,
        config_path,
        produced,
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
