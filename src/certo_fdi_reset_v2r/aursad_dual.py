"""A0-A2: AURSAD dual-protocol experiment (frozen before results).

PROTOCOL N (native): EXACT replication of the official loader's split
semantics (aursad v0.1.13, frozen repo): operations ordered by sample_nr,
per-operation single label, subsample_freq=2, sklearn train_test_split(
train_size=0.7, random_state=42, stratify=op_labels). Windows are built
WITHIN each side (as the official generator does) — so no window ever
crosses the split by construction; the leakage axis is same-workpiece /
session near-duplication across randomly-split operations, plus temporal
drift. Models: the official repo ships NO model code (notebooks only), so
classifiers are FAITHFUL_NATIVE_POLICY approximations of the paper's
supervised setting: logistic regression, MLP, 1D-CNN (ResNet-lite) — all
window-level 5-class classification (classes 0,1,2,3,5; class 4 n=3 ops
reported separately, never in macro).

PROTOCOL H (honest): identical pipeline, but operations are split by FILE
ORDER (first 70% train, last 30% test) — the most conservative group split
available (no workpiece/session IDs exist; recorded as such). Class balance
shifts naturally; that is part of deployment honesty.

Shared frozen choices: window W=100 stride 50, cap 40 windows/op,
standardize from train side only, float32, stochastic classifiers seeds
260824-26, logistic deterministic (1 fit + op-bootstrap), metrics =
macro-F1 over {0,1,2,3,5} + per-class F1 + accuracy; inflation effect size =
native - honest with 2000-resample operation-level bootstrap CIs.

Leakage quantification: exact duplicate window hashes across sides;
1-NN L2 distance of 2000 sampled test windows to the train side (both
protocols); same-operation-across-split verification (must be 0 in both —
correcting V2's 'sliding-window random split' overstatement).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import h5py
import numpy as np

H5 = Path("/mnt/g/CERTO-FDI/03_data/public/aursad/AURSAD.h5")
RUN = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r/aursad")
W, STRIDE, CAP = 100, 50, 40
SEEDS = (260824, 260825, 260826)
CLASSES = (0, 1, 2, 3, 5)


def load_ops_subsampled():
    with h5py.File(H5, "r") as f:
        g = f["complete_data"]
        b1 = [c.decode() for c in g["block1_items"][:]]
        feat_idx = [i for i, c in enumerate(b1) if c != "timestamp"]
        feats = g["block1_values"][:, :].astype(np.float32)[:, feat_idx]
        sn = g["block3_values"][:, 0]
        b2 = [c.decode() for c in g["block2_items"][:]]
        lab = g["block2_values"][:, b2.index("label")].astype(np.int64)
    feats, sn, lab = feats[::2], sn[::2], lab[::2]          # official subsample_freq=2
    bounds = np.flatnonzero(np.diff(sn)) + 1
    starts = np.concatenate([[0], bounds])
    ends = np.concatenate([bounds, [len(sn)]])
    ops = [{"cls": int(lab[st:en].max()), "slice": (int(st), int(en)), "order": k}
           for k, (st, en) in enumerate(zip(starts, ends))]
    return feats, ops


def windows_for(feats, o, mu, sd, rng):
    st, en = o["slice"]
    x = (feats[st:en] - mu) / sd
    if len(x) < W:
        x = np.concatenate([x, np.zeros((W - len(x), x.shape[1]), np.float32)])
    idx = np.arange(0, len(x) - W + 1, STRIDE)
    if len(idx) > CAP:
        idx = idx[np.sort(rng.choice(len(idx), CAP, replace=False))]
    return np.stack([x[i:i + W] for i in idx]).astype(np.float32)


def build_side(feats, ops_side, mu, sd, seed):
    rng = np.random.default_rng(seed)
    xs, ys, gids = [], [], []
    for o in ops_side:
        w = windows_for(feats, o, mu, sd, rng)
        xs.append(w)
        ys.append(np.full(len(w), o["cls"]))
        gids.append(np.full(len(w), o["order"]))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(gids)


# ------------------------------------------------------------------ models --

def fit_logistic(Xtr, ytr, seed):
    from sklearn.linear_model import LogisticRegression
    from sklearn.decomposition import PCA
    rng = np.random.default_rng(seed)
    flat = Xtr.reshape(len(Xtr), -1)
    p = PCA(n_components=60, random_state=seed).fit(
        flat[rng.choice(len(flat), min(20000, len(flat)), replace=False)])
    clf = LogisticRegression(max_iter=2000, multi_class="multinomial").fit(p.transform(flat), ytr)
    return lambda X: clf.predict(p.transform(X.reshape(len(X), -1)))


def fit_torch(kind, Xtr, ytr, seed, epochs=8, batch=256):
    import torch
    import torch.nn as nn
    torch.manual_seed(seed); np.random.seed(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    n_ch = Xtr.shape[2]
    n_cls = int(ytr.max()) + 1
    if kind == "mlp":
        net = nn.Sequential(nn.Flatten(), nn.Linear(W * n_ch, 256), nn.ReLU(),
                            nn.Linear(256, 128), nn.ReLU(), nn.Linear(128, n_cls)).to(dev)
    else:  # resnet1d-lite
        class Blk(nn.Module):
            def __init__(s, c):
                super().__init__()
                s.c1 = nn.Conv1d(c, c, 5, padding=2); s.b1 = nn.BatchNorm1d(c)
                s.c2 = nn.Conv1d(c, c, 5, padding=2); s.b2 = nn.BatchNorm1d(c)
                s.a = nn.ReLU()
            def forward(s, x):
                return s.a(x + s.b2(s.c2(s.a(s.b1(s.c1(x))))))
        net = nn.Sequential(
            nn.Conv1d(n_ch, 64, 7, stride=2, padding=3), nn.BatchNorm1d(64), nn.ReLU(),
            Blk(64), Blk(64), nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Linear(64, n_cls)).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    lossf = nn.CrossEntropyLoss()
    Xt = torch.tensor(Xtr.transpose(0, 2, 1) if kind == "resnet" else Xtr, dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.long)
    for _ in range(epochs):
        perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), batch):
            xb = Xt[perm[i:i + batch]].to(dev); yb = yt[perm[i:i + batch]].to(dev)
            opt.zero_grad(); loss = lossf(net(xb), yb); loss.backward(); opt.step()
    def predict(X):
        out = []
        with torch.no_grad():
            for i in range(0, len(X), 512):
                xb = torch.tensor(
                    X[i:i + 512].transpose(0, 2, 1) if kind == "resnet" else X[i:i + 512],
                    dtype=torch.float32).to(dev)
                out.append(net(xb).argmax(1).cpu().numpy())
        return np.concatenate(out)
    return predict


def metrics_block(y_true, y_pred, gids, n_boot=2000, seed=260824):
    from sklearn.metrics import f1_score, accuracy_score
    y_true = np.asarray(y_true); y_pred = np.asarray(y_pred)
    remap = {c: c for c in CLASSES}
    mask = np.isin(y_true, CLASSES)
    yt, yp, g = y_true[mask], y_pred[mask], gids[mask]
    macro = f1_score(yt, yp, labels=list(CLASSES), average="macro", zero_division=0)
    per = {int(c): float(f1_score(yt == c, yp == c, zero_division=0)) for c in CLASSES}
    acc = accuracy_score(yt, yp)
    rng = np.random.default_rng(seed)
    ops = np.unique(g)
    boots = []
    for _ in range(n_boot):
        pick = rng.choice(ops, len(ops), replace=True)
        m = np.isin(g, pick)
        boots.append(f1_score(yt[m], yp[m], labels=list(CLASSES), average="macro", zero_division=0))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"macro_f1": float(macro), "macro_f1_ci95": [float(lo), float(hi)],
            "accuracy": float(acc), "per_class_f1": per, "n_windows": int(mask.sum()),
            "n_ops": int(len(ops))}


def duplicate_audit(Xtr, Xte, gtr, gte, seed):
    rng = np.random.default_rng(seed)
    def h(a):
        return hashlib.sha1(np.ascontiguousarray(a).tobytes()).hexdigest()
    tr_hashes = {h(Xtr[i]) for i in rng.choice(len(Xtr), min(30000, len(Xtr)), replace=False)}
    te_idx = rng.choice(len(Xte), min(10000, len(Xte)), replace=False)
    exact = sum(1 for i in te_idx if h(Xte[i]) in tr_hashes)
    from sklearn.neighbors import NearestNeighbors
    tr_flat = Xtr.reshape(len(Xtr), -1)
    sub = tr_flat[rng.choice(len(tr_flat), min(20000, len(tr_flat)), replace=False)]
    nn = NearestNeighbors(n_neighbors=1).fit(sub)
    te_s = Xte.reshape(len(Xte), -1)[rng.choice(len(Xte), min(2000, len(Xte)), replace=False)]
    d, _ = nn.kneighbors(te_s)
    same_op = len(set(np.unique(gtr)) & set(np.unique(gte)))
    return {"exact_dup_rate_sampled": exact / len(te_idx),
            "nn_l2_p05_p50_p95": [float(np.percentile(d, q)) for q in (5, 50, 95)],
            "same_operation_across_split": same_op}


def main():
    from sklearn.model_selection import train_test_split
    RUN.mkdir(parents=True, exist_ok=True)
    feats, ops = load_ops_subsampled()
    eligible = [o for o in ops if o["cls"] in CLASSES]
    c4 = [o for o in ops if o["cls"] == 4]
    labels = np.array([o["cls"] for o in eligible])

    tr_n, te_n = train_test_split(eligible, train_size=0.7, random_state=42, stratify=labels)
    n_split = int(0.7 * len(eligible))
    tr_h, te_h = eligible[:n_split], eligible[n_split:]

    results = {"_meta": {"n_ops_eligible": len(eligible), "n_ops_class4_separate": len(c4),
                         "W": W, "stride": STRIDE, "cap": CAP,
                         "native_split": "train_test_split(0.7, rs=42, stratify) op-level (official semantics)",
                         "honest_split": "file-order temporal 70/30 op-level"}}
    for proto, (tr, te) in (("native", (tr_n, te_n)), ("honest", (tr_h, te_h))):
        raw = np.concatenate([feats[o["slice"][0]:o["slice"][1]] for o in tr[:500]])
        mu, sd = raw.mean(0), raw.std(0); sd = np.where(sd < 1e-9, 1, sd)
        Xtr, ytr, gtr = build_side(feats, tr, mu, sd, SEEDS[0])
        Xte, yte, gte = build_side(feats, te, mu, sd, SEEDS[0])
        results[f"{proto}_dup_audit"] = duplicate_audit(Xtr, Xte, gtr, gte, SEEDS[0])
        print(f"[{proto}] train {Xtr.shape} test {Xte.shape} dup={results[f'{proto}_dup_audit']}", flush=True)
        out_path = RUN / "dual_protocol_results.json"
        if out_path.exists():
            results.update(json.loads(out_path.read_text()))
        lkey = f"{proto}_logistic_seed260824"
        if lkey not in results:
            pred = fit_logistic(Xtr, ytr, SEEDS[0])
            results[lkey] = metrics_block(yte, pred(Xte), gte)
            out_path.write_text(json.dumps(results, indent=2))
        print(f"[{proto}] logistic macroF1={results[lkey]['macro_f1']:.3f}", flush=True)
        for kind in ("mlp", "resnet"):
            for seed in SEEDS:
                key = f"{proto}_{kind}_seed{seed}"
                if key in results:
                    print(f"[skip] {key}", flush=True)
                    continue
                t0 = time.time()
                pred = fit_torch(kind, Xtr, ytr, seed)
                results[key] = metrics_block(yte, pred(Xte), gte)
                results[key]["wall_s"] = round(time.time() - t0, 1)
                out_path.write_text(json.dumps(results, indent=2))
                print(f"[{proto}] {kind} s{seed} macroF1={results[key]['macro_f1']:.3f} "
                      f"({results[key]['wall_s']}s)", flush=True)
    print("wrote dual_protocol_results.json", flush=True)


if __name__ == "__main__":
    main()
