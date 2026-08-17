"""Phase 2/3: reconstruct the exact Stage 2A and Stage 2B contact-localization evidence.

Both stages saved the per-window, per-link score arrays the reproduction gate was computed from,
so the audit reads evidence source #1 in the contract's preferred order and never has to re-run
inference:

``Stage 2A``  ``p5_ablations/scores_seed<S>.npz`` -> ``contact_residual`` (Nw, 7)
    the ridge projection residual **norm**, produced by ``pathways.geometry.batched_projection``
    via ``window_features._project``. ``run_stage2a_metrics.py`` reads this exact file to build
    ``stage2a_localization_metrics.csv``, which is the number the gate uses as its reference.

``Stage 2B``  ``p1_loadpath/controls_seed<S>.npz`` -> ``time_aligned_jacobian__rss`` (Nw, 7)
    the exact rank-truncated projection residual **energy**, produced by
    ``stage2b.rank_aware_scores.project``. ``run_stage2b_decide.py`` reads the table built from
    this file as the gate's observed value.

The two are joined on ``(seed, episode_id, window_start)`` -- the only key that is unique in both
and carries no derived quantity. Both stages then apply the *same* aggregation, so any label
difference has to come from the score.

Nothing here recomputes science. The frozen arrays are read, joined and compared.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

N_LINKS = 7
#: Stage 2A ranks by the residual norm, Stage 2B by its square. Squaring is monotone, so it moves
#: no label; it is applied only so the two live in the same units and can be differenced.
STAGE2A_KEY = "contact_residual"
STAGE2B_KEY = "time_aligned_jacobian__rss"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def episode_vote(pred: np.ndarray, n_links: int = N_LINKS) -> int:
    """The frozen majority vote, identical in both stages' metric code.

    ``run_stage2a_metrics._episode_vote`` and ``run_stage2b_loadpath._episode_vote`` are the same
    function: ``np.bincount(pred[pred >= 0], minlength=7).argmax()``. Deterministic in the counts,
    with the tie broken toward the lowest link index.
    """
    p = np.asarray(pred, dtype=int)
    p = p[p >= 0]
    return int(np.bincount(p, minlength=n_links).argmax()) if p.size else -1


def vote_detail(pred: np.ndarray, n_links: int = N_LINKS) -> dict:
    p = np.asarray(pred, dtype=int)
    p = p[p >= 0]
    counts = np.bincount(p, minlength=n_links) if p.size else np.zeros(n_links, dtype=int)
    order = np.argsort(-counts, kind="stable")
    return {"counts": counts.astype(int).tolist(),
            "predicted_link": int(np.argmax(counts)) if p.size else -1,
            "vote_margin": int(counts[order[0]] - counts[order[1]]),
            "runner_up": int(order[1]),
            "is_vote_tie": bool(counts[order[0]] == counts[order[1]]),
            "n_windows": int(p.size)}


def load_pair(stage2a_run: Path, stage2b_run: Path, seed: int) -> dict:
    """Load and join one seed's frozen score arrays.

    Returns the F4 faulty windows present in **both** stages, with the join asserted complete and
    unique. A window that exists in only one stage is reported rather than dropped silently.
    """
    pa = Path(stage2a_run) / "p5_ablations" / f"scores_seed{seed}.npz"
    pb = Path(stage2b_run) / "p1_loadpath" / f"controls_seed{seed}.npz"
    a = np.load(pa, allow_pickle=False)
    b = np.load(pb, allow_pickle=False)

    ka = np.char.add(np.char.add(a["episode"].astype(str), "|"), a["start"].astype(str))
    kb = np.char.add(np.char.add(b["episode"].astype(str), "|"), b["start"].astype(str))
    if len(set(ka.tolist())) != len(ka):
        raise ValueError(f"Stage 2A seed {seed}: join key is not unique")
    if len(set(kb.tolist())) != len(kb):
        raise ValueError(f"Stage 2B seed {seed}: join key is not unique")

    # the localizer votes on faulty F4 windows only, in both stages
    fa = (a["family"].astype(str) == "F4_contact") & (a["label"] == 1) & (a["target"] >= 0)
    fb = (b["family"].astype(str) == "F4_contact") & (b["label"] == 1) & (b["target"] >= 0)
    set_a, set_b = set(ka[fa].tolist()), set(kb[fb].tolist())
    only_a, only_b = sorted(set_a - set_b), sorted(set_b - set_a)

    common = sorted(set_a & set_b)
    ia = {k: i for i, k in enumerate(ka.tolist())}
    ib = {k: i for i, k in enumerate(kb.tolist())}
    idx_a = np.array([ia[k] for k in common], dtype=int)
    idx_b = np.array([ib[k] for k in common], dtype=int)

    score_a = np.asarray(a[STAGE2A_KEY], dtype=float)[idx_a] ** 2      # norm -> energy
    score_b = np.asarray(b[STAGE2B_KEY], dtype=float)[idx_b]
    rank_b = np.asarray(b["time_aligned_jacobian__rank"], dtype=int)[idx_b]
    ess_b = np.asarray(b["time_aligned_jacobian__ess"], dtype=float)[idx_b]

    episode = a["episode"].astype(str)[idx_a]
    target = np.asarray(a["target"], dtype=int)[idx_a]
    target_b = np.asarray(b["target"], dtype=int)[idx_b]
    if not np.array_equal(target, target_b):
        raise ValueError(f"seed {seed}: truth links disagree between the two frozen runs")

    return {
        "seed": seed,
        "path_a": str(pa), "path_b": str(pb),
        "sha_a": sha256_file(pa), "sha_b": sha256_file(pb),
        "key": np.array(common), "episode": episode, "target": target,
        "start": np.asarray(a["start"], dtype=int)[idx_a],
        "split": a["split"].astype(str)[idx_a],
        "score_a": score_a, "score_b": score_b,
        "rank_b": rank_b, "ess_b": ess_b,
        # RSS + ESS reconstructs the residual energy; it is per-link only because RSS is, and the
        # spread across links is a free consistency check on the frozen arrays
        "z_energy_b": (score_b + ess_b).mean(1),
        "z_energy_link_spread": float(np.max(np.ptp(score_b + ess_b, axis=1))),
        "n_windows_a_only": len(only_a), "n_windows_b_only": len(only_b),
        "windows_a_only": only_a[:20], "windows_b_only": only_b[:20],
        "join_complete": bool(not only_a and not only_b),
        "n_common": len(common),
    }


def window_predictions(score: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``argmin`` over links plus the top-two margin, exactly as both stages do it.

    NumPy's ``argmin`` returns the first minimum, so an exact tie resolves to the lowest link
    index. ``order`` uses a stable sort for the same reason.
    """
    s = np.asarray(score, dtype=float)
    valid = np.isfinite(s).all(1)
    filled = np.where(np.isfinite(s), s, np.inf)
    pred = np.where(valid, np.argmin(filled, axis=1), -1).astype(int)
    order = np.argsort(filled, axis=1, kind="stable")
    idx = np.arange(len(pred))
    margin = filled[idx, order[:, 1]] - filled[idx, order[:, 0]]
    return pred, margin, order


