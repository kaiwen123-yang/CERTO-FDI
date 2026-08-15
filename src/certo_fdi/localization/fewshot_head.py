"""Few-shot fault-family attribution on frozen window embeddings (logistic regression)."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler


def expected_calibration_error(prob: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    conf = prob.max(1)
    pred = prob.argmax(1)
    acc = (pred == y).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(acc[m].mean() - conf[m].mean())
    return float(ece)


def fewshot_attribution(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, test_y: np.ndarray, test_group: np.ndarray, seed: int = 0) -> dict[str, float]:
    scaler = StandardScaler().fit(train_x)
    clf = LogisticRegression(max_iter=2000, C=0.5, random_state=seed)
    clf.fit(scaler.transform(train_x), train_y)
    prob = clf.predict_proba(scaler.transform(test_x))
    classes = clf.classes_
    pred = classes[prob.argmax(1)]
    # episode-level majority vote
    ep_pred, ep_true = [], []
    for g in np.unique(test_group):
        m = test_group == g
        votes = np.bincount(np.searchsorted(classes, pred[m]), minlength=len(classes))
        ep_pred.append(classes[votes.argmax()])
        ep_true.append(np.bincount(np.searchsorted(classes, test_y[m]), minlength=len(classes)).argmax())
    ep_true = classes[np.asarray(ep_true)]
    return {
        "window_macro_f1": float(f1_score(test_y, pred, average="macro")),
        "window_balanced_accuracy": float(balanced_accuracy_score(test_y, pred)),
        "episode_macro_f1": float(f1_score(ep_true, ep_pred, average="macro")),
        "episode_balanced_accuracy": float(balanced_accuracy_score(ep_true, ep_pred)),
        "ece": expected_calibration_error(prob, np.searchsorted(classes, test_y)),
        "n_train_windows": int(len(train_y)),
        "n_test_windows": int(len(test_y)),
        "n_test_episodes": int(len(ep_true)),
    }
