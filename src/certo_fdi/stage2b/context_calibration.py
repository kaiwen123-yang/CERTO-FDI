"""Healthy-only context calibration of the detection threshold (kickoff §05.4).

Stage 2A ran at ~1650 event false alarms/hour with a single global 0.995 healthy quantile, and
its healthy-OOD alarm rate was 2.75x its healthy-ID rate. Both numbers say the threshold does
not transfer across context. Stage 2B compares four ways of making the threshold
context-aware, all fitted on **healthy validation episodes only**:

``global_quantile``               one threshold for everything (the historical baseline)
``grouped_mondrian_backoff``      a per-context-group quantile with an explicit backoff path
``conditional_quantile_regression``  a small quantile regressor on the declared context
``episode_blocked_conformal``     conformal scores with whole episodes as the blocks

Context is the six declared physical fields only. Configuration-region id, trajectory-family id,
fault labels, contact link, severity and any truth state are never inputs.

On language: the conformal variant reports **marginal or grouped empirical coverage**. Nothing
here is an exact conditional CFAR guarantee and the code refuses to describe it as one -- the
whitener and the density head are both estimated from finite healthy data, and the windows
inside an episode are strongly dependent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

METHODS = ("global_quantile", "grouped_mondrian_backoff", "conditional_quantile_regression",
           "episode_blocked_conformal")
FORBIDDEN_LANGUAGE = ("exact conditional CFAR", "exact CFAR", "guaranteed conditional coverage")


def context_group(ctx_row: np.ndarray, names: list[str], level: list[str], cfg: dict) -> tuple:
    """The group key of one context vector at one hierarchy level."""
    idx = {n: i for i, n in enumerate(names)}
    key = []
    for field_name in level:
        if field_name == "controller_id":
            key.append(int(round(float(ctx_row[idx["controller_id"]]))))
        elif field_name == "speed_band":
            key.append(int(np.digitize(float(ctx_row[idx["speed_scale"]]), cfg["speed_bands"][1:-1])))
        elif field_name == "tool_mass_band":
            key.append(int(np.digitize(float(ctx_row[idx["tool_mass_kg"]]), cfg["tool_mass_bands"][1:-1])))
        else:
            key.append(float(ctx_row[idx[field_name]]))
    return tuple(key)


@dataclass
class Calibrator:
    """A fitted healthy-only threshold model. ``threshold(ctx)`` returns a per-window threshold."""

    method: str
    quantile: float
    params: dict = field(default_factory=dict)
    context_names: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    def threshold(self, ctx: np.ndarray) -> np.ndarray:
        ctx = np.atleast_2d(np.asarray(ctx, dtype=float))
        if self.method == "global_quantile":
            return np.full(len(ctx), float(self.params["threshold"]))
        if self.method == "grouped_mondrian_backoff":
            out = np.empty(len(ctx))
            for i, row in enumerate(ctx):
                out[i] = self._mondrian_lookup(row)[0]
            return out
        if self.method == "conditional_quantile_regression":
            model = self.params["model"]
            return np.asarray(model.predict(ctx), dtype=float)
        if self.method == "episode_blocked_conformal":
            # a conformal threshold is the (1-alpha) empirical quantile of the block scores;
            # marginal by construction, reported as such
            return np.full(len(ctx), float(self.params["threshold"]))
        raise ValueError(self.method)

    def _mondrian_lookup(self, row: np.ndarray) -> tuple[float, str]:
        cfg = self.params["mondrian_cfg"]
        for li, level in enumerate(self.params["hierarchy"]):
            key = context_group(row, self.context_names, level, cfg)
            hit = self.params["tables"][li].get(key)
            if hit is not None:
                return float(hit), f"level{li}:{level}"
        return float(self.params["global"]), "global"

    def backoff_path(self, ctx: np.ndarray) -> list[str]:
        if self.method != "grouped_mondrian_backoff":
            return ["n/a"] * len(np.atleast_2d(ctx))
        return [self._mondrian_lookup(r)[1] for r in np.atleast_2d(np.asarray(ctx, dtype=float))]

    def to_dict(self) -> dict[str, Any]:
        d = {"method": self.method, "quantile": self.quantile, "context_names": list(self.context_names),
             **{k: v for k, v in self.diagnostics.items()}}
        if self.method == "grouped_mondrian_backoff":
            d["n_groups_by_level"] = [len(t) for t in self.params["tables"]]
            d["min_episodes_per_leaf"] = self.params["mondrian_cfg"]["min_episodes_per_leaf"]
        if self.method in ("global_quantile", "episode_blocked_conformal"):
            d["threshold"] = float(self.params["threshold"])
        d["coverage_claim"] = ("marginal / grouped empirical only; NOT an exact conditional CFAR "
                               "guarantee (the whitener and head are estimated, and windows within "
                               "an episode are dependent)")
        return d


def fit(method: str, scores: np.ndarray, ctx: np.ndarray, episode: np.ndarray, quantile: float,
        context_names: list[str], cfg: dict) -> Calibrator:
    """Fit one calibrator on healthy validation windows. No fault data is ever passed in."""
    scores = np.asarray(scores, dtype=float)
    ctx = np.atleast_2d(np.asarray(ctx, dtype=float))
    episode = np.asarray(episode)
    diag = {"n_windows": int(len(scores)), "n_episodes": int(len(np.unique(episode)))}

    if method == "global_quantile":
        thr = float(np.quantile(scores, quantile))
        return Calibrator(method, quantile, {"threshold": thr}, context_names, diag)

    if method == "grouped_mondrian_backoff":
        m = cfg["mondrian"]
        hierarchy = [list(level) for level in m["hierarchy"]]
        tables = []
        for level in hierarchy:
            tab: dict[tuple, float] = {}
            if level:
                keys = [context_group(r, context_names, level, m) for r in ctx]
                keys_arr = np.array([hash(k) for k in keys])
                for k in {tuple(x) for x in keys}:
                    sel = np.array([kk == k for kk in keys])
                    if len(np.unique(episode[sel])) >= int(m["min_episodes_per_leaf"]):
                        tab[k] = float(np.quantile(scores[sel], quantile))
            tables.append(tab)
        return Calibrator(method, quantile,
                          {"hierarchy": hierarchy, "tables": tables, "mondrian_cfg": m,
                           "global": float(np.quantile(scores, quantile))},
                          context_names, diag)

    if method == "conditional_quantile_regression":
        from sklearn.ensemble import GradientBoostingRegressor

        q = cfg["quantile_regression"]
        model = GradientBoostingRegressor(loss="quantile", alpha=float(quantile),
                                          max_depth=int(q["max_depth"]), n_estimators=int(q["n_estimators"]),
                                          learning_rate=float(q["learning_rate"]), random_state=0)
        model.fit(ctx, scores)
        diag["model"] = "gradient_boosting_quantile"
        diag["model_fixed_before_fault_evaluation"] = True
        return Calibrator(method, quantile, {"model": model}, context_names, diag)

    if method == "episode_blocked_conformal":
        # nonconformity = the window score; the calibration set is the *episode maxima*, so the
        # unit of exchangeability is the episode rather than the overlapping window
        per_ep = np.array([scores[episode == e].max() for e in np.unique(episode)])
        n = len(per_ep)
        k = int(np.ceil((n + 1) * quantile)) - 1
        k = int(np.clip(k, 0, n - 1))
        thr = float(np.sort(per_ep)[k])
        diag.update({"n_calibration_blocks": n, "block_unit": "episode",
                     "nonconformity": "per-episode maximum window score",
                     "rank_used": k + 1, "nominal_marginal_coverage": (k + 1) / (n + 1)})
        return Calibrator(method, quantile, {"threshold": thr}, context_names, diag)

    raise ValueError(method)


def grouped_coverage(cal: Calibrator, scores: np.ndarray, ctx: np.ndarray, episode: np.ndarray,
                     context_names: list[str], cfg: dict) -> list[dict]:
    """Empirical (marginal and per-group) non-alarm coverage on held-out healthy windows."""
    thr = cal.threshold(ctx)
    below = scores <= thr
    rows = [{"group": "MARGINAL", "n_windows": int(len(scores)), "n_episodes": int(len(np.unique(episode))),
             "empirical_coverage": float(below.mean()), "alarm_rate": float(1 - below.mean())}]
    m = cfg["mondrian"]
    level = m["hierarchy"][0]
    keys = [context_group(r, context_names, level, m) for r in np.atleast_2d(ctx)]
    for k in sorted({tuple(x) for x in keys}):
        sel = np.array([kk == k for kk in keys])
        rows.append({"group": str(k), "n_windows": int(sel.sum()),
                     "n_episodes": int(len(np.unique(episode[sel]))),
                     "empirical_coverage": float(below[sel].mean()),
                     "alarm_rate": float(1 - below[sel].mean())})
    return rows
