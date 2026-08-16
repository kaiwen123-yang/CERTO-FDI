"""Stage 1R-B evaluation of one trained run (contract 06 §6–§9).

* healthy prediction (torque-correction RMSE) per split;
* anomaly detection with the **residual-only** conditional Gaussian head (primary; identical for
  every model) and the secondary "representation" head; window/event metrics per split, fault
  family and severity; healthy-OOD false-alarm audit;
* localization: **counterfactual link masking** (primary, unified) and the joint-residual pattern
  decoders (secondary);
* frame-reparameterization drift of the correction and of the residual-only score (S5);
* oracle acceleration diagnostic: the same checkpoint evaluated with ``qdd_true`` (never used for
  the decision);
* latency / parameter count.

Thresholds and head selection use healthy validation windows only; no fault data is used for any
choice.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch

from certo_fdi.anomaly.calibration import healthy_quantile_threshold
from certo_fdi.anomaly.event_detection import safe_auroc
from certo_fdi.anomaly.gaussian_head import ConditionalGaussian
from certo_fdi.data.windows import WindowSet
from certo_fdi.dynamics.rnea_torch import TorchChain
from certo_fdi.experiments.evaluation import LOCALIZABLE, SPLITS, _detection_rows, _episode_meta, _latency_rows, _localization_rows, fit_head_loo
from certo_fdi.experiments.pipeline import DataBundle, density_input, extract_features
from certo_fdi.experiments.r0_model_covariance import tool_chain
from certo_fdi.geometry.se3 import SE3
from certo_fdi.localization.counterfactual import counterfactual_contributions, rank_by_contribution
from certo_fdi.localization.link_scores import localization_metrics
from certo_fdi.models.chain_gnn import run_front_end

PRIMARY_VARIANT = "residual_only"
SECONDARY_VARIANT = "representation"


def _healthy_rows(base: dict, model_name: str, ws_test: WindowSet, f_test, f_val, acc: str) -> list[dict]:
    meta_t = _episode_meta(ws_test, f_test)
    rows = []
    for split in SPLITS + ("OOD",):
        m = (meta_t["kind"] == "healthy") & ((np.isin(meta_t["split"], ["S1", "S2", "S3", "S4"])) if split == "OOD" else (meta_t["split"] == split))
        if m.sum() == 0:
            continue
        post = np.sqrt(f_test.resid_ms[m].mean(0))
        pre = np.sqrt(f_test.pre_ms[m].mean(0))
        rows.append({**base, "model": model_name, "acceleration_input": acc, "split": split, "n_windows": int(m.sum()), "torque_rmse_post_nm": float(np.sqrt(f_test.resid_ms[m].mean())), "torque_rmse_pre_nm": float(np.sqrt(f_test.pre_ms[m].mean())),
                     "rmse_ratio_post_over_pre": float(np.sqrt(f_test.resid_ms[m].mean()) / max(np.sqrt(f_test.pre_ms[m].mean()), 1e-9)), **{f"rmse_post_j{j + 1}": float(post[j]) for j in range(len(post))}, **{f"rmse_pre_j{j + 1}": float(pre[j]) for j in range(len(pre))}, "units": "N m"})
    rows.append({**base, "model": model_name, "acceleration_input": acc, "split": "VAL", "n_windows": int(len(f_val.label)), "torque_rmse_post_nm": float(np.sqrt(f_val.resid_ms.mean())), "torque_rmse_pre_nm": float(np.sqrt(f_val.pre_ms.mean())), "rmse_ratio_post_over_pre": float(np.sqrt(f_val.resid_ms.mean()) / max(np.sqrt(f_val.pre_ms.mean()), 1e-9)), "units": "N m"})
    return rows


@torch.no_grad()
def _counterfactual_rows(base: dict, model_name: str, model, head: ConditionalGaussian, bundle: DataBundle, tc: TorchChain, device: str, batch_size: int = 256) -> tuple[list[dict], list[dict]]:
    """Counterfactual link masking on the faulty windows of every localizable test fault episode."""
    eps = [e for e in bundle.test_ids if bundle.episodes[e].kind == "fault" and bundle.episodes[e].family in LOCALIZABLE and int(bundle.episodes[e].fault.get("target", -1)) >= 0]
    per_episode = []
    for eid in eps:
        ep = bundle.episodes[eid]
        ws = WindowSet([ep], bundle.window, bundle.stride_eval, device, min_start=bundle.eval_min_start)
        contribs, labels = [], []
        for batch in ws.iterate(batch_size, False, device=device):
            out = model(batch, tc)
            tb = run_front_end(tc, batch)
            _, c = counterfactual_contributions(head, out, tc, tb.X, batch["tau_meas"], batch["tau_nom"], batch["ctx"].cpu().numpy())
            contribs.append(c)
            labels.append(batch["active"][:, -1].cpu().numpy())
        c = np.concatenate(contribs)
        y = np.concatenate(labels)
        m = y == 1
        if m.sum() == 0:
            continue
        mean_c = c[m].mean(0)
        per_episode.append({"episode_id": eid, "family": ep.family, "split": ep.split, "target": int(ep.fault["target"]), "severity": float(ep.fault.get("severity", 0.0)), "contribution": mean_c.tolist(), "ranking": rank_by_contribution(mean_c[None])[0].tolist(), "n_fault_windows": int(m.sum())})
    n = bundle.n_links
    rows = []
    for split_tag in ("S0", "OOD", "ALL"):
        for fam in ("ALL",) + LOCALIZABLE:
            sel = [r for r in per_episode if (fam == "ALL" or r["family"] == fam) and (split_tag == "ALL" or (split_tag == "S0" and r["split"] == "S0") or (split_tag == "OOD" and r["split"] != "S0"))]
            if not sel:
                continue
            preds = np.stack([r["ranking"] for r in sel])
            targets = np.array([r["target"] for r in sel])
            met = localization_metrics(preds, targets, n, k=2)
            rows.append({**base, "model": model_name, "method": "counterfactual_link_masking", "density_variant": PRIMARY_VARIANT, "rule": "abs_contribution_argmax", "split": split_tag, "family": fam, "top1": met["top1"], "top2": met["top2"], "mean_chain_distance": met["mean_chain_distance"], "n_episodes": met["n"], "confusion": str(met["confusion"]), "units": "top-k accuracy; chain distance in links; contribution = NLL(mask link) - NLL(full)"})
    detail = [{**base, "model": model_name, **r} for r in per_episode]
    return rows, detail


@torch.no_grad()
def _frame_drift_rows(base: dict, model, model_name: str, bundle: DataBundle, manifest: dict, head: ConditionalGaussian, healthy_score_std: float, device: str, max_episodes: int = 12) -> list[dict]:
    rows = []
    dtype = torch.float32
    done = 0
    for eid, variants in manifest.get("episodes", {}).items():
        if eid not in bundle.episodes:
            continue
        ep = bundle.episodes[eid]
        ws = WindowSet([ep], bundle.window, bundle.stride_train, device, min_start=bundle.eval_min_start)
        chain = tool_chain(bundle.base_chain, ep.tool_id)
        tc0 = TorchChain.from_chain(chain, dtype=dtype, device=device)
        f0 = extract_features(model, ws, tc0, device, inertia_override=tc0.inertia)
        z0, _ = density_input(f0, PRIMARY_VARIANT)
        s0 = head.nll(z0, f0.ctx)
        for v, H in enumerate(variants[:4]):
            frames = [SE3.from_matrix(np.asarray(h)) for h in H]
            new_chain, _ = chain.reparameterize(frames)
            tc1 = TorchChain.from_chain(new_chain, dtype=dtype, device=device)
            f1 = extract_features(model, ws, tc1, device, inertia_override=tc1.inertia)
            z1, _ = density_input(f1, PRIMARY_VARIANT)
            s1 = head.nll(z1, f1.ctx)
            d_scale = max(float(np.abs(f0.delta_pool).max()), 1e-9)
            rows.append({**base, "model": model_name, "episode_id": eid, "variant": v, "kind": ep.kind, "family": ep.family, "split": ep.split, "density_variant": PRIMARY_VARIANT,
                         "delta_tau_pooled_max_abs_drift": float(np.abs(f1.delta_pool - f0.delta_pool).max()), "delta_tau_relative_drift": float(np.abs(f1.delta_pool - f0.delta_pool).max() / d_scale),
                         "score_abs_drift_max": float(np.abs(s1 - s0).max()), "score_drift_in_healthy_std": float(np.abs(s1 - s0).max() / max(healthy_score_std, 1e-9)),
                         "score_auroc_variant_vs_canonical": safe_auroc(np.r_[np.ones(len(s1)), np.zeros(len(s0))], np.r_[s1, s0]), "units": "N m (pooled delta tau); score units"})
        done += 1
        if done >= max_episodes:
            break
    return rows


def evaluate_run_stage1rb(model, run_info: dict, train_ids: list[str], bundle: DataBundle, cfg: dict, base_row: dict, device: str, *, full: bool, frame_manifest: dict | None, quantile: float, log: list[str] | None = None, acceleration_diagnostic: bool = True) -> dict[str, list[dict]]:
    dt = float(cfg["simulation"]["control_dt_s"])
    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=device)
    model.eval()
    model_name = run_info["name"]
    base = {**base_row, "n_train_episodes": len(train_ids), "n_params": run_info.get("n_params", 0), "checkpoint_sha256": run_info.get("checkpoint_sha256", ""), "acceleration_input": "qdd_est"}
    out: dict[str, list[dict]] = {k: [] for k in ("healthy_prediction", "detection", "ood_healthy", "localization", "localization_detail", "frame_invariance", "latency", "heads")}
    t0 = time.time()

    def run_once(acc: str) -> dict[str, Any]:
        ws_val = WindowSet(bundle.subset(bundle.val_ids), bundle.window, bundle.stride_train, device, min_start=bundle.eval_min_start, acceleration_source=acc)
        ws_test = WindowSet(bundle.subset(bundle.test_ids), bundle.window, bundle.stride_eval, device, min_start=bundle.eval_min_start, acceleration_source=acc)
        f_val = extract_features(model, ws_val, tc, device)
        f_test = extract_features(model, ws_test, tc, device)
        b = {**base, "acceleration_input": acc}
        res: dict[str, Any] = {"healthy": _healthy_rows(b, model_name, ws_test, f_test, f_val, acc), "det": [], "ood": [], "loc": [], "heads": [], "head_primary": None, "f_val": f_val, "ws_test": ws_test, "f_test": f_test}
        variants = (PRIMARY_VARIANT, SECONDARY_VARIANT) if acc == "qdd_est" else (PRIMARY_VARIANT,)
        for variant in variants:
            z_va, slices = density_input(f_val, variant)
            z_te, _ = density_input(f_test, variant)
            head, hinfo, loo, loo_blocks = fit_head_loo(z_va, f_val.ctx, f_val.episode, slices)
            s_te = head.nll(z_te, f_test.ctx)
            thr = healthy_quantile_threshold(loo, quantile)
            res["heads"].append({**b, "model": model_name, "density_variant": variant, "primary": variant == PRIMARY_VARIANT, "z_dim": int(z_va.shape[1]), "threshold": thr, "val_loo_nll_mean": hinfo["loo_val_nll_mean"], "val_insample_nll_mean": hinfo["in_sample_val_nll_mean"], "n_val_windows": int(len(z_va)), "n_val_episodes": hinfo["n_val_episodes"], "chosen_conditional": hinfo["conditional"], "chosen_covariance": hinfo["covariance"], "chosen_rank": hinfo["rank"], "protocol": "head fitted on healthy val; candidate chosen by LOO val NLL; threshold = LOO 0.995 quantile; no fault data"})
            det, ood = _detection_rows(b, model_name, variant, head, thr, ws_test, f_test, s_te, dt, loo)
            res["det"] += det
            res["ood"] += ood
            if acc == "qdd_est":
                for r in _localization_rows(b, model_name, variant, head, loo_blocks, ws_test, f_test, z_te):
                    r["method"] = f"joint_residual_pattern:{r['rule']}"
                    res["loc"].append(r)
            if variant == PRIMARY_VARIANT:
                res["head_primary"] = head
                res["loo_primary"] = loo
        return res

    main = run_once("qdd_est")
    out["healthy_prediction"] += main["healthy"]
    out["detection"] += main["det"]
    out["ood_healthy"] += main["ood"]
    out["localization"] += main["loc"]
    out["heads"] += main["heads"]
    if log is not None:
        log.append(f"  heads/detection/pattern-localization done ({time.time() - t0:.0f}s)")
    # counterfactual localization (primary method), residual-only head
    cf_rows, cf_detail = _counterfactual_rows(base, model_name, model, main["head_primary"], bundle, tc, device)
    out["localization"] += cf_rows
    out["localization_detail"] += cf_detail
    if log is not None:
        log.append(f"  counterfactual localization done ({time.time() - t0:.0f}s)")
    if acceleration_diagnostic:
        diag = run_once("qdd_true")
        out["healthy_prediction"] += diag["healthy"]
        out["detection"] += diag["det"]
        out["heads"] += diag["heads"]
        if log is not None:
            log.append(f"  qdd_true diagnostic done ({time.time() - t0:.0f}s)")
    if full:
        if frame_manifest is not None:
            out["frame_invariance"] += _frame_drift_rows(base, model, model_name, bundle, frame_manifest, main["head_primary"], float(np.std(main["loo_primary"])), device)
        out["latency"] += _latency_rows(base, model, model_name, main["ws_test"], tc, device, int(run_info.get("n_params", 0)))
        if log is not None:
            log.append(f"  frame drift/latency done ({time.time() - t0:.0f}s)")
    return out
