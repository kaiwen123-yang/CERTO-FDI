"""Phase B-RoAD native baselines, faithful to the paper's protocol (Table IV).

Protocol facts extracted from the RoAD paper text (road.txt l.694-745, 630-668):
  - per-SAMPLE evaluation (no windows) on the 86 signal columns,
  - min-max normalization fitted on the Training Set,
  - default scikit-learn parameters for kNN and Isolation Forest,
  - three test subsets: Collision (point anomalies inside the recordings),
    Weight and Velocity (ENTIRE recordings anomalous, labels 1/2),
  - for Weight/Velocity the negatives come from the independent CONTROL SET;
    for Collision the negatives are the recording's own normal samples,
  - metric: AUC-ROC per subset; paper Table IV reference:
        kNN               0.62 / 0.47 / 0.54
        IsolationForest   0.65 / 0.74 / 0.74
        (GDN 0.68/0.62/0.67, OmniAnomaly 0.67/0.70/0.63 — deep set not rerun here)

Reproduction level targeted: FAITHFUL_PAPER (paper text is the spec; the
paper's exact random seeds and library versions are not published).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROAD_REPO = Path("/mnt/g/CERTO-FDI/01_frozen_sources/public_baseline_repos/roaddataset")
RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/b_road"
)
PAPER_TABLE_IV = {
    "knn": {"collision": 0.62, "weight": 0.47, "velocity": 0.54},
    "iforest": {"collision": 0.65, "weight": 0.74, "velocity": 0.74},
}
SEEDS = (260824, 260825, 260826)

sys.path.insert(0, str(ROAD_REPO))


def main() -> int:
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import roc_auc_score
    from sklearn.neighbors import NearestNeighbors

    from RoADDataset.functions import Dataset

    ds = Dataset(normalize=False)
    train = np.concatenate([a[:, :86] for a in ds.sets["training"]], axis=0)
    mn, mx = train.min(0), train.max(0)
    span = np.where(mx - mn < 1e-12, 1.0, mx - mn)

    def norm(x: np.ndarray) -> np.ndarray:
        return (x - mn) / span

    xtr = norm(train)
    control = norm(np.concatenate([a[:, :86] for a in ds.sets["control"]], axis=0))

    # subsample training for kNN reference set to keep runtime sane; recorded.
    rng = np.random.default_rng(SEEDS[0])
    knn_ref = xtr[rng.choice(len(xtr), 60000, replace=False)]

    results: dict = {"protocol": "per-sample, min-max train-normalized, default params; "
                                 "weight/velocity vs control-set negatives (paper l.694-745)",
                     "knn_reference_subsample": 60000,
                     "paper_table_iv": PAPER_TABLE_IV, "models": {}}

    def eval_scores(score_fn, name: str) -> dict:
        out = {}
        # Collision: within-recording normals as negatives
        pos_scores, neg_scores = [], []
        for rec in ds.sets["collision"]:
            x = norm(rec[:, :86]); y = rec[:, 86] > 0
            s = score_fn(x)
            pos_scores.append(s[y]); neg_scores.append(s[~y])
        y_all = np.concatenate([np.ones(sum(map(len, pos_scores))), np.zeros(sum(map(len, neg_scores)))])
        s_all = np.concatenate(pos_scores + neg_scores)
        out["collision"] = float(roc_auc_score(y_all, s_all))
        # Weight / Velocity: entire recordings positive, control set negative
        s_ctrl = score_fn(control)
        for set_name in ("weight", "velocity"):
            s_pos = np.concatenate([score_fn(norm(rec[:, :86])) for rec in ds.sets[set_name]])
            y = np.concatenate([np.ones(len(s_pos)), np.zeros(len(s_ctrl))])
            s = np.concatenate([s_pos, s_ctrl])
            out[set_name] = float(roc_auc_score(y, s))
        ref = PAPER_TABLE_IV.get(name, {})
        out["abs_diff_vs_paper"] = {k: round(abs(out[k] - v), 4) for k, v in ref.items()}
        return out

    # kNN (paper default: sklearn defaults => n_neighbors=5, mean distance used
    # as the standard anomaly score for kNN detectors)
    nn = NearestNeighbors(n_neighbors=5).fit(knn_ref)

    def knn_score(x, batch=20000):
        out = []
        for i in range(0, len(x), batch):
            d, _ = nn.kneighbors(x[i : i + batch])
            out.append(d.mean(1))
        return np.concatenate(out)

    results["models"]["knn"] = eval_scores(knn_score, "knn")
    print("[native] knn:", results["models"]["knn"], flush=True)

    for seed in SEEDS:
        f = IsolationForest(random_state=seed).fit(xtr)  # paper: default params
        res = eval_scores(lambda x: -f.score_samples(x), "iforest")
        results["models"][f"iforest_seed{seed}"] = res
        print(f"[native] iforest seed{seed}:", res, flush=True)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "native_baselines.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("wrote native_baselines.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
