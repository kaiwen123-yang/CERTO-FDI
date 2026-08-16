"""Feature assembly and the small, auditable fusers used by the Stage 2A ablations.

**Primary detection is healthy-only.** Every ablation uses the *same* conditional-Gaussian
healthy density head as the frozen Stage 1R-B baseline, fitted on healthy validation windows
with the same leave-one-episode-out candidate selection and the same 0.995 healthy-validation
threshold. Only the feature vector changes between ablations, so a difference in detection is
a difference in representation -- not in head capacity, training data or calibration.

Two controls make that attribution testable:

* ``chain_plus_shuffled_jacobian_control`` has the *identical* feature dimension to the
  primary geometry head but its Jacobians come from permuted time indices of the same
  episode. If it reproduces the gain, the gain was capacity, not geometry.
* every fault-label-trained fuser lives in :func:`supervised_attribution`, is fitted on the
  disjoint ``calib`` partition and is reported as a clearly separated *secondary* experiment.
"""

from __future__ import annotations

import numpy as np

from certo_fdi.pathways.window_features import (
    FAMILY_KEYS,
    contact_feature_block,
    ee_feature_block,
    family_feature_block,
    feature_block_names,
)

# ablation -> which blocks are concatenated onto the residual block
ABLATION_BLOCKS: dict[str, tuple[str, ...]] = {
    "rnea_threshold": ("residual_pre",),
    "rnea_gru": ("residual",),
    "chain_gnn_aug_residual_only": ("residual",),
    "geometry_only": ("residual_pre", "contact_window_pre", "families_pre"),
    "chain_plus_ee_jacobian": ("residual", "end_effector"),
    "chain_plus_all_link_instantaneous_jacobian": ("residual", "contact_instant"),
    "chain_plus_all_link_window_jacobian": ("residual", "contact_window"),
    "chain_plus_full_pathway_dictionary": ("residual", "contact_window", "families", "end_effector"),
    "chain_plus_shuffled_jacobian_control": ("residual", "contact_shuffled"),
    "chain_plus_all_link_window_jacobian_oracle_point": ("residual", "contact_oracle"),
}
GEOMETRY_ABLATIONS = tuple(k for k, v in ABLATION_BLOCKS.items() if any(b not in ("residual", "residual_pre") for b in v))


def assemble(blocks: dict[str, np.ndarray], names: tuple[str, ...]) -> tuple[np.ndarray, dict[str, slice]]:
    """Concatenate the requested feature blocks and return the per-block column slices."""
    parts, slices, start = [], {}, 0
    for nm in names:
        if nm not in blocks:
            raise KeyError(f"missing feature block '{nm}' (have {sorted(blocks)})")
        b = np.atleast_2d(np.asarray(blocks[nm], dtype=float))
        parts.append(b)
        slices[nm] = slice(start, start + b.shape[1])
        start += b.shape[1]
    return np.concatenate(parts, 1), slices


def per_link_slices(n_links: int, residual_width: int = 3) -> dict[str, slice]:
    """Per-link block slices of the residual-only feature vector (localization fallback)."""
    return {f"link{i}": slice(i * residual_width, (i + 1) * residual_width) for i in range(n_links)}


def geometry_blocks_from(geom, *, oracle_link: int | None = None) -> dict[str, np.ndarray]:
    """Turn a :class:`WindowGeometry` into the fixed feature blocks."""
    out: dict[str, np.ndarray] = {
        "contact_window": contact_feature_block(geom.contact_window),
        "contact_instant": contact_feature_block(geom.contact_instant),
        "end_effector": ee_feature_block(geom.end_effector),
    }
    if geom.families:
        out["families"] = family_feature_block(geom.families)
    if geom.contact_shuffled:
        out["contact_shuffled"] = contact_feature_block(geom.contact_shuffled)
    if geom.contact_oracle:
        o = geom.contact_oracle
        out["contact_oracle"] = np.stack([
            np.log1p(np.clip(o["projection_energy"], 0.0, None)), o["explained_fraction"],
            np.log1p(np.clip(o["coefficient_norm_force"], 0.0, None)), o["projection_residual"],
        ], 1)
    return out


