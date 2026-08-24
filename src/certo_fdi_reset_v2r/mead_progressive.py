"""M3/M4: ME-AD progressive metrics + earliest detection + context calibration
+ sample efficiency (frozen; cycle index used EVAL_ONLY for ordering).

Progressive span: for each F1-50 op (1050-1053, Task1 ops), score EVERY 10th
cycle of the FULL progression with a fixed front-end (window_ae seed 260824,
fit on Task1 fit-cycles) -> Kendall tau / Spearman rho between score and cycle
order (EVAL_ONLY), time-dependent AUROC (healthy 20-69 vs sliding late blocks),
and lead time: first cycle index (in the every-10 grid) whose score exceeds
the healthy-cal max threshold, relative to benchmark_onset := N-50 (script
truth) and to README's cycle-71 wording (both reported).

Earliest-detection comparison (gate 10.1 item 4): per task, at the fixed
operating point 'healthy-test q95', the first faulty-cycle index (official
faulty block, ordered) exceeding it — residual model vs strongest CORE-8.

Context calibration (M4): fronts = {window_ae, gru_pred, tcn_ae} on Task7
(multi-op task); context = op code of the source cycle (official metadata);
per-context z-calibration on cal cycles vs marginal vs context-permuted.
NOTE: task files CONCATENATE ops per cycle, so op-context needs per-op
scoring — we rebuild Task7 cycles from Pandas per op (same indices) which the
task audit verified identical.

Sample efficiency: Task1, window_ae, healthy fractions of fit cycles
{5,10,25,50,100}% (>=1 cycle), 3 seeds.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi_reset_v2.benchmarks.models import fit_model
from certo_fdi_reset_v2r.mead_common import (
    MEAD, RAW24, SEEDS, TASKS, cycle_windows, fit_stats, load_task,
)

RUN = Path("/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/run_20260824T084349Z_paper_reset_v2r/mead")
F1_OPS = ("1050", "1051", "1052", "1053")
T7_OPS = ("3000", "3100", "2000", "2100", "2200", "2300", "2400", "2500")


def load_op_cycle(op: str, idx: int) -> np.ndarray:
    df = pd.read_pickle(MEAD / "Pandas" / op / f"cleaned_dataset_{idx}.pkl")
    return df[RAW24].to_numpy(dtype=np.float32)


def progressive() -> dict:
    from scipy.stats import kendalltau, spearmanr
    from sklearn.metrics import roc_auc_score
    data = load_task("Task1")
    fit_c, cal_c = data["train"][:15], data["train"][15:20]
    mu, sd = fit_stats(fit_c)
    train_w = np.concatenate([cycle_windows(c, mu, sd) for c in fit_c], 0)
    score = fit_model("window_ae", train_w, SEEDS[0])
    out = {}
    for op in F1_OPS:
        n = len(list((MEAD / "Pandas" / op).glob("cleaned_dataset_*.pkl")))
        grid = list(range(0, n, 10))
        s = np.array([float(np.mean(score(cycle_windows(load_op_cycle(op, i), mu, sd))))
                      for i in grid])
        idx = np.array(grid)  # EVAL_ONLY ordering
        tau = kendalltau(idx, s); rho = spearmanr(idx, s)
        heal_mask = (idx >= 20) & (idx < 70)
        onset_script = n - 50
        td_auroc = {}
        for name, sel in (("late_last50", idx >= onset_script),
                          ("mid_block", (idx >= n // 2) & (idx < n // 2 + 200)),
                          ("post_readme71", idx >= 71)):
            if sel.sum() >= 5:
                y = np.concatenate([np.zeros(heal_mask.sum()), np.ones(sel.sum())])
                sc = np.concatenate([s[heal_mask], s[sel]])
                td_auroc[name] = float(roc_auc_score(y, sc))
        thr = float(np.max([np.mean(score(cycle_windows(c, mu, sd))) for c in cal_c]))
        above = idx[s > thr]
        first_alarm = int(above.min()) if len(above) else None
        out[op] = {"n_cycles": n, "grid_step": 10,
                   "kendall_tau": float(tau.statistic), "kendall_p": float(tau.pvalue),
                   "spearman_rho": float(rho.statistic),
                   "time_dependent_auroc": td_auroc,
                   "benchmark_onset_script": onset_script,
                   "first_alarm_cycle_at_cal_thr": first_alarm,
                   "lead_vs_script_onset": (onset_script - first_alarm) if first_alarm is not None else None,
                   "monotonicity_sign": float(np.sign(tau.statistic))}
        print(f"[prog] {op}: tau={tau.statistic:.3f} first_alarm={first_alarm} "
              f"onset={onset_script}", flush=True)
    (RUN / "mead_progressive_metrics.json").write_text(json.dumps(out, indent=2))
    return out


def earliest_detection() -> dict:
    """Per task: first exceeding faulty index at healthy-test q95 threshold,
    residual (mlp physical, seed 260824) vs strongest CORE-8 (from metrics)."""
    core = json.loads((RUN / "mead_core8_metrics.json").read_text())
    res_dir = RUN / "cycle_scores"
    out = {}
    for task in TASKS:
        # strongest core8 by AUROC (seed 260824 entries)
        best_m, best_a = None, -1
        for k, v in core.items():
            if k.startswith(task + "_") and k.endswith("_seed260824"):
                if v["auroc"] > best_a:
                    best_a, best_m = v["auroc"], k
        entry = {"strongest_core8": best_m, "core8_auroc": best_a}
        for label, path in (("core8", res_dir / f"{best_m}.npz"),
                            ("residual_mlp", res_dir / f"res_{task}_mlp_physical_seed260824.npz")):
            if not path.exists():
                entry[label] = "MISSING"
                continue
            z = np.load(path)
            thr = float(np.quantile(z["healthy"], 0.95))
            above = np.flatnonzero(z["faulty"] > thr)
            entry[label] = {"first_faulty_index_above_q95": (int(above.min()) if len(above) else None),
                            "frac_faulty_above": float((z["faulty"] > thr).mean())}
        out[task] = entry
    (RUN / "mead_earliest_detection.json").write_text(json.dumps(out, indent=2))
    return out


def context_calibration() -> dict:
    from certo_fdi_reset_v2.candidate.context_calibration import (
        ContextCalibrator, permute_contexts,
    )
    from sklearn.metrics import roc_auc_score
    out = {}
    idxs = {"fit": range(0, 15), "cal": range(15, 20),
            "heal": range(20, 70)}
    for fe in ("window_ae", "gru_pred", "tcn_ae"):
        for seed in SEEDS:
            # build per-op windows for Task7 ops
            fit_ws = []
            for op in T7_OPS:
                for i in idxs["fit"]:
                    fit_ws.append(load_op_cycle(op, i))
            mu, sd = fit_stats(fit_ws)
            train_w = np.concatenate([cycle_windows(c, mu, sd) for c in fit_ws], 0)
            score = fit_model(fe, train_w, seed)

            def group(ix_range, faulty=False):
                s_list, c_list, cyc = [], [], []
                for op in T7_OPS:
                    n = len(list((MEAD / "Pandas" / op).glob("cleaned_dataset_*.pkl")))
                    rng = range(n - 50, n) if faulty else ix_range
                    for j, i in enumerate(rng):
                        w = cycle_windows(load_op_cycle(op, i), mu, sd)
                        s_list.append(score(w))
                        c_list.append(np.full(len(w), op))
                        cyc.append(np.full(len(w), f"{op}_{i}"))
                return (np.concatenate(s_list), np.concatenate(c_list), np.concatenate(cyc))

            s_cal, c_cal, _ = group(idxs["cal"])
            s_h, c_h, cy_h = group(idxs["heal"])
            s_f, c_f, cy_f = group(None, faulty=True)

            def cyc_scores(s, cyc):
                uni = np.unique(cyc)
                return np.array([s[cyc == u].mean() for u in uni])

            def evaluate(transform):
                sh = cyc_scores(transform(s_h, c_h), cy_h)
                sf = cyc_scores(transform(s_f, c_f), cy_f)
                y = np.concatenate([np.zeros(len(sh)), np.ones(len(sf))])
                sc = np.concatenate([sh, sf])
                thr = np.quantile(sh, 0.99)
                return {"auroc": float(roc_auc_score(y, sc)),
                        "healthy_fa_rate_q99": float((sh > thr).mean()),
                        "fa_per_1000_healthy_cycles_at_calmax": None}

            variants = {"marginal": evaluate(lambda s, c: s)}
            cal = ContextCalibrator("z").fit(s_cal, c_cal)
            variants["ctx_z"] = evaluate(cal.transform)
            pc = ContextCalibrator("z").fit(s_cal, permute_contexts(c_cal, seed))
            variants["permuted_z"] = evaluate(pc.transform)
            out[f"{fe}_seed{seed}"] = variants
            print(f"[ctx] {fe} s{seed}: marg={variants['marginal']['auroc']:.3f} "
                  f"ctx={variants['ctx_z']['auroc']:.3f} perm={variants['permuted_z']['auroc']:.3f}",
                  flush=True)
    (RUN / "mead_context_calibration_metrics.json").write_text(json.dumps(out, indent=2))
    return out


def sample_efficiency() -> dict:
    from sklearn.metrics import roc_auc_score
    data = load_task("Task1")
    out = {}
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        order = rng.permutation(15)
        for frac in (0.05, 0.10, 0.25, 0.50, 1.00):
            k = max(1, int(round(frac * 15)))
            fit_c = [data["train"][i] for i in order[:k]]
            mu, sd = fit_stats(fit_c)
            train_w = np.concatenate([cycle_windows(c, mu, sd) for c in fit_c], 0)
            score = fit_model("window_ae", train_w, seed)
            sh = np.array([float(np.mean(score(cycle_windows(c, mu, sd)))) for c in data["healthy"]])
            sf = np.array([float(np.mean(score(cycle_windows(c, mu, sd)))) for c in data["faulty"]])
            y = np.concatenate([np.zeros(len(sh)), np.ones(len(sf))])
            out[f"seed{seed}_frac{frac}"] = {"n_fit_cycles": k,
                                             "auroc": float(roc_auc_score(y, np.concatenate([sh, sf])))}
            print(f"[sampeff] s{seed} f={frac}: n={k} AUROC={out[f'seed{seed}_frac{frac}']['auroc']:.3f}",
                  flush=True)
    (RUN / "mead_sample_efficiency.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "prog"):
        progressive()
    if which in ("all", "early"):
        earliest_detection()
    if which in ("all", "ctx"):
        context_calibration()
    if which in ("all", "sampeff"):
        sample_efficiency()
