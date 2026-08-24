"""Shared unified-baseline model primitives.

Each ``fit_*`` returns a closure ``score(windows) -> per-window scores`` so the
same frozen models serve datasets with different windowing (voraus W=50,
AURSAD W=100, RoAD W=50). Definitions are verbatim extractions of
voraus_unified's model code (same hyperparameters, same seeds semantics).
"""

from __future__ import annotations

import numpy as np

CLASSICAL = ("pca_spe", "mahalanobis", "iforest", "ocsvm")
NEURAL = ("window_ae", "gru_ae", "tcn_ae", "gru_pred")


def fit_classical(name: str, train_w: np.ndarray, seed: int):
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
        def score(wn):
            x = wn.reshape(len(wn), -1)
            r = p.inverse_transform(p.transform(x))
            return ((x - r) ** 2).mean(1)
    elif name == "mahalanobis":
        lw = LedoitWolf().fit(ztr)
        prec, mu = lw.precision_, ztr.mean(0)
        def score(wn):
            z = p.transform(wn.reshape(len(wn), -1)) - mu
            return np.einsum("ij,jk,ik->i", z, prec, z)
    elif name == "iforest":
        f = IsolationForest(n_estimators=200, random_state=seed).fit(ztr)
        def score(wn):
            return -f.score_samples(p.transform(wn.reshape(len(wn), -1)))
    elif name == "ocsvm":
        sv = OneClassSVM(nu=0.05, kernel="rbf", gamma="scale").fit(
            ztr[rng.choice(len(ztr), min(15000, len(ztr)), replace=False)]
        )
        def score(wn):
            return -sv.decision_function(p.transform(wn.reshape(len(wn), -1)))
    else:
        raise ValueError(name)
    return score


def fit_neural(name: str, train_w: np.ndarray, seed: int,
               epochs: int = 15, batch: int = 256):
    import torch
    import torch.nn as nn

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)
    np.random.seed(seed)
    n_ch = train_w.shape[2]
    W = train_w.shape[1]

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
                out, tgt = fwd(xb[:, :-1]), xb[:, 1:]
            else:
                out, tgt = fwd(xb), xb
            loss = ((out - tgt) ** 2).mean()
            opt.zero_grad(); loss.backward(); opt.step()

    def score(wn, batch_sz: int = 256):
        out = []
        with torch.no_grad():
            for i in range(0, len(wn), batch_sz):
                xb = torch.tensor(wn[i : i + batch_sz], dtype=torch.float32).to(device)
                if name == "gru_pred":
                    err = ((fwd(xb[:, :-1]) - xb[:, 1:]) ** 2).mean(dim=(1, 2))
                else:
                    err = ((fwd(xb) - xb) ** 2).mean(dim=(1, 2))
                out.append(err.cpu().numpy())
        return np.concatenate(out) if out else np.empty((0,))
    return score


def fit_model(name: str, train_w: np.ndarray, seed: int):
    if name in CLASSICAL:
        return fit_classical(name, train_w, seed)
    if name in NEURAL:
        return fit_neural(name, train_w, seed)
    raise ValueError(name)
