"""Shared plumbing for the Stage 1R-B runners: run layout, provenance gate, data bundle, job
execution (train + evaluate, resumable per-job JSON), and result-row schema."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import torch

from certo_fdi.experiments.common import capture_environment, load_config, seed_everything, sha256_file, utc_now, write_json
from certo_fdi.experiments.evaluation_stage1rb import evaluate_run_stage1rb
from certo_fdi.experiments.pipeline import DataBundle, load_bundle, load_checkpoint, train_model, training_subset
from certo_fdi.paths import RunLayout, create_or_resume_run, git_sha

PRIMARY_MODELS = ("chain_gnn_aug", "ligra_v2_typed")
DIAGNOSTIC_MODELS = ("rnea_gru", "ligra_free_output")
RESULT_TABLES = ("healthy_prediction", "detection", "ood_healthy", "localization", "localization_detail", "frame_invariance", "latency", "heads")
REQUIRED_COLUMNS = ("run_id", "git_sha", "config_sha256", "dataset_sha256_or_manifest_sha", "model", "seed", "status", "provisional", "strict_claim")


def common_parser(desc: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--config", required=True)
    ap.add_argument("--storage-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return ap


class Stage:
    """Run context: config, layout, provenance, logging."""

    def __init__(self, args, phase: str):
        self.args = args
        self.cfg, self.cfg_sha = load_config(args.config)
        self.repo_root = Path(args.repo_root).resolve()
        self.layout: RunLayout = create_or_resume_run(args.storage_root, args.run_id, stage=self.cfg["stage"])
        self.phase = phase
        self.lines: list[str] = []
        (self.layout.sub("config") / Path(args.config).name).write_bytes(Path(args.config).read_bytes())
        capture_environment(self.layout, self.repo_root, f"stage1rb_{phase}_start", {"config_sha256": self.cfg_sha})
        fi = self.cfg["frozen_inputs"]
        self.data_root = Path(args.data_root or self.cfg["paths"]["data_root"]) / f"{fi['dataset_profile']}_seed{fi['dataset_seed']}"
        self.device = args.device
        gate = self.layout.results / "stage1rb_provenance_gate.json"
        self.provenance = json.loads(gate.read_text()) if gate.exists() else {}
        self.manifest_sha = self.provenance.get("postgmo_manifest_sha256", "")
        self._bundle: DataBundle | None = None
        self.log(f"phase {phase} start (git {git_sha(self.repo_root)[:8]}, config {self.cfg_sha[:8]}, device {self.device})")

    def _debug_row_filter(self):
        """``debug_subset`` (smoke configs only): cap episodes per (kind, partition, family) group."""
        lim = self.cfg.get("debug_subset")
        if not lim:
            return None
        counts: dict[tuple, int] = {}

        def keep(r: dict) -> bool:
            key = (r["kind"], r["partition"], r["family"] if r["kind"] == "fault" else "healthy")
            cap = lim.get(f"{r['kind']}_{r['partition']}", lim.get("default", 10**9))
            counts[key] = counts.get(key, 0) + 1
            return counts[key] <= int(cap)

        return keep

    def log(self, msg: str) -> None:
        line = f"[{utc_now()}] {msg}"
        print(line, flush=True)
        self.lines.append(line)
        (self.layout.sub("logs") / f"stage1rb_{self.phase}.log").write_text("\n".join(self.lines) + "\n", encoding="utf-8")

    def require_provenance(self) -> bool:
        ok = self.provenance.get("gate") == "PASS" and bool(self.manifest_sha)
        if not ok:
            self.log("BLOCKED: provenance gate missing or failed (run the Phase A audit first)")
        return ok

    def require_r0(self) -> bool:
        p = self.layout.results / "stage1rb_r0_gate.json"
        ok = p.exists() and json.loads(p.read_text()).get("decision") == "PASS"
        if not ok:
            self.log("BLOCKED: R0 gate has not passed in this run")
        return ok

    @property
    def bundle(self) -> DataBundle:
        if self._bundle is None:
            t0 = time.time()
            self._bundle = load_bundle(self.cfg, self.data_root, row_filter=self._debug_row_filter())
            self.log(f"data bundle loaded: train={len(self._bundle.train_ids)} val={len(self._bundle.val_ids)} test={len(self._bundle.test_ids)} calib={len(self._bundle.calib_ids)} ({time.time() - t0:.0f}s)")
        return self._bundle

    def base_row(self, **kw) -> dict[str, Any]:
        row = {"run_id": self.layout.run_id, "git_sha": git_sha(self.repo_root), "config_sha256": self.cfg_sha, "dataset_sha256_or_manifest_sha": self.manifest_sha, "model": "", "seed": "", "split": "", "checkpoint_sha256": "", "status": "OK", "provisional": False, "strict_claim": ""}
        row.update(kw)
        return row

    def finish(self, extra: dict | None = None) -> None:
        capture_environment(self.layout, self.repo_root, f"stage1rb_{self.phase}_end", extra or {})


def train_cfg(cfg: dict) -> dict:
    t = cfg["training"]
    return {"epochs": int(t.get("epochs", 40)), "min_epochs": int(t.get("min_epochs", 15)), "patience": int(t.get("patience", 10)), "batch_size": int(t.get("batch_size", 64)), "weight_decay": float(t.get("weight_decay", 1e-6)), "grad_clip": float(t.get("grad_clip", 1.0))}


def model_cfg(cfg: dict) -> dict:
    """The ``cfg['model']`` dict expected by build_model (widths), derived from cfg['models']."""
    m = cfg["models"]
    return {"scalar_hidden_dim": int(m.get("scalar_hidden_dim", 64)), "scalar_layers": int(m.get("scalar_layers", 2)), "baseline_gru_hidden": int(m.get("baseline_gru_hidden", 80)), "ligra_v2": dict(m.get("ligra_v2", {}))}


def ensure_model_cfg(cfg: dict) -> dict:
    if "model" not in cfg:
        cfg = dict(cfg)
        cfg["model"] = model_cfg(cfg)
    return cfg


def val_healthy_rmse(model, bundle: DataBundle, device: str) -> float:
    """Healthy validation torque-correction RMSE (N m) on evaluation windows (settle period excluded)."""
    from certo_fdi.data.windows import WindowSet
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.experiments.pipeline import extract_features

    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=device)
    ws = WindowSet(bundle.subset(bundle.val_ids), bundle.window, bundle.stride_train, device, min_start=bundle.eval_min_start)
    f = extract_features(model, ws, tc, device)
    return float(np.sqrt(f.resid_ms.mean()))


def run_job(stage: Stage, name: str, frac: float, seed: int, lr: float, scheduler: str, tag: str, out_json: Path, *, evaluate: bool = True, full: bool = True, frame_manifest: dict | None = None, reevaluate: bool = False) -> dict | None:
    """Train (or load) one job and evaluate it; writes ``out_json``; returns the result dict."""
    cfg = ensure_model_cfg(stage.cfg)
    bundle = stage.bundle
    tcfg = train_cfg(cfg)
    ckpt_dir = stage.layout.sub("checkpoints")
    t0 = time.time()
    try:
        seed_everything(seed)
        train_ids = training_subset(bundle, frac, seed)
        ckpt_path = ckpt_dir / f"{name}{('_' + tag) if tag else ''}_seed{seed}_frac{len(train_ids)}ep.pt"
        if ckpt_path.exists() and (reevaluate or out_json.exists()):
            info = load_checkpoint(name, ckpt_path, bundle, cfg, stage.device)
            info["lr"], info["scheduler"], info["tag"] = lr, scheduler, tag
            stage.log(f"loaded checkpoint {ckpt_path.name}")
        else:
            info = train_model(name, seed, train_ids, bundle, cfg, ckpt_dir, stage.device, epochs=tcfg["epochs"], batch_size=tcfg["batch_size"], lr=lr, patience=tcfg["patience"], min_epochs=tcfg["min_epochs"], log=stage.lines, scheduler=scheduler, weight_decay=tcfg["weight_decay"], grad_clip=tcfg["grad_clip"], tag=tag)
            stage.log(f"trained {name} tag={tag} frac={frac} seed={seed}: params={info['n_params']} epochs={info['epochs_run']} best_val_loss={info['best_val_loss']:.4f} ({info['train_seconds']:.0f}s)")
        res: dict[str, Any] = {"train_info": [{k: v for k, v in info.items() if k != "model"}]}
        res["train_info"][0].update({"training_fraction": frac, "seed": seed, "n_train_episodes": len(train_ids), "val_healthy_rmse_nm": val_healthy_rmse(info["model"], bundle, stage.device)})
        if evaluate:
            brow = stage.base_row(seed=seed, model=info["name"], checkpoint_sha256=info["checkpoint_sha256"])
            brow["training_fraction"] = frac
            brow["config_tag"] = tag
            brow["lr"] = lr
            brow["scheduler"] = scheduler
            ev = evaluate_run_stage1rb(info["model"], info, train_ids, bundle, cfg, brow, stage.device, full=full, frame_manifest=frame_manifest, quantile=float(cfg["anomaly"]["threshold_quantile"]), log=stage.lines, acceleration_diagnostic=True)
            res.update(ev)
        write_json(out_json, res)
        stage.log(f"job done {out_json.name} ({time.time() - t0:.0f}s)")
        del info
        if stage.device.startswith("cuda"):
            torch.cuda.empty_cache()
        return res
    except Exception as e:  # pragma: no cover
        stage.log(f"FAILED {name} tag={tag} frac={frac} seed={seed}: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        write_json(out_json.with_suffix(".FAILED.json"), {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()})
        return None
