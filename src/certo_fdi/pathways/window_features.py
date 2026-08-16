"""Per-window geometry statistics and the feature blocks handed to the auditable fusers.

Contact model. The frozen simulator injects a **point force** on a link, and a constant point
force on a *rotating* link is **not** a constant wrench at the body origin: the moment arm
``R(t) r`` turns with the link, so ``n(t) = (R(t) r) x f`` varies over the window. The two
window dictionaries are therefore genuinely different hypotheses, neither contained in the
other, and the matched one is the 3-column point force:

* ``point force at candidate point p``  ``D = stack_t -J_{l,p}(q(t))^T``   (3 columns)
* ``constant body-origin wrench``       ``D = stack_t -J_l(q(t))^T``       (6 columns)

The **primary** per-link statistic is the best fit over that link's fixed geometric candidate
points; the body-wrench form is computed and reported alongside it as the point-agnostic
variant. Getting this backwards costs about two orders of magnitude in fit quality on a clean
synthetic contact, which ``tests/test_stage2a_mutations.py`` pins down.

One pass per episode also produces the instantaneous contact geometry, the end-effector /
joint-null split, the non-contact family geometries, the diagnosability map, and a
**shuffled-Jacobian control** (identical feature count, Jacobians taken at permuted time
indices of the same episode) so that any gain can be attributed to geometry rather than to
feature-vector capacity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from certo_fdi.pathways.dictionaries import EpisodePathways, contact_columns_batched, family_dictionaries_batched
from certo_fdi.pathways.geometry import batched_fisher_min_eigenvalue, batched_projection, principal_angles
from certo_fdi.pathways.whitening import ConditionalWhitener

FAMILY_KEYS = ("F1_actuator", "F2_viscous", "F2_coulomb", "F2_stribeck", "F3_payload", "F5_encoder_q", "F5_encoder_qd", "F6_delay")
CONTACT_STATS = ("explained_fraction", "projection_energy", "coefficient_norm_force", "projection_residual", "fisher_min_eigenvalue")
ANGLE_SUBSAMPLE = 24  # windows per episode at which the (expensive) principal angles are evaluated


@dataclass
class WindowGeometry:
    """Geometry statistics of every evaluation window of one episode."""

    episode_id: str
    n_windows: int
    n_links: int
    contact_window: dict[str, np.ndarray] = field(default_factory=dict)      # primary: best candidate point
    contact_wrench: dict[str, np.ndarray] = field(default_factory=dict)      # point-agnostic body wrench
    contact_instant: dict[str, np.ndarray] = field(default_factory=dict)
    contact_points: dict[str, np.ndarray] = field(default_factory=dict)      # (Nw, n_links, n_points)
    contact_oracle: dict[str, np.ndarray] = field(default_factory=dict)      # truth point (oracle only)
    contact_shuffled: dict[str, np.ndarray] = field(default_factory=dict)
    families: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)
    end_effector: dict[str, np.ndarray] = field(default_factory=dict)
    diagnosability: dict[str, np.ndarray] = field(default_factory=dict)
    point_names: list[str] = field(default_factory=list)


def _project(D: np.ndarray, z: np.ndarray) -> dict[str, np.ndarray]:
    p = batched_projection(D, z)
    theta = p["theta"]
    return {
        "explained_fraction": p["explained_fraction"],
        "projection_energy": p["explained_energy"],
        "projection_residual": p["projection_residual"],
        "coefficient_norm_force": np.linalg.norm(theta[:, -3:], axis=1),
        "fisher_min_eigenvalue": batched_fisher_min_eigenvalue(D),
    }


def _best_over_points(per_point: list[dict[str, np.ndarray]]) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Pick, per window, the candidate point with the smallest projection residual."""
    resid = np.stack([p["projection_residual"] for p in per_point], 1)  # (Nw, n_points)
    best = np.argmin(resid, axis=1)
    idx = np.arange(len(best))
    out = {k: np.stack([p[k] for p in per_point], 1)[idx, best] for k in CONTACT_STATS}
    return out, best


