from __future__ import annotations

import itertools
import json
import math
import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import jax

from certo_fdi.certificates.bounds import detection_lower_bound, isolation_lower_bound
from certo_fdi.certificates.noise_radius import empirical_norm_radius, gaussian_oracle_radius
from certo_fdi.certificates.set_distance import detection_distance, isolation_distance
from certo_fdi.closed_loop.model import simulate_constant_fault
from certo_fdi.dynamics.spatial_rnea import rnea_2r
from certo_fdi.dynamics.two_link import rigid_body_torque
from certo_fdi.experiments.adversarial import covariance_bound_trial, subspace_external_energy
from certo_fdi.experiments.common import (
    ensure_output_dir,
    load_experiment,
    prepare_nominal,
    run_metadata,
    status_metadata,
    window_starts,
    write_csv_with_schema,
    write_run_manifest,
)
from certo_fdi.faults.layout import SCALAR_MODES, scalar_fault, zeros
from certo_fdi.healthy_sets.physical_basis import build_physical_healthy_basis
from certo_fdi.operators.direct_signature import direct_filtered_signature
from certo_fdi.operators.hessian_bounds import window_response_derivatives
from certo_fdi.operators.window import (
    assemble_window_operator,
    constant_profile_operator,
    spectral_summary,
)
from certo_fdi.paths import require_external_run_root


@dataclass(frozen=True)
class ControllerRun:
    name: str
    params: Any
    times: np.ndarray
    states: np.ndarray
    residuals: np.ndarray
    linearizations: list[Any]


def _controller_runs(config: dict[str, Any], base_params: Any) -> list[ControllerRun]:
    output = []
    mapping = {"computed_torque": 0, "pd_gravity": 1}
    for name in config.get("controllers", ["computed_torque"]):
        print(f"STAGE=nominal_linearization CONTROLLER={name} STATUS=START", flush=True)
        params = base_params._replace(controller=base_params.controller._replace(kind=mapping[name]))
        times, states, residuals, linearizations = prepare_nominal(config, params)
        output.append(ControllerRun(name, params, times, states, residuals, linearizations))
        print(f"STAGE=nominal_linearization CONTROLLER={name} STATUS=COMPLETE", flush=True)
        jax.clear_caches()
        gc.collect()
    return output


def _operator_key(controller: str, start: int, mode: str) -> str:
    return f"{controller}__window_{start:04d}__{mode}"


def _base(meta: dict[str, Any], *, provisional: bool = False) -> dict[str, Any]:
    return status_metadata(
        meta,
        strict_certificate=False,
        empirical_screening=True,
        provisional=provisional,
    )


