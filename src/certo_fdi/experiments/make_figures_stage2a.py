"""Stage 2A figures (contract §9). All plots are written to ``<run>/figures/``."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DPI = 150


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def fig_contact_observability(obs: pd.DataFrame, out: Path) -> None:
    """Per-link contact observability map, by context stratum."""
    d = obs[obs.form == "window_stacked_body_wrench"] if "form" in obs else obs
    piv = d.pivot_table(index="split", columns="link", values="fisher_eigenvalue_min_positive", aggfunc="median")
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    v = np.log10(np.clip(piv.values, 1e-12, None))
    im = ax.imshow(v, aspect="auto", cmap="viridis")
    ax.set_xticks(range(piv.shape[1]), [f"link {c}" for c in piv.columns])
    ax.set_yticks(range(piv.shape[0]), piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax.text(j, i, f"{v[i, j]:.1f}", ha="center", va="center", color="w", fontsize=8)
    ax.set_title("Per-link contact observability  log10 $\\lambda_{min}^+(\\bar D^T \\bar D)$  (median per split)")
    fig.colorbar(im, ax=ax, label="log10 Fisher $\\lambda_{min}^+$")
    _save(fig, out / "fig01_contact_observability_map.png")


def fig_principal_angles(ang: pd.DataFrame, out: Path) -> None:
    """Fault-family and contact-link minimum principal-angle heatmaps."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, kind, title in zip(axes, ("fault_family", "contact_link"), ("fault-family dictionaries", "per-link contact dictionaries")):
        d = ang[ang.pair_kind == kind]
        if d.empty:
            ax.set_visible(False)
            continue
        keys = sorted(set(d.a) | set(d.b))
        M = np.full((len(keys), len(keys)), np.nan)
        for _, r in d.groupby(["a", "b"])["min_principal_angle_deg"].median().reset_index().iterrows():
            i, j = keys.index(r["a"]), keys.index(r["b"])
            M[i, j] = M[j, i] = r["min_principal_angle_deg"]
        np.fill_diagonal(M, 0.0)
        im = ax.imshow(M, cmap="magma", vmin=0, vmax=90)
        ax.set_xticks(range(len(keys)), keys, rotation=60, ha="right", fontsize=7)
        ax.set_yticks(range(len(keys)), keys, fontsize=7)
        ax.set_title(f"min principal angle (deg)\n{title}")
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle("Pathway ambiguity: 0 deg = indistinguishable, 90 deg = orthogonal")
    _save(fig, out / "fig02_principal_angle_heatmaps.png")


def fig_geometry_vs_localization_error(dia: pd.DataFrame, out: Path) -> None:
    """Reliability curves: diagnosability metric vs the actual localization error."""
    d = dia[dia.error_metric == "link_localization_error"]
    if d.empty:
        return
    metrics = sorted(d.diagnosability_metric.unique())
    fig, axes = plt.subplots(1, min(4, len(metrics)), figsize=(4 * min(4, len(metrics)), 3.6), squeeze=False)
    for ax, metric in zip(axes[0], metrics[:4]):
        rows = d[d.diagnosability_metric == metric]
        for _, r in rows.iterrows():
            bins = json.loads(r["reliability_bins"])
            ax.plot([b["x_median"] for b in bins], [b["error_rate"] for b in bins], marker="o", ms=3, alpha=0.8, label=f"seed {r['seed']}")
        rho = rows["spearman_rho"].mean()
        ax.set_title(f"{metric}\nSpearman $\\rho$ = {rho:+.2f}", fontsize=9)
        ax.set_xlabel(metric, fontsize=8)
        ax.set_ylabel("link localization error rate", fontsize=8)
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
    axes[0][0].legend(fontsize=7)
    fig.suptitle("Diagnosability map vs actual F4 link-localization error")
    _save(fig, out / "fig03_geometry_vs_localization_error.png")