def _aggregates(explained: np.ndarray, residual: np.ndarray) -> dict[str, np.ndarray]:
    """Best link (by projection residual), best-vs-second margins and normalised entropy."""
    order = np.argsort(residual, axis=1)
    idx = np.arange(len(residual))
    best = explained[idx, order[:, 0]]
    second = explained[idx, order[:, 1]] if explained.shape[1] > 1 else np.zeros(len(explained))
    r0, r1 = residual[idx, order[:, 0]], residual[idx, order[:, 1]] if residual.shape[1] > 1 else residual[idx, order[:, 0]]
    w = np.clip(explained, 1e-12, None)
    w = w / w.sum(1, keepdims=True)
    ent = -(w * np.log(w)).sum(1) / np.log(max(explained.shape[1], 2))
    return {"best_link": order[:, 0].astype(int), "best_explained": best, "margin": best - second,
            "residual_margin": r1 - r0, "min_residual": r0, "entropy": ent, "rank_order": order}


def episode_geometry(
    ep: EpisodePathways,
    rows: np.ndarray,
    z_window: np.ndarray,
    z_instant: np.ndarray,
    whitener: ConditionalWhitener,
    whitener_instant: ConditionalWhitener,
    *,
    candidate_points: dict[int, list[tuple[str, np.ndarray]]],
    ee_link: int,
    ee_point: np.ndarray,
    truth_contact: tuple[int, np.ndarray] | None = None,
    shuffle_rows: np.ndarray | None = None,
    with_families: bool = True,
    with_angles: bool = True,
) -> WindowGeometry:
    """``rows`` is ``(Nw, M)``: the pathway-cache row index of every window time point."""
    Nw = rows.shape[0]
    n = ep.n_links
    W = whitener.whitener
    g = WindowGeometry(episode_id=ep.episode_id, n_windows=Nw, n_links=n,
                       point_names=[nm for nm, _ in candidate_points[0]])

    def wh(D: np.ndarray) -> np.ndarray:
        return np.einsum("de,nep->ndp", W, D)

    # ---- primary: per-link point-force dictionaries, best over the fixed candidate points
    n_pts = len(candidate_points[0])
    for stat in ("explained_fraction", "projection_energy", "projection_residual"):
        g.contact_points[stat] = np.zeros((Nw, n, n_pts))
    per_link, best_point, D_link_primary = [], np.zeros((Nw, n), dtype=int), []
    for l in range(n):
        pp = []
        Ds = []
        for pi, (_, r_link) in enumerate(candidate_points[l]):
            D = wh(contact_columns_batched(ep, rows, l, r_link))
            Ds.append(D)
            p = _project(D, z_window)
            pp.append(p)
            g.contact_points["explained_fraction"][:, l, pi] = p["explained_fraction"]
            g.contact_points["projection_energy"][:, l, pi] = p["projection_energy"]
            g.contact_points["projection_residual"][:, l, pi] = p["projection_residual"]
        blk, bp = _best_over_points(pp)
        per_link.append(blk)
        best_point[:, l] = bp
        D_link_primary.append(np.stack(Ds, 1)[np.arange(Nw), bp])  # (Nw, d, 3) the chosen point
    g.contact_window = {k: np.stack([b[k] for b in per_link], 1) for k in CONTACT_STATS}
    g.contact_window.update(_aggregates(g.contact_window["explained_fraction"], g.contact_window["projection_residual"]))
    g.contact_window["best_point"] = best_point

    # ---- point-agnostic body-wrench variant (a different hypothesis, reported alongside)
    D_wrench = [wh(contact_columns_batched(ep, rows, l, None)) for l in range(n)]
    blocks = [_project(D_wrench[l], z_window) for l in range(n)]
    g.contact_wrench = {k: np.stack([b[k] for b in blocks], 1) for k in CONTACT_STATS}
    g.contact_wrench.update(_aggregates(g.contact_wrench["explained_fraction"], g.contact_wrench["projection_residual"]))

    # ---- instantaneous (window's last sample only), against the instantaneous whitened residual
    last = rows[:, -1]
    Wi = whitener_instant.whitener
    inst = []
    for l in range(n):
        pp = []
        for _, r_link in candidate_points[l]:
            from certo_fdi.pathways.jacobians import skew

            r_world = (ep.r_link[last, l] @ np.asarray(r_link, dtype=float)[None, :, None])[..., 0]
            Jp = ep.j_link[last, l, 3:, :] - skew(r_world) @ ep.j_link[last, l, :3, :]
            D = np.einsum("de,nep->ndp", Wi, -np.swapaxes(Jp, 1, 2))
            pp.append(_project(D, z_instant))
        blk, _ = _best_over_points(pp)
        inst.append(blk)
    g.contact_instant = {k: np.stack([b[k] for b in inst], 1) for k in CONTACT_STATS}
    g.contact_instant.update(_aggregates(g.contact_instant["explained_fraction"], g.contact_instant["projection_residual"]))

    # ---- oracle: the truth contact point (upper bound only, never deployed)
    if truth_contact is not None and truth_contact[0] >= 0:
        l_true, r_true = truth_contact
        po = _project(wh(contact_columns_batched(ep, rows, int(l_true), r_true)), z_window)
        g.contact_oracle = {**po, "link": int(l_true)}

    # ---- capacity/permutation control: same construction, time-permuted Jacobians
    if shuffle_rows is not None:
        per_link_s = []
        for l in range(n):
            pp = [_project(wh(contact_columns_batched(ep, shuffle_rows, l, r_link)), z_window) for _, r_link in candidate_points[l]]
            blk, _ = _best_over_points(pp)
            per_link_s.append(blk)
        g.contact_shuffled = {k: np.stack([b[k] for b in per_link_s], 1) for k in CONTACT_STATS}
        g.contact_shuffled.update(_aggregates(g.contact_shuffled["explained_fraction"], g.contact_shuffled["projection_residual"]))

    # ---- non-contact families
    D_fam = {}
    if with_families:
        fam = family_dictionaries_batched(ep, rows)
        for key in FAMILY_KEYS:
            D = wh(fam[key])
            D_fam[key] = D
            p = batched_projection(D, z_window)
            g.families[key] = {
                "explained_fraction": p["explained_fraction"],
                "projection_energy": p["explained_energy"],
                "projection_residual": p["projection_residual"],
                "coefficient_norm": p["coefficient_norm"],
            }

    # ---- end-effector: point force at the declared EE point + the instantaneous null split
    D_ee = wh(contact_columns_batched(ep, rows, ee_link, ee_point))
    p_ee = batched_projection(D_ee, z_window)
    J_ee = ep.j_link[last, ee_link]                                     # (Nw, 6, n) instantaneous
    D_ee_inst = np.einsum("de,nep->ndp", Wi, -np.swapaxes(J_ee, 1, 2))  # (Nw, n, 6)
    ee_energy = np.zeros(Nw)
    for i in range(Nw):
        U, s, _ = np.linalg.svd(D_ee_inst[i], full_matrices=False)
        keep = s > s[0] * 1e-8 if s.size else np.zeros(0, dtype=bool)
        ee_energy[i] = float(((U[:, keep].T @ z_instant[i]) ** 2).sum())
    total_inst = (z_instant**2).sum(1)
    g.end_effector = {
        "explained_fraction": p_ee["explained_fraction"],
        "projection_energy": p_ee["explained_energy"],
        "coefficient_norm_force": np.linalg.norm(p_ee["theta"], axis=1),
        "end_effector_explainable_energy": ee_energy,
        "joint_null_energy": np.maximum(total_inst - ee_energy, 0.0),
        "joint_null_fraction": np.maximum(total_inst - ee_energy, 0.0) / np.maximum(total_inst, 1e-12),
        "ee_jacobian_rank": np.array([int((np.linalg.svd(J_ee[i], compute_uv=False) > 1e-8).sum()) for i in range(Nw)]),
        "ee_jacobian_sigma_min": np.array([float(np.linalg.svd(J_ee[i], compute_uv=False)[-1]) for i in range(Nw)]),
    }

    # ---- diagnosability map (principal angles are sub-sampled and held piecewise constant)
    fmin = g.contact_window["fisher_min_eigenvalue"]
    link_angle = np.full(Nw, np.pi / 2)
    fam_angle = np.full(Nw, np.pi / 2)
    if with_angles:
        sub = np.unique(np.linspace(0, Nw - 1, min(ANGLE_SUBSAMPLE, Nw)).astype(int))
        for si, w in enumerate(sub):
            ang = [principal_angles(D_link_primary[a][w], D_link_primary[b][w]).min() for a in range(n) for b in range(a + 1, n)]
            lo, hi = int(w), int(sub[si + 1]) if si + 1 < len(sub) else Nw
            link_angle[lo:hi] = float(np.min(ang)) if ang else np.pi / 2
            if si == 0:
                link_angle[:lo + 1] = link_angle[lo]
            if D_fam:
                keys = list(D_fam)
                fang = [principal_angles(D_fam[keys[i]][w], D_fam[keys[j]][w]).min() for i in range(len(keys)) for j in range(i + 1, len(keys))]
                fam_angle[lo:hi] = float(np.min(fang)) if fang else np.pi / 2
                if si == 0:
                    fam_angle[:lo + 1] = fam_angle[lo]
    g.diagnosability = {
        "contact_observability": fmin.min(1),
        "contact_observability_best_link": fmin.max(1),
        "fisher_min_eigenvalue": fmin[np.arange(Nw), g.contact_window["best_link"]],
        "link_min_angle": link_angle,
        "fault_family_min_angle": fam_angle,
        "predicted_ambiguity": 1.0 / (1.0 + np.clip(g.contact_window["residual_margin"], 0.0, None)),
        "entropy": g.contact_window["entropy"],
        "ee_jacobian_sigma_min": g.end_effector["ee_jacobian_sigma_min"],
    }
    return g


