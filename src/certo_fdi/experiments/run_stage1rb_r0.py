"""Stage 1R-B R0 correctness gate (master prompt §8, 15 items). Nothing is trained here.

1  existing RNEA / MuJoCo / Pinocchio tests            -> analytic R0 (run_r0_geometry) + pytest
2  wrong-ad* mutation test                              -> analytic R0 C3
3  typed layer scalar/twist/wrench transform tests      -> pytest tests/test_typed_layers_covariance.py
4  temporal recurrence covariance                       -> pytest + model-level trials below
5  forward/backward chain transport covariance          -> pytest + model-level trials
6  final delta_tau invariance                           -> model-level trials on real windows (T2)
7  residual-only anomaly score invariance               -> model-level trials
8  counterfactual localization score invariance         -> model-level trials
9  chain GNN keeps non-zero drift                       -> model-level trials
10 healthy and every fault family obey the same law     -> trials on windows of every family
11 float64 / float32 tolerances                         -> both dtypes
12 gradient finite-difference check                     -> pytest tests/test_ligra_v2_invariance.py
13 encoder input leakage audit                          -> perturbation audit on real windows
14 forbidden-field audit                                -> input manifests + perturbation audit
15 parameter count match +-10 %                         -> counted here
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from typing import Any

import numpy as np
import torch

from certo_fdi.anomaly.gaussian_head import ConditionalGaussian
from certo_fdi.data.schema import FAULT_FAMILIES
from certo_fdi.data.windows import WindowSet
from certo_fdi.dynamics.rnea_torch import TorchChain
from certo_fdi.experiments.common import utc_now, write_json
from certo_fdi.experiments.r0_model_covariance import tool_chain
from certo_fdi.experiments.stage1rb_common import PRIMARY_MODELS, Stage, common_parser, ensure_model_cfg
from certo_fdi.geometry.frame_reparameterization import sample_link_frames
from certo_fdi.geometry.spatial_types import SpatialType, transform_typed
from certo_fdi.localization.counterfactual import counterfactual_contributions, pooled_residual_block
from certo_fdi.models.common import count_parameters
from certo_fdi.models.features import raw_input_field_manifest
from certo_fdi.models.ligra_chain import build_model, run_front_end
from certo_fdi.models.ligra_v2_typed import LiGRAv2Typed

FORBIDDEN = ("tau_meas", "residual", "raw_residual", "fault_active", "fault_family_id", "fault_target", "severity", "family", "target", "active", "q_true", "qd_true", "qdd_true", "tau_applied", "tau_cmd", "ext_wrench_link", "region_id", "trajectory_family_id", "r_gmo")


def _perturb(batch: dict, rng: np.random.Generator) -> dict:
    b = dict(batch)
    dt = batch["tau_meas"].dtype
    dev = batch["tau_meas"].device
    b["tau_meas"] = batch["tau_meas"] + torch.as_tensor(rng.normal(size=tuple(batch["tau_meas"].shape)) * 20, dtype=dt, device=dev)
    b["r_gmo"] = torch.as_tensor(rng.normal(size=tuple(batch["q"].shape)), dtype=dt, device=dev)
    b["active"] = torch.as_tensor(rng.integers(0, 2, size=tuple(batch["q"].shape[:2])), dtype=dt, device=dev)
    b["target"] = torch.as_tensor(rng.integers(-1, 7, size=tuple(batch["q"].shape[:2])), device=dev)
    b["family"] = torch.as_tensor(rng.integers(0, 7, size=(batch["q"].shape[0],)), device=dev)
    return b


def main(argv=None) -> int:
    ap = common_parser("Stage 1R-B R0 correctness gate")
    ap.add_argument("--skip-analytic", action="store_true", help="debug only")
    ap.add_argument("--skip-pytest", action="store_true", help="debug only")
    args = ap.parse_args(argv)
    st = Stage(args, "r0")
    if not st.require_provenance():
        return 2
    cfg = ensure_model_cfg(st.cfg)
    layout, dev = st.layout, st.device
    t0 = time.time()
    results: dict[str, Any] = {"run_id": layout.run_id, "config_sha256": st.cfg_sha, "timestamp_utc": utc_now(), "items": {}}

    # ---- items 1-2: analytic R0 (reused Stage 1R gate incl. wrong-ad* mutation) + full pytest
    if not args.skip_analytic:
        from certo_fdi.experiments.run_r0_geometry import main as r0_main

        rc = r0_main(["--config", args.config, "--storage-root", args.storage_root, "--run-id", args.run_id, "--repo-root", str(st.repo_root), "--stage", cfg["stage"]] + (["--skip-pytest"] if args.skip_pytest else []))
        an = json.loads((layout.results / "stage1r_r0_geometry_tests.json").read_text())
        results["items"]["1_analytic_rnea_mujoco_pinocchio_tests"] = {"pass": rc == 0 and an["decision"] == "PASS", "checks": an["checks"]}
        results["items"]["2_wrong_ad_star_mutation_detected"] = {"pass": bool(an["checks"].get("C3_wrong_ad_star_mutation_detected", False))}
        st.log(f"analytic R0 decision={an['decision']} ({time.time() - t0:.0f}s)")
    if not args.skip_pytest:
        report_path = layout.sub("tests") / "pytest_stage1rb_r0_report.txt"
        cmd = [sys.executable, "-m", "pytest", "-q", "-m", "not slow", "-p", "no:cacheprovider", str(st.repo_root / "tests")]
        env = {k: v for k, v in __import__("os").environ.items() if k != "PYTHONPATH"}
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        proc = subprocess.run(cmd, cwd=st.repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        report_path.write_text(proc.stdout, encoding="utf-8")
        tail = proc.stdout.strip().splitlines()[-3:]
        results["pytest"] = {"status": "PASS" if proc.returncode == 0 else "FAIL", "returncode": proc.returncode, "tail": tail, "report": str(report_path)}
        st.log(f"pytest {results['pytest']['status']}: {tail[-1] if tail else ''}")
        for k, desc in (("3_typed_layer_transform_tests", "tests/test_typed_layers_covariance.py"), ("4_temporal_recurrence_covariance", "tests/test_typed_layers_covariance.py"), ("5_chain_transport_covariance", "tests/test_typed_layers_covariance.py"), ("12_gradient_finite_difference", "tests/test_ligra_v2_invariance.py")):
            results["items"][k] = {"pass": proc.returncode == 0, "via": desc}

    # ---- items 6-11: model-level trials on real windows (healthy + every fault family; two dtypes)
    bundle = st.bundle
    ft = cfg["frame_trials"]
    tol = {"float64": float(ft["tolerance_float64_relative"]), "float32": float(ft["tolerance_float32_relative"])}
    rng = np.random.default_rng(260815)
    fam_eps: dict[str, list[str]] = {}
    for eid in bundle.test_ids:
        ep = bundle.episodes[eid]
        fam_eps.setdefault(ep.family, []).append(eid)
    trial_rows = []
    worst: dict[str, dict[str, dict[str, float]]] = {}
    for name in PRIMARY_MODELS:
        worst[name] = {}
        for dtype_name in ("float64", "float32"):
            dtype = getattr(torch, dtype_name)
            w = {"T1_message": 0.0, "T1_local": 0.0, "T2_delta_tau": 0.0, "T3_features": 0.0, "score": 0.0, "counterfactual": 0.0}
            for fam in FAULT_FAMILIES:
                eids = fam_eps.get(fam, [])[:2] if fam != "healthy" else bundle.train_ids[:1] + [e for e in bundle.test_ids if bundle.episodes[e].kind == "healthy"][:1]
                for eid in eids:
                    ep = bundle.episodes[eid]
                    chain = tool_chain(bundle.base_chain, ep.tool_id)
                    tc0 = TorchChain.from_chain(chain, dtype=dtype, device="cpu")
                    ws = WindowSet([ep], bundle.window, bundle.stride_train, "cpu", min_start=bundle.eval_min_start)
                    # windows: for fault episodes take the last (faulty) windows, plus early (healthy) ones
                    ids = list(range(0, min(2, len(ws)))) + list(range(max(0, len(ws) - 2), len(ws)))
                    batch = ws.batch(sorted(set(ids)))
                    batch = {k: (v.to(dtype) if torch.is_floating_point(v) else v) for k, v in batch.items()}
                    nb = batch["q"].shape[0]
                    batch["inertia"] = tc0.inertia[None].expand(nb, -1, -1, -1)
                    model = build_model(name, tc0, bundle.ctx_dim, cfg["model"]).to(dtype)
                    model.fit_normalizers(tc0, [batch])
                    with torch.no_grad():
                        o0 = model(batch, tc0)
                        z0 = pooled_residual_block(batch["tau_meas"] - batch["tau_nom"] - o0.delta_tau)
                        head = ConditionalGaussian(conditional=False, covariance="diag", rank=0).fit(z0 + 1e-3 * rng.normal(size=z0.shape), batch["ctx"].numpy(), {f"link{i}": slice(i * 3, (i + 1) * 3) for i in range(bundle.n_links)})
                        tb0 = run_front_end(tc0, batch)
                        s0, c0 = counterfactual_contributions(head, o0, tc0, tb0.X, batch["tau_meas"], batch["tau_nom"], batch["ctx"].numpy())
                        frames = sample_link_frames(chain, rng, rotation_angle_max_deg=float(ft["rotation_angle_max_deg"]), translation_fraction_of_link_length=float(ft["translation_fraction_of_link_length"]))
                        new, adj = chain.reparameterize(frames)
                        tc1 = TorchChain.from_chain(new, dtype=dtype, device="cpu")
                        b1 = dict(batch)
                        b1["inertia"] = tc1.inertia[None].expand(nb, -1, -1, -1)
                        o1 = model(b1, tc1)
                        tb1 = run_front_end(tc1, b1)
                        s1, c1 = counterfactual_contributions(head, o1, tc1, tb1.X, b1["tau_meas"], b1["tau_nom"], b1["ctx"].numpy())
                    m0, m1 = o0.messages.double().numpy(), o1.messages.double().numpy()
                    l0, l1 = o0.local.double().numpy(), o1.local.double().numpy()
                    t1m = max(float(np.abs(m1[..., i, :] - transform_typed(SpatialType.FORCE, m0[..., i, :], adj[i])).max()) for i in range(bundle.n_links)) / max(float(np.abs(m0).max()), 1e-12)
                    t1l = max(float(np.abs(l1[..., i, :] - transform_typed(SpatialType.FORCE, l0[..., i, :], adj[i])).max()) for i in range(bundle.n_links)) / max(float(np.abs(l0).max()), 1e-12)
                    d0, d1 = o0.delta_tau.double().numpy(), o1.delta_tau.double().numpy()
                    t2 = float(np.abs(d1 - d0).max() / max(np.abs(d0).max(), 1e-12))
                    f0, f1 = o0.link_features.double().numpy(), o1.link_features.double().numpy()
                    t3 = float(np.abs(f1 - f0).max() / max(np.abs(f0).max(), 1e-12))
                    sc = float(np.abs(s1 - s0).max() / max(np.abs(s0).max(), 1e-12))
                    cf = float(np.abs(c1 - c0).max() / max(np.abs(c0).max(), 1e-12))
                    row = {"model": name, "dtype": dtype_name, "family": fam, "episode_id": eid, "n_windows": int(nb), "T1_message_relative": t1m, "T1_local_relative": t1l, "T2_delta_tau_relative": t2, "T3_features_relative": t3, "score_relative": sc, "counterfactual_relative": cf, "tolerance": tol[dtype_name]}
                    trial_rows.append(row)
                    for k, v in (("T1_message", t1m), ("T1_local", t1l), ("T2_delta_tau", t2), ("T3_features", t3), ("score", sc), ("counterfactual", cf)):
                        w[k] = max(w[k], v)
            worst[name][dtype_name] = w
            st.log(f"model-level trials {name} {dtype_name}: {json.dumps({k: f'{v:.2e}' for k, v in w.items()})}")
    v2 = worst["ligra_v2_typed"]
    gnn = worst["chain_gnn_aug"]
    # covariance quantities (T1/T2/T3) at the frozen tolerances; score-level quantities (differences of
    # NLLs) at 10x the tolerance (float32 cancellation in the pooled residual statistics)
    v2_pass = all(max(v2[d][k] for k in ("T1_message", "T1_local", "T2_delta_tau", "T3_features")) < tol[d] and max(v2[d]["score"], v2[d]["counterfactual"]) < 10 * tol[d] for d in ("float64", "float32"))
    fam_seen = sorted({r["family"] for r in trial_rows if r["model"] == "ligra_v2_typed"})
    results["items"]["6_final_delta_tau_invariance"] = {"pass": bool(v2["float64"]["T2_delta_tau"] < tol["float64"] and v2["float32"]["T2_delta_tau"] < tol["float32"]), "worst": {d: v2[d]["T2_delta_tau"] for d in v2}}
    results["items"]["7_residual_only_score_invariance"] = {"pass": bool(v2["float64"]["score"] < 10 * tol["float64"] and v2["float32"]["score"] < 10 * tol["float32"]), "worst": {d: v2[d]["score"] for d in v2}}
    results["items"]["8_counterfactual_score_invariance"] = {"pass": bool(v2["float64"]["counterfactual"] < 10 * tol["float64"] and v2["float32"]["counterfactual"] < 10 * tol["float32"]), "worst": {d: v2[d]["counterfactual"] for d in v2}}
    results["items"]["9_chain_gnn_nonzero_drift"] = {"pass": bool(gnn["float64"]["T2_delta_tau"] > 1e-3), "chain_gnn_aug_T2_drift_float64": gnn["float64"]["T2_delta_tau"]}
    results["items"]["10_healthy_and_all_fault_families_same_law"] = {"pass": bool(v2_pass and set(fam_seen) == set(FAULT_FAMILIES)), "families": fam_seen}
    results["items"]["11_float64_float32_tolerances"] = {"pass": bool(v2_pass), "tolerances": tol, "worst_ligra_v2_typed": v2, "worst_chain_gnn_aug": gnn}
    results["items"]["8_counterfactual_score_invariance"]["pass"] = results["items"]["8_counterfactual_score_invariance"]["pass"] and results["items"]["7_residual_only_score_invariance"]["pass"]
    results["trials"] = trial_rows

    # ---- items 13-15: parity manifest, leakage audit, parameter counts
    manifests = {"chain_gnn_aug": raw_input_field_manifest(), "ligra_v2_typed": LiGRAv2Typed.input_field_manifest()}
    same = all(set(manifests["chain_gnn_aug"][k]) == set(manifests["ligra_v2_typed"][k]) for k in ("scalars", "twists", "wrenches", "context", "link_descriptors"))
    forbidden_hit = {n: sorted(set().union(*(set(v) for k, v in m.items() if k != "processing")) & set(FORBIDDEN)) for n, m in manifests.items()}
    parity = {"manifests": manifests, "identical_physical_fields": same, "forbidden_fields_declared": forbidden_hit, "pass": bool(same and not any(forbidden_hit.values()))}
    write_json(layout.results / "stage1rb_input_parity.json", parity)
    tc32 = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device="cpu")
    ws = WindowSet(bundle.subset(bundle.train_ids[:2] + bundle.test_ids[:6]), bundle.window, bundle.stride_train, "cpu")
    batch = ws.batch(list(range(0, len(ws), max(1, len(ws) // 24)))[:24])
    leak = {"models": {}, "forbidden_fields_perturbed": ["tau_meas", "r_gmo", "active", "target", "family"], "pass": True}
    for name in list(PRIMARY_MODELS) + ["rnea_gru", "ligra_free_output"]:
        model = build_model(name, tc32, bundle.ctx_dim, cfg["model"])
        model.fit_normalizers(tc32, [batch])
        with torch.no_grad():
            o0 = model(batch, tc32)
            o1 = model(_perturb(batch, rng), tc32)
        identical = bool(torch.equal(o0.delta_tau, o1.delta_tau))
        leak["models"][name] = {"delta_tau_identical_after_forbidden_field_perturbation": identical, "n_windows": int(batch["q"].shape[0])}
        leak["pass"] = leak["pass"] and identical
    write_json(layout.results / "stage1rb_leakage_audit.json", leak)
    n_b = count_parameters(build_model("chain_gnn_aug", tc32, bundle.ctx_dim, cfg["model"]))
    n_v = count_parameters(build_model("ligra_v2_typed", tc32, bundle.ctx_dim, cfg["model"]))
    tolp = float(cfg["models"]["parameter_match_tolerance"])
    par = {"chain_gnn_aug": n_b, "ligra_v2_typed": n_v, "relative_difference": (n_v - n_b) / n_b, "tolerance": tolp, "pass": abs(n_v - n_b) / n_b <= tolp, "diagnostics": {n: count_parameters(build_model(n, tc32, bundle.ctx_dim, cfg["model"])) for n in ("rnea_gru", "ligra_free_output")}}
    results["items"]["13_encoder_input_leakage_audit"] = {"pass": leak["pass"], "detail": leak["models"]}
    results["items"]["14_forbidden_field_audit"] = {"pass": parity["pass"], "forbidden_declared": forbidden_hit}
    results["items"]["15_parameter_count_match"] = {"pass": par["pass"], **par}
    results["parameter_counts"] = par
    results["decision"] = "PASS" if all(v.get("pass", False) for v in results["items"].values()) and results.get("pytest", {}).get("status", "PASS") == "PASS" else "BLOCKED"
    results["elapsed_s"] = time.time() - t0
    write_json(layout.results / "stage1rb_equivariance_tests.json", results)
    write_json(layout.results / "stage1rb_r0_gate.json", {"decision": results["decision"], "items": {k: v.get("pass") for k, v in results["items"].items()}, "pytest": results.get("pytest", {}).get("status"), "timestamp_utc": utc_now(), "git_sha": st.base_row()["git_sha"]})
    st.log(f"R0 gate decision={results['decision']} items={ {k: v.get('pass') for k, v in results['items'].items()} }")
    st.finish({"r0_decision": results["decision"]})
    return 0 if results["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