def fig_split_auroc(det: pd.DataFrame, out: Path, models: list[str]) -> None:
    """AUROC per split (S0-S4, OOD, ALL) for the ablation ladder."""
    d = det[(det.fault_family == "ALL")]
    splits = ["S0", "S1", "S2", "S3", "S4", "OOD", "ALL"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6))
    for ax, fam in zip(axes, ("ALL", "F4_contact")):
        dd = det[det.fault_family == fam]
        x = np.arange(len(splits))
        w = 0.8 / max(len(models), 1)
        for k, m in enumerate(models):
            vals = [float(dd[(dd.model == m) & (dd.split == s)]["auroc"].mean()) for s in splits]
            err = [float(dd[(dd.model == m) & (dd.split == s)]["auroc"].std()) for s in splits]
            ax.bar(x + k * w - 0.4, vals, w, yerr=err, capsize=2, label=m if fam == "ALL" else None)
        ax.axhline(0.5, color="k", ls=":", lw=1)
        ax.set_xticks(x, splits)
        ax.set_ylim(0.4, 1.0)
        ax.set_ylabel("window AUROC")
        ax.set_title(f"family = {fam}")
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle("Detection AUROC by context split (mean +- s.d. over seeds)")
    _save(fig, out / "fig04_split_auroc.png")


