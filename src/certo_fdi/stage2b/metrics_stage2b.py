"""Shared Stage 2B metric definitions (kickoff §13).

Every number that reaches a decision rule is computed here, once, so the decision code and the
figures cannot silently disagree with the tables. Three conventions are enforced throughout:

* the **episode** is the independent unit -- top-1, chain distance and every confidence interval
  are episode-level, and the bootstrap resamples whole episodes;
* a metric that cannot be computed returns ``nan`` and is reported as ``MISSING``, never imputed;
* differences between methods are **paired by episode** wherever the same episodes were scored by
  both, because the episode-to-episode variance dwarfs the effect sizes at n = 24.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

import numpy as np

#: the load-path gains the decomposition has to separate (kickoff §04.4)
GAIN_TERMS = ("support", "shape", "temporal")


# ---------------------------------------------------------------- localization
def localization_metrics(pred: Sequence[int], truth: Sequence[int], ranking: np.ndarray | None = None,
                         links: Sequence[int] | None = None) -> dict[str, Any]:
    """Episode-level top-1 / top-2 / mean chain distance and per-link recall.

    ``ranking`` is the (n_episodes, n_links) ordering of link hypotheses, best first; top-2 is
    ``nan`` when no ranking was supplied rather than silently equal to top-1.
    """
    P = np.asarray(pred, dtype=int)
    T = np.asarray(truth, dtype=int)
    if len(P) == 0:
        return {"episode_top1": float("nan"), "episode_top2": float("nan"),
                "mean_chain_distance": float("nan"), "n_episodes": 0, "per_link_recall": {},
                "n_links_recall_ge_040": 0, "status": "MISSING"}
    top2 = float("nan")
    if ranking is not None and np.asarray(ranking).size:
        R = np.asarray(ranking, dtype=int)
        top2 = float(np.mean([T[i] in R[i, :2] for i in range(len(T))]))
    present = sorted(set(int(t) for t in T)) if links is None else [int(l) for l in links]
    per_link = {int(l): (float((P[T == l] == l).mean()) if (T == l).any() else float("nan")) for l in present}
    return {"episode_top1": float((P == T).mean()),
            "episode_top2": top2,
            "mean_chain_distance": float(np.abs(P - T).mean()),
            "n_episodes": int(len(P)),
            "per_link_recall": per_link,
            "n_links_recall_ge_040": int(sum(1 for v in per_link.values() if v == v and v >= 0.40)),
            "status": "OK"}


def confusion_matrix(pred: Sequence[int], truth: Sequence[int], links: Sequence[int]) -> np.ndarray:
    """Rows = truth link, columns = predicted link, over the declared link set."""
    links = [int(l) for l in links]
    idx = {l: i for i, l in enumerate(links)}
    M = np.zeros((len(links), len(links)), dtype=int)
    for p, t in zip(pred, truth):
        if int(t) in idx and int(p) in idx:
            M[idx[int(t)], idx[int(p)]] += 1
    return M


# ---------------------------------------------------------------- load-path gains
def gain_decomposition(aligned: float, shuffled: float, fixed: float, support: float,
                       random_within: float) -> dict[str, float]:
    """Split the localization gain into support / subspace-shape / time-alignment terms.

    ``support``   what a rank-matched, geometry-free prefix mask alone achieves;
    ``fixed``     one real Jacobian at a reference configuration -- adds the *shape* of the
                  Cartesian subspace but no per-window trajectory information;
    ``shuffled``  the episode's real Jacobians with the time correspondence destroyed;
    ``aligned``   the true time-aligned Jacobians.

    The three gains are therefore ``support - random_within`` (does the mask beat a rank-matched
    random frame at all), ``fixed - support`` (shape) and ``aligned - fixed`` (trajectory
    geometry, of which ``aligned - shuffled`` is the part that needs exact time correspondence).
    """
    return {"delta_support": float(support - random_within),
            "delta_shape": float(fixed - support),
            "delta_temporal": float(aligned - fixed),
            "delta_time_alignment": float(aligned - shuffled),
            "delta_total": float(aligned - random_within),
            "aligned": float(aligned), "shuffled_time": float(shuffled), "fixed_reference": float(fixed),
            "support_prefix": float(support), "random_within_support": float(random_within)}


def rank_matched(ranks_by_method: dict[str, float], tolerance: float = 1e-6) -> dict[str, Any]:
    """True only when the synthetic controls realise the *same* mean rank as the aligned run."""
    vals = {k: float(v) for k, v in ranks_by_method.items()}
    if not vals:
        return {"matched": False, "reason": "no ranks supplied", "ranks": {}}
    ref = vals.get("time_aligned_jacobian", next(iter(vals.values())))
    spread = {k: abs(v - ref) for k, v in vals.items()}
    return {"matched": all(d <= tolerance for d in spread.values()),
            "reference_mean_rank": ref, "ranks": vals, "abs_deviation": spread,
            "tolerance": float(tolerance)}


# ---------------------------------------------------------------- episode-level uncertainty
def episode_bootstrap_ci(episode_ids: Sequence, values: Sequence[float],
                         statistic: Callable[[np.ndarray], float] = np.mean,
                         n_resamples: int = 2000, alpha: float = 0.05, seed: int = 20260816) -> dict[str, float]:
    """Percentile CI that resamples whole episodes. Window-level IID bootstrap is forbidden."""
    from certo_fdi.experiments.stage2b_common import episode_cluster_bootstrap

    return episode_cluster_bootstrap(np.asarray(episode_ids), np.asarray(values, dtype=float),
                                     statistic, n_resamples=n_resamples, alpha=alpha, seed=seed)


def paired_difference_ci(episode_ids: Sequence, a: Sequence[float], b: Sequence[float],
                         n_resamples: int = 2000, alpha: float = 0.05, seed: int = 20260816) -> dict[str, float]:
    """CI on ``mean(a - b)`` with episodes resampled jointly, so the pairing is preserved."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    out = episode_bootstrap_ci(episode_ids, a - b, np.mean, n_resamples, alpha, seed)
    out["mean_a"] = float(np.nanmean(a))
    out["mean_b"] = float(np.nanmean(b))
    out["excludes_zero"] = bool(out["ci_low"] == out["ci_low"] and (out["ci_low"] > 0 or out["ci_high"] < 0))
    return out


