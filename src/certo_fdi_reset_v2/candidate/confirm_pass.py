"""Single confirmation pass on the SEALED sets, after the survival-gate FAIL.

Not a candidate rescue: the exploration verdict (survival FAIL) is already
frozen. This pass exists so the benchmark-paper record is complete on the
sealed data under the pre-registered protocol, one shot, no tuning:
  - AURSAD classes c2, c3 (sealed in exploration): marginal vs ctx_z vs
    permuted_z for the three AE-family front-ends, seeds 260824-26.
  - voraus sample-efficiency: ocsvm marginal vs ctx_z at healthy fractions
    (0.05, 0.10, 0.25, 0.50, 1.00) of the fit split, seed 260824.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/confirm"
)
SEEDS = (260824, 260825, 260826)


def aursad_sealed() -> dict:
    from sklearn import metrics as M

    from certo_fdi_reset_v2.benchmarks.aursad_unified import load_ops, op_windows
    from certo_fdi_reset_v2.benchmarks.models import fit_model
    from certo_fdi_reset_v2.candidate.context_calibration import (
        ContextCalibrator, permute_contexts,
    )
    from certo_fdi_reset_v2.candidate.explore_aursad import op_contexts

    feats, ops = load_ops()
    class0 = [o for o in ops if o["cls"] == 0]
    n_tr = int(0.7 * len(class0))
    train0, heal_test = class0[:n_tr], class0[n_tr:]
    move_all = [o for o in ops if o["cls"] == 5]
    move_train = move_all[: int(0.7 * len(move_all))]
    sealed = {c: [o for o in ops if o["cls"] == c] for c in (2, 3)}

    out: dict = {}
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
        prep = lambda o: op_windows(feats, o["slice"], mu, sd)
        fit_w = np.concatenate([prep(o) for o in fit_ops[:400]], 0)

        for fe in ("gru_pred", "window_ae", "tcn_ae"):
            score = fit_model(fe, fit_w, seed)

            def gs(group, is_move=False):
                ws, cs, eids = [], [], []
                for k, o in enumerate(group):
                    w = prep(o)
                    ws.append(score(w)); cs.append(op_contexts(len(w), is_move))
                    eids.append(np.full(len(w), k))
                return np.concatenate(ws), np.concatenate(cs), np.concatenate(eids), len(group)

            s0, c0, _, _ = gs(cal0)
            sm, cm, _, _ = gs(move_cal, True)
            s_cal, c_cal = np.concatenate([s0, sm]), np.concatenate([c0, cm])
            heal = gs(heal_test)

            def agg(t, g):
                sc, cc, eids, n = g
                ts = t(sc, cc)
                return np.array([ts[eids == k].mean() for k in range(n)])

            for cls, group_ops in sealed.items():
                g = gs(group_ops)
                entry = {}
                for name, transform in (
                    ("marginal", lambda s, c: s),
                    ("ctx_z", ContextCalibrator("z").fit(s_cal, c_cal).transform),
                    ("permuted_z", ContextCalibrator("z").fit(s_cal, permute_contexts(c_cal, seed)).transform),
                ):
                    pos, neg = agg(transform, g), agg(transform, heal)
                    y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
                    s = np.concatenate([pos, neg])
                    fpr, tpr, _ = M.roc_curve(y, s)
                    i = int(np.searchsorted(tpr, 0.9, side="left"))
                    entry[name] = {"auroc": float(M.auc(fpr, tpr)),
                                   "auprc": float(M.average_precision_score(y, s)),
                                   "fpr_at_tpr90": float(fpr[min(i, len(fpr) - 1)])}
                out[f"c{cls}_{fe}_seed{seed}"] = entry
                print(f"[sealed] c{cls} {fe} s{seed}: " + " ".join(
                    f"{k}={v['auroc']:.3f}" for k, v in entry.items()), flush=True)
    return out


def voraus_sample_efficiency() -> dict:
    from certo_fdi_reset_v2.benchmarks.models import fit_model
    from certo_fdi_reset_v2.candidate.context_calibration import ContextCalibrator
    from certo_fdi_reset_v2.candidate.explore_voraus import (
        DATASET, episode_windows, load_actions, per_category_metrics, window_contexts,
    )
    import sys
    sys.path.insert(0, str(Path.home() / "research/CERTO-FDI-BASELINES/voraus-ad-dataset-gpu"))
    from voraus_ad import Signals, load_torch_dataloaders

    seed = SEEDS[0]
    actions = load_actions()
    train_ds, _, _, test_dl = load_torch_dataloaders(
        dataset=DATASET, batch_size=32, columns=Signals.groups()["machine"],
        seed=seed, frequency_divider=1, train_gain=1.0, normalize=True, pad=True)
    train_eps = [t[0].numpy() for t in train_ds]
    train_ids = [int(t[1]["sample"]) for t in train_ds]
    test_eps, test_meta = [], []
    for tensors, labels in test_dl:
        arr = tensors.float().numpy()
        for j in range(arr.shape[0]):
            test_eps.append(arr[j])
            test_meta.append({k: (v[j].item() if hasattr(v, "shape") else v[j]) for k, v in labels.items()})
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(train_eps))
    n_fit = int(0.8 * len(train_eps))
    fit_all, cal_idx = order[:n_fit], order[n_fit:]
    n_padded = train_eps[0].shape[0]

    def wc(eps, ids):
        ws, cs, eids = [], [], []
        for k, (ep, sid) in enumerate(zip(eps, ids)):
            w = episode_windows(ep)
            ws.append(w); cs.append(window_contexts(actions[sid], n_padded))
            eids.append(np.full(len(w), k))
        return np.concatenate(ws), np.concatenate(cs), np.concatenate(eids)

    cal_w, cal_c, _ = wc([train_eps[i] for i in cal_idx], [train_ids[i] for i in cal_idx])
    test_w, test_c, test_e = wc(test_eps, [int(m["sample"]) for m in test_meta])

    out = {}
    for frac in (0.05, 0.10, 0.25, 0.50, 1.00):
        k = max(5, int(frac * len(fit_all)))
        sub = fit_all[:k]
        fit_w, _, _ = wc([train_eps[i] for i in sub], [train_ids[i] for i in sub])
        score = fit_model("ocsvm", fit_w, seed)
        s_cal, s_test = score(cal_w), score(test_w)
        agg = lambda ws: np.array([ws[test_e == kk].mean() for kk in range(len(test_eps))])
        marg = per_category_metrics(test_meta, agg(s_test))
        cal = ContextCalibrator("z").fit(s_cal, cal_c)
        ctx = per_category_metrics(test_meta, agg(cal.transform(s_test, test_c)))
        out[f"frac_{frac}"] = {"n_fit_episodes": int(k),
                               "marginal_auroc": marg["auroc_mean"],
                               "ctx_z_auroc": ctx["auroc_mean"],
                               "marginal_fpr90": marg["fpr_at_tpr90_mean"],
                               "ctx_z_fpr90": ctx["fpr_at_tpr90_mean"]}
        print(f"[sampeff] frac={frac}: n={k} marg={marg['auroc_mean']:.4f} ctx={ctx['auroc_mean']:.4f}",
              flush=True)
    return out


if __name__ == "__main__":
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    res = {"aursad_sealed_c2_c3": aursad_sealed(),
           "voraus_sample_efficiency_ocsvm": voraus_sample_efficiency(),
           "wall_seconds": None}
    res["wall_seconds"] = round(time.time() - t0, 1)
    (RUN_DIR / "confirm_pass.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("wrote confirm_pass.json")
