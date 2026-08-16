"""Shared Stage 2A pathway pipeline: window grids, residuals, whitening and the pathway cache.

The pathway dictionaries are a function of the *episode signals and the nominal model only* --
they do not depend on the trained correction or on the seed -- so they are computed once per
episode and cached under ``<run>/p3_dictionaries/cache/``. Phases 4, 5 and 6 all read that
cache.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from certo_fdi.data.schema import EpisodeContext
from certo_fdi.pathways.dictionaries import EpisodePathways, build_episode_pathways
from certo_fdi.pathways.whitening import ConditionalWhitener, window_time_offsets

CACHE_VERSION = 4


# --------------------------------------------------------------------------- window grid
@dataclass(frozen=True)
class WindowGrid:
    """The fixed time grid shared by the residual and every dictionary column."""

    window: int
    n_points: int
    offsets: np.ndarray          # (M,) within-window sample offsets
    sample_stride: int           # spacing of the cached per-sample grid
    first_sample: int            # first cached sample index

    @staticmethod
    def build(window: int, n_points: int) -> "WindowGrid":
        off = window_time_offsets(window, n_points)
        stride = int(off[1] - off[0]) if len(off) > 1 else window
        return WindowGrid(window=window, n_points=n_points, offsets=off, sample_stride=stride, first_sample=int(off[0]))

    def sample_index(self, n_samples: int) -> np.ndarray:
        """The per-sample grid a cached episode is evaluated on."""
        return np.arange(self.first_sample, n_samples, self.sample_stride, dtype=int)

    def rows(self, starts: np.ndarray) -> np.ndarray:
        """(Nw, M) cache-row indices of every window's time points."""
        abs_idx = np.asarray(starts, dtype=int)[:, None] + self.offsets[None, :]
        rows = (abs_idx - self.first_sample) // self.sample_stride
        if np.any((abs_idx - self.first_sample) % self.sample_stride != 0):
            raise ValueError("window starts are not aligned with the cached sample grid")
        return rows


# --------------------------------------------------------------------------- pathway cache
_CACHE_ARRAYS = ("t_index", "d_gain", "d_viscous", "d_coulomb", "d_stribeck", "y_load", "j_link", "r_link",
                 "d_sensor_q", "d_sensor_qd", "d_sensor_q_cmd", "d_sensor_qd_cmd", "d_delay", "d_delay_buffer")


def cache_path(root: Path, episode_id: str) -> Path:
    return Path(root) / f"{episode_id}.npz"


def save_pathways(root: Path, ep: EpisodePathways) -> Path:
    p = cache_path(root, ep.episode_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, version=CACHE_VERSION, episode_id=ep.episode_id, n_links=ep.n_links,
                        meta=json.dumps(ep.meta), **{k: getattr(ep, k) for k in _CACHE_ARRAYS})
    return p


def load_pathways(root: Path, episode_id: str) -> EpisodePathways | None:
    p = cache_path(root, episode_id)
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as z:
        if int(z["version"]) != CACHE_VERSION:
            return None
        return EpisodePathways(episode_id=str(z["episode_id"]), n_links=int(z["n_links"]),
                               meta=json.loads(str(z["meta"])), **{k: z[k] for k in _CACHE_ARRAYS})


def episode_signals(ep_arrays, data_root: Path) -> dict[str, np.ndarray]:
    """Signals needed by the dictionaries: the bundle carries most, ``q_ref`` comes from HDF5."""
    import h5py

    sig = {k: np.asarray(v, dtype=float) for k, v in ep_arrays.signals.items()}
    if "q_ref" not in sig:
        path = Path(data_root) / "episodes" / f"{ep_arrays.episode_id}.h5"
        if not path.exists():
            path = next(Path(data_root).rglob(f"{ep_arrays.episode_id}.h5"))
        with h5py.File(path, "r") as f:
            sig["q_ref"] = f["signals"]["q_ref"][()].astype(float)
    return sig


def nominal_for_episode(base_chain, tool_id: int, cfg: dict):
    """The deployed nominal model and controller of one episode (declared context only)."""
    from certo_fdi.data.controllers import make_controller
    from certo_fdi.data.franka_generator import nominal_chain_with_tool
    from certo_fdi.dynamics.nominal_model import NominalModel

    pm = cfg["plant_mismatch"]
    chain = nominal_chain_with_tool(base_chain, int(tool_id), np.asarray(pm["nominal_viscous_nms"], dtype=float), np.asarray(pm["nominal_coulomb_nm"], dtype=float))
    return chain, NominalModel(chain)