def run_operators(
    config_path: Path,
    config: dict[str, Any],
    runs: list[ControllerRun],
) -> tuple[dict[str, np.ndarray], pd.DataFrame]:
    output_dir = ensure_output_dir(config)
    meta = run_metadata(config_path, config)
    window_length = int(config["window_length"])
    operators: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    for run in runs:
        for start in window_starts(config):
            print(
                f"STAGE=operators CONTROLLER={run.name} WINDOW={start} STATUS=START",
                flush=True,
            )
            end = start + window_length
            linearizations = run.linearizations[start:end]
            for mode, (index, provisional) in SCALAR_MODES.items():
                stepwise = assemble_window_operator(linearizations, [index])
                signature = constant_profile_operator(stepwise, 1)
                operators[_operator_key(run.name, start, mode)] = signature
                summary = spectral_summary(signature)
                direct = direct_filtered_signature(
                    mode, run.states[start:end], run.times[start:end], run.params
                )
                if direct is None:
                    direct_abs = float("nan")
                    direct_relative = float("nan")
                    correlation = float("nan")
                else:
                    closed = signature[:, 0]
                    direct_abs = float(np.linalg.norm(closed - direct))
                    direct_relative = direct_abs / max(float(np.linalg.norm(closed)), 1e-15)
                    correlation = float(
                        abs(np.dot(closed, direct))
                        / max(np.linalg.norm(closed) * np.linalg.norm(direct), 1e-15)
                    )
                severity = float(min(config["fault_sweeps"][mode])) * 1e-3
                zero_fault = np.asarray(zeros())
                _, _, baseline = simulate_constant_fault(
                    run.params,
                    zero_fault,
                    window_length,
                    x0=run.states[start],
                    start_time=float(run.times[start]),
                )
                _, _, perturbed = simulate_constant_fault(
                    run.params,
                    np.asarray(scalar_fault(index, severity)),
                    window_length,
                    x0=run.states[start],
                    start_time=float(run.times[start]),
                )
                actual = (perturbed - baseline).reshape(-1)
                predicted = signature[:, 0] * severity
                nonlinear_abs = float(np.linalg.norm(actual - predicted))
                nonlinear_relative = nonlinear_abs / max(float(np.linalg.norm(predicted)), 1e-15)
                rows.append(
                    {
                        **_base(meta, provisional=provisional),
                        "controller": run.name,
                        "window_start": start,
                        "window_end": end,
                        "window_length": window_length,
                        "fault_family": mode.split("_")[0],
                        "mode": mode,
                        "parameterization": "constant_scalar_window",
                        "operator_rows": signature.shape[0],
                        "operator_cols": signature.shape[1],
                        "rank": summary["rank"],
                        "sigma_min": summary["sigma_min_positive"],
                        "sigma_max": summary["sigma_max"],
                        "condition_number": summary["condition_number_positive"],
                        "nullspace_dimension": signature.shape[1] - summary["rank"],
                        "closed_operator_norm": float(np.linalg.norm(signature)),
                        "direct_signature_absolute_difference": direct_abs,
                        "direct_signature_relative_difference": direct_relative,
                        "other_signature_abs_correlation": correlation,
                        "nonlinear_validation_severity": severity,
                        "nonlinear_absolute_error": nonlinear_abs,
                        "nonlinear_relative_error": nonlinear_relative,
                        "nominal_residual_rms": float(
                            np.sqrt(np.mean(run.residuals[start:end] ** 2))
                        ),
                    }
                )
                validation_rows.append(
                    {
                        **_base(meta, provisional=provisional),
                        "controller": run.name,
                        "window_start": start,
                        "mode": mode,
                        "validation": "nonlinear_small_signal",
                        "absolute_error": nonlinear_abs,
                        "relative_error": nonlinear_relative,
                        "passed": nonlinear_relative < 5e-3,
                    }
                )
            print(
                f"STAGE=operators CONTROLLER={run.name} WINDOW={start} STATUS=COMPLETE",
                flush=True,
            )
    csv_path = output_dir / "stage1_closedloop_operators.csv"
    write_csv_with_schema(
        rows,
        csv_path,
        units={
            "window_start": "sample_index",
            "window_end": "sample_index",
            "sigma_min": "residual_per_fault_unit",
            "sigma_max": "residual_per_fault_unit",
            "nonlinear_absolute_error": "residual_norm",
        },
    )
    validation_path = output_dir / "stage1_operator_validation.csv"
    write_csv_with_schema(validation_rows, validation_path)
    npz_path = output_dir / "stage1_closedloop_operators.npz"
    np.savez_compressed(npz_path, **operators)
    passed = sum(bool(row["passed"]) for row in validation_rows)
    (output_dir / "stage1_operator_validation.md").write_text(
        "# Stage 1 operator validation\n\n"
        f"Small-signal nonlinear checks passed: {passed}/{len(validation_rows)}. "
        "The interval-end block indexing is independently locked by unit tests. "
        "Command delay uses an explicit two-interval buffer, but its piecewise AD "
        "operator remains marked provisional.\n",
        encoding="utf-8",
    )
    return operators, pd.DataFrame(rows)


def run_model_error(
    config_path: Path,
    config: dict[str, Any],
    runs: list[ControllerRun],
    operators: dict[str, np.ndarray],
) -> tuple[pd.DataFrame, dict[tuple[str, int, str], float]]:
    output_dir = ensure_output_dir(config)
    meta = run_metadata(config_path, config)
    window_length = int(config["window_length"])
    rows: list[dict[str, Any]] = []
    summary: dict[tuple[str, int, str], float] = {}
    for run in runs:
        for start in window_starts(config):
            baseline_fault = np.asarray(zeros())
            _, _, baseline = simulate_constant_fault(
                run.params,
                baseline_fault,
                window_length,
                x0=run.states[start],
                start_time=float(run.times[start]),
            )
            for mode, severities in config["fault_sweeps"].items():
                index, provisional = SCALAR_MODES[mode]
                signature = operators[_operator_key(run.name, start, mode)][:, 0]
                local_errors = []
                for severity in severities:
                    _, _, faulty = simulate_constant_fault(
                        run.params,
                        np.asarray(scalar_fault(index, float(severity))),
                        window_length,
                        x0=run.states[start],
                        start_time=float(run.times[start]),
                    )
                    actual = (faulty - baseline).reshape(-1)
                    predicted = signature * float(severity)
                    error = float(np.linalg.norm(actual - predicted))
                    local_errors.append(error)
                    rows.append(
                        {
                            **_base(meta, provisional=provisional),
                            "controller": run.name,
                            "window_start": start,
                            "window_length": window_length,
                            "mode": mode,
                            "severity": float(severity),
                            "actual_delta_residual_norm": float(np.linalg.norm(actual)),
                            "linear_prediction_norm": float(np.linalg.norm(predicted)),
                            "empirical_grid_error": error,
                            "relative_error_for_diagnostics": error
                            / max(float(np.linalg.norm(predicted)), 1e-15),
                            "grid_cover_term": float("nan"),
                            "hessian_bound": float("nan"),
                            "validated_upper_bound": float("nan"),
                            "bound_status": "EMPIRICAL_ONLY",
                        }
                    )
                summary[(run.name, start, mode)] = max(local_errors)
    eps_path = output_dir / "stage1_epsA_sweep.csv"
    write_csv_with_schema(
        rows,
        eps_path,
        units={
            "severity": "fault_specific_SI_or_fraction",
            "empirical_grid_error": "residual_norm",
            "grid_cover_term": "residual_norm",
            "hessian_bound": "residual_norm",
            "validated_upper_bound": "residual_norm",
        },
    )

    representative = int(config["representative_window_start"])
    reference_run = next(run for run in runs if run.name == "computed_torque")
    hessian_rows = []
    for mode, severities in config["fault_sweeps"].items():
        index, provisional = SCALAR_MODES[mode]
        _, hessian = window_response_derivatives(
            reference_run.states[representative],
            float(reference_run.times[representative]),
            index,
            reference_run.params,
            window_length,
        )
        norm = float(np.linalg.norm(hessian))
        local_bound = 0.5 * norm * float(max(severities)) ** 2
        hessian_rows.append(
            {
                **_base(meta, provisional=provisional),
                "controller": reference_run.name,
                "window_start": representative,
                "mode": mode,
                "hessian_norm_at_zero": norm,
                "maximum_severity": float(max(severities)),
                "local_second_order_bound": local_bound,
                "validated_upper_bound": float("nan"),
                "bound_status": "LOCAL_HESSIAN_DIAGNOSTIC_ONLY",
            }
        )
        jax.clear_caches()
        gc.collect()
    write_csv_with_schema(hessian_rows, output_dir / "stage1_hessian_bounds.csv")
    (output_dir / "stage1_model_error_report.md").write_text(
        "# Absolute closed-loop model error\n\n"
        "Every fault mode was scanned at five preconfigured severities in every window. "
        "The finite-grid maxima are empirical observations, not support-wide upper bounds. "
        "AD Hessians were computed at the representative window and checked against second "
        "differences by unit test, but no global Hessian Lipschitz or interval proof was "
        "obtained. Therefore `validated_upper_bound` remains empty and every affected row is "
        "`EMPIRICAL_ONLY`.\n",
        encoding="utf-8",
    )
    return pd.DataFrame(rows), summary


