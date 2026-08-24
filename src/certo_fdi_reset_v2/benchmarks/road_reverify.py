"""Phase B-RoAD: independent local re-verification of the RoAD claims.

The two ChatGPT sandbox result packages are absent from this host (frozen in
PROTOCOL_FREEZE.md), so every load-bearing claim from contract section 1.4 is
re-derived here from the frozen RoAD checkout, with simple control models only
(contract 5.3 forbids designing another Chain/SO(3) candidate on RoAD):

  R1  channel-grouping order: sensor-grouped AE with true grouping vs multiple
      random channel-group permutations
  R2  healthy-split sensitivity: metrics across resampled 6/3 recording splits
  R3  SO(3)-derived quaternion-rate features vs same-dimension random-projection
      control features
  R4  channel-family ablation: electrical / acc / gyr / mag / quat families
  R5  event-level detection: event recall and false alarms per hour with
      thresholds set on healthy validation only (10 Hz per the RoAD paper,
      "After resampling the recordings to 10 Hz", road.txt line 366)

Facts this module must respect (verified V1 D0 + here):
  9 healthy training recordings (86 cols), 6 anomaly recordings with a binary
  `anomaly` label col 86: collision x2, control x1, weight x1, velocity x2.
  15 recordings total -- too few for episode-level cluster bootstrap; results
  are reported per recording and per split, never as a bootstrap CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROAD_REPO = Path("/mnt/g/CERTO-FDI/01_frozen_sources/public_baseline_repos/roaddataset")
RUN_DIR = Path(
    "/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/b_road"
)
SAMPLE_HZ = 10.0  # RoAD paper: recordings resampled to 10 Hz
WINDOW = 50       # 5 s
STRIDE = 10       # 1 s
SEEDS = (260824, 260825, 260826)

sys.path.insert(0, str(ROAD_REPO))


# ------------------------------------------------------------------ loading --

@dataclass
class Road:
    columns: list[str]
    training: list[np.ndarray]          # 9 x (T, 86)
    anomalies: dict[str, list[np.ndarray]]  # name -> [(T, 87)]

    @classmethod
    def load(cls) -> "Road":
        from RoADDataset.functions import Dataset

        ds = Dataset(normalize=False)
        return cls(
            columns=list(ds.columns)[:86],
            training=[a.astype(np.float64) for a in ds.sets["training"]],
            anomalies={
                k: [a.astype(np.float64) for a in ds.sets[k]]
                for k in ("collision", "control", "weight", "velocity")
            },
        )

    def channel_families(self) -> dict[str, list[int]]:
        fams: dict[str, list[int]] = {
            "electrical": [], "acc": [], "gyr": [], "mag": [], "quat": [], "other": []
        }
        for i, c in enumerate(self.columns):
            lc = c.lower()
            if "kuka robot" in lc:
                fams["electrical"].append(i)
            elif "_acc" in lc:
                fams["acc"].append(i)
            elif "_gyr" in lc:
                fams["gyr"].append(i)
            elif "_mag" in lc:
                fams["mag"].append(i)
            elif "_q" in lc and lc.split("_")[-1] in ("q1", "q2", "q3", "q4"):
                fams["quat"].append(i)
            else:
                fams["other"].append(i)
        return fams

    def sensor_groups(self) -> list[list[int]]:
        """Channels grouped by physical sensor unit (the 'true' grouping)."""
        groups: dict[str, list[int]] = {}
        for i, c in enumerate(self.columns):
            if c.lower().startswith("sensor_id"):
                key = c.split("_")[1]          # id4, id3, ...
            elif "kuka robot" in c.lower():
                key = "power"
            else:
                key = "misc"
            groups.setdefault(key, []).append(i)
        # order: base->tip by sensor id if numeric, power/misc last
        def rank(k: str):
            return (0, int(k[2:])) if k.startswith("id") else (1, 0)
        return [groups[k] for k in sorted(groups, key=rank)]


def windows(arr: np.ndarray, cols: list[int] | None = None,
            window: int = WINDOW, stride: int = STRIDE) -> tuple[np.ndarray, np.ndarray]:
    """Return (n_win, window, C) windows and per-window anomaly fraction."""
    feats = arr[:, :86] if cols is None else arr[:, cols]
    label = arr[:, 86] if arr.shape[1] > 86 else np.zeros(len(arr))
    if len(arr) < window:
        return np.empty((0, window, feats.shape[1])), np.empty((0,))
    idx = np.arange(0, len(arr) - window + 1, stride)
    w = np.stack([feats[i : i + window] for i in idx])
    y = np.array([label[i : i + window].max() for i in idx])
    return w, y


def fit_scaler(train_arrays: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    cat = np.concatenate([a[:, :86] for a in train_arrays], axis=0)
    mn, mx = cat.min(0), cat.max(0)
    span = np.where(mx - mn < 1e-12, 1.0, mx - mn)
    return mn, span


def apply_scaler(arr: np.ndarray, mn: np.ndarray, span: np.ndarray) -> np.ndarray:
    out = arr.copy()
    out[:, :86] = (out[:, :86] - mn) / span
    return out


# ------------------------------------------------------------------- models --

def score_pca_spe(train_w: np.ndarray, test_w: np.ndarray, var: float = 0.95) -> np.ndarray:
    """PCA squared prediction error on flattened windows."""
    from sklearn.decomposition import PCA

    Xtr = train_w.reshape(len(train_w), -1)
    Xte = test_w.reshape(len(test_w), -1)
    p = PCA(n_components=min(var if var < 1 else int(var), 0.95), svd_solver="full")
    p.fit(Xtr)
    rec = p.inverse_transform(p.transform(Xte))
    return ((Xte - rec) ** 2).mean(1)


def score_knn(train_w: np.ndarray, test_w: np.ndarray, k: int = 5) -> np.ndarray:
    from sklearn.neighbors import NearestNeighbors

    Xtr = train_w.reshape(len(train_w), -1)
    Xte = test_w.reshape(len(test_w), -1)
    nn = NearestNeighbors(n_neighbors=k).fit(Xtr)
    d, _ = nn.kneighbors(Xte)
    return d.mean(1)


def score_iforest(train_w: np.ndarray, test_w: np.ndarray, seed: int = 0) -> np.ndarray:
    from sklearn.ensemble import IsolationForest

    Xtr = train_w.reshape(len(train_w), -1)
    Xte = test_w.reshape(len(test_w), -1)
    f = IsolationForest(n_estimators=200, random_state=seed).fit(Xtr)
    return -f.score_samples(Xte)


class GruAE:
    """Small GRU autoencoder; optionally with per-group encoders whose group
    assignment is given (identical parameter count across permutations)."""

    def __init__(self, n_ch: int, groups: list[list[int]] | None = None,
                 hidden: int = 48, seed: int = 0, epochs: int = 12, lr: float = 1e-3):
        import torch
        import torch.nn as nn

        torch.manual_seed(seed)
        np.random.seed(seed)
        self.torch, self.nn = torch, nn
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.groups = groups
        self.epochs, self.lr = epochs, lr
        if groups is None:
            self.enc = nn.GRU(n_ch, hidden, batch_first=True)
            dec_in = hidden
        else:
            g_h = max(8, hidden // len(groups))
            self.encs = nn.ModuleList([nn.GRU(len(g), g_h, batch_first=True) for g in groups])
            self.enc = None
            dec_in = g_h * len(groups)
        self.dec = nn.GRU(dec_in, dec_in, batch_first=True)
        self.head = nn.Linear(dec_in, n_ch)
        mods = ([self.enc] if self.enc is not None else list(self.encs)) + [self.dec, self.head]
        for m in mods:
            m.to(self.device)
        self.params = [p for m in mods for p in m.parameters()]

    def _embed(self, x):
        if self.groups is None:
            h, _ = self.enc(x)
            return h
        outs = []
        for g, enc in zip(self.groups, self.encs):
            h, _ = enc(x[:, :, g])
            outs.append(h)
        return self.torch.cat(outs, dim=-1)

    def _recon(self, x):
        h = self._embed(x)
        d, _ = self.dec(h)
        return self.head(d)

    def fit(self, train_w: np.ndarray, batch: int = 64):
        t = self.torch
        x = t.tensor(train_w, dtype=t.float32, device=self.device)
        opt = t.optim.Adam(self.params, lr=self.lr)
        loss_fn = self.nn.MSELoss()
        n = len(x)
        for _ in range(self.epochs):
            perm = t.randperm(n)
            for i in range(0, n, batch):
                xb = x[perm[i : i + batch]]
                opt.zero_grad()
                loss = loss_fn(self._recon(xb), xb)
                loss.backward()
                opt.step()
        return self

    def score(self, test_w: np.ndarray, batch: int = 256) -> np.ndarray:
        t = self.torch
        out = []
        with t.no_grad():
            for i in range(0, len(test_w), batch):
                xb = t.tensor(test_w[i : i + batch], dtype=t.float32, device=self.device)
                err = ((self._recon(xb) - xb) ** 2).mean(dim=(1, 2))
                out.append(err.cpu().numpy())
        return np.concatenate(out) if out else np.empty((0,))


MODELS = ("pca_spe", "knn", "iforest", "gru_ae")

# Fit-once cache. Deterministic seeds mean a cached fit is numerically identical
# to a refit; this only removes the redundant per-recording refits that made the
# first runs pathologically slow. Keyed on the training-array object identity,
# which stays alive for the duration of each experiment's split scope.
_FIT_CACHE: dict = {}


def _fingerprint(a: np.ndarray) -> tuple:
    # content-aware cache key: id() may be reused after gc (observed: an 86-ch
    # model served a 93-ch array), so key on shape + cheap content probes.
    return (a.shape, a.dtype.str, float(a[0].sum()), float(a[-1].sum()), round(float(a.mean()), 9))


def _scorer(name: str, train_w, seed: int, groups):
    key = (name, seed, _fingerprint(train_w), repr(groups)[:200])
    if key in _FIT_CACHE:
        return _FIT_CACHE[key]
    if name == "pca_spe":
        from sklearn.decomposition import PCA
        Xtr = train_w.reshape(len(train_w), -1)
        pca = PCA(n_components=0.95, svd_solver="full").fit(Xtr)
        def fn(test_w):
            Xte = test_w.reshape(len(test_w), -1)
            rec = pca.inverse_transform(pca.transform(Xte))
            return ((Xte - rec) ** 2).mean(1)
    elif name == "knn":
        from sklearn.neighbors import NearestNeighbors
        nn = NearestNeighbors(n_neighbors=5).fit(train_w.reshape(len(train_w), -1))
        def fn(test_w):
            d, _ = nn.kneighbors(test_w.reshape(len(test_w), -1))
            return d.mean(1)
    elif name == "iforest":
        from sklearn.ensemble import IsolationForest
        f = IsolationForest(n_estimators=200, random_state=seed).fit(
            train_w.reshape(len(train_w), -1))
        def fn(test_w):
            return -f.score_samples(test_w.reshape(len(test_w), -1))
    elif name == "gru_ae":
        model = GruAE(train_w.shape[2], groups=groups, seed=seed).fit(train_w)
        fn = model.score
    else:
        raise ValueError(name)
    _FIT_CACHE[key] = fn
    if len(_FIT_CACHE) > 64:
        _FIT_CACHE.pop(next(iter(_FIT_CACHE)))
    return fn


def model_scores(name: str, train_w, test_w, seed: int, groups=None) -> np.ndarray:
    return _scorer(name, train_w, seed, groups)(test_w)


# -------------------------------------------------------------- experiments --

def split_recordings(n: int, n_val: int, seed: int) -> tuple[list[int], list[int]]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    return sorted(idx[n_val:].tolist()), sorted(idx[:n_val].tolist())


def auroc(y: np.ndarray, s: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    if len(np.unique(y > 0)) < 2:
        return float("nan")
    return float(roc_auc_score(y > 0, s))


def auprc(y: np.ndarray, s: np.ndarray) -> float:
    from sklearn.metrics import average_precision_score

    if len(np.unique(y > 0)) < 2:
        return float("nan")
    return float(average_precision_score(y > 0, s))


def evaluate_split(road: Road, train_ids: list[int], seed: int,
                   cols: list[int] | None = None, groups=None,
                   models=MODELS, extra_feats=None) -> dict:
    """Fit on chosen healthy recordings; score every anomaly recording."""
    train_arrays = [road.training[i] for i in train_ids]
    mn, span = fit_scaler(train_arrays)

    def prep(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        w, y = windows(apply_scaler(arr, mn, span), cols)
        if extra_feats is not None:
            w = extra_feats(w, arr, mn, span)
        return w, y

    train_w = np.concatenate([prep(a)[0] for a in train_arrays], axis=0)
    out: dict = {}
    for m in models:
        print(f"[eval] model={m}", flush=True)
        per_set = {}
        for set_name, recs in road.anomalies.items():
            ys, ss = [], []
            for rec in recs:
                w, y = prep(rec)
                if not len(w):
                    continue
                s = model_scores(m, train_w, w, seed, groups=groups)
                ys.append(y)
                ss.append(s)
            y_all, s_all = np.concatenate(ys), np.concatenate(ss)
            per_set[set_name] = {
                "auroc": auroc(y_all, s_all),
                "auprc": auprc(y_all, s_all),
                "n_windows": int(len(y_all)),
                "anomaly_frac": float((y_all > 0).mean()),
            }
        vals = [v["auroc"] for v in per_set.values() if not np.isnan(v["auroc"])]
        per_set["macro_auroc"] = float(np.mean(vals)) if vals else float("nan")
        out[m] = per_set
    return out


def r2_split_sensitivity(road: Road, n_splits: int = 5) -> dict:
    res = {}
    for k in range(n_splits):
        train_ids, val_ids = split_recordings(len(road.training), 3, SEEDS[0] + k)
        res[f"split_{k}"] = {
            "train_ids": train_ids,
            "val_ids": val_ids,
            "metrics": evaluate_split(road, train_ids, SEEDS[0] + k),
        }
    return res


def r1_grouping_permutations(road: Road, n_perms: int = 5) -> dict:
    groups = road.sensor_groups()
    flat = [i for g in groups for i in g]
    sizes = [len(g) for g in groups]
    train_ids, _ = split_recordings(len(road.training), 3, SEEDS[0])
    out = {"true_grouping": evaluate_split(road, train_ids, SEEDS[0],
                                           models=("gru_ae",), groups=groups)}
    rng = np.random.default_rng(SEEDS[1])
    for p in range(n_perms):
        perm = rng.permutation(flat)
        shuffled, at = [], 0
        for s in sizes:
            shuffled.append(list(perm[at : at + s]))
            at += s
        out[f"perm_{p}"] = evaluate_split(road, train_ids, SEEDS[0],
                                          models=("gru_ae",), groups=shuffled)
    return out


def _quat_rate_features(w: np.ndarray, quat_idx: dict[str, list[int]]) -> np.ndarray:
    """Per-sensor geodesic rotation rate |2*arccos(|<q_t,q_{t+1}>|)| appended per step."""
    feats = []
    for _, idx in sorted(quat_idx.items()):
        q = w[:, :, idx]
        q = q / (np.linalg.norm(q, axis=-1, keepdims=True) + 1e-9)
        dot = np.abs((q[:, 1:] * q[:, :-1]).sum(-1)).clip(0, 1)
        ang = 2 * np.arccos(dot)
        ang = np.concatenate([ang[:, :1], ang], axis=1)
        feats.append(ang[..., None])
    return np.concatenate(feats, axis=-1)


def r3_so3_features(road: Road) -> dict:
    quat_by_sensor: dict[str, list[int]] = {}
    for i, c in enumerate(road.columns):
        if c.lower().startswith("sensor_id") and c.split("_")[-1] in ("q1", "q2", "q3", "q4"):
            quat_by_sensor.setdefault(c.split("_")[1], []).append(i)
    n_extra = len(quat_by_sensor)
    rng = np.random.default_rng(SEEDS[2])
    proj = rng.standard_normal((86, n_extra)) / np.sqrt(86)

    def with_quat(w, arr, mn, span):
        return np.concatenate([w, _quat_rate_features(w, quat_by_sensor)], axis=-1)

    def with_random(w, arr, mn, span):
        return np.concatenate([w, w @ proj], axis=-1)

    train_ids, _ = split_recordings(len(road.training), 3, SEEDS[0])
    return {
        "baseline_raw": evaluate_split(road, train_ids, SEEDS[0], models=("gru_ae", "pca_spe")),
        "plus_quat_rate": evaluate_split(road, train_ids, SEEDS[0],
                                         models=("gru_ae", "pca_spe"), extra_feats=with_quat),
        "plus_random_proj": evaluate_split(road, train_ids, SEEDS[0],
                                           models=("gru_ae", "pca_spe"), extra_feats=with_random),
        "n_extra_features": n_extra,
    }


def r4_channel_families(road: Road) -> dict:
    fams = road.channel_families()
    train_ids, _ = split_recordings(len(road.training), 3, SEEDS[0])
    out = {}
    for fam, cols in fams.items():
        if not cols:
            continue
        out[fam] = {
            "n_channels": len(cols),
            "metrics": evaluate_split(road, train_ids, SEEDS[0], cols=cols,
                                      models=("pca_spe", "gru_ae")),
        }
    return out


def r5_event_level(road: Road) -> dict:
    """Thresholds from healthy validation only; event recall + FA/hour."""
    train_ids, val_ids = split_recordings(len(road.training), 3, SEEDS[0])
    train_arrays = [road.training[i] for i in train_ids]
    val_arrays = [road.training[i] for i in val_ids]
    mn, span = fit_scaler(train_arrays)

    def prep(arr):
        return windows(apply_scaler(arr, mn, span))

    train_w = np.concatenate([prep(a)[0] for a in train_arrays], axis=0)
    out: dict = {}
    for m in MODELS:
        val_scores = np.concatenate(
            [model_scores(m, train_w, prep(a)[0], SEEDS[0]) for a in val_arrays]
        )
        entry: dict = {}
        for q in (0.99, 0.999, 1.0):
            thr = float(np.quantile(val_scores, q)) if q < 1.0 else float(val_scores.max())
            events_total = events_hit = 0
            fp_windows = 0
            healthy_hours = 0.0
            for recs in road.anomalies.values():
                for rec in recs:
                    w, y = prep(rec)
                    s = model_scores(m, train_w, w, SEEDS[0])
                    alarm = s > thr
                    lab = rec[:, 86]
                    edges = np.flatnonzero(np.diff(np.concatenate([[0], lab > 0, [0]])))
                    starts, ends = edges[::2], edges[1::2]
                    idx = np.arange(0, len(rec) - WINDOW + 1, STRIDE)
                    for st, en in zip(starts, ends):
                        events_total += 1
                        touching = (idx + WINDOW > st) & (idx < en)
                        if alarm[touching].any():
                            events_hit += 1
                    fp_windows += int((alarm & (y == 0)).sum())
                    healthy_hours += float((y == 0).sum()) * STRIDE / SAMPLE_HZ / 3600.0
            # false alarms on held-out healthy recordings
            for a in val_arrays:
                w, _ = prep(a)
                s = model_scores(m, train_w, w, SEEDS[0])
                fp_windows += int((s > thr).sum())
                healthy_hours += len(w) * STRIDE / SAMPLE_HZ / 3600.0
            entry[f"q{q}"] = {
                "threshold": thr,
                "event_recall": events_hit / events_total if events_total else float("nan"),
                "events_total": events_total,
                "false_alarm_windows": fp_windows,
                "healthy_hours_scored": round(healthy_hours, 3),
                "false_alarms_per_hour": (fp_windows / healthy_hours) if healthy_hours else float("nan"),
            }
        out[m] = entry
    return out


EXPERIMENTS = {
    "r1": r1_grouping_permutations,
    "r2": r2_split_sensitivity,
    "r3": r3_so3_features,
    "r4": r4_channel_families,
    "r5": r5_event_level,
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exp", required=True, choices=sorted(EXPERIMENTS) + ["all"])
    args = parser.parse_args(argv)
    road = Road.load()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    todo = sorted(EXPERIMENTS) if args.exp == "all" else [args.exp]
    for name in todo:
        print(f"[road-reverify] running {name}", flush=True)
        result = EXPERIMENTS[name](road)
        path = RUN_DIR / f"{name}_result.json"
        path.write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
        print(f"[road-reverify] wrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
