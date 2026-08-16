"""Stage 2B Phase 3: context calibration and sequential monitoring.

The encoder is frozen. For each of the four calibrators and each wrapper in the frozen
sequential grid, the quantile knob is tuned on **healthy validation episodes only** to hit two
pre-registered event false-alarm targets (50/h primary, 10/h stretch). If a combination cannot
reach a target on validation it is recorded as ``TARGET_NOT_REACHED`` rather than silently
replaced by the closest thing.

The selected operating points are then applied unchanged to held-out healthy ID episodes,
healthy OOD episodes and the F4 contact test episodes. Window rates and event rates are reported
separately; the headline is the **event** false-alarm rate.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from certo_fdi.anomaly.gaussian_head import ConditionalGaussian
from certo_fdi.experiments.common import write_csv, write_json
from certo_fdi.experiments.evaluation import fit_head_loo
from certo_fdi.experiments.pipeline import density_input, extract_features
from certo_fdi.experiments.stage2b_common import (
    Stage,
    common_parser,
    ensure_model_cfg,
    episode_cluster_bootstrap,
    seedwise,
)
from certo_fdi.stage2b import context_calibration as CAL
from certo_fdi.stage2b import event_accounting as EA
from certo_fdi.stage2b import sequential_monitor as SEQ

CONTEXT_NAMES = ["controller_id", "speed_scale", "tool_mass_kg", "tool_com_z_m", "temperature_proxy", "noise_level"]


def _episode_arrays(model, ep, bundle, tc, device, dt):
    """Per-window score inputs for one episode, time ordered."""
    from certo_fdi.data.windows import WindowSet

    ws = WindowSet([ep], bundle.window, bundle.stride_eval, device, min_start=bundle.eval_min_start)
    f = extract_features(model, ws, tc, device)
    order = np.argsort(f.start)
    z, _ = density_input(f, "residual_only")
    return {"z": z[order], "ctx": f.ctx[order], "label": f.label[order].astype(int),
            "t_end": (f.start[order] + bundle.window) * dt, "start": f.start[order],
            "episode_id": ep.episode_id, "kind": ep.kind, "split": ep.split, "family": ep.family,
            "onset_s": float(ep.fault.get("onset_s", 0.0)), "target": int(ep.fault.get("target", -1))}


def _fa_per_hour(specs, cal, eps, ecfg, scale) -> tuple[float, list[dict]]:
    rows = []
    for e in eps:
        thr = cal.threshold(e["ctx"])
        alarm = specs.apply(e["score"], thr, scale)
        rows.append(EA.healthy_false_alarms(alarm, e["t_end"], e["label"], ecfg, e["episode_id"]))
    agg = EA.aggregate_events(rows, [], ecfg)
    return agg["false_alarms_per_hour"], rows


#: frozen quantile grid, log-spaced in the tail mass so both the 50/h and 10/h targets are
#: reachable without refitting a calibrator inside a search loop
QUANTILE_GRID = tuple(float(1.0 - t) for t in
                      (2e-1, 1e-1, 5e-2, 2e-2, 1e-2, 5e-3, 2e-3, 1e-3, 5e-4, 2e-4,
                       1e-4, 5e-5, 2e-5, 1e-5, 5e-6, 2e-6, 1e-6))


def _tune_on_grid(fitted, spec, val_eps, ecfg, target, scale):
    """Smallest quantile on the frozen grid whose healthy-validation event FA/h meets ``target``.

    Smallest = most sensitive threshold that still satisfies the operating point. The calibrators
    are fitted once per (method, quantile) outside this function, so a quantile regressor is
    never refitted inside a search. Returns ``None`` when no grid point reaches the target, which
    the caller records as TARGET_NOT_REACHED rather than substituting the closest thing.
    """
    for q, cal in fitted:
        fa, _ = _fa_per_hour(spec, cal, val_eps, ecfg, scale)
        if fa <= target:
            return q, cal, fa
    return None


def main() -> int:
    ap = common_parser("Stage 2B Phase 3: context calibration and sequential monitoring")
    ap.add_argument("--seeds", default="")
    args = ap.parse_args()
    st = Stage(args, "calibration")
    if not st.require_freeze():
        return 3
    import torch

    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import load_checkpoint

    cfg = ensure_model_cfg(st.cfg)
    bundle = st.bundle
    dt = float(cfg["simulation"]["control_dt_s"])
    ecfg = EA.EventConfig.from_cfg(cfg)
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [int(s) for s in cfg["seed_list"]]
    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=st.device)
    targets = [float(t) for t in cfg["calibration"]["target_false_alarms_per_hour"]]
    cal_cfg = cfg["calibration"]          # the calibrators only ever see their own config section
    specs = SEQ.candidate_specs(cfg)
    st.log(f"event accounting frozen: {json.dumps(ecfg.to_dict())}")

    cal_rows, seq_rows, ev_rows, cov_rows = [], [], [], []
    chosen: dict[int, dict] = {}
    for seed in seeds:
        t0 = time.time()
        fc = cfg["models"]["frozen_best_config"]["chain_gnn_aug"]
        ck = st.layout.sub("checkpoints") / f"chain_gnn_aug_{fc['tag']}_seed{seed}_frac{len(bundle.train_ids)}ep.pt"
        model = load_checkpoint("chain_gnn_aug", ck, bundle, cfg, st.device)["model"]

        # ---- frozen residual-only head, fitted on healthy validation windows (Stage 2A protocol)
        val_eps = [_episode_arrays(model, bundle.episodes[e], bundle, tc, st.device, dt) for e in bundle.val_ids]
        z_val = np.concatenate([e["z"] for e in val_eps])
        c_val = np.concatenate([e["ctx"] for e in val_eps])
        e_val = np.concatenate([np.full(len(e["z"]), i) for i, e in enumerate(val_eps)])
        slices = {f"link{i}": slice(i * 3, (i + 1) * 3) for i in range(bundle.n_links)}
        head, hinfo, loo, _ = fit_head_loo(z_val, c_val, e_val, slices)
        for i, e in enumerate(val_eps):
            e["score"] = loo[e_val == i]          # out-of-sample healthy scores
        scale = float(np.std(loo)) or 1.0
        st.log(f"[seed {seed}] head fitted ({hinfo['conditional']},{hinfo['covariance']},r={hinfo['rank']}) "
               f"on {len(z_val)} healthy val windows; LOO score sd {scale:.2f}")

        # ---- held-out evaluation episodes
        test_ids = [e for e in bundle.test_ids
                    if bundle.episodes[e].kind == "healthy" or bundle.episodes[e].family == "F4_contact"]
        test_eps = [_episode_arrays(model, bundle.episodes[e], bundle, tc, st.device, dt) for e in test_ids]
        for e in test_eps:
            e["score"] = head.nll(e["z"], e["ctx"])
        healthy_id = [e for e in test_eps if e["kind"] == "healthy" and e["split"] == "S0"]
        healthy_ood = [e for e in test_eps if e["kind"] == "healthy" and e["split"] != "S0"]
        f4 = [e for e in test_eps if e["family"] == "F4_contact"]
        st.log(f"[seed {seed}] test episodes: healthy ID {len(healthy_id)}, healthy OOD {len(healthy_ood)}, F4 {len(f4)}")

        for method in CAL.METHODS:
            t_m = time.time()
            fitted = [(q, CAL.fit(method, loo, c_val, e_val, q, CONTEXT_NAMES, cal_cfg)) for q in QUANTILE_GRID]
            st.log(f"[seed {seed}] {method}: {len(fitted)} calibrators fitted ({time.time() - t_m:.0f}s)")
            for spec in specs:
                for target in targets:
                    tuned = _tune_on_grid(fitted, spec, val_eps, ecfg, target, scale)
                    if tuned is None:
                        seq_rows.append(st.base_row(method=f"{method}|{spec.method}", partition="healthy_val",
                                                    split="ALL", seed=seed, fault_family="",
                                                    calibrator=method, sequential=spec.method,
                                                    sequential_params=json.dumps(spec.params),
                                                    target_false_alarms_per_hour=target,
                                                    status="TARGET_NOT_REACHED",
                                                    units="validation tuning outcome"))
                        continue
                    q, cal, fa_val = tuned
                    # ---- apply unchanged to the held-out partitions
                    h_rows_id, h_rows_ood, f_rows, w_id, w_ood, w_f4 = [], [], [], [], [], []
                    for e in healthy_id:
                        a = spec.apply(e["score"], cal.threshold(e["ctx"]), scale)
                        h_rows_id.append(EA.healthy_false_alarms(a, e["t_end"], e["label"], ecfg, e["episode_id"]))
                        w_id.append(EA.window_alarm_rate(a, e["label"]))
                    for e in healthy_ood:
                        a = spec.apply(e["score"], cal.threshold(e["ctx"]), scale)
                        h_rows_ood.append(EA.healthy_false_alarms(a, e["t_end"], e["label"], ecfg, e["episode_id"]))
                        w_ood.append(EA.window_alarm_rate(a, e["label"]))
                    for e in f4:
                        a = spec.apply(e["score"], cal.threshold(e["ctx"]), scale)
                        f_rows.append(EA.fault_event_detection(a, e["t_end"], e["label"], e["onset_s"], ecfg, e["episode_id"]))
                        f_rows[-1]["healthy_seconds"] = float((e["label"] == 0).sum()) * ecfg.window_dt_s
                        w_f4.append(EA.window_alarm_rate(a, e["label"]))
                    agg_all = EA.aggregate_events(h_rows_id + h_rows_ood, f_rows, ecfg)
                    agg_id = EA.aggregate_events(h_rows_id, [], ecfg)
                    agg_ood = EA.aggregate_events(h_rows_ood, [], ecfg)
                    ratio = (agg_ood["false_alarms_per_hour"] / agg_id["false_alarms_per_hour"]
                             if agg_id["false_alarms_per_hour"] > 0 else float("inf"))
                    row = st.base_row(method=f"{method}|{spec.method}", partition="F4_TEST", split="ALL",
                                      seed=seed, fault_family="F4_contact",
                                      calibrator=method, sequential=spec.method,
                                      sequential_params=json.dumps(spec.params),
                                      target_false_alarms_per_hour=target, quantile=q,
                                      validation_false_alarms_per_hour=fa_val,
                                      false_alarms_per_hour=agg_all["false_alarms_per_hour"],
                                      false_alarms_per_hour_id=agg_id["false_alarms_per_hour"],
                                      false_alarms_per_hour_ood=agg_ood["false_alarms_per_hour"],
                                      healthy_ood_id_ratio=ratio,
                                      arl0_hours=agg_all["arl0_hours"],
                                      event_tpr=agg_all["event_tpr"], event_f1=agg_all["event_f1"],
                                      event_precision=agg_all["event_precision"],
                                      median_delay_s=agg_all["detection_delay_median_s"],
                                      p90_delay_s=agg_all["detection_delay_p90_s"],
                                      p95_delay_s=agg_all["detection_delay_p95_s"],
                                      window_alarm_rate_healthy_id=float(np.mean([w["window_alarm_rate_healthy"] for w in w_id])) if w_id else float("nan"),
                                      window_alarm_rate_healthy_ood=float(np.mean([w["window_alarm_rate_healthy"] for w in w_ood])) if w_ood else float("nan"),
                                      window_alarm_rate_faulty=float(np.nanmean([w["window_alarm_rate_faulty"] for w in w_f4])) if w_f4 else float("nan"),
                                      n_fault_events=agg_all["n_fault_events"], healthy_hours=agg_all["healthy_hours"],
                                      status="OK",
                                      units="event rates per hour; delays in s; window rates are fractions")
                    ev_rows.append(row)
                    seq_rows.append(st.base_row(method=f"{method}|{spec.method}", partition="healthy_val",
                                                split="ALL", seed=seed, fault_family="",
                                                calibrator=method, sequential=spec.method,
                                                sequential_params=json.dumps(spec.params),
                                                target_false_alarms_per_hour=target, quantile=q,
                                                validation_false_alarms_per_hour=fa_val, status="OK",
                                                units="validation tuning outcome"))
            # coverage diagnostics for this calibrator at the primary target
            best_q = next((r["quantile"] for r in seq_rows
                           if r["seed"] == seed and r["calibrator"] == method and r.get("status") == "OK"), None)
            if best_q is not None:
                cal = CAL.fit(method, loo, c_val, e_val, float(best_q), CONTEXT_NAMES, cal_cfg)
                for grp in CAL.grouped_coverage(cal, np.concatenate([e["score"] for e in healthy_id + healthy_ood]),
                                                np.concatenate([e["ctx"] for e in healthy_id + healthy_ood]),
                                                np.concatenate([np.full(len(e["score"]), e["episode_id"]) for e in healthy_id + healthy_ood]),
                                                CONTEXT_NAMES, cal_cfg):
                    cov_rows.append(st.base_row(method=method, partition="healthy_test", split="ALL", seed=seed,
                                                fault_family="", **grp, quantile=float(best_q),
                                                units="empirical marginal/grouped coverage; NOT exact conditional CFAR"))
                cal_rows.append(st.base_row(method=method, partition="healthy_val", split="ALL", seed=seed,
                                            fault_family="", quantile=float(best_q),
                                            **{k: v for k, v in cal.to_dict().items() if k not in ("method", "quantile", "context_names")},
                                            units="fitted calibrator diagnostics"))
        st.log(f"[seed {seed}] calibration sweep done ({time.time() - t0:.0f}s)")

    st.write_table("stage2b_context_calibration.csv", cal_rows,
                   units="fitted healthy-only calibrator diagnostics",
                   schema={"coverage_claim": "marginal/grouped empirical only"})
    st.write_table("stage2b_sequential_metrics.csv", seq_rows,
                   units="healthy-validation tuning outcome per (calibrator, wrapper, target)",
                   schema={"status": "OK or TARGET_NOT_REACHED"})
    st.write_table("stage2b_event_metrics.csv", ev_rows,
                   units="event false alarms per hour, event TPR/F1, detection delays in s",
                   schema={"false_alarms_per_hour": "the headline; window rates are reported separately"})
    write_csv(st.layout.sub("p3_calibration") / "stage2b_calibration_coverage.csv", cov_rows)
    write_json(st.layout.results / "stage2b_event_accounting.json", ecfg.to_dict())
    st.finish({"seeds": seeds, "n_event_rows": len(ev_rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