def block_dimensions(n_links: int) -> dict[str, int]:
    names = feature_block_names(n_links)
    return {"contact_window": len(names["contact"]), "contact_instant": len(names["contact"]),
            "contact_shuffled": len(names["contact"]), "families": len(names["families"]),
            "end_effector": len(names["end_effector"]), "contact_oracle": 4}


# --------------------------------------------------------------------------- rule fuser
def rule_score(blocks: dict[str, np.ndarray], healthy_mean: np.ndarray, healthy_std: np.ndarray) -> np.ndarray:
    """Standardised-score rule fuser: max over blocks of the healthy-standardised feature.

    Reported alongside the density head as the simplest possible auditable fuser; it uses only
    healthy statistics.
    """
    z, _ = assemble(blocks, tuple(blocks))
    return np.max((z - healthy_mean) / np.where(healthy_std < 1e-12, 1.0, healthy_std), axis=1)


# --------------------------------------------------------------------------- secondary supervised
def supervised_attribution(z_train: np.ndarray, y_train: np.ndarray, z_test: np.ndarray, y_test: np.ndarray, *, seed: int = 0, kind: str = "logistic", max_params: int = 10000) -> dict:
    """SECONDARY experiment: a fault-label-trained coarse-class fuser.

    Trained on the disjoint ``calib`` partition and evaluated on the fault test partition; its
    numbers never enter the primary detection conclusion. ``kind`` is ``logistic`` (default) or
    ``mlp`` (a two-layer network capped at ``max_params`` parameters).
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score, confusion_matrix
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler

    sc = StandardScaler().fit(z_train)
    xt, xe = sc.transform(z_train), sc.transform(z_test)
    classes = sorted(set(y_train.tolist()))
    if kind == "logistic":
        clf = LogisticRegression(max_iter=2000, multi_class="multinomial", C=1.0, random_state=seed)
        n_params = (xt.shape[1] + 1) * len(classes)
    else:
        hidden = max(4, min(32, max_params // max(xt.shape[1] + len(classes) + 2, 1)))
        clf = MLPClassifier(hidden_layer_sizes=(hidden,), max_iter=800, random_state=seed)
        n_params = (xt.shape[1] + 1) * hidden + (hidden + 1) * len(classes)
    clf.fit(xt, y_train)
    pred = clf.predict(xe)
    return {
        "kind": kind, "n_features": int(xt.shape[1]), "n_classes": len(classes), "n_parameters": int(n_params),
        "n_train": int(len(y_train)), "n_test": int(len(y_test)),
        "accuracy": float((pred == y_test).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, pred)),
        "classes": classes,
        "confusion": confusion_matrix(y_test, pred, labels=classes).tolist(),
        "protocol": "fitted on the disjoint calib partition; SECONDARY, never part of the primary healthy-only detection decision",
    }


def zero_shot_coarse_class(family_stats: dict[str, dict[str, np.ndarray]], contact_block: dict[str, np.ndarray],
                           healthy_reference: dict[str, tuple[float, float]], coarse_map: dict[str, list[str]]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Zero-shot coarse attribution: argmax over classes of the healthy-standardised evidence.

    Uses no fault labels: each family's explained energy is standardised by its **healthy
    validation** mean and standard deviation, and each coarse class takes the maximum over the
    families it contains.
    """
    per_family: dict[str, np.ndarray] = {}
    for key, stats in family_stats.items():
        mu, sd = healthy_reference.get(key, (0.0, 1.0))
        per_family[key] = (stats["explained_fraction"] - mu) / (sd if sd > 1e-12 else 1.0)
    mu_c, sd_c = healthy_reference.get("F4_contact", (0.0, 1.0))
    per_family["F4_contact"] = (contact_block["best_explained"] - mu_c) / (sd_c if sd_c > 1e-12 else 1.0)
    family_to_coarse = {f: c for c, fams in coarse_map.items() for f in fams}
    classes = sorted(coarse_map)
    scores = np.full((len(next(iter(per_family.values()))), len(classes)), -np.inf)
    for key, val in per_family.items():
        fam = "F2_friction" if key.startswith("F2_") else ("F5_encoder" if key.startswith("F5_") else ("F6_command" if key.startswith("F6_") else key))
        cls = family_to_coarse.get(fam)
        if cls is None:
            continue
        j = classes.index(cls)
        scores[:, j] = np.maximum(scores[:, j], val)
    return np.array(classes)[np.argmax(scores, axis=1)], scores, classes
