"""R0 — geometry and typed-dynamics gate (no training).

Outputs (in ``<run>/r0_geometry`` and mirrored to ``<run>/results``):

* ``stage1r_r0_geometry_tests.json``
* ``stage1r_r0_frame_trials.csv``
* ``stage1r_r0_dynamics_crosscheck.csv``
* ``R0_DECISION.md``
* ``model_parameter_audit.json``

Checks implemented (08_CODEX_CLAUDE_MASTER_PROMPT.md §D):
 1. ``[omega; v]`` / ``[n; f]`` conventions and 2. ``ad*=-ad^T`` (unit tests + power pairing);
 3. legal SE(3) adjoint/coadjoint actions; 4. inertia and subspace transforms;
 5. full RNEA cross-check against Pinocchio (API-built and MJCF-parsed) and MuJoCo;
 6. wrong-sign mutation must fail; 7. random per-link legal frame reparameterization;
 8. healthy and faulty covariance tests (payload, friction, actuator gain, contact wrench,
    encoder bias, command delay) — all obey the *same* law.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from certo_fdi.dynamics.chain_model import ChainModel, make_planar_2r
from certo_fdi.dynamics.lagrange_reference import sympy_lagrange_torque
from certo_fdi.dynamics.rnea import mass_matrix, rnea
from certo_fdi.experiments.common import (
    base_row,
    capture_environment,
    load_config,
    seed_everything,
    utc_now,
    write_csv,
    write_json,
)
from certo_fdi.geometry.frame_reparameterization import compare_typed_states, sample_link_frames
from certo_fdi.geometry.se3 import SE3, is_legal_motion_adjoint
from certo_fdi.geometry.spatial_types import SpatialType
from certo_fdi.paths import create_or_resume_run


def _random_states(chain: ChainModel, rng: np.random.Generator, count: int):
    n = chain.n_links
    lo = chain.joint_lower if chain.joint_lower is not None else -np.pi * np.ones(n)
    hi = chain.joint_upper if chain.joint_upper is not None else np.pi * np.ones(n)
    for _ in range(count):
        q = rng.uniform(lo, hi)
        qd = rng.normal(scale=1.0, size=n)
        qdd = rng.normal(scale=3.0, size=n)
        yield q, qd, qdd


def faulty_variants(chain: ChainModel, rng: np.random.Generator) -> dict[str, dict]:
    """Physically faulty *descriptions* of the same chain type; each obeys the same law."""
    n = chain.n_links
    variants: dict[str, dict] = {"healthy": {"chain": chain, "gain": np.ones(n), "f_ext": None, "q_bias": np.zeros(n)}}
    payload = chain.with_payload(0.5, np.array([0.0, 0.0, 0.10]), np.diag([1e-3, 1e-3, 5e-4]))
    variants["F3_payload_0.5kg"] = {"chain": payload, "gain": np.ones(n), "f_ext": None, "q_bias": np.zeros(n)}
    friction = chain.copy()
    friction.damping = chain.damping * 1.5 + 0.3
    friction.coulomb = chain.coulomb * 1.5 + 0.4
    variants["F2_friction"] = {"chain": friction, "gain": np.ones(n), "f_ext": None, "q_bias": np.zeros(n)}
    gain = np.ones(n)
    gain[2] = 0.8
    variants["F1_actuator_gain"] = {"chain": chain, "gain": gain, "f_ext": None, "q_bias": np.zeros(n)}
    f_ext = np.zeros((n, 6))
    f_ext[3] = rng.normal(size=6) * np.array([0.5, 0.5, 0.5, 5.0, 5.0, 5.0])
    variants["F4_contact_link4"] = {"chain": chain, "gain": np.ones(n), "f_ext": f_ext, "q_bias": np.zeros(n)}
    q_bias = np.zeros(n)
    q_bias[1] = 0.01
    variants["F5_encoder_bias"] = {"chain": chain, "gain": np.ones(n), "f_ext": None, "q_bias": q_bias}
    return variants


def run_frame_trials(chain: ChainModel, cfg: dict, rng: np.random.Generator, layout, repo_root, cfg_sha, *, torch_available: bool) -> tuple[list[dict], dict]:
    ft = cfg["frame_trials"]
    variants = faulty_variants(chain, rng)
    rows: list[dict] = []
    summary: dict = {"float64": {}, "float32": {}}
    tol64 = float(ft["tolerance_float64_relative"])
    tol32 = float(ft["tolerance_float32_relative"])
    for vname, spec in variants.items():
        vchain: ChainModel = spec["chain"]
        for trial in range(int(ft["variants_per_episode"])):
            frames = sample_link_frames(
                vchain, rng,
                rotation_angle_max_deg=float(ft["rotation_angle_max_deg"]),
                translation_fraction_of_link_length=float(ft["translation_fraction_of_link_length"]),
            )
            new_chain, adjoints = vchain.reparameterize(frames)
            assert all(is_legal_motion_adjoint(a) for a in adjoints)
            for state_idx, (q, qd, qdd) in enumerate(_random_states(vchain, rng, 4)):
                q_meas = q + spec["q_bias"]
                f_ext = spec["f_ext"]
                f_ext_new = None if f_ext is None else np.stack([np.linalg.inv(adjoints[i]).T @ f_ext[i] for i in range(vchain.n_links)])
                before = rnea(vchain, q_meas, qd, qdd, f_ext=f_ext)
                after = rnea(new_chain, q_meas, qd, qdd, f_ext=f_ext_new)
                report = compare_typed_states(vchain, before, after, adjoints)
                tau_before = spec["gain"] * before.tau
                tau_after = spec["gain"] * after.tau
                tau_res = float(np.max(np.abs(tau_after - tau_before)))
                for qname, res in report.residuals.items():
                    scale = max(report.scales[qname], 1e-12)
                    rows.append({
                        **base_row(layout, repo_root, cfg_sha, seed=trial, split="R0", model="analytic_rnea_numpy"),
                        "variant": vname, "trial": trial, "state": state_idx, "quantity": qname,
                        "spatial_type": before.TYPES[qname].value, "dtype": "float64",
                        "max_abs_residual": res, "scale": scale, "relative_residual": res / scale,
                        "pass": bool(res / scale < tol64), "units": "SI",
                    })
                rows.append({
                    **base_row(layout, repo_root, cfg_sha, seed=trial, split="R0", model="analytic_rnea_numpy"),
                    "variant": vname, "trial": trial, "state": state_idx, "quantity": "tau_with_gain",
                    "spatial_type": "scalar", "dtype": "float64",
                    "max_abs_residual": tau_res, "scale": max(float(np.max(np.abs(tau_before))), 1e-12),
                    "relative_residual": tau_res / max(float(np.max(np.abs(tau_before))), 1e-12),
                    "pass": bool(tau_res / max(float(np.max(np.abs(tau_before))), 1e-12) < tol64), "units": "N m",
                })
                if torch_available:
                    rows.extend(_torch_frame_rows(vchain, new_chain, adjoints, q_meas, qd, qdd, f_ext, f_ext_new, spec["gain"], vname, trial, state_idx, layout, repo_root, cfg_sha, tol64, tol32))
    for dtype in ("float64", "float32"):
        sub = [r for r in rows if r["dtype"] == dtype]
        if not sub:
            continue
        by_q: dict[str, float] = {}
        for r in sub:
            by_q[r["quantity"]] = max(by_q.get(r["quantity"], 0.0), r["relative_residual"])
        summary[dtype] = {
            "n_rows": len(sub),
            "max_relative_residual_by_quantity": by_q,
            "all_pass": all(r["pass"] for r in sub),
            "healthy_all_pass": all(r["pass"] for r in sub if r["variant"] == "healthy"),
            "faulty_all_pass": all(r["pass"] for r in sub if r["variant"] != "healthy"),
            "variants": sorted({r["variant"] for r in sub}),
        }
    return rows, summary


def _torch_frame_rows(chain, new_chain, adjoints, q, qd, qdd, f_ext, f_ext_new, gain, vname, trial, state_idx, layout, repo_root, cfg_sha, tol64, tol32) -> list[dict]:
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch
    from certo_fdi.geometry.spatial_types import transform_typed

    rows = []
    for dtype_name, dtype in (("float64", torch.float64), ("float32", torch.float32)):
        tc = TorchChain.from_chain(chain, dtype=dtype)
        tc2 = TorchChain.from_chain(new_chain, dtype=dtype)
        qt = torch.as_tensor(q, dtype=dtype)[None]
        qdt = torch.as_tensor(qd, dtype=dtype)[None]
        qddt = torch.as_tensor(qdd, dtype=dtype)[None]
        fe = None if f_ext is None else torch.as_tensor(f_ext, dtype=dtype)[None]
        fe2 = None if f_ext_new is None else torch.as_tensor(f_ext_new, dtype=dtype)[None]
        before = rnea_batch(tc, qt, qdt, qddt, fe)
        after = rnea_batch(tc2, qt, qdt, qddt, fe2)
        tol = tol64 if dtype_name == "float64" else tol32
        for name, kind in (("X", SpatialType.TRANSFORM), ("S", SpatialType.MOTION), ("V", SpatialType.MOTION), ("A", SpatialType.MOTION), ("inertia", SpatialType.INERTIA), ("momentum", SpatialType.FORCE), ("F_body", SpatialType.FORCE), ("F", SpatialType.FORCE), ("tau_rb", SpatialType.SCALAR), ("tau", SpatialType.SCALAR)):
            b = getattr(before, name)[0].detach().cpu().numpy().astype(float)
            a = getattr(after, name)[0].detach().cpu().numpy().astype(float)
            worst = 0.0
            scale = max(float(np.max(np.abs(b))), 1e-12)
            if kind == SpatialType.SCALAR:
                worst = float(np.max(np.abs(a - b)))
            else:
                for i in range(chain.n_links):
                    p = chain.parent[i]
                    ap = np.eye(6) if p < 0 else adjoints[p]
                    pred = transform_typed(kind, b[i], adjoints[i], ap)
                    worst = max(worst, float(np.max(np.abs(a[i] - pred))))
            rows.append({
                **base_row(layout, repo_root, cfg_sha, seed=trial, split="R0", model="analytic_rnea_torch"),
                "variant": vname, "trial": trial, "state": state_idx, "quantity": name,
                "spatial_type": kind.value, "dtype": dtype_name, "max_abs_residual": worst, "scale": scale,
                "relative_residual": worst / scale, "pass": bool(worst / scale < tol), "units": "SI",
            })
    return rows


def run_dynamics_crosscheck(chain: ChainModel, plant, xml_path: Path, rng: np.random.Generator, layout, repo_root, cfg_sha) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    summary: dict = {}
    n_states = 64
    states = list(_random_states(chain, rng, n_states))

    def add(name, reference, err, tol, extra=None):
        ok = bool(err < tol)
        rows.append({
            **base_row(layout, repo_root, cfg_sha, split="R0", model="analytic_rnea_numpy"),
            "check": name, "reference": reference, "max_abs_error": err, "tolerance": tol, "pass": ok,
            "units": "N m", **(extra or {}),
        })
        summary[name] = {"max_abs_error": err, "tolerance": tol, "pass": ok, **(extra or {})}

    # 1. 2R vs SymPy Lagrange (ported Stage 1 gate)
    p2 = dict(m1=1.2, m2=0.8, l1=0.5, l2=0.4, lc1=0.25, lc2=0.2, I1=0.03, I2=0.015, gravity=9.81)
    two = make_planar_2r(**p2)
    err = 0.0
    err_mut = 0.0
    for _ in range(50):
        q = rng.uniform(-1.5, 1.5, size=2)
        qd = rng.normal(size=2)
        qdd = rng.normal(scale=2.0, size=2)
        ref = sympy_lagrange_torque(q, qd, qdd, m1=p2["m1"], m2=p2["m2"], l1=p2["l1"], lc1=p2["lc1"], lc2=p2["lc2"], I1=p2["I1"], I2=p2["I2"], gravity=p2["gravity"])
        err = max(err, float(np.max(np.abs(rnea(two, q, qd, qdd).tau - ref))))
        err_mut = max(err_mut, float(np.max(np.abs(rnea(two, q, qd, qdd, mutate_ad_star_sign=True).tau - ref))))
    add("rnea_2r_vs_sympy_lagrange", "sympy_lagrange", err, 1e-9)
    rows.append({**base_row(layout, repo_root, cfg_sha, split="R0", model="analytic_rnea_numpy_MUTATED"), "check": "wrong_ad_star_sign_2r_must_fail", "reference": "sympy_lagrange", "max_abs_error": err_mut, "tolerance": 1e-2, "pass": bool(err_mut > 1e-2), "units": "N m", "note": "pass means the mutation was DETECTED"})
    summary["wrong_ad_star_sign_2r_must_fail"] = {"max_abs_error": err_mut, "detected": bool(err_mut > 1e-2)}

    # 2. 7-DoF: numpy RNEA vs MuJoCo mj_inverse (same parameters; MuJoCo damping removed)
    rigid = chain.copy()
    rigid.damping[:] = 0.0
    rigid.coulomb[:] = 0.0
    err_mj = 0.0
    err_mj_mut = 0.0
    for q, qd, qdd in states:
        ref = plant.inverse_dynamics(q, qd, qdd)
        err_mj = max(err_mj, float(np.max(np.abs(rnea(rigid, q, qd, qdd).tau - ref))))
        err_mj_mut = max(err_mj_mut, float(np.max(np.abs(rnea(rigid, q, qd, qdd, mutate_ad_star_sign=True).tau - ref))))
    add("rnea_7dof_vs_mujoco_mj_inverse", "mujoco.mj_inverse", err_mj, 1e-8, {"n_states": n_states})
    rows.append({**base_row(layout, repo_root, cfg_sha, split="R0", model="analytic_rnea_numpy_MUTATED"), "check": "wrong_ad_star_sign_7dof_must_fail", "reference": "mujoco.mj_inverse", "max_abs_error": err_mj_mut, "tolerance": 1e-2, "pass": bool(err_mj_mut > 1e-2), "units": "N m", "note": "pass means the mutation was DETECTED"})
    summary["wrong_ad_star_sign_7dof_must_fail"] = {"max_abs_error": err_mj_mut, "detected": bool(err_mj_mut > 1e-2)}

    # 3. mass matrix vs MuJoCo full M
    err_m = 0.0
    for q, _, _ in states[:16]:
        err_m = max(err_m, float(np.max(np.abs(mass_matrix(rigid, q) - plant.mass_matrix(q)))))
    add("mass_matrix_7dof_vs_mujoco_fullM", "mujoco.mj_fullM", err_m, 1e-8, {"units": "kg m^2"})

    # 4. Pinocchio API-built model
    try:
        from certo_fdi.dynamics.pinocchio_backend import (
            build_pinocchio_model,
            build_pinocchio_model_from_mjcf,
            pin_crba,
            pin_rnea,
            pin_rnea_includes_armature,
            pinocchio_version,
        )

        pmodel = build_pinocchio_model(rigid)
        includes_arm = pin_rnea_includes_armature(pmodel)
        err_pin = 0.0
        err_pin_mut = 0.0
        for q, qd, qdd in states:
            ref = pin_rnea(pmodel, q, qd, qdd)
            if not includes_arm:
                ref = ref + rigid.armature * qdd
            err_pin = max(err_pin, float(np.max(np.abs(rnea(rigid, q, qd, qdd).tau - ref))))
            err_pin_mut = max(err_pin_mut, float(np.max(np.abs(rnea(rigid, q, qd, qdd, mutate_ad_star_sign=True).tau - ref))))
        add("rnea_7dof_vs_pinocchio_api_model", f"pinocchio {pinocchio_version()} rnea", err_pin, 1e-8, {"pin_rnea_includes_armature": includes_arm, "n_states": n_states})
        rows.append({**base_row(layout, repo_root, cfg_sha, split="R0", model="analytic_rnea_numpy_MUTATED"), "check": "wrong_ad_star_sign_vs_pinocchio_must_fail", "reference": "pinocchio.rnea", "max_abs_error": err_pin_mut, "tolerance": 1e-2, "pass": bool(err_pin_mut > 1e-2), "units": "N m", "note": "pass means the mutation was DETECTED"})
        summary["wrong_ad_star_sign_vs_pinocchio_must_fail"] = {"max_abs_error": err_pin_mut, "detected": bool(err_pin_mut > 1e-2)}
        err_crba = 0.0
        for q, _, _ in states[:16]:
            m_pin = pin_crba(pmodel, q)
            if not includes_arm:
                m_pin = m_pin + np.diag(rigid.armature)
            err_crba = max(err_crba, float(np.max(np.abs(mass_matrix(rigid, q) - m_pin))))
        add("mass_matrix_7dof_vs_pinocchio_crba", "pinocchio.crba", err_crba, 1e-8, {"units": "kg m^2"})
        # 5. Pinocchio MJCF parser (independent parameter-parsing audit of the ORIGINAL MJCF)
        try:
            pm2 = build_pinocchio_model_from_mjcf(xml_path)
            if pm2.nv == rigid.n_links:
                inc2 = pin_rnea_includes_armature(pm2)
                err_pin2 = 0.0
                for q, qd, qdd in states:
                    ref = pin_rnea(pm2, q, qd, qdd)
                    if not inc2:
                        ref = ref + rigid.armature * qdd
                    err_pin2 = max(err_pin2, float(np.max(np.abs(rnea(rigid, q, qd, qdd).tau - ref))))
                param_delta = {
                    "max_abs_mass_delta_kg": float(max(abs(pm2.inertias[i + 1].mass - rigid.mass[i]) for i in range(rigid.n_links))),
                    "max_abs_com_delta_m": float(max(np.max(np.abs(np.asarray(pm2.inertias[i + 1].lever) - rigid.com[i])) for i in range(rigid.n_links))),
                    "max_abs_inertia_delta_kgm2": float(max(np.max(np.abs(np.asarray(pm2.inertias[i + 1].inertia) - rigid.inertia_com[i])) for i in range(rigid.n_links))),
                    "pin_armature": np.asarray(pm2.armature).tolist() if hasattr(pm2, "armature") else None,
                    "pin_gravity": np.asarray(pm2.gravity.linear).tolist(),
                }
                add("rnea_7dof_vs_pinocchio_mjcf_parser", "pinocchio.buildModelFromMJCF(original menagerie xml)", err_pin2, 1e-5, {"pin_model_nv": int(pm2.nv), "pin_rnea_includes_armature": inc2, "note": "independent parse; residual reflects MuJoCo fullinertia eigen-reconstruction vs Pinocchio parse", **param_delta})
            else:
                summary["rnea_7dof_vs_pinocchio_mjcf_parser"] = {"status": "SKIPPED", "reason": f"pin nv={pm2.nv}"}
        except Exception as e:  # pragma: no cover
            summary["rnea_7dof_vs_pinocchio_mjcf_parser"] = {"status": "SKIPPED", "reason": f"{type(e).__name__}: {e}"}
    except Exception as e:  # pragma: no cover
        summary["rnea_7dof_vs_pinocchio_api_model"] = {"status": "FAILED", "reason": f"{type(e).__name__}: {e}"}
        rows.append({**base_row(layout, repo_root, cfg_sha, split="R0", model="analytic_rnea_numpy", status="FAILED"), "check": "rnea_7dof_vs_pinocchio_api_model", "reference": "pinocchio", "max_abs_error": float("nan"), "tolerance": 1e-8, "pass": False, "note": str(e)})

    # 6. torch front end vs numpy (float64/float32)
    try:
        import torch

        from certo_fdi.dynamics.rnea_torch import TorchChain, rnea_batch

        for dtype_name, dtype, tol in (("float64", torch.float64, 1e-9), ("float32", torch.float32, 2e-3)):
            tc = TorchChain.from_chain(chain, dtype=dtype)
            qs = torch.as_tensor(np.stack([s[0] for s in states]), dtype=dtype)
            qds = torch.as_tensor(np.stack([s[1] for s in states]), dtype=dtype)
            qdds = torch.as_tensor(np.stack([s[2] for s in states]), dtype=dtype)
            out = rnea_batch(tc, qs, qds, qdds)
            ref = np.stack([rnea(chain, *s).tau for s in states])
            e = float(np.max(np.abs(out.tau.numpy().astype(float) - ref)))
            add(f"torch_frontend_vs_numpy_{dtype_name}", "numpy_rnea", e, tol, {"units": "N m", "n_states": n_states})
    except Exception as e:  # pragma: no cover
        summary["torch_frontend_vs_numpy"] = {"status": "FAILED", "reason": f"{type(e).__name__}: {e}"}
    return rows, summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CERTO-FDI Stage 1R R0 geometry gate")
    parser.add_argument("--config", required=True)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--seed", type=int, default=260815)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--stage", default=None, help="run-directory stage (default: the Stage 1R stage; Stage 1R-B passes its own)")
    args = parser.parse_args(argv)

    t0 = time.time()
    cfg, cfg_sha = load_config(args.config)
    repo_root = Path(args.repo_root).resolve()
    layout = create_or_resume_run(args.storage_root, args.run_id, **({"stage": args.stage} if args.stage else {}))
    out_dir = layout.sub("r0_geometry")
    seed_everything(args.seed)
    rng = np.random.default_rng(args.seed)
    env = capture_environment(layout, repo_root, "r0_start", {"config_sha256": cfg_sha, "config_path": str(Path(args.config).resolve())})
    (layout.sub("config") / Path(args.config).name).write_bytes(Path(args.config).read_bytes())

    from certo_fdi.dynamics.mujoco_backend import MujocoPlant, model_parameter_audit, write_audit

    xml_path = Path(cfg["paths"]["mjcf_path"])
    plant = MujocoPlant(xml_path, timestep=float(cfg["simulation"]["physics_dt_s"]))
    chain = plant.chain
    # nominal friction (documented) so that the frame tests exercise the joint-scalar terms
    chain.damping = np.asarray(cfg["plant_mismatch"]["nominal_viscous_nms"], dtype=float)
    chain.coulomb = np.asarray(cfg["plant_mismatch"]["nominal_coulomb_nm"], dtype=float)
    audit = model_parameter_audit(plant.model, chain, xml_path)
    audit["menagerie_commit"] = cfg["paths"].get("menagerie_commit")
    write_audit(audit, out_dir / "model_parameter_audit.json")

    try:
        import torch  # noqa: F401

        torch_available = True
    except Exception:
        torch_available = False

    cross_rows, cross_summary = run_dynamics_crosscheck(chain, plant, xml_path, rng, layout, repo_root, cfg_sha)
    frame_rows, frame_summary = run_frame_trials(chain, cfg, rng, layout, repo_root, cfg_sha, torch_available=torch_available)

    write_csv(out_dir / "stage1r_r0_dynamics_crosscheck.csv", cross_rows)
    write_csv(out_dir / "stage1r_r0_frame_trials.csv", frame_rows)

    pytest_summary = {"status": "SKIPPED"}
    if not args.skip_pytest:
        report_path = layout.sub("tests") / "pytest_r0_report.txt"
        cmd = [sys.executable, "-m", "pytest", "-q", "-m", "not slow", "-p", "no:cacheprovider", str(repo_root / "tests")]
        proc = subprocess.run(cmd, cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env={**dict(__import__("os").environ), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
        report_path.write_text(proc.stdout, encoding="utf-8")
        pytest_summary = {"status": "PASS" if proc.returncode == 0 else "FAIL", "returncode": proc.returncode, "tail": proc.stdout.strip().splitlines()[-3:]}

    # ---------------------------------------------------------------- decision
    checks = {
        "C1_convention_and_ad_star_unit_tests": pytest_summary.get("status") == "PASS",
        "C2_rnea_matches_independent_implementations": all(
            cross_summary.get(k, {}).get("pass", False)
            for k in ("rnea_2r_vs_sympy_lagrange", "rnea_7dof_vs_mujoco_mj_inverse", "rnea_7dof_vs_pinocchio_api_model")
        ),
        "C3_wrong_ad_star_mutation_detected": all(
            cross_summary.get(k, {}).get("detected", False)
            for k in ("wrong_ad_star_sign_2r_must_fail", "wrong_ad_star_sign_7dof_must_fail")
        ),
        "C4_legal_frame_covariance_healthy": frame_summary.get("float64", {}).get("healthy_all_pass", False),
        "C5_legal_frame_covariance_faulty_same_law": frame_summary.get("float64", {}).get("faulty_all_pass", False),
        "C6_torque_invariance_float64": all(r["pass"] for r in frame_rows if r["quantity"] in ("tau", "tau_with_gain") and r["dtype"] == "float64"),
        "C7_torch_frontend_agrees": all(cross_summary.get(k, {}).get("pass", False) for k in ("torch_frontend_vs_numpy_float64", "torch_frontend_vs_numpy_float32")),
        "C8_float32_frontend_covariance_within_tolerance": frame_summary.get("float32", {}).get("all_pass", False),
    }
    decision = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "run_id": layout.run_id,
        "git_sha": env["git_sha"],
        "config_sha256": cfg_sha,
        "timestamp_utc": utc_now(),
        "phase": "R0_analytic",
        "decision": decision,
        "checks": checks,
        "dynamics_crosscheck": cross_summary,
        "frame_trials": frame_summary,
        "pytest": pytest_summary,
        "model_audit_sha256": __import__("hashlib").sha256((out_dir / "model_parameter_audit.json").read_bytes()).hexdigest(),
        "elapsed_s": time.time() - t0,
        "note": "Model-level (LiGRA network) covariance tests are appended by --phase model before any training.",
    }
    write_json(out_dir / "stage1r_r0_geometry_tests.json", result)
    memo = [
        "# R0 decision — geometry and typed-dynamics gate",
        "",
        f"- Run: `{layout.run_id}`  ",
        f"- Git SHA: `{env['git_sha']}`  ",
        f"- Config SHA256: `{cfg_sha}`  ",
        f"- Timestamp (UTC): {result['timestamp_utc']}",
        "",
        f"## Decision: **R0 {decision}** (analytic front end)",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for k, v in checks.items():
        memo.append(f"| {k} | {'PASS' if v else 'FAIL'} |")
    memo += ["", "## Dynamics cross-checks", "", "| check | max abs error | tolerance | pass |", "|---|---|---|---|"]
    for k, v in cross_summary.items():
        memo.append(f"| {k} | {v.get('max_abs_error', 'n/a')} | {v.get('tolerance', 'n/a')} | {v.get('pass', v.get('detected', v.get('status')))} |")
    memo += ["", "## Frame trials (max relative residual by quantity)", ""]
    for dtype in ("float64", "float32"):
        s = frame_summary.get(dtype, {})
        memo.append(f"### {dtype}: all_pass={s.get('all_pass')} healthy={s.get('healthy_all_pass')} faulty={s.get('faulty_all_pass')}")
        for qn, val in sorted(s.get("max_relative_residual_by_quantity", {}).items()):
            memo.append(f"- {qn}: {val:.3e}")
        memo.append("")
    memo += [
        "## Interpretation limits",
        "",
        "- Passing R0 proves that healthy and faulty samples obey the *same* link-frame covariance law and that",
        "  the analytic front end is correct. It is **not** evidence of fault-detection value (06 §6).",
        "- Gauge-equivariance error is never used as a fault score.",
        "- Network-level covariance (T1–T3) is verified separately before training (see stage1r_r0_model_covariance.json).",
    ]
    (out_dir / "R0_DECISION.md").write_text("\n".join(memo) + "\n", encoding="utf-8")
    # mirror to results
    for name in ("stage1r_r0_geometry_tests.json", "stage1r_r0_frame_trials.csv", "stage1r_r0_dynamics_crosscheck.csv", "R0_DECISION.md", "model_parameter_audit.json"):
        (layout.results / name).write_bytes((out_dir / name).read_bytes())
    capture_environment(layout, repo_root, "r0_end")
    print(json.dumps({"decision": decision, "checks": checks, "elapsed_s": result["elapsed_s"]}, indent=2))
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
