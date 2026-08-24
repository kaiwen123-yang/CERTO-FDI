"""Shared ME-AD loading + the B8 anchor (frozen).

Inputs (frozen): RAW 24 channels q_1..6, dq_1..6, ddq_1..6, tau_1..6 (contract
7.3 L0 wording). tau_MAT_* (undocumented) and *_filt_* (derived duplicates)
are EXCLUDED from model inputs. Cycle is the sample unit; windows W=100
stride 50 inherit the cycle id; cycle score = window MEAN (project-frozen
aggregator). Standardization fitted on fit-cycles only.

B8 anchor = `mvt_flow_adapted`: the OFFICIAL voraus-AD NormalizingFlow
architecture + loss + hyperparameters (frozen GPU checkout), instantiated on
each dataset's (channels, window) tensors. This is an ADAPTED anchor, not the
native voraus result; rows are labeled accordingly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MEAD = Path("/mnt/g/CERTO-FDI/03_data/public/me_ad/extracted_v1/ME-AD")
RAW24 = ([f"q_{i}" for i in range(1, 7)] + [f"dq_{i}" for i in range(1, 7)]
         + [f"ddq_{i}" for i in range(1, 7)] + [f"tau_{i}" for i in range(1, 7)])
W, STRIDE = 100, 50
TASKS = [f"Task{i}" for i in range(1, 8)]
SEEDS = (260824, 260825, 260826)

sys.path.insert(0, str(Path.home() / "research/CERTO-FDI-BASELINES/voraus-ad-dataset-gpu"))


def load_task(task: str):
    """Return dict split -> list of per-cycle raw-24 float32 arrays."""
    out = {}
    for split in ("train", "healthy", "faulty"):
        d = MEAD / "Tasks" / task / split
        files = sorted(d.glob("cleaned_dataset_*.pkl"),
                       key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        arrs = []
        for f in files:
            df = pd.read_pickle(f)
            arrs.append(df[RAW24].to_numpy(dtype=np.float32))
        out[split] = arrs
    return out


def cycle_windows(arr: np.ndarray, mu, sd) -> np.ndarray:
    x = (arr - mu) / sd
    if len(x) < W:
        x = np.concatenate([x, np.zeros((W - len(x), x.shape[1]), np.float32)])
    idx = np.arange(0, len(x) - W + 1, STRIDE)
    return np.stack([x[i:i + W] for i in idx]).astype(np.float32)


def fit_stats(arrs):
    cat = np.concatenate(arrs, 0)
    mu, sd = cat.mean(0), cat.std(0)
    return mu, np.where(sd < 1e-9, 1, sd)


def fit_mvt_flow_adapted(train_w: np.ndarray, seed: int, epochs: int = 70):
    """Official NormalizingFlow (architecture/loss/optimizer/schedule) on
    generic (N, W, C) windows. Returns score(windows)->per-window NLL."""
    import torch
    from configuration import Configuration
    from normalizing_flow import NormalizingFlow, get_loss, get_loss_per_sample

    torch.manual_seed(seed); np.random.seed(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    cfg = Configuration(
        columns="machine", epochs=epochs, frequencyDivider=1, trainGain=1.0,
        seed=seed, batchsize=32, nCouplingBlocks=4, clamp=1.2,
        learningRate=8e-4, normalize=True, pad=True, nHiddenLayers=0,
        scale=2, kernelSize1=13, dilation1=2, kernelSize2=1, dilation2=1,
        kernelSize3=1, dilation3=1, milestones=[11, 61], gamma=0.1)
    n_signals, n_times = train_w.shape[2], train_w.shape[1]
    model = NormalizingFlow((n_signals, n_times), cfg).float().to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate)
    sch = torch.optim.lr_scheduler.MultiStepLR(opt, milestones=cfg.milestones, gamma=cfg.gamma)
    x_all = torch.tensor(train_w.transpose(0, 2, 1), dtype=torch.float32)  # (N, C, T)
    n = len(x_all)
    for _ in range(cfg.epochs):
        perm = torch.randperm(n)
        for i in range(0, n, cfg.batchsize):
            xb = x_all[perm[i:i + cfg.batchsize]].to(dev)
            opt.zero_grad()
            z, jac = model.forward(xb)
            jac = torch.sum(jac, dim=tuple(range(1, jac.dim())))
            loss = get_loss(z, jac)
            loss.backward(); opt.step()
        sch.step()

    def score(wn: np.ndarray, batch: int = 256) -> np.ndarray:
        out = []
        with torch.no_grad():
            for i in range(0, len(wn), batch):
                xb = torch.tensor(wn[i:i + batch].transpose(0, 2, 1), dtype=torch.float32).to(dev)
                z, jac = model.forward(xb)
                jac = torch.sum(jac, dim=tuple(range(1, jac.dim())))
                out.append(get_loss_per_sample(z, jac).cpu().numpy())
        return np.concatenate(out)
    return score