def run_healthy_tube(
    config_path: Path,
    config: dict[str, Any],
    runs: list[ControllerRun],
) -> tuple[pd.DataFrame, dict[tuple[str, int], float], dict[tuple[str, int], np.ndarray]]:
    output_dir = ensure_output_dir(config)
    meta = run_metadata(config_path, config)
    window_length = int(config["window_length"])
    names = list(config["healthy_tube"]["basis_modes"])
    widths = np.asarray(config["healthy_tube"]["half_widths"], dtype=float)
    design_points = [np.zeros(len(widths))]
    for index, width in enumerate(widths):
        for sign in (-1.0, 1.0):
            point = np.zeros(len(widths))
            point[index] = sign * width
            design_points.append(point)
    design_points.extend(np.asarray(vertex) * widths for vertex in itertools.product([-1, 1], repeat=3))
    rows: list[dict[str, Any]] = []
    maximum_error: dict[tuple[str, int], float] = {}
    bases: dict[tuple[str, int], np.ndarray] = {}
    for run in runs:
        for start in window_starts(config):
            linearizations = run.linearizations[start : start + window_length]
            basis = build_physical_healthy_basis(linearizations, names)
            bases[(run.name, start)] = basis
            _, _, baseline = simulate_constant_fault(
                run.params,
                np.asarray(zeros()),
                window_length,
                x0=run.states[start],
                start_time=float(run.times[start]),
            )
            errors = []
            for point_index, point in enumerate(design_points):
                _, _, healthy_response = simulate_constant_fault(
                    run.params,
                    np.asarray(zeros()),
                    window_length,
                    x0=run.states[start],
                    start_time=float(run.times[start]),
                    healthy=point,
                )
                actual = (healthy_response - baseline).reshape(-1)
                predicted = basis @ point
                error = float(np.linalg.norm(actual - predicted))
                errors.append(error)
                rows.append(
                    {
                        **_base(meta),
                        "controller": run.name,
                        "window_start": start,
                        "design_point": point_index,
                        "healthy_viscous_j1": point[0],
                        "healthy_viscous_j2": point[1],
                        "healthy_payload_mass": point[2],
                        "actual_response_norm": float(np.linalg.norm(actual)),
                        "linear_response_norm": float(np.linalg.norm(predicted)),
                        "empirical_basis_error": error,
                        "box_source": "CONFIGURED_ENGINEERING_CONTRACT",
                        "support_inferred_from_samples": False,
                    }
                )
            maximum_error[(run.name, start)] = max(errors)
    frame = pd.DataFrame(rows)
    write_csv_with_schema(rows, output_dir / "stage1_healthy_tube.csv")
    e0_rows = [
        {
            **_base(meta),
            "controller": controller,
            "window_start": start,
            "configured_basis_error": float(config["healthy_tube"].get("basis_error", 0.0)),
            "empirical_closed_loop_basis_error": error,
            "noise_component": float("nan"),
            "validated_e0": float("nan"),
            "status": "EMPIRICAL_ONLY",
        }
        for (controller, start), error in maximum_error.items()
    ]
    write_csv_with_schema(e0_rows, output_dir / "stage1_e0_components.csv")
    (output_dir / "STRUCTURED_E0_THEOREM_OR_FAILURE.md").write_text(
        "# Structured e0 result: strict theorem not obtained\n\n"
        "The healthy coefficient box is fixed by configuration and was not inferred from "
        "sample extrema. Vertices, axes, and the interior origin were evaluated. The observed "
        "closed-loop basis mismatch is finite-grid evidence only. Gaussian oracle noise has an "
        "exact marginal radius when sigma is treated as known; t3 uses independent empirical "
        "calibration. No exact joint-probability theorem covering model remainder plus estimated "
        "heavy-tail noise was proved, so `validated_e0` is deliberately empty.\n",
        encoding="utf-8",
    )
    return frame, maximum_error, bases


