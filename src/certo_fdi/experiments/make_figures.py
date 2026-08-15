"""Static figures (PNG + companion table CSV) for the review package.

Design: fixed categorical hue order per model (validated palette, adjacent-pair CVD safe),
one axis per panel, thin marks, recessive grid, legend + selective direct labels, and a
table view next to every figure (relief for low-contrast hues).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MODEL_ORDER = ["ligra", "chain_gnn", "chain_gnn_aug", "rnea_gru", "rnea_mlp", "rnea_only", "ligra_free_output", "ligra_mlp_encoder", "ligra_unshared", "gru_no_rnea"]
COLORS = {"ligra": "#2a78d6", "chain_gnn": "#eb6834", "chain_gnn_aug": "#1baf7a", "rnea_gru": "#eda100", "rnea_mlp": "#e87ba4", "rnea_only": "#008300", "ligra_free_output": "#4a3aa7", "ligra_mlp_encoder": "#e34948", "ligra_unshared": "#7a7a7a", "gru_no_rnea": "#a0a0a0"}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_sample_efficiency(results: Path, out: Path) -> None:
    p = results / "stage1r_event_detection.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    d = d[(d.density_variant == "representation") & (d.family == "ALL") & (d.severity == "ALL") & (d.split.isin(["ALL", "OOD"]))]
    if d.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=SURFACE)
    table = []
    for ax, split in zip(axes, ["ALL", "OOD"]):
        _style(ax)
        for m in MODEL_ORDER[:5]:
            g = d[(d.model == m) & (d.split == split)].groupby("training_fraction")["auroc"].agg(["mean", "std", "count"]).reset_index()
            if g.empty:
                continue
            x = g["training_fraction"] * 100
            ax.errorbar(x, g["mean"], yerr=g["std"].fillna(0), color=COLORS[m], lw=2, marker="o", ms=6, capsize=2, label=m)
            ax.annotate(m, (x.iloc[-1], g["mean"].iloc[-1]), textcoords="offset points", xytext=(6, 0), fontsize=8, color=INK2, va="center")
            for _, r in g.iterrows():
                table.append({"split": split, "model": m, "training_fraction_pct": r["training_fraction"] * 100, "auroc_mean": r["mean"], "auroc_std": r["std"], "n_seeds": r["count"]})
        ax.set_xscale("log")
        ax.set_xticks([10, 25, 50, 100])
        ax.set_xticklabels(["10%", "25%", "50%", "100%"])
        ax.set_xlabel("healthy training data", color=INK2)
        ax.set_ylabel("window AUROC (representation head)", color=INK2)
        ax.set_title(f"Sample efficiency — {split} test split", color=INK, fontsize=11, loc="left")
        ax.set_ylim(0.4, 1.0)
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "fig_sample_efficiency.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)
    pd.DataFrame(table).to_csv(out / "fig_sample_efficiency.table.csv", index=False)


def fig_split_auroc(results: Path, out: Path) -> None:
    p = results / "stage1r_event_detection.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    d = d[(d.density_variant == "representation") & (d.family == "ALL") & (d.severity == "ALL") & (d.training_fraction >= 1.0)]
    splits = ["S0", "S1", "S2", "S3", "S4"]
    models = [m for m in MODEL_ORDER[:6] if m in set(d.model)]
    if not models:
        return
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=SURFACE)
    _style(ax)
    w = 0.8 / len(models)
    table = []
    for k, m in enumerate(models):
        means = [d[(d.model == m) & (d.split == s)]["auroc"].mean() for s in splits]
        stds = [d[(d.model == m) & (d.split == s)]["auroc"].std() for s in splits]
        x = np.arange(len(splits)) + (k - len(models) / 2 + 0.5) * w
        ax.bar(x, means, width=w * 0.9, color=COLORS[m], label=m, yerr=np.nan_to_num(stds), capsize=2, ecolor=INK2, linewidth=0)
        for s, mu, sd in zip(splits, means, stds):
            table.append({"model": m, "split": s, "auroc_mean": mu, "auroc_std": sd})
    ax.set_xticks(np.arange(len(splits)))
    ax.set_xticklabels(["S0 IID", "S1 config", "S2 payload", "S3 speed", "S4 combined"])
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("window AUROC (fault vs healthy windows)", color=INK2)
    ax.set_title("Healthy-only anomaly detection by context split (fraction 1.0, seed mean ± sd)", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    fig.savefig(out / "fig_split_auroc.png", dpi=160, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    pd.DataFrame(table).to_csv(out / "fig_split_auroc.table.csv", index=False)


def fig_family_heatmap(results: Path, out: Path) -> None:
    p = results / "stage1r_event_detection.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    d = d[(d.density_variant == "representation") & (d.family != "ALL") & (d.severity == "ALL") & (d.training_fraction >= 1.0) & (d.split == "OOD")]
    if d.empty:
        return
    fams = sorted(d.family.unique())
    models = [m for m in MODEL_ORDER if m in set(d.model)]
    mat = np.array([[d[(d.model == m) & (d.family == f)]["auroc"].mean() for f in fams] for m in models])
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(models) + 1.5), facecolor=SURFACE)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq_blue", SEQ)
    im = ax.imshow(mat, cmap=cmap, vmin=0.5, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels([f.replace("_", "\n") for f in fams], fontsize=8, color=INK2)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models, fontsize=9, color=INK2)
    for i in range(len(models)):
        for j in range(len(fams)):
            v = mat[i, j]
            ax.text(j, i, "n/a" if np.isnan(v) else f"{v:.2f}", ha="center", va="center", fontsize=8, color=INK if (np.isnan(v) or v < 0.8) else "#ffffff")
    ax.set_title("OOD (S1–S4) window AUROC by fault family (fraction 1.0, seed mean)", color=INK, fontsize=11, loc="left")
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.ax.tick_params(labelsize=8, colors=INK2)
    fig.tight_layout()
    fig.savefig(out / "fig_family_ood_heatmap.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)
    pd.DataFrame(mat, index=models, columns=fams).to_csv(out / "fig_family_ood_heatmap.table.csv")


def fig_frame_drift(results: Path, out: Path) -> None:
    p = results / "stage1r_frame_invariance.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    if d.empty:
        return
    models = [m for m in MODEL_ORDER if m in set(d.model)]
    fig, ax = plt.subplots(figsize=(8, 4), facecolor=SURFACE)
    _style(ax)
    table = []
    for k, m in enumerate(models):
        v = d[d.model == m]["delta_tau_relative_drift"].clip(lower=1e-12).values
        x = k + (np.random.default_rng(0).uniform(-0.15, 0.15, size=len(v)))
        ax.scatter(x, v, s=14, color=COLORS[m], alpha=0.6, linewidths=0)
        ax.plot([k - 0.25, k + 0.25], [np.median(v)] * 2, color=INK, lw=2)
        table.append({"model": m, "median_relative_drift": float(np.median(v)), "max_relative_drift": float(v.max()), "n": int(len(v))})
    ax.set_yscale("log")
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, fontsize=9)
    ax.set_ylabel("relative drift of pooled Δτ under legal link-frame changes", color=INK2)
    ax.set_title("S5 frame-reparameterization drift (same physical episodes; median bar)", color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(out / "fig_frame_drift.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)
    pd.DataFrame(table).to_csv(out / "fig_frame_drift.table.csv", index=False)


def fig_localization(results: Path, out: Path) -> None:
    p = results / "stage1r_localization.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    d = d[(d.density_variant == "representation") & (d.split == "ALL") & (d.training_fraction >= 1.0)]
    if "rule" in d:
        d = d[d.rule == "pattern"]
    if d.empty:
        return
    fams = ["ALL", "F1_actuator", "F2_friction", "F3_payload", "F4_contact", "F5_encoder"]
    models = [m for m in MODEL_ORDER[:6] if m in set(d.model)]
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=SURFACE)
    _style(ax)
    w = 0.8 / max(len(models), 1)
    table = []
    for k, m in enumerate(models):
        means = [d[(d.model == m) & (d.family == f)]["top1"].mean() for f in fams]
        stds = [d[(d.model == m) & (d.family == f)]["top1"].std() for f in fams]
        x = np.arange(len(fams)) + (k - len(models) / 2 + 0.5) * w
        ax.bar(x, means, width=w * 0.9, color=COLORS[m], label=m, yerr=np.nan_to_num(stds), capsize=2, ecolor=INK2, linewidth=0)
        for f, mu, sd in zip(fams, means, stds):
            table.append({"model": m, "family": f, "top1_mean": mu, "top1_std": sd})
    ax.axhline(1 / 7, color=INK2, lw=1, ls="--")
    ax.annotate("chance (1/7)", (len(fams) - 0.5, 1 / 7), fontsize=8, color=INK2, va="bottom", ha="right")
    ax.set_xticks(np.arange(len(fams)))
    ax.set_xticklabels([f.replace("_", "\n") for f in fams], fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("top-1 link/joint localization accuracy", color=INK2)
    ax.set_title("Unsupervised localization from per-link healthy NLL excess (all splits, seed mean ± sd)", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    fig.tight_layout()
    fig.savefig(out / "fig_localization.png", dpi=160, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    pd.DataFrame(table).to_csv(out / "fig_localization.table.csv", index=False)


def fig_fewshot(results: Path, out: Path) -> None:
    p = results / "stage1r_fewshot_attribution.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    d = d[d.split == "ALL"]
    if d.empty:
        return
    models = [m for m in MODEL_ORDER[:6] if m in set(d.model)]
    fig, ax = plt.subplots(figsize=(7, 4), facecolor=SURFACE)
    _style(ax)
    table = []
    for m in models:
        g = d[d.model == m].groupby("shots_per_class")["episode_macro_f1"].agg(["mean", "std", "count"]).reset_index()
        ax.errorbar(g["shots_per_class"], g["mean"], yerr=g["std"].fillna(0), color=COLORS[m], lw=2, marker="o", ms=6, capsize=2, label=m)
        for _, r in g.iterrows():
            table.append({"model": m, "shots_per_class": r["shots_per_class"], "episode_macro_f1_mean": r["mean"], "std": r["std"], "n_seeds": r["count"]})
    ax.set_xlabel("labeled calibration episodes per class", color=INK2)
    ax.set_ylabel("episode-level macro F1 (7 classes)", color=INK2)
    ax.set_ylim(0, 1)
    ax.set_title("Few-shot fault-family attribution on frozen embeddings", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_fewshot.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)
    pd.DataFrame(table).to_csv(out / "fig_fewshot.table.csv", index=False)


def make_all(run_root: Path) -> list[str]:
    results = run_root / "results"
    out = run_root / "figures"
    out.mkdir(exist_ok=True)
    for fn in (fig_sample_efficiency, fig_split_auroc, fig_family_heatmap, fig_frame_drift, fig_localization, fig_fewshot):
        try:
            fn(results, out)
        except Exception as e:  # pragma: no cover
            (out / f"{fn.__name__}.FAILED.txt").write_text(f"{type(e).__name__}: {e}\n")
    return sorted(p.name for p in out.iterdir())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args(argv)
    print("\n".join(make_all(Path(args.run_root))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