def reference_trajectory(context: dict, seed: int, chain, cfg: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reconstruct the episode's exact reference trajectory from its stored seed.

    ``generate_episode`` draws the trajectory from a fresh ``default_rng(seed)`` before anything
    else consumes it, so this reproduces ``traj.q/qd/qdd`` bit-for-bit (the Phase 0 replay check
    verifies the whole episode).
    """
    from certo_fdi.data.trajectories import make_trajectory

    sim = cfg["simulation"]
    steps = int(round(float(sim["episode_duration_s"]) / float(sim["control_dt_s"])))
    t_grid = np.arange(steps) * float(sim["control_dt_s"])
    rng = np.random.default_rng(int(seed))
    traj = make_trajectory(str(context["trajectory_family"]), t_grid, int(context["region_id"]), rng, float(context["speed_scale"]),
                           chain.joint_lower, chain.joint_upper, chain.velocity_limit)
    return traj.q, traj.qd, traj.qdd


def build_and_cache(ep_arrays, base_chain, cfg: dict, grid: WindowGrid, data_root: Path, cache_root: Path, seed: int) -> EpisodePathways:
    cached = load_pathways(cache_root, ep_arrays.episode_id)
    if cached is not None:
        return cached
    sig = episode_signals(ep_arrays, data_root)
    chain, nominal = nominal_for_episode(base_chain, ep_arrays.tool_id, cfg)
    controller_chain, _ = nominal_for_episode(base_chain, ep_arrays.tool_id, cfg)
    from certo_fdi.data.controllers import make_controller

    controller = make_controller(str(ep_arrays.context["controller"]), controller_chain)
    traj = reference_trajectory(ep_arrays.context, seed, chain, cfg)
    pw = cfg["pathway"]
    ep = build_episode_pathways(
        chain, sig, grid.sample_index(sig["q_meas"].shape[0]), episode_id=ep_arrays.episode_id,
        trajectory=traj, controller=controller, nominal=nominal, torque_limit=chain.torque_limit,
        control_dt=float(cfg["simulation"]["control_dt_s"]),
        coulomb_eps=float(pw["coulomb_eps_rad_s"]), stribeck_velocity=float(pw["stribeck_velocity_rad_s"]),
        delta_q=float(pw["encoder_delta_rad"]), delta_qd=float(pw["encoder_delta_rad_s"]), delta_delay=float(pw["delay_delta_s"]),
    )
    save_pathways(cache_root, ep)
    return ep


def _worker(args):
    (eid, row, cfg, grid_kw, data_root, cache_root, seed) = args
    from certo_fdi.data.windows import load_episode_arrays
    from certo_fdi.experiments.pipeline import make_base_chain

    base = make_base_chain(cfg)
    ea = load_episode_arrays(row, base)
    grid = WindowGrid.build(**grid_kw)
    build_and_cache(ea, base, cfg, grid, Path(data_root), Path(cache_root), seed)
    return eid


def build_cache_parallel(rows: list[dict], seeds: dict[str, int], cfg: dict, grid: WindowGrid, data_root: Path, cache_root: Path, n_workers: int = 8, log=print) -> int:
    """Build the pathway cache for ``rows`` with a process pool (the dictionaries are seed independent)."""
    import multiprocessing as mp

    todo = [r for r in rows if not cache_path(cache_root, r["episode_id"]).exists()]
    if not todo:
        log(f"pathway cache complete ({len(rows)} episodes)")
        return 0
    grid_kw = {"window": grid.window, "n_points": grid.n_points}
    args = [(r["episode_id"], r, cfg, grid_kw, str(data_root), str(cache_root), seeds[r["episode_id"]]) for r in todo]
    log(f"building pathway cache for {len(todo)} episodes with {n_workers} workers...")
    done = 0
    with mp.get_context("spawn").Pool(n_workers) as pool:
        for eid in pool.imap_unordered(_worker, args, chunksize=2):
            done += 1
            if done % 25 == 0:
                log(f"  pathway cache {done}/{len(todo)}")
    log(f"pathway cache built ({done} episodes)")
    return done


# --------------------------------------------------------------------------- residuals + whitening
@dataclass
class EpisodeWindows:
    """Window bookkeeping and residuals of one episode under one correction model."""

    episode_id: str
    starts: np.ndarray            # (Nw,)
    rows: np.ndarray              # (Nw, M)
    resid: np.ndarray             # (Nw, M, n) corrected residual on the grid
    resid_pre: np.ndarray         # (Nw, M, n) RNEA-only residual on the grid
    resid_pooled: np.ndarray      # (Nw, 3n) per-link mean/std/absmax over the FULL window
    resid_pre_pooled: np.ndarray
    ctx: np.ndarray               # (Nw, C)
    label: np.ndarray             # (Nw,) fault active at the window end
    target: np.ndarray            # (Nw,) fault target at the window end
    family: str
    split: str
    kind: str
    severity: float
    onset_s: float
    t_end: np.ndarray             # (Nw,) window end time in seconds


def _pool_per_link(x: np.ndarray) -> np.ndarray:
    """(Nw, T, n) -> (Nw, 3n) with the frozen [link][mean,std,absmax] layout."""
    m, s, a = x.mean(1), x.std(1), np.abs(x).max(1)
    return np.stack([m, s, a], 2).reshape(x.shape[0], -1)


def episode_windows(model, ep_arrays, bundle, tc, grid: WindowGrid, device: str, batch_size: int = 256) -> EpisodeWindows:
    """Run one episode through the frozen correction model and slice the window residuals."""
    import torch

    from certo_fdi.data.windows import WindowSet

    ws = WindowSet([ep_arrays], bundle.window, bundle.stride_eval, device, min_start=bundle.eval_min_start)
    resid, pre, ctx, label, target, starts = [], [], [], [], [], []
    with torch.no_grad():
        for batch in ws.iterate(batch_size, False, device=device):
            out = model(batch, tc)
            r = (batch["tau_meas"] - batch["tau_nom"] - out.delta_tau).cpu().numpy().astype(np.float64)
            p = (batch["tau_meas"] - batch["tau_nom"]).cpu().numpy().astype(np.float64)
            resid.append(r)
            pre.append(p)
            ctx.append(batch["ctx"].cpu().numpy())
            label.append(batch["active"][:, -1].cpu().numpy())
            target.append(batch["target"][:, -1].cpu().numpy())
            starts.append(batch["start"].numpy())
    resid = np.concatenate(resid)
    pre = np.concatenate(pre)
    starts = np.concatenate(starts)
    ep = ep_arrays
    return EpisodeWindows(
        episode_id=ep.episode_id, starts=starts, rows=grid.rows(starts),
        resid=resid[:, grid.offsets, :], resid_pre=pre[:, grid.offsets, :],
        resid_pooled=_pool_per_link(resid), resid_pre_pooled=_pool_per_link(pre),
        ctx=np.concatenate(ctx), label=np.concatenate(label), target=np.concatenate(target),
        family=ep.family, split=ep.split, kind=ep.kind,
        severity=float(ep.fault.get("severity", 0.0)), onset_s=float(ep.fault.get("onset_s", 0.0)),
        t_end=(starts + bundle.window) * 0.002,
    )


def stack_window_residual(resid: np.ndarray) -> np.ndarray:
    """(Nw, M, n) -> (Nw, n*M) with the time-major layout used by every dictionary."""
    return resid.reshape(resid.shape[0], -1)


def fit_whiteners(healthy: list[EpisodeWindows], cfg: dict) -> tuple[ConditionalWhitener, ConditionalWhitener]:
    """Fit the window and instantaneous whiteners on healthy train+val windows only."""
    w = cfg["pathway"]["whitening"]
    E = np.concatenate([stack_window_residual(h.resid) for h in healthy])
    C = np.concatenate([h.ctx for h in healthy])
    win = ConditionalWhitener(ridge_mean=float(w["ridge_mean"]), shrinkage=float(w["shrinkage_relative"])).fit(E, C)
    E1 = np.concatenate([h.resid[:, -1, :] for h in healthy])
    inst = ConditionalWhitener(ridge_mean=float(w["ridge_mean"]), shrinkage=float(w["shrinkage_relative"])).fit(E1, C)
    return win, inst


def fit_whiteners_pre(healthy: list[EpisodeWindows], cfg: dict) -> tuple[ConditionalWhitener, ConditionalWhitener]:
    """The same whiteners for the ``geometry_only`` ablation (RNEA residual, no chain correction)."""
    w = cfg["pathway"]["whitening"]
    E = np.concatenate([stack_window_residual(h.resid_pre) for h in healthy])
    C = np.concatenate([h.ctx for h in healthy])
    win = ConditionalWhitener(ridge_mean=float(w["ridge_mean"]), shrinkage=float(w["shrinkage_relative"])).fit(E, C)
    E1 = np.concatenate([h.resid_pre[:, -1, :] for h in healthy])
    inst = ConditionalWhitener(ridge_mean=float(w["ridge_mean"]), shrinkage=float(w["shrinkage_relative"])).fit(E1, C)
    return win, inst


def truth_contact_point(ep_arrays) -> tuple[int, np.ndarray] | None:
    """The frozen episode's real contact link and point (ORACLE ONLY -- never a deployed input)."""
    f = ep_arrays.fault
    if f.get("family") != "F4_contact":
        return None
    extra = f.get("extra") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra.replace("'", '"'))
        except Exception:
            extra = {}
    r = extra.get("point_link", [0.0, 0.0, 0.05])
    return int(f.get("target", -1)), np.asarray(r, dtype=float)