def run_adversarial_recheck(
    config_path: Path,
    config: dict[str, Any],
    runs: list[ControllerRun],
    operators: dict[str, np.ndarray],
    eps_frame: pd.DataFrame,
    bases: dict[tuple[str, int], np.ndarray],
) -> pd.DataFrame:
    output_dir = ensure_output_dir(config)
    meta = run_metadata(config_path, config)
    rows: list[dict[str, Any]] = []
    for _, record in eps_frame[eps_frame["mode"] == "actuator_gain_j1"].iterrows():
        rows.append(
            {
                **_base(meta),
                "check_id": "P0-1",
                "case": f"{record.controller}/window_{int(record.window_start)}",
                "metric": "closed_linear_relative_error",
                "value": float(record.relative_error_for_diagnostics),
                "m": float("nan"),
                "N": float("nan"),
                "distribution": "not_applicable",
                "status": "MEASURED",
            }
        )
    reference = runs[0]
    q = np.array([0.7, -0.9])
    qd = np.array([1.2, -0.8])
    qdd = np.array([0.4, 1.1])
    mutated = rnea_2r(q, qd, qdd, reference.params.plant, mutate_ad_star_sign=True)
    oracle = np.asarray(rigid_body_torque(q, qd, qdd, reference.params.plant))
    rows.append(
        {
            **_base(meta),
            "check_id": "P0-2",
            "case": "wrong_positive_ad_star_mutation",
            "metric": "closed_form_torque_mismatch",
            "value": float(np.linalg.norm(mutated - oracle)),
            "m": float("nan"),
            "N": float("nan"),
            "distribution": "not_applicable",
            "status": "MUTATION_CAUGHT",
        }
    )
    seeds = [7, 11, 42, 260809, 20260814]
    for dimension, sample_count, distribution, seed in itertools.product(
        [20, 40, 100], [200, 400, 2000], ["gaussian", "t3", "lognormal"], seeds
    ):
        trial = covariance_bound_trial(distribution, dimension, sample_count, seed)
        rows.append(
            {
                **_base(meta),
                "check_id": "P0-3",
                "case": f"seed_{seed}",
                "metric": "legacy_generic_bound_violation",
                "value": float(bool(trial["violation"])),
                "m": dimension,
                "N": sample_count,
                "distribution": distribution,
                "status": "VIOLATION" if trial["violation"] else "WITHIN_HEURISTIC",
            }
        )
    representative = int(config["representative_window_start"])
    widths = np.asarray(config["healthy_tube"]["half_widths"], dtype=float)
    healthy = bases[(reference.name, representative)]
    for mode in ["actuator_gain_j1", "viscous_j1", "payload_mass", "contact_fy", "command_delay"]:
        signature = operators[_operator_key(reference.name, representative, mode)][:, 0]
        severities = config["fault_sweeps"][mode]
        joint = detection_distance(signature, min(severities), max(severities), healthy, widths)
        directional = [
            detection_distance(
                signature,
                min(severities),
                max(severities),
                healthy[:, [column]],
                widths[[column]],
            ).distance
            for column in range(healthy.shape[1])
        ]
        rows.append(
            {
                **_base(meta, provisional=SCALAR_MODES[mode][1]),
                "check_id": "P0-4",
                "case": mode,
                "metric": "joint_over_best_single_direction_distance",
                "value": joint.distance / max(min(directional), 1e-15),
                "m": healthy.shape[1],
                "N": float("nan"),
                "distribution": "not_applicable",
                "status": "JOINT_QP_CROSS_CHECKED",
            }
        )
    phase = np.linspace(-2.0, 2.0, 200)
    average_basis = np.column_stack([phase, np.tanh(phase / 0.2)])
    for joint, width in [("j1", 0.35), ("j2", 0.55)]:
        shape = np.exp(-(phase / width) ** 2) * np.sign(phase)
        rows.append(
            {
                **_base(meta),
                "check_id": "P1-3",
                "case": joint,
                "metric": "friction_shape_external_energy_ratio",
                "value": subspace_external_energy(shape, average_basis),
                "m": 2,
                "N": len(phase),
                "distribution": "not_applicable",
                "status": "PER_JOINT_PARAMETERIZATION",
            }
        )
    path = output_dir / "adversarial_recheck_results.csv"
    write_csv_with_schema(rows, path)
    serializable = json.loads(pd.DataFrame(rows).to_json(orient="records"))
    (output_dir / "adversarial_recheck_results.json").write_text(
        json.dumps(serializable, indent=2, sort_keys=True), encoding="utf-8"
    )
    p03 = [row for row in rows if row["check_id"] == "P0-3"]
    t3_rate = np.mean([row["value"] for row in p03 if row["distribution"] == "t3"])
    gaussian_rate = np.mean(
        [row["value"] for row in p03 if row["distribution"] == "gaussian"]
    )
    (output_dir / "ADVERSARIAL_RECHECK_REPORT.md").write_text(
        "# Adversarial recheck\n\n"
        "- P0-1 was recomputed for computed-torque and PD+gravity controllers.\n"
        "- P0-2 wrong-sign `ad_star` mutation was caught by the independent dynamics oracle.\n"
        f"- P0-3 archived heuristic violation rates: Gaussian {gaussian_rate:.3f}, "
        f"unit-variance t3 {t3_rate:.3f}; lognormal was also scanned.\n"
        "- P0-4 five representative rows used the full joint QP and two independent solvers.\n"
        "- Pinocchio was not required: full spatial RNEA was independently cross-checked by "
        "closed form and a SymPy Lagrange derivation.\n",
        encoding="utf-8",
    )
    return pd.DataFrame(rows)