def seed_spread(values_by_seed: dict[int, float]) -> dict[str, Any]:
    """Mean / min / max across retraining seeds. Seeds are a separate axis from episodes."""
    v = np.array([float(x) for x in values_by_seed.values()], dtype=float)
    finite = v[np.isfinite(v)]
    if finite.size == 0:
        return {"mean": float("nan"), "min": float("nan"), "max": float("nan"),
                "n_seeds": len(values_by_seed), "status": "MISSING"}
    return {"mean": float(finite.mean()), "min": float(finite.min()), "max": float(finite.max()),
            "std": float(finite.std(ddof=1)) if finite.size > 1 else 0.0,
            "n_seeds": int(finite.size), "by_seed": {str(k): float(x) for k, x in values_by_seed.items()},
            "status": "OK"}


# ---------------------------------------------------------------- reproduction / monotonicity
def relative_deviation(observed: float, reference: float) -> float:
    """|observed - reference| / |reference|, ``nan`` if either side is missing."""
    if observed != observed or reference != reference or reference == 0:
        return float("nan")
    return float(abs(observed - reference) / abs(reference))


def monotone_improvement(values: Sequence[float], lower_is_better: bool = False) -> dict[str, Any]:
    """Whether a learning curve improves at every step, and by how much overall."""
    v = np.asarray(values, dtype=float)
    if v.size < 2 or not np.isfinite(v).all():
        return {"monotone_improving": False, "n_improving_steps": 0, "n_steps": max(0, v.size - 1),
                "total_change": float("nan"), "status": "MISSING"}
    d = np.diff(v)
    better = d < 0 if lower_is_better else d > 0
    return {"monotone_improving": bool(better.all()), "n_improving_steps": int(better.sum()),
            "n_steps": int(len(d)), "total_change": float(v[-1] - v[0]),
            "values": v.tolist(), "status": "OK"}


# ---------------------------------------------------------------- detection / sequential
def operating_point(fa_per_hour: float, event_tpr: float, delay_median_s: float,
                    delay_p95_s: float, target_fa_per_hour: float) -> dict[str, Any]:
    """One row of the detection operating characteristic, with the target verdict attached."""
    meets = bool(fa_per_hour == fa_per_hour and fa_per_hour <= target_fa_per_hour)
    return {"false_alarms_per_hour": float(fa_per_hour), "event_tpr": float(event_tpr),
            "detection_delay_median_s": float(delay_median_s), "detection_delay_p95_s": float(delay_p95_s),
            "target_fa_per_hour": float(target_fa_per_hour),
            "meets_target": meets, "status": "OK" if meets else "TARGET_NOT_REACHED"}


def ood_id_alarm_ratio(fa_ood: float, fa_id: float) -> dict[str, Any]:
    """Healthy OOD / healthy ID alarm-rate ratio, with the degenerate zero-denominator case named.

    A healthy-ID rate of exactly zero over a finite number of episodes is *not* evidence that the
    threshold transfers; it means the ID rate is below the resolution of the sample. The ratio is
    reported as infinite and the condition is failed conservatively rather than being waived.
    """
    if fa_id != fa_id or fa_ood != fa_ood:
        return {"ratio": float("nan"), "status": "MISSING", "degenerate": False,
                "interpretation": "one of the two rates is missing"}
    if fa_id == 0.0:
        return {"ratio": float("inf") if fa_ood > 0 else float("nan"),
                "status": "DEGENERATE", "degenerate": True,
                "fa_ood_per_hour": float(fa_ood), "fa_id_per_hour": 0.0,
                "interpretation": ("healthy-ID false alarms are exactly zero on the observed episodes, so the "
                                   "ratio is not estimable; the transfer condition is failed conservatively "
                                   "rather than waived")}
    return {"ratio": float(fa_ood / fa_id), "status": "OK", "degenerate": False,
            "fa_ood_per_hour": float(fa_ood), "fa_id_per_hour": float(fa_id),
            "interpretation": "finite ratio of healthy-OOD to healthy-ID event false alarms per hour"}
