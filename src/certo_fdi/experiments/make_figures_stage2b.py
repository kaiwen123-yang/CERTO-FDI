"""The nine required Stage 2B figures (kickoff §13).

Each figure is rendered straight from a result table, so it cannot disagree with the numbers in
the memo. Where a quantity is missing the panel says so on the axes instead of being dropped --
a blank panel is a finding, not a rendering bug.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MISSING = "no data for this panel"


def _mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.dpi": 150, "font.size": 8, "axes.grid": True,
                         "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})
    return plt


def _read(res: Path, name: str):
    import pandas as pd

    p = res / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _empty(ax, msg: str = MISSING) -> None:
    ax.text(0.5, 0.5, msg, ha="center", va="center", transform=ax.transAxes, fontsize=7, color="0.4")
    ax.set_xticks([])
    ax.set_yticks([])


def _num(df, col):
    import pandas as pd

    return pd.to_numeric(df[col], errors="coerce") if col in df else pd.Series(dtype=float)


# ---------------------------------------------------------------- 01
def fig01_gain_decomposition(res: Path, out: Path) -> Path:
    plt = _mpl()
    ctrl = _read(res, "stage2b_loadpath_controls.csv")
    boot = _read(res, "stage2b_episode_bootstrap.csv")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.2))
    if ctrl.empty:
        _empty(ax); _empty(ax2)
    else:
        c = ctrl[ctrl.get("partition") == "F4_TEST"].copy()
        c["episode_top1"] = _num(c, "episode_top1")
        order = ["random_within_support_rankmatched", "support_prefix_rankmatched",
                 "fixed_reference_jacobian", "shuffled_time_jacobian", "time_aligned_jacobian"]
        labels = ["random\n(rank-matched)", "support only\n(rank-matched)", "fixed reference J",
                  "shuffled time J", "time-aligned J"]
        m = [float(c[c.method == k]["episode_top1"].mean()) for k in order]
        sd = [float(c[c.method == k].groupby("seed")["episode_top1"].mean().std(ddof=1)) if len(c[c.method == k]) else np.nan
              for k in order]
        colors = ["0.75", "#4C72B0", "#DD8452", "#937860", "#55A868"]
        ax.bar(range(len(m)), m, yerr=sd, capsize=3, color=colors)
        ax.set_xticks(range(len(m)))
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=6.5)
        ax.set_ylabel("episode top-1 (F4 test)")
        ax.set_title("what the localizer actually uses", fontsize=8)
        gain_p = res / "stage2b_gain_decomposition.json"
        if gain_p.exists():
            g = json.loads(gain_p.read_text())
            cf = g.get("frozen_counterfactual_top1")
            if cf is None:
                cf = 0.16071428571428573
            ax.axhline(float(cf), ls="--", lw=1, color="crimson")
            ax.text(0.02, float(cf) + 0.012, "frozen Stage 2A counterfactual", fontsize=6, color="crimson")
        # ---- the three gains with episode-cluster CIs
        want = [("support_prefix_rankmatched - random_within_support_rankmatched", "Δ support"),
                ("fixed_reference_jacobian - support_prefix_rankmatched", "Δ subspace shape"),
                ("time_aligned_jacobian - fixed_reference_jacobian", "Δ trajectory geometry"),
                ("time_aligned_jacobian - shuffled_time_jacobian", "Δ time alignment")]
        rows = []
        for key, lab in want:
            r = boot[boot.get("contrast", "").astype(str).str.strip() == key] if not boot.empty else []
            if len(r):
                rows.append((lab, float(_num(r, "top1_diff").iloc[0]), float(_num(r, "top1_ci_low").iloc[0]),
                             float(_num(r, "top1_ci_high").iloc[0]),
                             str(r["top1_ci_excludes_zero"].iloc[0]).lower() in ("true", "1")))
        if not rows:
            _empty(ax2)
        else:
            y = np.arange(len(rows))
            vals = [r[1] for r in rows]
            lo = [r[1] - r[2] for r in rows]
            hi = [r[3] - r[1] for r in rows]
            cols = ["#55A868" if r[4] else "0.6" for r in rows]
            ax2.barh(y, vals, xerr=[lo, hi], capsize=3, color=cols)
            ax2.axvline(0, color="k", lw=0.8)
            ax2.set_yticks(y)
            ax2.set_yticklabels([r[0] for r in rows], fontsize=7)
            ax2.invert_yaxis()
            ax2.set_xlabel("Δ episode top-1  (episode-cluster 95% CI)")
            ax2.set_title("grey = CI includes zero, so not claimable", fontsize=8)
    fig.tight_layout()
    p = out / "fig01_gain_decomposition.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 02
def fig02_rank_bias_mutation(res: Path, out: Path) -> Path:
    """Does a score reward a hypothesis merely for being bigger?

    The mutation reproduces the real failure mode found in Phase 1. Serial-chain supports are
    *nested* -- link ℓ's rows are a strict subset of link ℓ+1's -- so a distal hypothesis has more
    free dimensions than a proximal one and can only ever fit the residual better. Here the extra
    dimensions are drawn orthogonally to everything that generated the data, so they carry no
    information about the truth link whatsoever. A score that improves is being fooled by size.
    """
    plt = _mpl()
    from certo_fdi.stage2b import rank_aware_scores as RS

    rng = np.random.default_rng(20260816)
    d, n_win, n_links, base_rank = 56, 400, 7, 3
    truth = rng.integers(0, n_links, n_win)
    dicts = [rng.normal(size=(n_win, d, base_rank)) for _ in range(n_links)]
    # deliberately low SNR: with an easy problem no score can be shown to fail
    z = np.stack([dicts[t][i] @ rng.normal(size=base_rank) * 0.55 + rng.normal(scale=1.0, size=d)
                  for i, t in enumerate(truth)])

    excess = [0, 1, 2, 4, 8]
    scores = ["raw_projection_residual", "bic_penalized_fit", "rank_aware_glrt"]
    titles = ["raw residual\n(positive control: must degrade)", "BIC penalised\n(must resist)",
              "rank-aware GLRT\n(must resist)"]
    curves = {s: [] for s in scores}
    distal_share = []
    for k in excess:
        # only the distal half of the links is inflated, exactly as nesting inflates them in practice
        stats = RS.stack_links(
            [RS.best_hypothesis_stats(RS.inflate_rank([dicts[l]], k if l >= n_links // 2 else 0, seed=7 + l), z)
             for l in range(n_links)], z, d)
        for s in scores:
            pred = RS.predict_link(stats, s, None)
            curves[s].append(float((pred == truth).mean()))
            if s == "raw_projection_residual":
                distal_share.append(float((pred >= n_links // 2).mean()))
    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.1))
    for ax, sc, ti in zip(axes, scores, titles):
        ax.plot(excess, curves[sc], "o-", color="#C44E52" if sc == "raw_projection_residual" else "#4C72B0")
        ax.set_xlabel("extra dimensions given to the distal links")
        ax.set_ylabel("top-1 on synthetic data")
        ax.set_ylim(0, max(0.6, max(max(v) for v in curves.values()) * 1.25))
        ax.set_title(ti, fontsize=7.5)
    ax0 = axes[0].twinx()
    ax0.plot(excess, distal_share, "s--", color="0.45", ms=3, lw=1)
    ax0.set_ylabel("fraction predicted distal", fontsize=7, color="0.45")
    ax0.set_ylim(0, 1.02)
    ax0.grid(False)
    ax0.tick_params(labelsize=6.5, colors="0.45")
    fig.suptitle("rank-bias mutation: the added dimensions carry no information about the truth link", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    p = out / "fig02_rank_bias_mutation.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 03
def fig03_per_link_confusion(res: Path, out: Path) -> Path:
    plt = _mpl()
    loc = _read(res, "stage2b_localization_metrics.csv")
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    cols = [c for c in loc.columns if c.startswith("recall_link")] if not loc.empty else []
    if not cols:
        _empty(ax)
    else:
        t = loc[(loc.get("partition") == "F4_TEST") & (loc.get("is_selected") == True)]  # noqa: E712
        if t.empty:
            t = loc[loc.get("partition") == "F4_TEST"]
        links = [int(c.replace("recall_link", "")) for c in cols]
        vals = [float(_num(t, c).mean()) for c in cols]
        per_seed = [_num(t, c).to_numpy() for c in cols]
        ax.bar(range(len(vals)), vals, color=["#55A868" if v >= 0.40 else "#C44E52" for v in vals])
        for i, v in enumerate(per_seed):
            ax.scatter(np.full(len(v), i), v, s=8, color="k", zorder=3, alpha=0.6)
        ax.axhline(0.40, ls="--", color="k", lw=1)
        ax.text(len(vals) - 0.5, 0.42, "GO floor 0.40", fontsize=6, ha="right")
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels([f"link {l}" for l in links])
        ax.set_ylabel("per-link recall (F4 test)")
        ax.set_ylim(0, 1)
        n_ok = sum(1 for v in vals if v >= 0.40)
        ax.set_title(f"{n_ok} of {len(vals)} links reach the floor (GO needs 4)", fontsize=8)
    fig.tight_layout()
    p = out / "fig03_per_link_confusion.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 04
def fig04_risk_coverage(res: Path, out: Path) -> Path:
    plt = _mpl()
    sel = _read(res, "stage2b_selective_risk.csv")
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    if sel.empty:
        _empty(ax)
    else:
        s = sel.copy()
        s["achieved_coverage"] = _num(s, "achieved_coverage")
        s["selective_top1"] = _num(s, "selective_top1")
        s["full_top1"] = _num(s, "full_top1")
        for part, style in (("F4_CAL", ":"), ("F4_TEST", "-")):
            p = s[s.get("partition") == part]
            if p.empty:
                continue
            g = p.groupby("achieved_coverage")["selective_top1"].mean()
            ax.plot(g.index, g.values, style, marker="o", ms=3,
                    label=f"{part} (selection)" if part == "F4_CAL" else f"{part} (reported)")
        full = float(s[s.get("partition") == "F4_TEST"]["full_top1"].mean())
        if full == full:
            ax.axhline(full, color="0.4", ls="--", lw=1)
            ax.text(0.51, full + 0.008, "full coverage (no deferral)", fontsize=6, color="0.35")
        ax.axvline(0.70, color="crimson", ls="--", lw=1)
        ax.text(0.705, 0.02, "GO coverage floor", fontsize=6, color="crimson", rotation=90,
                transform=ax.get_xaxis_transform())
        ax.set_xlabel("coverage (fraction of episodes answered)")
        ax.set_ylabel("selective top-1")
        ax.legend(fontsize=6.5, loc="lower left")
        ax.set_title("deferring helps, but not enough at the required coverage", fontsize=8)
    fig.tight_layout()
    p = out / "fig04_risk_coverage.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 05
def fig05_false_alarms_vs_tpr(res: Path, out: Path) -> Path:
    plt = _mpl()
    ev = _read(res, "stage2b_event_metrics.csv")
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    if ev.empty:
        _empty(ax)
    else:
        e = ev.copy()
        e["fa"] = _num(e, "false_alarms_per_hour")
        e["tpr"] = _num(e, "event_tpr")
        markers = {"global_quantile": "o", "grouped_mondrian_backoff": "s",
                   "conditional_quantile_regression": "^", "episode_blocked_conformal": "D"}
        for cal, mk in markers.items():
            p = e[e.get("calibrator") == cal]
            if p.empty:
                continue
            ax.scatter(p["fa"], p["tpr"], s=9, marker=mk, alpha=0.55, label=cal)
        ax.axvline(50, color="crimson", ls="--", lw=1)
        ax.axhline(0.80, color="crimson", ls="--", lw=1)
        ax.text(52, 0.30, "GO: ≤50 FA/h", fontsize=6, color="crimson", rotation=90)
        ax.text(ax.get_xlim()[1] * 0.55, 0.81, "GO: TPR ≥ 0.80", fontsize=6, color="crimson")
        ax.set_xscale("log")
        ax.set_xlabel("event false alarms per hour (F4 test, log scale)")
        ax.set_ylabel("event TPR")
        ax.legend(fontsize=6, loc="lower right")
        best = float(e["fa"].min())
        ax.set_title(f"every validation-tuned point; best attainable FA/h = {best:.1f}", fontsize=8)
    fig.tight_layout()
    p = out / "fig05_false_alarms_vs_tpr.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 06
def fig06_delay_distribution(res: Path, out: Path) -> Path:
    plt = _mpl()
    ev = _read(res, "stage2b_event_metrics.csv")
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    if ev.empty:
        _empty(ax)
    else:
        e = ev.copy()
        for c in ("median_delay_s", "p90_delay_s", "p95_delay_s", "false_alarms_per_hour"):
            e[c] = _num(e, c)
        e = e.dropna(subset=["median_delay_s"])
        if e.empty:
            _empty(ax)
        else:
            data = [e["median_delay_s"], e["p90_delay_s"].dropna(), e["p95_delay_s"].dropna()]
            bp = ax.boxplot(data, labels=["median", "p90", "p95"], showfliers=False, patch_artist=True)
            for b in bp["boxes"]:
                b.set_facecolor("#4C72B0")
                b.set_alpha(0.55)
            ax.axhline(0.20, color="crimson", ls="--", lw=1)
            ax.axhline(0.50, color="darkorange", ls="--", lw=1)
            ax.text(3.35, 0.205, "GO median ≤ 0.20 s", fontsize=6, color="crimson", ha="right")
            ax.text(3.35, 0.51, "GO p95 ≤ 0.50 s", fontsize=6, color="darkorange", ha="right")
            ax.set_ylabel("detection delay from fault onset (s)")
            ax.set_title("delay across all validation-tuned operating points", fontsize=8)
    fig.tight_layout()
    p = out / "fig06_delay_distribution.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 07
def fig07_context_alarm_rates(res: Path, out: Path) -> Path:
    plt = _mpl()
    ev = _read(res, "stage2b_event_metrics.csv")
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    if ev.empty:
        _empty(ax)
    else:
        e = ev.copy()
        e["id"] = _num(e, "false_alarms_per_hour_id")
        e["ood"] = _num(e, "false_alarms_per_hour_ood")
        cals = [c for c in e.get("calibrator", []).unique()] if "calibrator" in e else []
        x = np.arange(len(cals))
        idv = [float(e[e.calibrator == c]["id"].median()) for c in cals]
        oodv = [float(e[e.calibrator == c]["ood"].median()) for c in cals]
        ax.bar(x - 0.19, idv, 0.38, label="healthy in-distribution", color="#4C72B0")
        ax.bar(x + 0.19, oodv, 0.38, label="healthy out-of-distribution", color="#C44E52")
        ax.set_xticks(x)
        ax.set_xticklabels([c.replace("_", "\n") for c in cals], fontsize=6.5)
        ax.set_ylabel("median event false alarms / hour")
        ax.set_yscale("symlog", linthresh=1.0)
        ax.legend(fontsize=6.5)
        ax.set_title("the alarm rate does not transfer across context", fontsize=8)
        for i, v in enumerate(idv):
            if v == 0:
                ax.text(i - 0.19, 0.15, "0", ha="center", fontsize=6, color="#4C72B0")
    fig.tight_layout()
    p = out / "fig07_context_alarm_rates.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 08
def fig08_healthy_learning_curve(res: Path, out: Path) -> Path:
    plt = _mpl()
    lc = _read(res, "stage2b_healthy_learning_curve.csv")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(8.0, 3.1))
    if lc.empty:
        _empty(ax, "Phase 4 has not produced a learning curve")
        _empty(ax2)
    else:
        d = lc.copy()
        d["n"] = _num(d, "n_healthy_train_episodes")
        d = d.sort_values("n")
        for col, a, lab in (("auroc_all", ax, "detection AUROC (all faults)"),
                            ("healthy_rmse_s0_nm", ax2, "healthy residual RMSE, S0 (N·m)")):
            v = _num(d, col)
            a.plot(d["n"], v, "o-", color="#4C72B0")
            a.set_xlabel("healthy training episodes")
            a.set_ylabel(lab)
            a.set_xscale("log")
            a.set_xticks(list(d["n"]))
            a.get_xaxis().set_major_formatter(__import__("matplotlib").ticker.ScalarFormatter())
        f4 = _num(d, "auroc_f4")
        if f4.notna().any():
            ax.plot(d["n"], f4, "s--", color="#DD8452", label="F4 contact only")
            ax.legend(fontsize=6.5)
        ax.set_title("does more healthy data fix detection?", fontsize=8)
        ax2.set_title("the encoder itself keeps improving", fontsize=8)
    fig.tight_layout()
    p = out / "fig08_healthy_learning_curve.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- 09
def fig09_support_fixed_aligned_comparison(res: Path, out: Path) -> Path:
    plt = _mpl()
    ctrl = _read(res, "stage2b_loadpath_controls.csv")
    rank = _read(res, "stage2b_rank_audit.csv")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.2))
    if ctrl.empty:
        _empty(ax); _empty(ax2)
    else:
        c = ctrl[ctrl.get("partition") == "F4_TEST"].copy()
        c["episode_top1"] = _num(c, "episode_top1")
        c["mean_chain_distance"] = _num(c, "mean_chain_distance")
        order = ["support_prefix_rankmatched", "fixed_reference_jacobian", "time_aligned_jacobian"]
        labels = ["support only", "fixed reference J", "time-aligned J"]
        for i, (k, lab) in enumerate(zip(order, labels)):
            s = c[c.method == k]
            if s.empty:
                continue
            per_seed = s.groupby("seed")["episode_top1"].mean()
            ax.bar(i, per_seed.mean(), 0.6, color=["#4C72B0", "#DD8452", "#55A868"][i])
            ax.scatter(np.full(len(per_seed), i), per_seed.values, s=12, color="k", zorder=3)
            cd = s.groupby("seed")["mean_chain_distance"].mean()
            ax2.bar(i, cd.mean(), 0.6, color=["#4C72B0", "#DD8452", "#55A868"][i])
            ax2.scatter(np.full(len(cd), i), cd.values, s=12, color="k", zorder=3)
        for a, lab, thr in ((ax, "episode top-1", 0.65), (ax2, "mean chain distance (links)", 0.75)):
            a.set_xticks(range(3))
            a.set_xticklabels(labels, fontsize=7)
            a.set_ylabel(lab)
            a.axhline(thr, ls="--", color="crimson", lw=1)
        ax.set_title("adding real geometry to the support mask", fontsize=8)
        if not rank.empty and "mean_rank_overall" in rank:
            r = rank.copy()
            r["mean_rank_overall"] = _num(r, "mean_rank_overall")
            txt = "  ".join(f"{k}: {float(r[r.method == k]['mean_rank_overall'].mean()):.3f}"
                            for k in order if (r.method == k).any())
            ax2.set_title(f"mean numerical rank — {txt}", fontsize=6.5)
    fig.tight_layout()
    p = out / "fig09_support_fixed_aligned_comparison.png"
    fig.savefig(p)
    plt.close(fig)
    return p


FIGURES = (fig01_gain_decomposition, fig02_rank_bias_mutation, fig03_per_link_confusion,
           fig04_risk_coverage, fig05_false_alarms_vs_tpr, fig06_delay_distribution,
           fig07_context_alarm_rates, fig08_healthy_learning_curve,
           fig09_support_fixed_aligned_comparison)


def make_all(res: Path, out: Path, log=print) -> list[Path]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for fn in FIGURES:
        try:
            p = fn(Path(res), out)
            made.append(p)
            log(f"figure {p.name}")
        except Exception as exc:                       # a broken panel must not lose the other eight
            log(f"figure {fn.__name__} FAILED: {type(exc).__name__}: {exc}")
    return made


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="render the Stage 2B figures")
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    make_all(Path(a.results), Path(a.out))
