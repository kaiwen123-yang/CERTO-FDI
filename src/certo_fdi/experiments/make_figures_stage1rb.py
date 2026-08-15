"""Static figures for the Stage 1R-B review package (each with a companion .table.csv).

Colour follows the entity (model), never its rank; one axis per chart; thin marks; direct labels
where the palette contrast is low (relief rule)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_COLORS = {"ligra_v2_typed": "#2a78d6", "chain_gnn_aug": "#eb6834", "rnea_gru": "#1baf7a", "ligra_free_output": "#eda100"}
MODEL_ORDER = ["ligra_v2_typed", "chain_gnn_aug", "rnea_gru", "ligra_free_output"]
SEQ_CMAP = "Blues"


def _mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e3", "grid.linewidth": 0.6, "axes.edgecolor": "#8a8984", "font.size": 9})
    return plt


def _save(fig, out: Path, table: pd.DataFrame | None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    if table is not None:
        table.to_csv(out.with_suffix(".table.csv"), index=False)


def fig_four_axes(M: dict, ev: dict, out: Path) -> None:
    plt = _mpl()
    ax_ev = ev.get("axes", {})
    labels = ["S1 AUROC\n(unseen config.)", "ALL AUROC\nv2@25 % vs base@100 %", "counterfactual top-1\n(localization)", "mean(S2,S4) AUROC\n(context shift)"]
    a1, a2, a3, a4 = (ax_ev.get(k, {}) for k in ("axis1_unseen_configuration", "axis2_sample_efficiency", "axis3_localization", "axis4_context_shift"))
    cand = [a1.get("candidate_auroc"), a2.get("candidate_auroc_ALL_at_25pct"), a3.get("candidate_top1"), a4.get("candidate_auroc")]
    base = [a1.get("baseline_auroc"), a2.get("baseline_auroc_ALL_at_100pct"), a3.get("baseline_top1"), a4.get("baseline_auroc")]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    x = np.arange(4)
    w = 0.36
    for k, (vals, name) in enumerate(((cand, "ligra_v2_typed"), (base, "chain_gnn_aug"))):
        v = [np.nan if x_ is None else x_ for x_ in vals]
        ax.bar(x + (k - 0.5) * w, v, width=w - 0.04, color=MODEL_COLORS[name], label=name, linewidth=0)
        for xi, vi in zip(x + (k - 0.5) * w, v):
            if vi == vi:
                ax.text(xi, vi + 0.01, f"{vi:.3f}", ha="center", va="bottom", fontsize=7.5, color="#0b0b0b")
    # per-seed dots
    for k, (name, keys) in enumerate((("ligra_v2_typed", ("auroc_S1_by_seed", "auroc_ALL_frac0.25_by_seed", "loc_cf_top1_ALL_by_seed", None)), ("chain_gnn_aug", ("auroc_S1_by_seed", "auroc_ALL_frac1.00_by_seed", "loc_cf_top1_ALL_by_seed", None)))):
        m = M.get(name, {})
        for j, key in enumerate(keys):
            if key is None:
                s2, s4 = m.get("auroc_S2_by_seed", {}), m.get("auroc_S4_by_seed", {})
                vals = [(s2[s] + s4[s]) / 2 for s in s2 if s in s4]
            else:
                vals = list((m.get(key) or {}).values())
            if vals:
                ax.scatter(np.full(len(vals), x[j] + (k - 0.5) * w), vals, s=12, color="#0b0b0b", zorder=3, linewidths=0)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_ylabel("metric value (seed mean; dots = seeds)")
    ax.set_title(f"Four value axes — axes won by ligra_v2_typed: {len(ev.get('axes_won', []))}/4 (residual-only head, qdd_est)")
    ax.legend(frameon=False, loc="upper right")
    _save(fig, out, pd.DataFrame({"axis": labels, "ligra_v2_typed": cand, "chain_gnn_aug": base}))
    plt.close(fig)


def fig_family_heatmap(M: dict, out: Path, key: str = "auroc_OOD_by_family", title: str = "OOD window AUROC by fault family (fraction 1.0, seed means, residual-only head)") -> None:
    plt = _mpl()
    models = [m for m in MODEL_ORDER if M.get(m, {}).get(key)]
    if not models:
        return
    fams = sorted({f for m in models for f in M[m][key] if f != "ALL"})
    mat = np.array([[M[m][key].get(f, np.nan) for f in fams] for m in models])
    fig, ax = plt.subplots(figsize=(1.1 * len(fams) + 2, 0.55 * len(models) + 1.2))
    im = ax.imshow(mat, cmap=SEQ_CMAP, vmin=0.4, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels(fams, rotation=30, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)
    ax.grid(False)
    for i in range(len(models)):
        for j in range(len(fams)):
            v = mat[i, j]
            if v == v:
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color="white" if v > 0.78 else "#0b0b0b")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="AUROC")
    ax.set_title(title, fontsize=9)
    _save(fig, out, pd.DataFrame(mat, index=models, columns=fams).reset_index().rename(columns={"index": "model"}))
    plt.close(fig)


def fig_sample_efficiency(se: pd.DataFrame, out: Path) -> None:
    plt = _mpl()
    if se.empty:
        return
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for m in MODEL_ORDER:
        d = se[se.model == m].sort_values("training_fraction")
        if d.empty:
            continue
        ax.errorbar(d.training_fraction, d.auroc_ALL, yerr=d.auroc_ALL_std.fillna(0), color=MODEL_COLORS[m], marker="o", ms=4, lw=1.6, capsize=2, label=m)
        for xf, y in zip(d.training_fraction, d.auroc_ALL):
            ax.text(xf, y + 0.006, f"{y:.3f}", fontsize=7, ha="center", color="#52514e")
    ax.set_xlabel("healthy training fraction")
    ax.set_ylabel("window AUROC (ALL, seed mean ± std)")
    ax.set_xticks([0.25, 1.0])
    ax.set_title("Sample efficiency (residual-only head)")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, out, se[["model", "training_fraction", "auroc_ALL", "auroc_ALL_std", "auroc_OOD", "rmse_ratio_S0"]])
    plt.close(fig)


def fig_oracle_capacity(oc: pd.DataFrame, out: Path) -> None:
    plt = _mpl()
    g = oc[oc.phase == "lambda_grid"] if "phase" in oc else pd.DataFrame()
    if g.empty:
        return
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    colors = {"oracle_basis12": "#2a78d6", "oracle_free6": "#eb6834", "oracle_basis11_no_Fbody": "#1baf7a"}
    for name, d in g.groupby("model"):
        d = d.sort_values("edf_per_observation")
        ax.plot(d.edf_per_observation, d.insample_rmse_nm, ".", ms=5, color=colors.get(name, "#8a8984"), label=f"{name} (in-sample)", alpha=0.85)
        ax.plot(d.edf_per_observation, d.heldout_rmse_nm, "x", ms=4, color=colors.get(name, "#8a8984"), alpha=0.6, label=f"{name} (held-out steps)")
    ax.set_xlabel("effective degrees of freedom per observation (VAL windows)")
    ax.set_ylabel("torque-correction RMSE (N m)")
    ax.set_title("Oracle A ceilings over the regularization grid: capacity at matched freedom")
    ax.legend(frameon=False, fontsize=6.5, ncol=1)
    _save(fig, out, g[["model", "lambda_tikhonov", "lambda_smoothness", "edf_per_observation", "insample_rmse_nm", "heldout_rmse_nm"]])
    plt.close(fig)


def fig_frame_drift(M: dict, out: Path) -> None:
    plt = _mpl()
    models = [m for m in MODEL_ORDER if M.get(m, {}).get("frame_drift_median") is not None]
    if not models:
        return
    vals = [max(float(M[m]["frame_drift_median"]), 1e-9) for m in models]
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    ax.bar(range(len(models)), vals, color=[MODEL_COLORS[m] for m in models], width=0.6, linewidth=0)
    for i, v in enumerate(vals):
        ax.text(i, v * 1.3, f"{v:.1e}", ha="center", fontsize=7.5)
    ax.set_yscale("log")
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, rotation=15)
    ax.set_ylabel("median relative delta-tau drift under legal frame changes")
    ax.set_title("Frame-reparameterization drift (implementation property, not a value axis)", fontsize=8.5)
    _save(fig, out, pd.DataFrame({"model": models, "frame_drift_median": vals}))
    plt.close(fig)


def fig_localization(M: dict, out: Path) -> None:
    plt = _mpl()
    models = [m for m in MODEL_ORDER if M.get(m, {}).get("loc_cf_top1_ALL_by_family")]
    if not models:
        return
    fams = sorted({f for m in models for f in M[m]["loc_cf_top1_ALL_by_family"] if f != "ALL"})
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    x = np.arange(len(fams) + 1)
    w = 0.8 / len(models)
    for k, m in enumerate(models):
        vals = [M[m]["loc_cf_top1_ALL_by_family"].get(f, np.nan) for f in fams] + [M[m].get("loc_cf_top1_ALL", np.nan)]
        ax.bar(x + (k - (len(models) - 1) / 2) * w, vals, width=w - 0.03, color=MODEL_COLORS[m], label=m, linewidth=0)
    ax.axhline(1 / 7, color="#8a8984", lw=0.8, ls="--")
    ax.text(len(fams) + 0.55, 1 / 7 + 0.01, "chance (1/7)", fontsize=7, color="#52514e", ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels(fams + ["ALL"], rotation=20)
    ax.set_ylabel("counterfactual top-1 accuracy")
    ax.set_ylim(0, 1)
    ax.set_title("Localization by counterfactual link masking (all splits, seed means)")
    ax.legend(frameon=False, fontsize=7.5)
    _save(fig, out, pd.DataFrame([{**{"model": m}, **{f: M[m]["loc_cf_top1_ALL_by_family"].get(f) for f in fams}, "ALL": M[m].get("loc_cf_top1_ALL")} for m in models]))
    plt.close(fig)


def fig_healthy_rmse(hp: pd.DataFrame, out: Path) -> None:
    plt = _mpl()
    if hp.empty:
        return
    d = hp[(hp.training_fraction >= 1.0) & (hp.acceleration_input == "qdd_est") & (hp.split.isin(["S0", "OOD"]))]
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    x = np.arange(2)
    models = [m for m in MODEL_ORDER if (d.model == m).any()]
    w = 0.8 / max(len(models), 1)
    rows = []
    for k, m in enumerate(models):
        vals = []
        for j, sp in enumerate(["S0", "OOD"]):
            g = d[(d.model == m) & (d.split == sp)]
            v = float(g.rmse_ratio_post_over_pre.mean()) if len(g) else np.nan
            vals.append(v)
            ax.scatter(np.full(len(g), x[j] + (k - (len(models) - 1) / 2) * w), g.rmse_ratio_post_over_pre, s=10, color="#0b0b0b", zorder=3, linewidths=0)
        ax.bar(x + (k - (len(models) - 1) / 2) * w, vals, width=w - 0.03, color=MODEL_COLORS[m], label=m, linewidth=0)
        rows.append({"model": m, "rmse_ratio_S0": vals[0], "rmse_ratio_OOD": vals[1]})
    ax.set_xticks(x)
    ax.set_xticklabels(["S0 (in-distribution)", "OOD (S1–S4)"])
    ax.set_ylabel("healthy RMSE ratio post/pre (lower = better)")
    ax.set_title("Healthy torque-correction fit (fraction 1.0; dots = seeds)")
    ax.legend(frameon=False, fontsize=7.5)
    _save(fig, out, pd.DataFrame(rows))
    plt.close(fig)


def make_all(run_root: Path) -> list[str]:
    res = run_root / "results"
    figs = run_root / "figures"
    figs.mkdir(exist_ok=True)
    M = json.loads((res / "stage1rb_metrics_summary.json").read_text()) if (res / "stage1rb_metrics_summary.json").exists() else {}
    ev = json.loads((res / "stage1rb_decision_evidence.json").read_text()) if (res / "stage1rb_decision_evidence.json").exists() else {}
    made = []

    def _try(fn, *a):
        try:
            fn(*a)
            made.append(a[-1].name)
        except Exception as e:  # pragma: no cover
            print(f"figure {fn.__name__} failed: {type(e).__name__}: {e}")

    if M and ev:
        _try(fig_four_axes, M, ev, figs / "fig_four_axes.png")
        _try(fig_family_heatmap, M, figs / "fig_family_ood_auroc.png")
        _try(fig_frame_drift, M, figs / "fig_frame_drift.png")
        _try(fig_localization, M, figs / "fig_localization_counterfactual.png")
    if (res / "stage1rb_sample_efficiency.csv").exists() and (res / "stage1rb_sample_efficiency.csv").stat().st_size:
        _try(fig_sample_efficiency, pd.read_csv(res / "stage1rb_sample_efficiency.csv"), figs / "fig_sample_efficiency.png")
    if (res / "stage1rb_oracle_torque_capacity.csv").exists():
        _try(fig_oracle_capacity, pd.read_csv(res / "stage1rb_oracle_torque_capacity.csv"), figs / "fig_oracle_capacity.png")
    if (res / "stage1rb_healthy_prediction.csv").exists() and (res / "stage1rb_healthy_prediction.csv").stat().st_size:
        _try(fig_healthy_rmse, pd.read_csv(res / "stage1rb_healthy_prediction.csv"), figs / "fig_healthy_rmse.png")
    return made


if __name__ == "__main__":
    import sys

    print(make_all(Path(sys.argv[1])))
