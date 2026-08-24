"""E2: CC-FDI exploration on AURSAD (audited healthy-only temporal protocol).

Contexts: movement ops (class 5, healthy) = context 'move' and part of healthy
calibration; screw ops carry progress-tertile contexts t1/t2/t3. Dev anomaly =
class c1 ONLY (c2/c3 sealed for confirmation). Negatives = class-0 test ops
(same as B-AURSAD matrix). The movement-probe AUROC must FALL under context
calibration (its rise above 0.5 is the failure mechanism).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from certo_fdi_reset_v2.benchmarks.aursad_unified import H5, W, STRIDE, load_ops, op_windows
from certo_fdi_reset_v2.benchmarks.models import fit_model
from certo_fdi_reset_v2.candidate.context_calibration import (
    ContextCalibrator, permute_contexts,
)

RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/explore"
)
SEEDS = (260824, 260825, 260826)


def op_contexts(n_windows: int, is_move: bool) -> np.ndarray:
    if is_move:
        return np.array(["move"] * n_windows)
    tert = np.linspace(0, 3, n_windows, endpoint=False).astype(int)
    return np.array([f"screw_t{t+1}" for t in tert])


def main() -> int:
    from sklearn import metrics as M

    feats, ops = load_ops()
    class0 = [o for o in ops if o["cls"] == 0]
    n_tr = int(0.7 * len(class0))
    train0, heal_test = class0[:n_tr], class0[n_tr:]
    move_all = [o for o in ops if o["cls"] == 5]
    n_mtr = int(0.7 * len(move_all))
    move_train, move_probe = move_all[:n_mtr], move_all[n_mtr:][:200]
    c1 = [o for o in ops if o["cls"] == 1]

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RUN_DIR / "e2_aursad.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else {}
    results["_protocol"] = {
        "train0": len(train0), "heal_test": len(heal_test),
        "move_train": len(move_train), "move_probe": len(move_probe),
        "dev_anomaly": "c1 only", "sealed": "c2,c3",
    }

    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        order = rng.permutation(len(train0))
        n_fit = int(0.8 * len(train0))
        fit_ops = [train0[i] for i in order[:n_fit]]
        cal0 = [train0[i] for i in order[n_fit:]]
        m_order = rng.permutation(len(move_train))
        move_cal = [move_train[i] for i in m_order[: max(40, len(move_train) // 5)]]

        raw = np.concatenate([feats[o["slice"][0]: o["slice"][1]] for o in fit_ops[:400]], 0)
        mu, sd = raw.mean(0), raw.std(0)
        sd = np.where(sd < 1e-9, 1.0, sd)

        def prep(o):
            return op_windows(feats, o["slice"], mu, sd)

        fit_w = np.concatenate([prep(o) for o in fit_ops[:400]], 0)

        for fe in ("gru_pred", "window_ae", "tcn_ae"):
            key = f"{fe}_seed{seed}"
            if key in results:
                print(f"[skip] {key}", flush=True)
                continue
            t0 = time.time()
            score = fit_model(fe, fit_w, seed)

            def group_scores(group, is_move=False):
                ws, cs, eids = [], [], []
                for k, o in enumerate(group):
                    w = prep(o)
                    ws.append(score(w))
                    cs.append(op_contexts(len(w), is_move))
                    eids.append(np.full(len(w), k))
                return np.concatenate(ws), np.concatenate(cs), np.concatenate(eids), len(group)

            s_cal0, c_cal0, _, _ = group_scores(cal0)
            s_calm, c_calm, _, _ = group_scores(move_cal, is_move=True)
            s_cal = np.concatenate([s_cal0, s_calm])
            c_cal = np.concatenate([c_cal0, c_calm])

            groups = {"heal": group_scores(heal_test), "c1": group_scores(c1),
                      "move": group_scores(move_probe, is_move=True)}

            def episode_agg(sc, eids, n):
                return np.array([sc[eids == k].mean() for k in range(n)])

            def evaluate(transform):
                out = {}
                ep = {}
                for g, (sc, cc, eids, n) in groups.items():
                    ep[g] = episode_agg(transform(sc, cc), eids, n)
                y = np.concatenate([np.ones(len(ep["c1"])), np.zeros(len(ep["heal"]))])
                s = np.concatenate([ep["c1"], ep["heal"]])
                fpr, tpr, _ = M.roc_curve(y, s)
                i = int(np.searchsorted(tpr, 0.9, side="left"))
                out["c1_auroc"] = float(M.auc(fpr, tpr))
                out["c1_auprc"] = float(M.average_precision_score(y, s))
                out["c1_fpr_at_tpr90"] = float(fpr[min(i, len(fpr) - 1)])
                ym = np.concatenate([np.ones(len(ep["move"])), np.zeros(len(ep["heal"]))])
                sm = np.concatenate([ep["move"], ep["heal"]])
                out["movement_probe_auroc"] = float(M.roc_auc_score(ym, sm))
                return out

            variants = {"marginal": evaluate(lambda s, c: s)}
            for mode in ("z", "quantile"):
                cal = ContextCalibrator(mode).fit(s_cal, c_cal)
                variants[f"ctx_{mode}"] = evaluate(cal.transform)
                pc = ContextCalibrator(mode).fit(s_cal, permute_contexts(c_cal, seed))
                variants[f"permuted_{mode}"] = evaluate(pc.transform)
            results[key] = {"variants": variants, "wall_seconds": round(time.time() - t0, 1)}
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            v = variants
            print(f"[done] {key}: c1 marg={v['marginal']['c1_auroc']:.3f} "
                  f"ctx_z={v['ctx_z']['c1_auroc']:.3f} ctx_q={v['ctx_quantile']['c1_auroc']:.3f} "
                  f"perm_z={v['permuted_z']['c1_auroc']:.3f} | moveProbe marg={v['marginal']['movement_probe_auroc']:.3f} "
                  f"ctx_z={v['ctx_z']['movement_probe_auroc']:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