# --------------------------------------------------------------------------- feature blocks
def contact_feature_block(block: dict[str, np.ndarray]) -> np.ndarray:
    """(Nw, 3*n_links + 3) per-link contact statistics plus the three window aggregates."""
    parts = [np.log1p(np.clip(block["projection_energy"], 0.0, None)), block["explained_fraction"], np.log1p(np.clip(block["coefficient_norm_force"], 0.0, None))]
    agg = np.stack([block["best_explained"], block["margin"], block["entropy"]], 1)
    return np.concatenate([np.concatenate(parts, 1), agg], 1)


def family_feature_block(families: dict[str, dict[str, np.ndarray]], keys=FAMILY_KEYS) -> np.ndarray:
    """(Nw, 3*len(keys)) non-contact family statistics."""
    cols = []
    for k in keys:
        f = families[k]
        cols += [np.log1p(np.clip(f["projection_energy"], 0.0, None)), f["explained_fraction"], np.log1p(np.clip(f["coefficient_norm"], 0.0, None))]
    return np.stack(cols, 1)


def ee_feature_block(ee: dict[str, np.ndarray]) -> np.ndarray:
    """(Nw, 6) end-effector statistics and the instantaneous joint-null split."""
    return np.stack([
        np.log1p(np.clip(ee["projection_energy"], 0.0, None)), ee["explained_fraction"],
        np.log1p(np.clip(ee["coefficient_norm_force"], 0.0, None)),
        np.log1p(np.clip(ee["end_effector_explainable_energy"], 0.0, None)),
        np.log1p(np.clip(ee["joint_null_energy"], 0.0, None)), ee["joint_null_fraction"],
    ], 1)


def feature_block_names(n_links: int) -> dict[str, list[str]]:
    """Human-readable column names of every feature block (recorded in the schema sidecars)."""
    contact = ([f"log1p_proj_energy_link{i}" for i in range(n_links)]
               + [f"explained_fraction_link{i}" for i in range(n_links)]
               + [f"log1p_coef_force_link{i}" for i in range(n_links)]
               + ["best_explained", "margin", "entropy"])
    fam = []
    for k in FAMILY_KEYS:
        fam += [f"log1p_proj_energy_{k}", f"explained_fraction_{k}", f"log1p_coef_norm_{k}"]
    ee = ["log1p_proj_energy_ee", "explained_fraction_ee", "log1p_coef_force_ee",
          "log1p_ee_explainable_energy", "log1p_joint_null_energy", "joint_null_fraction"]
    return {"contact": contact, "families": fam, "end_effector": ee}