def episode_table(pair: dict) -> list[dict]:
    """One row per (seed, episode): both stages' votes, labels and vote margins."""
    pred_a, margin_a, _ = window_predictions(pair["score_a"])
    pred_b, margin_b, _ = window_predictions(pair["score_b"])
    rows = []
    for eid in sorted(set(pair["episode"].tolist())):
        m = pair["episode"] == eid
        t = int(pair["target"][m][0])
        va, vb = vote_detail(pred_a[m]), vote_detail(pred_b[m])
        rows.append({
            "seed": pair["seed"], "episode_id": eid, "truth_link": t,
            "n_windows": int(m.sum()),
            "stage2a_predicted_link": va["predicted_link"],
            "stage2b_predicted_link": vb["predicted_link"],
            "label_changed": bool(va["predicted_link"] != vb["predicted_link"]),
            "stage2a_correct": int(va["predicted_link"] == t),
            "stage2b_correct": int(vb["predicted_link"] == t),
            "stage2a_vote_counts": "|".join(map(str, va["counts"])),
            "stage2b_vote_counts": "|".join(map(str, vb["counts"])),
            "stage2a_vote_margin": va["vote_margin"],
            "stage2b_vote_margin": vb["vote_margin"],
            "n_windows_predicted_differently": int((pred_a[m] != pred_b[m]).sum()),
            "median_window_margin_stage2b": float(np.median(margin_b[m])),
            "min_window_margin_stage2b": float(np.min(margin_b[m])),
            "max_relative_score_gap": float(np.max(
                np.abs(pair["score_a"][m] - pair["score_b"][m])
                / np.maximum(np.abs(pair["score_b"][m]), 1e-300))),
        })
    return rows