def fig_fa_vs_delay(evt: pd.DataFrame, out: Path) -> None:
    """False alarms per hour against detection delay, per ablation."""
    d = evt[(evt.split == "ALL") & (evt.fault_family == "ALL")]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for m, g in d.groupby("model"):
        ax.scatter(g["false_alarms_per_hour"].mean(), g["detection_delay_median_s"].mean(), s=60)
        ax.annotate(m, (g["false_alarms_per_hour"].mean(), g["detection_delay_median_s"].mean()), fontsize=7,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("false alarms / hour (healthy windows, 0.995 healthy threshold)")
    ax.set_ylabel("median detection delay (s)")
    ax.set_title("Operating point: false alarms vs detection delay")
    ax.grid(alpha=0.3)
    _save(fig, out / "fig05_false_alarms_vs_delay.png")


def fig_selective(sel: pd.DataFrame, out: Path) -> None:
    """Selective accuracy against coverage under the geometric rejection rule."""
    d = sel[sel.split == "ALL"]
    fig, ax = plt.subplots(figsize=(7, 4.6))
    for m, g in d.groupby("model"):
        ax.scatter(g["coverage"].mean(), 1.0 - g["selective_error"].mean(), s=60)
        ax.annotate(m, (g["coverage"].mean(), 1.0 - g["selective_error"].mean()), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("coverage (fraction of windows not rejected)")
    ax.set_ylabel("selective accuracy")
    ax.set_title("Selective accuracy vs coverage (geometric rejection, healthy-calibrated)")
    ax.grid(alpha=0.3)
    _save(fig, out / "fig06_selective_accuracy_vs_coverage.png")


def fig_confusion(conf: dict, out: Path) -> None:
    """Contact-link confusion matrices for the deployed localizer and its controls."""
    keys = [k for k in ("contact_projection_residual", "contact_projection_residual_shuffled_control",
                        "contact_projection_residual_oracle_truth_point") if k in conf]
    if not keys:
        return
    fig, axes = plt.subplots(1, len(keys), figsize=(4.6 * len(keys), 4.2), squeeze=False)
    for ax, k in zip(axes[0], keys):
        C = np.sum([np.array(v) for v in conf[k].values()], 0)
        row = C.sum(1, keepdims=True)
        N = C / np.where(row == 0, 1, row)
        im = ax.imshow(N, cmap="Blues", vmin=0, vmax=1)
        for i in range(C.shape[0]):
            for j in range(C.shape[1]):
                if C[i].sum():
                    ax.text(j, i, f"{C[i, j]}", ha="center", va="center", fontsize=7,
                            color="w" if N[i, j] > 0.5 else "k")
        ax.set_xlabel("predicted link")
        ax.set_ylabel("true contact link")
        ax.set_title(k.replace("contact_projection_residual", "cpr"), fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle("F4 contact-link confusion (episode-level vote, all seeds pooled)")
    _save(fig, out / "fig07_contact_link_confusion.png")


def fig_learning_curve(lc: pd.DataFrame, out: Path) -> None:
    """Healthy-data learning curve; unavailable points are marked, never extrapolated."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for m, g in lc.groupby("model"):
        av = g[g.available.astype(str).str.lower().isin(["true", "1"])].sort_values("n_train_episodes")
        axes[0].errorbar(av["n_train_episodes"], av["auroc_ALL"], yerr=av.get("auroc_ALL_std"), marker="o", capsize=3, label=m)
        axes[1].plot(av["n_train_episodes"], av["healthy_rmse_S0_nm"], marker="o", label=m)
    na = lc[~lc.available.astype(str).str.lower().isin(["true", "1"])]
    for ax in axes:
        for n in sorted(set(na["n_train_episodes"])):
            ax.axvline(n, color="crimson", ls="--", lw=1)
            ax.text(n, ax.get_ylim()[0], " NOT AVAILABLE\n in the frozen data", color="crimson", fontsize=7, va="bottom")
        ax.set_xlabel("healthy training episodes")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("window AUROC (ALL)")
    axes[1].set_ylabel("healthy S0 torque RMSE (N m)")
    fig.suptitle("Data-volume diagnostic on the frozen healthy training episodes")
    _save(fig, out / "fig08_learning_curve.png")


def make_all(run_root: Path) -> list[str]:
    res, out = run_root / "results", run_root / "figures"
    p6 = run_root / "p6_metrics"
    made = []

    def _read(p: Path):
        return pd.read_csv(p) if p.exists() and p.stat().st_size else None

    det, evt, loc = _read(res / "stage2a_detection_metrics.csv"), _read(res / "stage2a_event_metrics.csv"), _read(res / "stage2a_localization_metrics.csv")
    dia, lc = _read(res / "stage2a_diagnosability_error_correlation.csv"), _read(res / "stage2a_learning_curve.csv")
    obs, ang = _read(res / "stage2a_contact_observability.csv"), _read(res / "stage2a_principal_angles.csv")
    sel = _read(p6 / "stage2a_selective_risk.csv")
    order = ["rnea_threshold", "rnea_gru", "chain_gnn_aug_residual_only", "geometry_only", "chain_plus_ee_jacobian",
             "chain_plus_all_link_instantaneous_jacobian", "chain_plus_all_link_window_jacobian",
             "chain_plus_full_pathway_dictionary", "chain_plus_shuffled_jacobian_control"]
    if obs is not None:
        fig_contact_observability(obs, out); made.append("fig01_contact_observability_map.png")
    if ang is not None:
        fig_principal_angles(ang, out); made.append("fig02_principal_angle_heatmaps.png")
    if dia is not None:
        fig_geometry_vs_localization_error(dia, out); made.append("fig03_geometry_vs_localization_error.png")
    if det is not None:
        fig_split_auroc(det, out, [m for m in order if m in set(det.model)]); made.append("fig04_split_auroc.png")
    if evt is not None:
        fig_fa_vs_delay(evt, out); made.append("fig05_false_alarms_vs_delay.png")
    if sel is not None:
        fig_selective(sel, out); made.append("fig06_selective_accuracy_vs_coverage.png")
    cp = p6 / "stage2a_link_confusion.json"
    if cp.exists():
        fig_confusion(json.loads(cp.read_text()), out); made.append("fig07_contact_link_confusion.png")
    if lc is not None:
        fig_learning_curve(lc, out); made.append("fig08_learning_curve.png")
    return [m for m in made if (out / m).exists()]


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    a = ap.parse_args()
    print(json.dumps(make_all(Path(a.run_root)), indent=2))


if __name__ == "__main__":
    main()
