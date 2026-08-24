"""Phase B-AURSAD: unified baseline matrix under the audited protocol.

Frozen protocol (from benchmarks/aursad_audit.py findings, BEFORE any result):
  - operations are the episode unit (sample_nr); each op carries ONE label;
  - healthy = operation-class 0; anomalies = classes 1,2,3;
    class 4 EXCLUDED (n=3); class 5 (movement ops) excluded from train and
    main eval, scored separately as a benign-context false-alarm probe;
  - split: TEMPORAL BLOCKS of class-0 ops in file order — first 70% train,
    last 30% healthy test negatives (no workpiece ids exist, so random splits
    would hide near-duplicate leakage; limitation recorded);
  - features: float signal block minus timestamp; standardization fitted on
    train subset only;
  - windows W=100, stride 50 @100 Hz; operation score = MEAN over windows
    (same frozen aggregator as voraus_unified);
  - metrics: operation-level AUROC / AUPRC / FPR@TPR90 per anomaly class vs
    the same healthy negatives + macro; movement-vs-healthy AUROC as the
    context-probe diagnostic (not a gate).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import h5py
import numpy as np

from certo_fdi_reset_v2.benchmarks.models import CLASSICAL, NEURAL, fit_model

H5 = Path("/mnt/g/CERTO-FDI/03_data/public/aursad/AURSAD.h5")
RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/b_aursad"
)
W, STRIDE = 100, 50
SEEDS = (260824, 260825, 260826)


def load_ops():
    with h5py.File(H5, "r") as f:
        g = f["complete_data"]
        b1_items = [c.decode() for c in g["block1_items"][:]]
        feat_idx = [i for i, c in enumerate(b1_items) if c != "timestamp"]
        feats = g["block1_values"][:, :].astype(np.float32)[:, feat_idx]
        sn = g["block3_values"][:, 0]
        b2_items = [c.decode() for c in g["block2_items"][:]]
        lab = g["block2_values"][:, b2_items.index("label")].astype(np.int64)
    boundaries = np.flatnonzero(np.diff(sn)) + 1
    starts = np.concatenate([[0], boundaries])
    ends = np.concatenate([boundaries, [len(sn)]])
    ops = [{"cls": int(lab[st:en].max()), "slice": (int(st), int(en))}
           for st, en in zip(starts, ends)]
    return feats, ops


def op_windows(feats, sl, mu, sd):
    st, en = sl
    x = (feats[st:en] - mu) / sd
    if len(x) < W:
        x = np.concatenate([x, np.zeros((W - len(x), x.shape[1]), dtype=x.dtype)], 0)
    idx = np.arange(0, len(x) - W + 1, STRIDE)
    return np.stack([x[i : i + W] for i in idx]).astype(np.float32)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(CLASSICAL + NEURAL))
    args = parser.parse_args(argv)
    wanted = [m for m in args.models.split(",") if m]

    from sklearn import metrics as M

    feats, ops = load_ops()
    class0 = [o for o in ops if o["cls"] == 0]
    n_tr = int(0.7 * len(class0))
    train_ops, heal_test = class0[:n_tr], class0[n_tr:]
    anom = {c: [o for o in ops if o["cls"] == c] for c in (1, 2, 3)}
    move_ops = [o for o in ops if o["cls"] == 5][:200]

    rng = np.random.default_rng(SEEDS[0])
    subset = [train_ops[i] for i in sorted(rng.choice(len(train_ops), min(400, len(train_ops)), replace=False))]
    raw = np.concatenate([feats[o["slice"][0]: o["slice"][1]] for o in subset], 0)
    mu, sd = raw.mean(0), raw.std(0)
    sd = np.where(sd < 1e-9, 1.0, sd)
    train_w = np.concatenate([op_windows(feats, o["slice"], mu, sd) for o in subset], 0)
    print(f"[aursad] train ops {len(train_ops)} (fit subset {len(subset)}), heal-test {len(heal_test)}, "
          f"anom {{1:{len(anom[1])},2:{len(anom[2])},3:{len(anom[3])}}}, move probe {len(move_ops)}, "
          f"train windows {len(train_w)}", flush=True)

    groups = {"heal": heal_test, "c1": anom[1], "c2": anom[2], "c3": anom[3], "move": move_ops}

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUN_DIR / "unified_baselines.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}
    results["_protocol"] = {
        "train_class0_ops": len(train_ops), "fit_subset_ops": len(subset),
        "healthy_test_ops": len(heal_test),
        "anomaly_ops": {k: len(v) for k, v in anom.items()},
        "movement_probe_ops": len(move_ops),
        "split": "temporal 70/30 on class-0; class-4 excluded (n=3)",
        "aggregator": "window-mean (frozen)", "W": W, "stride": STRIDE,
    }

    for model in wanted:
        seeds = SEEDS if (model in NEURAL or model in ("iforest", "ocsvm")) else SEEDS[:1]
        for seed in seeds:
            key = f"{model}_seed{seed}"
            if key in results:
                print(f"[skip] {key}", flush=True)
                continue
            t0 = time.time()
            score = fit_model(model, train_w, seed)
            op_scores = {}
            for gname, group in groups.items():
                op_scores[gname] = np.array(
                    [float(np.mean(score(op_windows(feats, o["slice"], mu, sd)))) for o in group]
                )
            neg = op_scores["heal"]
            entry = {"wall_seconds": round(time.time() - t0, 1), "seed": seed}
            aurocs, auprcs, fprs = [], [], []
            for cname in ("c1", "c2", "c3"):
                pos = op_scores[cname]
                y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
                s = np.concatenate([pos, neg])
                fpr, tpr, _ = M.roc_curve(y, s)
                auroc = M.auc(fpr, tpr)
                auprc = M.average_precision_score(y, s)
                i = int(np.searchsorted(tpr, 0.9, side="left"))
                entry[cname] = {"auroc": float(auroc), "auprc": float(auprc),
                                "fpr_at_tpr90": float(fpr[min(i, len(fpr) - 1)]), "n_pos": int(len(pos))}
                aurocs.append(auroc); auprcs.append(auprc); fprs.append(entry[cname]["fpr_at_tpr90"])
            entry["macro"] = {"auroc": float(np.mean(aurocs)), "auprc": float(np.mean(auprcs)),
                              "fpr_at_tpr90": float(np.mean(fprs))}
            ym = np.concatenate([np.ones(len(op_scores["move"])), np.zeros(len(neg))])
            sm = np.concatenate([op_scores["move"], neg])
            entry["movement_context_probe_auroc"] = float(M.roc_auc_score(ym, sm))
            results[key] = entry
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(f"[done] {key}: macroAUROC={entry['macro']['auroc']:.4f} "
                  f"AUPRC={entry['macro']['auprc']:.4f} moveProbe={entry['movement_context_probe_auroc']:.3f} "
                  f"({entry['wall_seconds']}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