def link_table(pair: dict) -> list[dict]:
    """One row per (seed, episode, link): both stages' scores, their gap, and the frozen rank."""
    rows = []
    for eid in sorted(set(pair["episode"].tolist())):
        m = pair["episode"] == eid
        t = int(pair["target"][m][0])
        a, b = pair["score_a"][m], pair["score_b"][m]
        rk = pair["rank_b"][m]
        for l in range(N_LINKS):
            gap = np.abs(a[:, l] - b[:, l])
            rel = gap / np.maximum(np.abs(b[:, l]), 1e-300)
            rows.append({
                "seed": pair["seed"], "episode_id": eid, "truth_link": t, "link": l,
                "n_windows": int(m.sum()),
                "stage2a_mean_score": float(a[:, l].mean()),
                "stage2b_mean_score": float(b[:, l].mean()),
                "median_abs_gap": float(np.median(gap)),
                "max_abs_gap": float(gap.max()),
                "median_relative_gap": float(np.median(rel)),
                "max_relative_gap": float(rel.max()),
                "frozen_rank_min": int(rk[:, l].min()),
                "frozen_rank_max": int(rk[:, l].max()),
                "frozen_rank_mean": float(rk[:, l].mean()),
            })
    return rows


def confusion(pred: np.ndarray, truth: np.ndarray, n_links: int = N_LINKS) -> np.ndarray:
    c = np.zeros((n_links, n_links), dtype=int)
    for t, p in zip(np.asarray(truth, int), np.asarray(pred, int)):
        if 0 <= t < n_links and 0 <= p < n_links:
            c[t, p] += 1
    return c


def flipped_episode_trace(pair: dict, episode_id: str) -> dict:
    """Everything the contract asks for about one episode, straight from the frozen arrays."""
    m = pair["episode"] == episode_id
    a, b = pair["score_a"][m], pair["score_b"][m]
    rk, zen = pair["rank_b"][m], pair["z_energy_b"][m]
    starts = pair["start"][m]
    pa, ma, oa = window_predictions(a)
    pb, mb, ob = window_predictions(b)
    t = int(pair["target"][m][0])

    windows = []
    for i in range(int(m.sum())):
        windows.append({
            "window_start": int(starts[i]),
            "z_energy": float(zen[i]),
            "stage2a_scores": [float(v) for v in a[i]],
            "stage2b_scores": [float(v) for v in b[i]],
            "stage2a_predicted_link": int(pa[i]), "stage2b_predicted_link": int(pb[i]),
            "stage2a_order": [int(v) for v in oa[i]], "stage2b_order": [int(v) for v in ob[i]],
            "stage2a_margin": float(ma[i]), "stage2b_margin": float(mb[i]),
            "frozen_rank_per_link": [int(v) for v in rk[i]],
            "prediction_changed": bool(pa[i] != pb[i]),
            "max_relative_score_gap": float(np.max(np.abs(a[i] - b[i]) / np.maximum(np.abs(b[i]), 1e-300))),
        })
    va, vb = vote_detail(pa), vote_detail(pb)
    changed = [w for w in windows if w["prediction_changed"]]
    return {
        "seed": pair["seed"], "episode_id": episode_id, "truth_link": t,
        "n_windows": int(m.sum()),
        "stage2a_vote": va, "stage2b_vote": vb,
        "n_windows_changed": len(changed),
        "changed_windows": changed,
        "score_gap": {
            "median_relative": float(np.median(np.abs(a - b) / np.maximum(np.abs(b), 1e-300))),
            "max_relative": float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300))),
            "n_bit_identical": int((a == b).sum()), "n_pairs": int(a.size),
        },
        "frozen_rank": {"min": int(rk.min()), "max": int(rk.max()),
                        "per_link_mean": [float(v) for v in rk.mean(0)]},
        "tie_break": "lowest link index (np.argmin / np.bincount().argmax() return the first extremum)",
        "all_windows": windows,
    }
