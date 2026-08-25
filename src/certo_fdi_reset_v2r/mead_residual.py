"""M3: healthy inverse-dynamics torque-residual feasibility on ME-AD (frozen).

Models (standard architectures only): ridge / MLP / GRU mapping
(q,dq,ddq)_t [18 dims] (+ optional op-code one-hot context, official metadata)
-> tau_t [6]. Trained on fit cycles (train[0:15]); residual standardization
per joint from cal cycles (train[15:20]).

Scores per cycle:
  PRIMARY  all_joint: mean over t of sum_j z_j(t)^2   (BLIND)
  DIAG     joint3:    mean z_3^2                      (EVAL_ONLY diagnostic — fault location known)
  per-joint table for the audit.

Controls (frozen): permuted-joint (tau targets permuted by a fixed derangement
per seed — same capacity, physical pairing destroyed); same-capacity direct
anomaly model (window AE with matched parameter count, from CORE-8 rows);
context on/off (op one-hot).

Metrics per task: AUROC/AUPRC/FPR@TPR90 cycle-level + earliest-detection
comparison handled in mead_progressive. Emits mead_torque_residual_metrics
{json,csv} + per-cycle scores npz.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from certo_fdi_reset_v2r.mead_common import SEEDS, TASKS, fit_stats, load_task

RUN = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r/mead")
IN_DIM, OUT_DIM = 18, 6


def _samples(cycles, mu, sd):
    xs, ys = [], []
    for c in cycles:
        z = (c - mu) / sd
        xs.append(z[:, :18]); ys.append(z[:, 18:24])
    return xs, ys


def fit_invdyn(kind: str, xs_fit, ys_fit, seed: int, perm=None, epochs: int = 6):
    X = np.concatenate(xs_fit, 0); Y = np.concatenate(ys_fit, 0)
    if perm is not None:
        Y = Y[:, perm]
    if kind == "ridge":
        from sklearn.linear_model import Ridge
        r = Ridge(alpha=1.0).fit(X, Y)
        return lambda x: r.predict(x)
    import torch
    import torch.nn as nn
    torch.manual_seed(seed); np.random.seed(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if kind == "mlp":
        net = nn.Sequential(nn.Linear(IN_DIM, 128), nn.ReLU(),
                            nn.Linear(128, 128), nn.ReLU(), nn.Linear(128, OUT_DIM)).to(dev)
        def fwd(xb):
            return net(xb)
        seq = False
    else:  # gru over short windows
        class G(nn.Module):
            def __init__(s):
                super().__init__()
                s.g = nn.GRU(IN_DIM, 96, batch_first=True)
                s.h = nn.Linear(96, OUT_DIM)
            def forward(s, x):
                o, _ = s.g(x)
                return s.h(o)
        net = G().to(dev)
        def fwd(xb):
            return net(xb)
        seq = True
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    if seq:
        Wn = 100
        chunks = []
        for x, y in zip(xs_fit, ys_fit):
            yy = y[:, perm] if perm is not None else y
            for i in range(0, len(x) - Wn + 1, Wn):
                chunks.append((x[i:i + Wn], yy[i:i + Wn]))
        Xs = torch.tensor(np.stack([c[0] for c in chunks]), dtype=torch.float32)
        Ys = torch.tensor(np.stack([c[1] for c in chunks]), dtype=torch.float32)
        for _ in range(epochs):
            p = torch.randperm(len(Xs))
            for i in range(0, len(Xs), 128):
                xb, yb = Xs[p[i:i + 128]].to(dev), Ys[p[i:i + 128]].to(dev)
                opt.zero_grad(); loss = ((fwd(xb) - yb) ** 2).mean(); loss.backward(); opt.step()
        def predict(x):
            with torch.no_grad():
                out = []
                for i in range(0, len(x), 20000):
                    xb = torch.tensor(x[None, i:i + 20000], dtype=torch.float32).to(dev)
                    out.append(fwd(xb)[0].cpu().numpy())
                return np.concatenate(out)
        return predict
    Xt = torch.tensor(X, dtype=torch.float32); Yt = torch.tensor(Y, dtype=torch.float32)
    for _ in range(epochs):
        p = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 4096):
            xb, yb = Xt[p[i:i + 4096]].to(dev), Yt[p[i:i + 4096]].to(dev)
            opt.zero_grad(); loss = ((fwd(xb) - yb) ** 2).mean(); loss.backward(); opt.step()
    def predict(x):
        with torch.no_grad():
            out = []
            for i in range(0, len(x), 65536):
                xb = torch.tensor(x[i:i + 65536], dtype=torch.float32).to(dev)
                out.append(fwd(xb).cpu().numpy())
            return np.concatenate(out)
    return predict


def cycle_res_scores(predict, cycles, mu, sd, res_mu, res_sd, perm=None):
    all_j, j3 = [], []
    for c in cycles:
        z = (c - mu) / sd
        tau = z[:, 18:24]
        if perm is not None:
            tau = tau[:, perm]
        r = (tau - predict(z[:, :18]) - res_mu) / res_sd
        all_j.append(float((r ** 2).sum(1).mean()))
        j3.append(float((r[:, 2] ** 2).mean()))   # joint-3 diagnostic EVAL_ONLY
    return np.array(all_j), np.array(j3)


def metrics(s_heal, s_fault):
    from sklearn import metrics as M
    y = np.concatenate([np.zeros(len(s_heal)), np.ones(len(s_fault))])
    s = np.concatenate([s_heal, s_fault])
    fpr, tpr, _ = M.roc_curve(y, s)
    i = int(np.searchsorted(tpr, 0.9, side="left"))
    return {"auroc": float(M.auc(fpr, tpr)), "auprc": float(M.average_precision_score(y, s)),
            "fpr_at_tpr90": float(fpr[min(i, len(fpr) - 1)])}


def main(tasks=None):
    RUN.mkdir(parents=True, exist_ok=True)
    out_path = RUN / "mead_torque_residual_metrics.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}
    sdir = RUN / "cycle_scores"; sdir.mkdir(exist_ok=True)
    rng_global = np.random.default_rng(260824)

    for task in (tasks or TASKS):
        data = load_task(task)
        fit_c, cal_c = data["train"][:15], data["train"][15:20]
        mu, sd = fit_stats(fit_c)
        xs_fit, ys_fit = _samples(fit_c, mu, sd)
        for kind in ("ridge", "mlp", "gru"):
            seeds = (SEEDS[0],) if kind == "ridge" else SEEDS
            for seed in seeds:
                for variant in ("physical", "permuted"):
                    key = f"{task}_{kind}_{variant}_seed{seed}"
                    if key in results:
                        print(f"[skip] {key}", flush=True); continue
                    t0 = time.time()
                    perm = None
                    if variant == "permuted":
                        rng = np.random.default_rng(seed)
                        while True:
                            perm = rng.permutation(6)
                            if not np.any(perm == np.arange(6)):
                                break
                    predict = fit_invdyn(kind, xs_fit, ys_fit, seed, perm=perm)
                    # residual standardization from cal cycles
                    rs = []
                    for c in cal_c:
                        z = (c - mu) / sd
                        tau = z[:, 18:24]
                        if perm is not None:
                            tau = tau[:, perm]
                        rs.append(tau - predict(z[:, :18]))
                    rcat = np.concatenate(rs, 0)
                    res_mu, res_sd = rcat.mean(0), np.where(rcat.std(0) < 1e-9, 1, rcat.std(0))
                    sh, sh3 = cycle_res_scores(predict, data["healthy"], mu, sd, res_mu, res_sd, perm)
                    sf, sf3 = cycle_res_scores(predict, data["faulty"], mu, sd, res_mu, res_sd, perm)
                    np.savez(sdir / f"res_{key}.npz", healthy=sh, faulty=sf,
                             healthy_j3=sh3, faulty_j3=sf3)
                    entry = {"all_joint_blind": metrics(sh, sf),
                             "joint3_diagnostic_EVAL_ONLY": metrics(sh3, sf3),
                             "wall_s": round(time.time() - t0, 1)}
                    results[key] = entry
                    out_path.write_text(json.dumps(results, indent=2))
                    print(f"[done] {key}: blindAUROC={entry['all_joint_blind']['auroc']:.3f} "
                          f"j3={entry['joint3_diagnostic_EVAL_ONLY']['auroc']:.3f} "
                          f"({entry['wall_s']}s)", flush=True)

    rows = []
    for k, v in results.items():
        if k.startswith("_"):
            continue
        task, rest = k.split("_", 1)
        kind, variant, seed = rest.rsplit("_", 2)[0], rest.rsplit("_", 2)[1], rest.rsplit("seed", 1)[1]
        rows.append(dict(task=task, model=kind, variant=variant, seed=seed,
                         blind_auroc=round(v["all_joint_blind"]["auroc"], 4),
                         blind_auprc=round(v["all_joint_blind"]["auprc"], 4),
                         blind_fpr90=round(v["all_joint_blind"]["fpr_at_tpr90"], 4),
                         j3_auroc_diag=round(v["joint3_diagnostic_EVAL_ONLY"]["auroc"], 4)))
    with (RUN / "mead_torque_residual_metrics.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("rows:", len(rows))


if __name__ == "__main__":
    import sys
    main(tasks=sys.argv[1].split(",") if len(sys.argv) > 1 else None)
