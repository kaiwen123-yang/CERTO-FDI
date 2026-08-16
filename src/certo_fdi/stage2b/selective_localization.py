"""Accept/defer for contact-link localization (kickoff §04.8, §07.3).

An ambiguity feature is only useful if declining to answer actually *reduces the error on the
answers you keep*. A feature that merely correlates with error is not enough -- it has to
produce a risk-coverage curve that beats full coverage. That is the bar the decision rules use,
and it is checked here rather than asserted.

Five frozen candidate features, all computed from the localizer's own output (no fault label,
no truth link, no test episode):

``best_second_margin``     rank-corrected margin between the best and second-best link
``subwindow_stability``    agreement between predictions on the two halves of the window set
``perturbation_stability`` agreement under bootstrap perturbations of the whitened residual
``normalized_link_evidence`` the posterior-like top-1 mass over links
``absolute_fit_adequacy``  how well the winning link explains the residual in absolute terms

Everything is aggregated to the **episode** level before thresholding: an episode is either
accepted or deferred as a whole, which is both the operationally meaningful unit and the
statistically independent one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

FEATURES = ("best_second_margin", "subwindow_stability", "perturbation_stability",
            "normalized_link_evidence", "absolute_fit_adequacy")
#: True when a larger feature value means "more confident" (so accept the high end)
HIGHER_IS_MORE_CONFIDENT = {f: True for f in FEATURES}


def subwindow_stability(pred_windows: np.ndarray) -> float:
    """Agreement between the majority vote of the first and second half of an episode's windows."""
    n = len(pred_windows)
    if n < 2:
        return 1.0
    a, b = pred_windows[: n // 2], pred_windows[n // 2:]
    va = int(np.bincount(a[a >= 0], minlength=7).argmax()) if (a >= 0).any() else -1
    vb = int(np.bincount(b[b >= 0], minlength=7).argmax()) if (b >= 0).any() else -1
    return float(va == vb and va >= 0)


def perturbation_stability(rss: np.ndarray, rank: np.ndarray, ess: np.ndarray, dimension: int,
                           score: str, acceptance: np.ndarray | None, n_replicates: int, seed: int) -> float:
    """Fraction of residual-bootstrap replicates that reproduce the episode's predicted link.

    The perturbation resamples the episode's own windows (an episode-level bootstrap), which is
    the same independence unit used everywhere else in this stage.
    """
    from certo_fdi.stage2b.rank_aware_scores import ProjectionStats, predict_link

    n = rss.shape[0]
    if n == 0:
        return 0.0
    stats = ProjectionStats(rss=rss, ess=ess, rank=rank, z_energy=rss.sum(1), dimension=dimension)
    base = predict_link(stats, score, acceptance)
    v0 = int(np.bincount(base[base >= 0], minlength=7).argmax()) if (base >= 0).any() else -1
    rng = np.random.default_rng(seed)
    agree = 0
    for _ in range(n_replicates):
        idx = rng.integers(0, n, size=n)
        s2 = ProjectionStats(rss=rss[idx], ess=ess[idx], rank=rank[idx], z_energy=rss[idx].sum(1), dimension=dimension)
        p = predict_link(s2, score, acceptance)
        v = int(np.bincount(p[p >= 0], minlength=7).argmax()) if (p >= 0).any() else -1
        agree += int(v == v0)
    return float(agree / max(n_replicates, 1))


@dataclass
class EpisodeConfidence:
    """Per-episode accept/defer features and the localizer's answer."""

    episode_id: str
    predicted_link: int
    target_link: int
    features: dict[str, float] = field(default_factory=dict)
    n_windows: int = 0
    split: str = ""


def risk_coverage(conf: list[EpisodeConfidence], feature: str, coverages: list[float]) -> list[dict]:
    """Selective top-1 / chain distance at each requested coverage, plus the accept threshold.

    Episodes are ranked by confidence and the least-confident tail is deferred. The threshold at
    each coverage is reported so it can be frozen from the calibration partition and *applied*
    unchanged to the test partition.
    """
    if not conf:
        return []
    v = np.array([c.features.get(feature, np.nan) for c in conf], dtype=float)
    correct = np.array([c.predicted_link == c.target_link for c in conf], dtype=float)
    dist = np.array([abs(c.predicted_link - c.target_link) for c in conf], dtype=float)
    order = np.argsort(-v if HIGHER_IS_MORE_CONFIDENT[feature] else v)   # most confident first
    out = []
    n = len(conf)
    for cov in coverages:
        k = max(1, int(round(cov * n)))
        keep = order[:k]
        thr = float(v[order[k - 1]]) if k <= n else float("-inf")
        out.append({"feature": feature, "target_coverage": float(cov), "achieved_coverage": float(k / n),
                    "n_accepted": int(k), "n_total": int(n),
                    "selective_top1": float(correct[keep].mean()),
                    "selective_chain_distance": float(dist[keep].mean()),
                    "full_top1": float(correct.mean()), "full_chain_distance": float(dist.mean()),
                    "top1_gain_over_full": float(correct[keep].mean() - correct.mean()),
                    "accept_threshold": thr,
                    "threshold_direction": "accept if feature >= threshold" if HIGHER_IS_MORE_CONFIDENT[feature] else "accept if feature <= threshold"})
    return out


def apply_threshold(conf: list[EpisodeConfidence], feature: str, threshold: float) -> np.ndarray:
    """(n,) accept mask from a threshold frozen on the calibration partition."""
    v = np.array([c.features.get(feature, np.nan) for c in conf], dtype=float)
    return (v >= threshold) if HIGHER_IS_MORE_CONFIDENT[feature] else (v <= threshold)


def selective_metrics(conf: list[EpisodeConfidence], accept: np.ndarray) -> dict[str, float]:
    correct = np.array([c.predicted_link == c.target_link for c in conf], dtype=float)
    dist = np.array([abs(c.predicted_link - c.target_link) for c in conf], dtype=float)
    accept = np.asarray(accept, dtype=bool)
    if accept.sum() == 0:
        return {"coverage": 0.0, "selective_top1": float("nan"), "selective_chain_distance": float("nan"),
                "full_top1": float(correct.mean()), "full_chain_distance": float(dist.mean()),
                "reduces_error": False, "n_accepted": 0, "n_total": int(len(conf))}
    sel_t1 = float(correct[accept].mean())
    sel_cd = float(dist[accept].mean())
    return {"coverage": float(accept.mean()), "selective_top1": sel_t1, "selective_chain_distance": sel_cd,
            "full_top1": float(correct.mean()), "full_chain_distance": float(dist.mean()),
            "top1_gain_over_full": sel_t1 - float(correct.mean()),
            "chain_distance_reduction_over_full": float(dist.mean()) - sel_cd,
            "reduces_error": bool(sel_t1 > correct.mean() + 1e-12),
            "n_accepted": int(accept.sum()), "n_total": int(len(conf))}


def select_feature_and_threshold(conf: list[EpisodeConfidence], coverages: list[float],
                                 min_coverage: float) -> dict:
    """Pick the accept/defer feature and threshold on the **calibration** partition only.

    Selection rule, fixed in advance: among features and coverages with achieved coverage at or
    above ``min_coverage``, take the one with the highest selective top-1; ties break toward the
    higher coverage, then alphabetically by feature so the choice is deterministic.
    """
    rows = []
    for f in FEATURES:
        rows += risk_coverage(conf, f, coverages)
    eligible = [r for r in rows if r["achieved_coverage"] >= min_coverage - 1e-9 and r["selective_top1"] == r["selective_top1"]]
    if not eligible:
        return {"selected": None, "rows": rows, "reason": "no feature reached the minimum coverage"}
    best = sorted(eligible, key=lambda r: (-r["selective_top1"], -r["achieved_coverage"], r["feature"]))[0]
    return {"selected": {"feature": best["feature"], "threshold": best["accept_threshold"],
                         "target_coverage": best["target_coverage"],
                         "calibration_selective_top1": best["selective_top1"],
                         "calibration_coverage": best["achieved_coverage"],
                         "calibration_full_top1": best["full_top1"]},
            "rows": rows,
            "rule": ("highest selective top-1 among (feature, coverage) points with coverage >= "
                     f"{min_coverage}; ties -> higher coverage, then alphabetical"),
            "partition": "F4_CAL only"}
