"""Phase B-voraus: unified baseline matrix on voraus-AD (official split/protocol).

Universal-traditional (PCA-SPE, shrinkage Mahalanobis, IsolationForest, OCSVM)
and universal-neural (window-AE, GRU-AE, TCN-AE, GRU one-step predictor)
baselines, trained healthy-only on the OFFICIAL train split and scored with the
OFFICIAL per-anomaly-category AUROC protocol (mean over the 12 categories,
each category ROC computed against all normal test episodes — mirrors
train.py). AUPRC and FPR@TPR90 are computed the same per-category way.

FROZEN BEFORE ANY RESULT: episode score = MEAN over window scores (max is
logged as a secondary diagnostic and must not gate anything). Window W=50,
stride 25. Seeds 260824/260825/260826 for stochastic models. No test-set
tuning of any kind: all model hyperparameters are fixed here, thresholds are
not selected at all (threshold-free metrics only).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

GPU_CHECKOUT = Path.home() / "research/CERTO-FDI-BASELINES/voraus-ad-dataset-gpu"
RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/b_voraus"
)
DATASET = Path.home() / "Downloads/voraus-ad-dataset-100hz.parquet"
W, STRIDE = 50, 25
SEEDS = (260824, 260825, 260826)

sys.path.insert(0, str(GPU_CHECKOUT))


def load_official(seed: int):
    from voraus_ad import Signals, load_torch_dataloaders

    train_ds, test_ds, train_dl, test_dl = load_torch_dataloaders(
        dataset=DATASET,
        batch_size=32,
        columns=Signals.groups()["machine"],
        seed=seed,
        frequency_divider=1,
        train_gain=1.0,
        normalize=True,
        pad=True,
    )
    return train_ds, test_dl


def episode_windows(ep: np.ndarray) -> np.ndarray:
    idx = np.arange(0, max(len(ep) - W + 1, 1), STRIDE)
    if len(ep) < W:
        pad = np.zeros((W - len(ep), ep.shape[1]), dtype=ep.dtype)
        ep = np.concatenate([ep, pad], 0)
        idx = np.array([0])
    return np.stack([ep[i : i + W] for i in idx])


def collect_arrays(train_ds, test_dl):
    train_eps = [t[0].numpy() for t in train_ds] if hasattr(train_ds, "__getitem__") else []
    if not train_eps:
        raise RuntimeError("unexpected train dataset structure")
    test_eps, test_meta = [], []
    for tensors, labels in test_dl:
        arr = tensors.float().numpy()
        for j in range(arr.shape[0]):
            test_eps.append(arr[j])
            test_meta.append(
                {k: (v[j].item() if hasattr(v, "shape") else v[j]) for k, v in labels.items()}
            )
    return train_eps, test_eps, test_meta


# --------------------------------------------------------------- metrics ----

def per_category_metrics(test_meta, scores) -> dict:
    from sklearn import metrics as M

    from voraus_ad import ANOMALY_CATEGORIES

    import pandas as pd

    df = pd.DataFrame(test_meta)
    df["score"] = scores
    per_cat = {}
    aurocs, auprcs, fprs = [], [], []
    for category in ANOMALY_CATEGORIES:
        dfn = df[(df["category"] == category.name) | (~df["anomaly"])]
        y = dfn["anomaly"].astype(bool).values
        s = dfn["score"].values
        if len(np.unique(y)) < 2:
            continue
        fpr, tpr, _ = M.roc_curve(y, s, pos_label=True)
        auroc = M.auc(fpr, tpr)
        auprc = M.average_precision_score(y, s)
        idx = int(np.searchsorted(tpr, 0.9, side="left"))
        fpr_at = float(fpr[min(idx, len(fpr) - 1)])
        per_cat[category.name] = {"auroc": float(auroc), "auprc": float(auprc), "fpr_at_tpr90": fpr_at}
        aurocs.append(auroc)
        auprcs.append(auprc)
        fprs.append(fpr_at)
    return {
        "auroc_mean": float(np.mean(aurocs)),
        "auprc_mean": float(np.mean(auprcs)),
        "fpr_at_tpr90_mean": float(np.mean(fprs)),
        "per_category": per_cat,
    }


# ---------------------------------------------------------------- models ----

def classical_scores(name: str, train_w: np.ndarray, test_eps, seed: int):
    from sklearn.covariance import LedoitWolf
    from sklearn.decomposition import PCA
    from sklearn.ensemble import IsolationForest
    from sklearn.svm import OneClassSVM

    rng = np.random.default_rng(seed)
    flat_tr = train_w.reshape(len(train_w), -1)
    sub = flat_tr[rng.choice(len(flat_tr), min(20000, len(flat_tr)), replace=False)]
    p = PCA(n_components=50, random_state=seed).fit(sub)
    ztr = p.transform(flat_tr)

    if name == "pca_spe":
        rec = p.inverse_transform(ztr)
        # noise floor from training SPE distribution (no test usage)
        def score_ep(ep):
            wn = episode_windows(ep).reshape(-1, flat_tr.shape[1])
            r = p.inverse_transform(p.transform(wn))
            return ((wn - r) ** 2).mean(1)
    elif name == "mahalanobis":
        lw = LedoitWolf().fit(ztr)
        prec = lw.precision_
        mu = ztr.mean(0)
        def score_ep(ep):
            wn = episode_windows(ep).reshape(-1, flat_tr.shape[1])
            z = p.transform(wn) - mu
            return np.einsum("ij,jk,ik->i", z, prec, z)
    elif name == "iforest":
        f = IsolationForest(n_estimators=200, random_state=seed).fit(ztr)
        def score_ep(ep):
            wn = episode_windows(ep).reshape(-1, flat_tr.shape[1])
            return -f.score_samples(p.transform(wn))
    elif name == "ocsvm":
        sv = OneClassSVM(nu=0.05, kernel="rbf", gamma="scale").fit(
            ztr[rng.choice(len(ztr), min(15000, len(ztr)), replace=False)]
        )
        def score_ep(ep):
            wn = episode_windows(ep).reshape(-1, flat_tr.shape[1])
            return -sv.decision_function(p.transform(wn))
    else:
        raise ValueError(name)

    means, maxes = [], []
    for ep in test_eps:
        s = score_ep(ep)
        means.append(float(np.mean(s)))
        maxes.append(float(np.max(s)))
    return np.array(means), np.array(maxes)


def neural_scores(name: str, train_w: np.ndarray, test_eps, seed: int,
                  epochs: int = 15, batch: int = 256):
    import torch
    import torch.nn as nn

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)
    np.random.seed(seed)
    n_ch = train_w.shape[2]

    if name == "window_ae":
        d = W * n_ch
        model = nn.Sequential(
            nn.Flatten(), nn.Linear(d, 256), nn.ReLU(), nn.Linear(256, 64), nn.ReLU(),
            nn.Linear(64, 256), nn.ReLU(), nn.Linear(256, d),
        ).to(device)
        def fwd(x):
            return model(x).view(x.shape)
    elif name in ("gru_ae", "gru_pred"):
        class GruNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.enc = nn.GRU(n_ch, 96, batch_first=True)
                self.head = nn.Linear(96, n_ch)
            def forward(self, x):
                h, _ = self.enc(x)
                return self.head(h)
        model = GruNet().to(device)
        def fwd(x):
            return model(x)
    elif name == "tcn_ae":
        class Tcn(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Conv1d(n_ch, 96, 5, padding=2), nn.ReLU(),
                    nn.Conv1d(96, 32, 5, padding=4, dilation=2), nn.ReLU(),
                    nn.Conv1d(32, 96, 5, padding=4, dilation=2), nn.ReLU(),
                    nn.Conv1d(96, n_ch, 5, padding=2),
                )
            def forward(self, x):
                return self.net(x.transpose(1, 2)).transpose(1, 2)
        model = Tcn().to(device)
        def fwd(x):
            return model(x)
    else:
        raise ValueError(name)

    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    x_all = torch.tensor(train_w, dtype=torch.float32)
    n = len(x_all)
    for _ in range(epochs):
        perm = torch.randperm(n)
        for i in range(0, n, batch):
            xb = x_all[perm[i : i + batch]].to(device)
            if name == "gru_pred":
                inp, tgt = xb[:, :-1], xb[:, 1:]
                out = fwd(inp)
            else:
                inp, tgt = xb, xb
                out = fwd(inp)
            loss = ((out - tgt) ** 2).mean()
            opt.zero_grad(); loss.backward(); opt.step()

    means, maxes = [], []
    with torch.no_grad():
        for ep in test_eps:
            wn = torch.tensor(episode_windows(ep), dtype=torch.float32).to(device)
            if name == "gru_pred":
                err = ((fwd(wn[:, :-1]) - wn[:, 1:]) ** 2).mean(dim=(1, 2))
            else:
                err = ((fwd(wn) - wn) ** 2).mean(dim=(1, 2))
            s = err.cpu().numpy()
            means.append(float(np.mean(s)))
            maxes.append(float(np.max(s)))
    return np.array(means), np.array(maxes)


CLASSICAL = ("pca_spe", "mahalanobis", "iforest", "ocsvm")
NEURAL = ("window_ae", "gru_ae", "tcn_ae", "gru_pred")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(CLASSICAL + NEURAL))
    args = parser.parse_args(argv)
    wanted = [m for m in args.models.split(",") if m]

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUN_DIR / "unified_baselines.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}

    for model in wanted:
        seeds = SEEDS if model in NEURAL or model in ("iforest", "ocsvm") else SEEDS[:1]
        for seed in seeds:
            key = f"{model}_seed{seed}"
            if key in results:
                print(f"[skip] {key}", flush=True)
                continue
            t0 = time.time()
            train_ds, test_dl = load_official(seed)
            train_eps, test_eps, test_meta = collect_arrays(train_ds, test_dl)
            train_w = np.concatenate([episode_windows(e) for e in train_eps], axis=0)
            if model in CLASSICAL:
                mean_s, max_s = classical_scores(model, train_w, test_eps, seed)
            else:
                mean_s, max_s = neural_scores(model, train_w, test_eps, seed)
            entry = {
                "primary_mean_agg": per_category_metrics(test_meta, mean_s),
                "secondary_max_agg": per_category_metrics(test_meta, max_s),
                "wall_seconds": round(time.time() - t0, 1),
                "n_train_windows": int(len(train_w)),
                "seed": seed,
            }
            results[key] = entry
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(
                f"[done] {key}: AUROC(mean-agg)={entry['primary_mean_agg']['auroc_mean']:.4f} "
                f"AUPRC={entry['primary_mean_agg']['auprc_mean']:.4f} "
                f"({entry['wall_seconds']}s)",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
