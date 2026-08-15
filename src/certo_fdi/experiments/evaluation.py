"""R1–R4 evaluation of one trained run: healthy prediction, healthy-only anomaly detection,
OOD-healthy audit, localization, few-shot attribution, frame invariance (S5), latency."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch

from certo_fdi.anomaly.calibration import healthy_quantile_threshold
from certo_fdi.anomaly.event_detection import episode_level_auroc, event_metrics, safe_auroc, window_metrics
from certo_fdi.anomaly.gaussian_head import ConditionalGaussian
from certo_fdi.data.schema import FAULT_FAMILIES
from certo_fdi.data.windows import WindowSet
from certo_fdi.dynamics.rnea_torch import TorchChain
from certo_fdi.experiments.pipeline import DataBundle, WindowFeatures, density_input, extract_features
from certo_fdi.experiments.r0_model_covariance import tool_chain
from certo_fdi.geometry.se3 import SE3
from certo_fdi.localization.fewshot_head import fewshot_attribution
from certo_fdi.localization.link_scores import localization_metrics, rank_links

SPLITS = ("S0", "S1", "S2", "S3", "S4")
LOCALIZABLE = ("F1_actuator", "F2_friction", "F3_payload", "F4_contact", "F5_encoder")
DENSITY_VARIANTS = ("residual_only", "representation", "residual_plus_gmo")


def _episode_meta(ws: WindowSet, f: WindowFeatures) -> dict[str, np.ndarray]:
    ep = f.episode
    split = np.array([ws.episodes[i].split for i in ep])
    kind = np.array([ws.episodes[i].kind for i in ep])
    fam = np.array([ws.episodes[i].family for i in ep])
    return {"split": split, "kind": kind, "family": fam}


def _episode_sequences(ws: WindowSet, f: WindowFeatures, scores: np.ndarray, dt: float, mask: np.ndarray | None = None) -> list[dict]:
    seqs = []
    idx_all = np.arange(len(f.label)) if mask is None else np.where(mask)[0]
    for e in np.unique(f.episode[idx_all]):
        m = idx_all[f.episode[idx_all] == e]
        order = m[np.argsort(f.start[m])]
        ep = ws.episodes[int(e)]
        seqs.append({
            "scores": scores[order], "labels": f.label[order], "t_end": (f.start[order] + ws.window) * dt,
            "is_fault_episode": ep.kind == "fault", "onset_s": float(ep.fault.get("onset_s", 0.0)), "family": ep.family, "split": ep.split,
            "severity": float(ep.fault.get("severity", 0.0)), "kind_detail": ep.fault.get("kind", "none"),
        })
    return seqs


def _detection_rows(base: dict, model_name: str, variant: str, head: ConditionalGaussian, threshold: float, ws_test: WindowSet, f_test: WindowFeatures, scores: np.ndarray, dt: float, healthy_val_scores: np.ndarray) -> tuple[list[dict], list[dict]]:
    meta = _episode_meta(ws_test, f_test)
    rows, ood_rows = [], []
    window_dt = ws_test.stride * dt

    def group_rows(mask_pos: np.ndarray, mask_neg: np.ndarray, tag: dict) -> None:
        y = np.r_[np.ones(mask_pos.sum()), np.zeros(mask_neg.sum())]
        s = np.r_[scores[mask_pos], scores[mask_neg]]
        wm = window_metrics(y, s, threshold)
        seqs = _episode_sequences(ws_test, f_test, scores, dt, mask_pos | mask_neg)
        em = event_metrics(seqs, threshold, window_dt)
        em3 = {f"p3_{k}": v for k, v in event_metrics(seqs, threshold, window_dt, persistence=3).items() if k in ("event_tpr", "false_alarms_per_hour", "detection_delay_median_s", "event_f1")}
        rows.append({**base, "model": model_name, "density_variant": variant, "threshold": threshold, **tag, **wm, **em, **em3, "episode_auroc": episode_level_auroc(seqs), "units": "score=-log p0; delay=s; fa/h; p3_* = 3-consecutive-window persistence rule"})

    healthy_ep = meta["kind"] == "healthy"
    for split in SPLITS + ("OOD", "ALL"):
        if split == "OOD":
            in_split = np.isin(meta["split"], ["S1", "S2", "S3", "S4"])
        elif split == "ALL":
            in_split = np.ones(len(f_test.label), dtype=bool)
        else:
            in_split = meta["split"] == split
        neg = in_split & (f_test.label == 0)
        for fam in ("ALL",) + tuple(FAULT_FAMILIES[1:]):
            pos = in_split & (f_test.label == 1) & ((meta["family"] == fam) if fam != "ALL" else True)
            if pos.sum() == 0 or neg.sum() == 0:
                continue
            group_rows(pos, neg, {"split": split, "family": fam, "severity": "ALL"})
        # per severity within split for each family
        if split in ("S0", "OOD"):
            for fam in FAULT_FAMILIES[1:]:
                sev_vals = sorted({float(ws_test.episodes[int(e)].fault.get("severity", 0.0)) for e in np.unique(f_test.episode[in_split & (meta["family"] == fam)])})
                for sv in sev_vals:
                    ep_mask = np.array([float(ws_test.episodes[int(e)].fault.get("severity", 0.0)) == sv for e in f_test.episode])
                    pos = in_split & (f_test.label == 1) & (meta["family"] == fam) & ep_mask
                    if pos.sum() == 0:
                        continue
                    group_rows(pos, neg, {"split": split, "family": fam, "severity": sv})
    # OOD-healthy audit: healthy OOD windows vs healthy ID windows (should NOT be separable)
    id_h = healthy_ep & (meta["split"] == "S0")
    for split in ("S1", "S2", "S3", "S4"):
        m = healthy_ep & (meta["split"] == split)
        if m.sum() == 0:
            continue
        seqs = _episode_sequences(ws_test, f_test, scores, dt, m)
        em = event_metrics(seqs, threshold, window_dt)
        ood_rows.append({**base, "model": model_name, "density_variant": variant, "split": split, "n_windows": int(m.sum()),
                         "healthy_ood_alarm_rate": float((scores[m] > threshold).mean()), "healthy_id_alarm_rate": float((scores[id_h] > threshold).mean()) if id_h.any() else float("nan"),
                         "ood_vs_id_healthy_auroc_anti_metric": safe_auroc(np.r_[np.ones(m.sum()), np.zeros(id_h.sum())], np.r_[scores[m], scores[id_h]]) if id_h.any() else float("nan"),
                         "false_alarms_per_hour": em["false_alarms_per_hour"], "median_score_ood": float(np.median(scores[m])), "median_score_id": float(np.median(scores[id_h])) if id_h.any() else float("nan"),
                         "median_score_val": float(np.median(healthy_val_scores)), "note": "healthy OOD alarms are false alarms, not detections"})
    return rows, ood_rows


def _localization_rows(base: dict, model_name: str, variant: str, head: ConditionalGaussian, z_val: np.ndarray, c_val: np.ndarray, ws_test: WindowSet, f_test: WindowFeatures, z_test: np.ndarray) -> list[dict]:
    n = f_test.n_links
    ref = head.block_nll(z_val, c_val)
    ref_mu = np.array([ref[f"link{i}"].mean() for i in range(n)])
    ref_sd = np.array([max(ref[f"link{i}"].std(), 1e-9) for i in range(n)])
    test_blocks = head.block_nll(z_test, f_test.ctx)
    excess_all = np.stack([(test_blocks[f"link{i}"] - ref_mu[i]) / ref_sd[i] for i in range(n)], 1)  # (N,n)
    meta = _episode_meta(ws_test, f_test)
    rows = []
    for split_tag in ("S0", "OOD", "ALL"):
        for fam in ("ALL",) + LOCALIZABLE:
            preds, targets = [], []
            for e in np.unique(f_test.episode):
                ep = ws_test.episodes[int(e)]
                if ep.kind != "fault" or ep.family not in LOCALIZABLE or (fam != "ALL" and ep.family != fam):
                    continue
                if split_tag == "S0" and ep.split != "S0":
                    continue
                if split_tag == "OOD" and ep.split == "S0":
                    continue
                m = (f_test.episode == e) & (f_test.label == 1)
                if m.sum() == 0:
                    continue
                target = int(ep.fault.get("target", -1))
                if target < 0:
                    continue
                exc = excess_all[m].mean(0)
                preds.append(rank_links(exc[None])[0])
                targets.append(target)
            if not targets:
                continue
            met = localization_metrics(np.stack(preds), np.asarray(targets), n, k=2)
            rows.append({**base, "model": model_name, "density_variant": variant, "split": split_tag, "family": fam, "top1": met["top1"], "top2": met["top2"], "mean_chain_distance": met["mean_chain_distance"], "n_episodes": met["n"], "confusion": str(met["confusion"]), "units": "top-k accuracy; chain distance in links"})
    return rows


def _fewshot_rows(base: dict, model_name: str, ws_calib: WindowSet, f_calib: WindowFeatures, ws_test: WindowSet, f_test: WindowFeatures, shots: list[int], seed: int) -> list[dict]:
    z_c, _ = density_input(f_calib, "representation")
    z_t, _ = density_input(f_test, "representation")
    z_c = np.concatenate([z_c, f_calib.z_gmo], 1)
    z_t = np.concatenate([z_t, f_test.z_gmo], 1)
    rng = np.random.default_rng(seed)
    meta_t = _episode_meta(ws_test, f_test)
    # test set: faulty windows of test fault episodes (label family) + S0 healthy test windows (healthy)
    test_mask = ((f_test.label == 1) & (meta_t["kind"] == "fault")) | ((meta_t["kind"] == "healthy") & (meta_t["split"] == "S0"))
    test_y = np.where(f_test.label[test_mask] == 1, meta_t["family"][test_mask], "healthy")
    rows = []
    calib_eps = {}
    for e in np.unique(f_calib.episode):
        ep = ws_calib.episodes[int(e)]
        calib_eps.setdefault(ep.family, []).append(int(e))
    for k in shots:
        train_idx = []
        for fam, eps in calib_eps.items():
            chosen = rng.choice(eps, size=min(k, len(eps)), replace=False)
            for e in chosen:
                m = f_calib.episode == e
                if fam != "healthy":
                    m = m & (f_calib.label == 1)
                train_idx.append(np.where(m)[0])
        train_idx = np.concatenate(train_idx)
        train_y = np.where(f_calib.label[train_idx] == 1, np.array([ws_calib.episodes[int(e)].family for e in f_calib.episode[train_idx]]), "healthy")
        for split_tag in ("S0", "ALL"):
            tm = test_mask & ((meta_t["split"] == "S0") if split_tag == "S0" else True)
            ty = np.where(f_test.label[tm] == 1, meta_t["family"][tm], "healthy")
            res = fewshot_attribution(z_c[train_idx], train_y, z_t[tm], ty, f_test.episode[tm], seed=seed)
            rows.append({**base, "model": model_name, "shots_per_class": k, "split": split_tag, **res, "n_classes": int(len(np.unique(train_y))), "embedding": "representation+gmo pooled window features (frozen encoder)"})
    return rows


@torch.no_grad()
def _frame_invariance_rows(base: dict, model, model_name: str, bundle: DataBundle, manifest: dict, head: ConditionalGaussian, healthy_score_std: float, device: str) -> list[dict]:
    rows = []
    dtype = torch.float32
    for eid, variants in manifest.get("episodes", {}).items():
        if eid not in bundle.episodes:
            continue
        ep = bundle.episodes[eid]
        ws = WindowSet([ep], bundle.window, bundle.stride_train, device)
        chain = tool_chain(bundle.base_chain, ep.tool_id)
        tc0 = TorchChain.from_chain(chain, dtype=dtype, device=device)
        f0 = extract_features(model, ws, tc0, device, inertia_override=tc0.inertia)
        z0, _ = density_input(f0, "representation")
        s0 = head.nll(z0, f0.ctx)
        for v, H in enumerate(variants):
            frames = [SE3.from_matrix(np.asarray(h)) for h in H]
            new_chain, _ = chain.reparameterize(frames)
            tc1 = TorchChain.from_chain(new_chain, dtype=dtype, device=device)
            f1 = extract_features(model, ws, tc1, device, inertia_override=tc1.inertia)
            z1, _ = density_input(f1, "representation")
            s1 = head.nll(z1, f1.ctx)
            d_scale = max(float(np.abs(f0.delta_pool).max()), 1e-9)
            z_scale = max(float(np.abs(z0).max()), 1e-9)
            rows.append({**base, "model": model_name, "episode_id": eid, "variant": v, "kind": ep.kind, "family": ep.family, "split": ep.split,
                         "delta_tau_pooled_max_abs_drift": float(np.abs(f1.delta_pool - f0.delta_pool).max()), "delta_tau_relative_drift": float(np.abs(f1.delta_pool - f0.delta_pool).max() / d_scale),
                         "z_relative_drift": float(np.abs(z1 - z0).max() / z_scale), "score_abs_drift_max": float(np.abs(s1 - s0).max()), "score_drift_in_healthy_std": float(np.abs(s1 - s0).max() / max(healthy_score_std, 1e-9)),
                         "score_auroc_variant_vs_canonical": safe_auroc(np.r_[np.ones(len(s1)), np.zeros(len(s0))], np.r_[s1, s0]), "units": "N m (pooled delta tau); score units"})
    return rows


@torch.no_grad()
def _latency_rows(base: dict, model, model_name: str, ws: WindowSet, tc: TorchChain, device: str, n_params: int) -> list[dict]:
    rows = []
    b = ws.batch(list(range(min(256, len(ws)))), device)
    for _ in range(2):
        model(b, tc)
    if device.startswith("cuda"):
        torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(5):
        model(b, tc)
    if device.startswith("cuda"):
        torch.cuda.synchronize()
    per_batch = (time.time() - t0) / 5
    rows.append({**base, "model": model_name, "device": device, "batch_windows": int(b["q"].shape[0]), "window_samples": ws.window, "latency_ms_per_batch": per_batch * 1e3, "latency_us_per_window": per_batch / b["q"].shape[0] * 1e6, "n_params": n_params, "units": "ms / us"})
    # single-window CPU latency (one 128-sample window)
    model_cpu = model.to("cpu")
    tc_cpu = tc.to(device="cpu")
    b1 = ws.batch([0], "cpu")
    for _ in range(2):
        model_cpu(b1, tc_cpu)
    t0 = time.time()
    for _ in range(5):
        model_cpu(b1, tc_cpu)
    rows.append({**base, "model": model_name, "device": "cpu", "batch_windows": 1, "window_samples": ws.window, "latency_ms_per_batch": (time.time() - t0) / 5 * 1e3, "latency_us_per_window": (time.time() - t0) / 5 * 1e6, "n_params": n_params, "units": "ms / us"})
    model.to(device)
    return rows


def evaluate_run(model, run_info: dict, train_ids: list[str], bundle: DataBundle, cfg: dict, base_row: dict, device: str, *, full: bool, frame_manifest: dict | None, shots: list[int], seed: int, quantile: float, log: list[str] | None = None) -> dict[str, list[dict]]:
    """Return result rows for every table for one trained run."""
    dt = float(cfg["simulation"]["control_dt_s"])
    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=device)
    model.eval()
    ws_train = WindowSet(bundle.subset(train_ids), bundle.window, bundle.stride_train, device)
    ws_val = WindowSet(bundle.subset(bundle.val_ids), bundle.window, bundle.stride_train, device)
    ws_test = WindowSet(bundle.subset(bundle.test_ids), bundle.window, bundle.stride_eval, device)
    t0 = time.time()
    f_train = extract_features(model, ws_train, tc, device)
    f_val = extract_features(model, ws_val, tc, device)
    f_test = extract_features(model, ws_test, tc, device)
    if log is not None:
        log.append(f"  features extracted train={len(f_train.label)} val={len(f_val.label)} test={len(f_test.label)} ({time.time() - t0:.0f}s)")
    base = {**base_row, "n_train_episodes": len(train_ids), "n_params": run_info.get("n_params", 0), "checkpoint_sha256": run_info.get("checkpoint_sha256", "")}
    model_name = run_info["name"]
    out: dict[str, list[dict]] = {k: [] for k in ("healthy_prediction", "event_detection", "ood_detection", "localization", "fewshot", "frame_invariance", "latency", "heads")}

    # ---- R1 healthy prediction per split (post- vs pre-correction)
    meta_t = _episode_meta(ws_test, f_test)
    for split in SPLITS + ("OOD",):
        m = (meta_t["kind"] == "healthy") & ((np.isin(meta_t["split"], ["S1", "S2", "S3", "S4"])) if split == "OOD" else (meta_t["split"] == split))
        if m.sum() == 0:
            continue
        post = np.sqrt(f_test.resid_ms[m].mean(0))
        pre = np.sqrt(f_test.pre_ms[m].mean(0))
        out["healthy_prediction"].append({**base, "model": model_name, "split": split, "n_windows": int(m.sum()), "torque_rmse_post_nm": float(np.sqrt(f_test.resid_ms[m].mean())), "torque_rmse_pre_nm": float(np.sqrt(f_test.pre_ms[m].mean())),
                                          "rmse_ratio_post_over_pre": float(np.sqrt(f_test.resid_ms[m].mean()) / max(np.sqrt(f_test.pre_ms[m].mean()), 1e-9)), **{f"rmse_post_j{j + 1}": float(post[j]) for j in range(len(post))}, **{f"rmse_pre_j{j + 1}": float(pre[j]) for j in range(len(pre))}, "units": "N m"})
    val_m = np.ones(len(f_val.label), dtype=bool)
    out["healthy_prediction"].append({**base, "model": model_name, "split": "VAL", "n_windows": int(val_m.sum()), "torque_rmse_post_nm": float(np.sqrt(f_val.resid_ms.mean())), "torque_rmse_pre_nm": float(np.sqrt(f_val.pre_ms.mean())), "rmse_ratio_post_over_pre": float(np.sqrt(f_val.resid_ms.mean()) / max(np.sqrt(f_val.pre_ms.mean()), 1e-9)), "units": "N m"})

    # ---- R2/R3 heads
    heads: dict[str, ConditionalGaussian] = {}
    scores_by_variant: dict[str, np.ndarray] = {}
    variants = list(DENSITY_VARIANTS) + (["gmo_only"] if model_name == "rnea_only" else [])
    for variant in variants:
        z_tr, slices = density_input(f_train, variant)
        z_va, _ = density_input(f_val, variant)
        z_te, _ = density_input(f_test, variant)
        for conditional in ((True, False) if variant == "representation" else (True,)):
            head = ConditionalGaussian(conditional=conditional, covariance="lowrank", rank=8).fit(z_tr, f_train.ctx, slices)
            s_va = head.nll(z_va, f_val.ctx)
            s_te = head.nll(z_te, f_test.ctx)
            thr = healthy_quantile_threshold(s_va, quantile)
            vname = variant if conditional else variant + "_unconditional"
            heads[vname] = head
            scores_by_variant[vname] = s_te
            out["heads"].append({**base, "model": model_name, "density_variant": vname, "z_dim": int(z_tr.shape[1]), "threshold": thr, "val_nll_mean": float(s_va.mean()), "train_nll_mean": float(head.nll(z_tr, f_train.ctx).mean()), "n_train_windows": int(len(z_tr))})
            det, ood = _detection_rows(base, model_name, vname, head, thr, ws_test, f_test, s_te, dt, s_va)
            out["event_detection"] += det
            out["ood_detection"] += ood
            if conditional and variant in ("residual_only", "representation"):
                out["localization"] += _localization_rows(base, model_name, vname, head, z_va, f_val.ctx, ws_test, f_test, z_te)
    if log is not None:
        log.append(f"  heads/detection/localization done ({time.time() - t0:.0f}s)")
    if full:
        ws_calib = WindowSet(bundle.subset(bundle.calib_ids), bundle.window, bundle.stride_train, device)
        f_calib = extract_features(model, ws_calib, tc, device)
        out["fewshot"] += _fewshot_rows(base, model_name, ws_calib, f_calib, ws_test, f_test, shots, seed)
        if frame_manifest is not None:
            head = heads["representation"]
            z_va, _ = density_input(f_val, "representation")
            out["frame_invariance"] += _frame_invariance_rows(base, model, model_name, bundle, frame_manifest, head, float(head.nll(z_va, f_val.ctx).std()), device)
        out["latency"] += _latency_rows(base, model, model_name, ws_test, tc, device, int(run_info.get("n_params", 0)))
        if log is not None:
            log.append(f"  few-shot/frame/latency done ({time.time() - t0:.0f}s)")
    return out