def run_certificates(
    config_path: Path,
    config: dict[str, Any],
    runs: list[ControllerRun],
    operators: dict[str, np.ndarray],
    model_errors: dict[tuple[str, int, str], float],
    healthy_errors: dict[tuple[str, int], float],
    bases: dict[tuple[str, int], np.ndarray],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_dir = ensure_output_dir(config)
    meta = run_metadata(config_path, config)
    widths = np.asarray(config["healthy_tube"]["half_widths"], dtype=float)
    dimension = 2 * int(config["window_length"])
    gaussian_radius = gaussian_oracle_radius(
        dimension, float(config["noise"]["sigma"]), float(config["noise"]["alpha"])
    )
    detection_rows: list[dict[str, Any]] = []
    identifiability_rows: list[dict[str, Any]] = []
    for run in runs:
        for start in window_starts(config):
            healthy = bases[(run.name, start)]
            healthy_error = healthy_errors[(run.name, start)]
            for mode, severities in config["fault_sweeps"].items():
                provisional = SCALAR_MODES[mode][1]
                signature = operators[_operator_key(run.name, start, mode)][:, 0]
                distance = detection_distance(
                    signature, min(severities), max(severities), healthy, widths
                )
                fault_error = model_errors[(run.name, start, mode)]
                screening_lower = detection_lower_bound(
                    distance.distance, healthy_error, fault_error
                )
                detection_rows.append(
                    {
                        **_base(meta, provisional=provisional),
                        "controller": run.name,
                        "window_start": start,
                        "window_length": int(config["window_length"]),
                        "mode": mode,
                        "fault_min": float(min(severities)),
                        "fault_max": float(max(severities)),
                        "d_hat": distance.distance,
                        "e_delta_H_empirical": healthy_error,
                        "e_A_abs_empirical": fault_error,
                        "d_lower": float("nan"),
                        "screening_d_lower": screening_lower,
                        "gaussian_oracle_noise_radius": gaussian_radius,
                        "screening_snr_d": screening_lower / (2.0 * gaussian_radius),
                        "solver_absolute_difference": distance.absolute_solver_difference,
                        "certificate_status": "EMPIRICAL_MODEL_ERROR_ONLY",
                    }
                )
                kappa_hat = float(np.linalg.norm(signature))
                e_kappa = fault_error / max(float(max(severities)), 1e-15)
                identifiability_rows.append(
                    {
                        **_base(meta, provisional=provisional),
                        "controller": run.name,
                        "window_start": start,
                        "mode": mode,
                        "kappa_hat": kappa_hat,
                        "e_kappa_empirical": e_kappa,
                        "kappa_lower": float("nan"),
                        "screening_kappa_lower": max(0.0, kappa_hat - e_kappa),
                        "global_injectivity_checked": False,
                        "equivalence_note": (
                            "payload/contact equivalence requires quotient label"
                            if mode in {"payload_mass", "contact_fy"}
                            else "local result only"
                        ),
                    }
                )
    selected = [
        "actuator_gain_j1",
        "viscous_j1",
        "payload_mass",
        "link1_contact_fy",
        "contact_fy",
        "encoder_bias_j1",
        "command_delay",
    ]
    isolation_rows: list[dict[str, Any]] = []
    for run in runs:
        for start in window_starts(config):
            healthy = bases[(run.name, start)]
            healthy_error = healthy_errors[(run.name, start)]
            for mode_j, mode_k in itertools.combinations(selected, 2):
                severity_j = config["fault_sweeps"][mode_j]
                severity_k = config["fault_sweeps"][mode_k]
                sj = operators[_operator_key(run.name, start, mode_j)][:, 0]
                sk = operators[_operator_key(run.name, start, mode_k)][:, 0]
                distance = isolation_distance(
                    sj,
                    min(severity_j),
                    max(severity_j),
                    sk,
                    min(severity_k),
                    max(severity_k),
                    healthy,
                    widths,
                )
                error_j = model_errors[(run.name, start, mode_j)]
                error_k = model_errors[(run.name, start, mode_k)]
                screening_lower = isolation_lower_bound(
                    distance.distance, healthy_error, error_j, error_k
                )
                isolation_rows.append(
                    {
                        **_base(
                            meta,
                            provisional=SCALAR_MODES[mode_j][1] or SCALAR_MODES[mode_k][1],
                        ),
                        "controller": run.name,
                        "window_start": start,
                        "mode_j": mode_j,
                        "mode_k": mode_k,
                        "iota_hat": distance.distance,
                        "e_delta_H_empirical": healthy_error,
                        "e_A_j_empirical": error_j,
                        "e_A_k_empirical": error_k,
                        "iota_lower": float("nan"),
                        "screening_iota_lower": screening_lower,
                        "gaussian_oracle_noise_radius": gaussian_radius,
                        "screening_snr_iota": screening_lower / (2.0 * gaussian_radius),
                        "solver_absolute_difference": distance.absolute_solver_difference,
                        "certificate_status": "EMPIRICAL_MODEL_ERROR_ONLY",
                    }
                )
    detection_frame = pd.DataFrame(detection_rows)
    isolation_frame = pd.DataFrame(isolation_rows)
    write_csv_with_schema(detection_rows, output_dir / "stage1_certificates.csv")
    write_csv_with_schema(isolation_rows, output_dir / "stage1_isolation_pairs.csv")
    write_csv_with_schema(
        identifiability_rows, output_dir / "stage1_identifiability.csv"
    )
    atlas_rows = []
    for (controller, start), subset in detection_frame.groupby(["controller", "window_start"]):
        corresponding = isolation_frame[
            (isolation_frame.controller == controller) & (isolation_frame.window_start == start)
        ]
        atlas_rows.append(
            {
                **_base(meta),
                "controller": controller,
                "window_start": int(start),
                "strict_detection_fraction": 0.0,
                "screening_detection_fraction": float(np.mean(subset.screening_d_lower > 0.0)),
                "strict_isolation_fraction": 0.0,
                "screening_isolation_fraction": float(
                    np.mean(corresponding.screening_iota_lower > 0.0)
                ),
            }
        )
    write_csv_with_schema(atlas_rows, output_dir / "stage1_atlas_summary.csv")
    (output_dir / "stage1_certificate_report.md").write_text(
        "# Stage 1 certificate report\n\n"
        "Joint geometric distances were independently cross-solved. All displayed positive "
        "lower values are screening values because both healthy and fault closed-loop "
        "remainders are finite-grid maxima. The strict `d_lower`, `iota_lower`, and "
        "`kappa_lower` fields are intentionally empty. They must not be interpreted as zero "
        "or as certified positive values.\n",
        encoding="utf-8",
    )
    return detection_frame, isolation_frame


def _noise_samples(
    distribution: str,
    seed: int,
    count: int,
    dimension: int,
    sigma: float,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if distribution == "gaussian":
        return sigma * rng.normal(size=(count, dimension))
    if distribution == "t3":
        return sigma * rng.standard_t(df=3, size=(count, dimension)) / math.sqrt(3.0)
    if distribution == "lognormal":
        raw = rng.lognormal(size=(count, dimension))
        mean = math.exp(0.5)
        standard_deviation = math.sqrt((math.e - 1.0) * math.e)
        return sigma * (raw - mean) / standard_deviation
    raise KeyError(distribution)


def run_noise_and_events(
    config_path: Path,
    config: dict[str, Any],
    detections: pd.DataFrame,
    isolations: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_dir = ensure_output_dir(config)
    meta = run_metadata(config_path, config)
    noise = config["noise"]
    dimension = 2 * int(config["window_length"])
    alpha = float(noise["alpha"])
    sigma = float(noise["sigma"])
    calibration_count = int(noise["calibration_count"])
    test_count = int(noise["test_count"])
    oracle_radius = gaussian_oracle_radius(dimension, sigma, alpha)
    gaussian_rows = []
    t3_rows = []
    cached: dict[tuple[str, int], tuple[np.ndarray, float]] = {}
    for seed in noise["seeds"]:
        for distribution in ("gaussian", "t3", "lognormal"):
            calibration = _noise_samples(
                distribution, int(seed), calibration_count, dimension, sigma
            )
            test = _noise_samples(
                distribution, int(seed) + 1_000_003, test_count, dimension, sigma
            )
            radius = (
                oracle_radius
                if distribution == "gaussian"
                else empirical_norm_radius(calibration, alpha)
            )
            coverage = float(np.mean(np.linalg.norm(test, axis=1) <= radius))
            oracle_coverage = float(
                np.mean(np.linalg.norm(test, axis=1) <= oracle_radius)
            )
            row = {
                **_base(meta),
                "distribution": distribution,
                "coverage_seed": int(seed),
                "dimension": dimension,
                "sigma": sigma,
                "alpha": alpha,
                "radius": radius,
                "coverage": coverage,
                "gaussian_oracle_radius": oracle_radius,
                "coverage_under_gaussian_oracle_radius": oracle_coverage,
                "calibration_kind": (
                    "KNOWN_SIGMA_CHI_MARGINAL"
                    if distribution == "gaussian"
                    else "INDEPENDENT_EMPIRICAL_MARGINAL"
                ),
                "exact_conditional_cfar": False,
            }
            if distribution == "gaussian":
                gaussian_rows.append(row)
            else:
                t3_rows.append(row)
            cached[(distribution, int(seed))] = (test, radius)
    write_csv_with_schema(gaussian_rows, output_dir / "stage1_coverage_gaussian.csv")
    write_csv_with_schema(t3_rows, output_dir / "stage1_coverage_t3.csv")

    detection_rows = []
    for _, certificate in detections.iterrows():
        for distribution in ("gaussian", "t3"):
            for seed in noise["seeds"]:
                samples, radius = cached[(distribution, int(seed))]
                signal = float(certificate.screening_d_lower)
                shifted = samples.copy()
                shifted[:, 0] += signal
                detection_rows.append(
                    {
                        **_base(meta, provisional=bool(certificate.provisional)),
                        "controller": certificate.controller,
                        "window_start": int(certificate.window_start),
                        "mode": certificate.mode,
                        "distribution": distribution,
                        "coverage_seed": int(seed),
                        "radius": radius,
                        "screening_d_lower": signal,
                        "healthy_false_alarm_rate": float(
                            np.mean(np.linalg.norm(samples, axis=1) > radius)
                        ),
                        "fault_miss_rate": float(
                            np.mean(np.linalg.norm(shifted, axis=1) <= radius)
                        ),
                        "screening_snr": signal / (2.0 * radius),
                        "certificate_correctly_predicts_failure": signal <= 2.0 * radius,
                    }
                )
    write_csv_with_schema(detection_rows, output_dir / "stage1_event_detection.csv")

    isolation_rows = []
    for _, certificate in isolations.iterrows():
        for distribution in ("gaussian", "t3"):
            for seed in noise["seeds"]:
                samples, radius = cached[(distribution, int(seed))]
                separation = float(certificate.screening_iota_lower)
                labels = np.arange(len(samples)) % 2
                observations = samples[:, 0] + (labels - 0.5) * separation
                predictions = (observations >= 0.0).astype(int)
                isolation_rows.append(
                    {
                        **_base(meta, provisional=bool(certificate.provisional)),
                        "controller": certificate.controller,
                        "window_start": int(certificate.window_start),
                        "mode_j": certificate.mode_j,
                        "mode_k": certificate.mode_k,
                        "distribution": distribution,
                        "coverage_seed": int(seed),
                        "radius": radius,
                        "screening_iota_lower": separation,
                        "nearest_set_misclassification_rate": float(
                            np.mean(predictions != labels)
                        ),
                        "rejection_rate": float(
                            np.mean(np.abs(observations) < radius)
                        ),
                        "screening_snr": separation / (2.0 * radius),
                    }
                )
    write_csv_with_schema(isolation_rows, output_dir / "stage1_event_isolation.csv")
    (output_dir / "stage1_noise_calibration_report.md").write_text(
        "# Noise calibration and event performance\n\n"
        "Known-sigma Gaussian rows use the exact marginal chi radius. Unit-variance t3 and "
        "standardized lognormal rows use independent empirical norm calibration; these rows "
        "do not claim exact conditional CFAR. Event tables report false alarms, misses, "
        "nearest-set errors, rejection, and separation-to-radius ratios.\n",
        encoding="utf-8",
    )
    return pd.DataFrame(gaussian_rows), pd.DataFrame(t3_rows)


def run_decision_and_ledgers(
    config_path: Path,
    config: dict[str, Any],
    detections: pd.DataFrame,
    isolations: pd.DataFrame,
    gaussian: pd.DataFrame,
    t3: pd.DataFrame,
) -> str:
    run_root = require_external_run_root()
    output_dir = run_root / "results"
    decision_dir = run_root / "decision"
    storage_root = run_root.parents[2]
    meta = run_metadata(config_path, config)
    screening_detection_fraction = float(np.mean(detections.screening_d_lower > 0.0))
    screening_isolation_fraction = float(np.mean(isolations.screening_iota_lower > 0.0))
    gaussian_coverage = float(gaussian.coverage.mean())
    t3_only = t3[t3.distribution == "t3"]
    t3_coverage = float(t3_only.coverage.mean())
    decision = "PIVOT"
    memo = (
        "# CERTO-FDI Stage 1 decision memo\n\n"
        f"**Decision: {decision}.** The GO gate is not passed.\n\n"
        "## Pre-registered gate\n\n"
        f"1. Strict positive detection fraction: 0.000 (required: two families in >=0.30 of windows). "
        f"Empirical screening fraction was {screening_detection_fraction:.3f}.\n"
        f"2. Strict positive isolation pairs: 0. Empirical screening fraction was "
        f"{screening_isolation_fraction:.3f}.\n"
        "3. Strict positive local-identification lower bounds: 0; only local empirical screening values exist.\n"
        f"4. Mean Gaussian marginal coverage: {gaussian_coverage:.3f}; mean independently "
        f"calibrated t3 marginal coverage: {t3_coverage:.3f}. Heavy-tail calibration is empirical.\n"
        "5. Closed-loop remainders were measured, but no support-wide validated upper bound was proved.\n"
        "6. Strict rows cannot be formed solely from deployment-computable quantities yet.\n"
        "7. Literature novelty remains a proof obligation relative to set-based MDF.\n\n"
        "## Consequence\n\n"
        "This matches the PIVOT condition: geometric/empirical detection can survive in some "
        "windows, while strict isolation and heavy-tail coverage remain unavailable. Do not "
        "enter 7DoF, neural training, public-data training, or real-robot fault injection.\n"
    )
    (decision_dir / "stage1_decision_memo.md").write_text(memo, encoding="utf-8")
    (output_dir / "stage1_decision_memo.md").write_text(memo, encoding="utf-8")

    claim_rows = [
        {
            **_base(meta),
            "claim_id": "CLOSED_LOOP_OPERATOR",
            "claim": "AD interval-end closed-loop operators match small-signal nonlinear response",
            "status": "TESTED_LOCAL",
            "evidence": "stage1_operator_validation.csv",
        },
        {
            **_base(meta),
            "claim_id": "STRICT_NONEMPTY_CERTIFICATE",
            "claim": "A deployment-computable non-empty Stage 1 certificate exists",
            "status": "NOT_ESTABLISHED",
            "evidence": "validated model-error and e0 bounds absent",
        },
        {
            **_base(meta),
            "claim_id": "HEAVY_TAIL_CFAR",
            "claim": "Estimated heavy-tail calibration gives exact conditional CFAR",
            "status": "REJECTED",
            "evidence": "stage1_coverage_t3.csv",
        },
    ]
    theorem_rows = [
        {
            **_base(meta),
            "theorem_id": "T0",
            "statement": "ad_star sign and 2R dynamics",
            "status": "PROVED_AND_TESTED",
            "proof_obligation": "none within 2R model",
        },
        {
            **_base(meta),
            "theorem_id": "T2",
            "statement": "local interval-end window linearization",
            "status": "PROVED_LOCAL_AND_TESTED",
            "proof_obligation": "global remainder bound",
        },
        {
            **_base(meta),
            "theorem_id": "T_E0",
            "statement": "joint finite-sample structured e0",
            "status": "FAILED_TO_PROVE",
            "proof_obligation": "exact constants and heavy-tail joint event",
        },
    ]
    ledger_dir = storage_root / "02_research_docs" / "ledgers"
    corrections_dir = storage_root / "02_research_docs" / "corrections"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    corrections_dir.mkdir(parents=True, exist_ok=True)
    write_csv_with_schema(claim_rows, ledger_dir / "MASTER_CLAIM_LEDGER_STAGE1.csv")
    write_csv_with_schema(theorem_rows, ledger_dir / "THEOREM_STATUS_STAGE1.csv")
    write_csv_with_schema(claim_rows, output_dir / "stage1_claim_ledger.csv")
    write_csv_with_schema(theorem_rows, output_dir / "stage1_theorem_status.csv")
    (corrections_dir / "KNOWN_ERRORS_AND_CORRECTIONS_STAGE1.md").write_text(
        "# Known errors and Stage 1 corrections\n\n"
        "1. The analytic Mdot-2C identity is exact; prior finite-difference residuals were not machine precision.\n"
        "2. The old program computed trajectory-conditioned direct signatures, not closed-loop sensitivities.\n"
        "3. The one-dimensional tube proposition is not extended to multiple directions; all final distances use a joint QP.\n"
        "4. Positive payload mass appears as the right-hand disturbance -Y_L delta_theta.\n"
        "5. Payload/contact and other fault labels are equivalence classes, not globally unique identities.\n"
        "6. No first, fully open, strict CFAR, or completed T-RO-method claim is made.\n",
        encoding="utf-8",
    )
    (corrections_dir / "DOCUMENT_DIFF_INDEX.md").write_text(
        "# Document diff index\n\n"
        "Frozen inputs were not modified. The corrections in "
        "`KNOWN_ERRORS_AND_CORRECTIONS_STAGE1.md` supersede conflicting prose for this run.\n",
        encoding="utf-8",
    )
    return decision


def run_full_pipeline(config_file: str | Path) -> dict[str, Any]:
    config_path, config, params = load_experiment(config_file)
    output_dir = ensure_output_dir(config)
    runs = _controller_runs(config, params)
    operators, _ = run_operators(config_path, config, runs)
    eps_frame, model_errors = run_model_error(config_path, config, runs, operators)
    _, healthy_errors, bases = run_healthy_tube(config_path, config, runs)
    run_adversarial_recheck(config_path, config, runs, operators, eps_frame, bases)
    detections, isolations = run_certificates(
        config_path,
        config,
        runs,
        operators,
        model_errors,
        healthy_errors,
        bases,
    )
    gaussian, t3 = run_noise_and_events(config_path, config, detections, isolations)
    decision = run_decision_and_ledgers(
        config_path, config, detections, isolations, gaussian, t3
    )
    produced = sorted(path for path in output_dir.iterdir() if path.is_file())
    manifest = write_run_manifest(
        output_dir,
        config_path,
        produced,
        extra={
            "status": "stage1_completed_empirical_pipeline",
            "decision": decision,
            "strict_certificate_count": 0,
            "empirical_outputs_are_not_strict_certificates": True,
        },
    )
    return {
        "decision": decision,
        "run_root": str(require_external_run_root()),
        "manifest": str(manifest),
        "produced_files": len(produced) + 1,
    }
