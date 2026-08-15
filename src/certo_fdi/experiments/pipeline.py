"""Data bundle, healthy-only training (R1), and pooled window-feature extraction."""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch

from certo_fdi.data.franka_generator import reference_chain
from certo_fdi.data.schema import FAULT_FAMILIES
from certo_fdi.data.windows import MODEL_CONTEXT_INDICES, EpisodeArrays, WindowSet, load_episode_arrays, load_index, select_episodes
from certo_fdi.dynamics.chain_model import ChainModel
from certo_fdi.dynamics.rnea_torch import TorchChain
from certo_fdi.experiments.common import sha256_file
from certo_fdi.geometry.frame_reparameterization import sample_link_frames
from certo_fdi.geometry.spatial_types import SpatialType
from certo_fdi.models.ligra_chain import build_model


@dataclass
class DataBundle:
    base_chain: ChainModel
    episodes: dict[str, EpisodeArrays]  # by episode id
    train_ids: list[str]
    val_ids: list[str]
    test_ids: list[str]
    calib_ids: list[str]
    window: int
    stride_train: int
    stride_eval: int
    ctx_dim: int
    n_links: int

    def subset(self, ids: list[str]) -> list[EpisodeArrays]:
        return [self.episodes[i] for i in ids]


def make_base_chain(cfg: dict) -> ChainModel:
    ch = reference_chain(cfg["paths"]["mjcf_path"])
    ch.damping = np.asarray(cfg["plant_mismatch"]["nominal_viscous_nms"], dtype=float)
    ch.coulomb = np.asarray(cfg["plant_mismatch"]["nominal_coulomb_nm"], dtype=float)
    ch.coulomb_eps = 0.05
    return ch


def load_bundle(cfg: dict, data_root: Path, *, max_episodes: int | None = None) -> DataBundle:
    base = make_base_chain(cfg)
    rows = load_index(data_root)
    if max_episodes:
        rows = rows[:max_episodes]
    episodes = {r["episode_id"]: load_episode_arrays(r, base) for r in rows}
    sim = cfg["simulation"]
    return DataBundle(
        base_chain=base,
        episodes=episodes,
        train_ids=[r["episode_id"] for r in select_episodes(rows, partition="train")],
        val_ids=[r["episode_id"] for r in select_episodes(rows, partition="val")],
        test_ids=[r["episode_id"] for r in select_episodes(rows, partition="test")],
        calib_ids=[r["episode_id"] for r in select_episodes(rows, partition="calib")],
        window=int(sim["window_samples"]),
        stride_train=int(sim.get("window_stride", 32)),
        stride_eval=int(sim.get("window_stride_eval", 16)),
        ctx_dim=len(MODEL_CONTEXT_INDICES),
        n_links=base.n_links,
    )


def training_subset(bundle: DataBundle, fraction: float, seed: int) -> list[str]:
    ids = list(bundle.train_ids)
    if fraction >= 1.0:
        return ids
    rng = np.random.default_rng(seed + 17)
    k = max(2, int(round(fraction * len(ids))))
    return sorted(rng.choice(ids, size=k, replace=False).tolist())


def reparameterize_batch(base_chain: ChainModel, batch: dict, rng: np.random.Generator, cfg_ft: dict, device: str, dtype=torch.float32) -> tuple[TorchChain, dict]:
    """Random legal frame reparameterization of a whole batch (chain + per-episode inertias)."""
    frames = sample_link_frames(base_chain, rng, rotation_angle_max_deg=float(cfg_ft["rotation_angle_max_deg"]), translation_fraction_of_link_length=float(cfg_ft["translation_fraction_of_link_length"]))
    new_chain, adjoints = base_chain.reparameterize(frames)
    tc = TorchChain.from_chain(new_chain, dtype=dtype, device=device)
    A = torch.as_tensor(adjoints, dtype=dtype, device=device)  # (n,6,6)
    A_inv = torch.linalg.inv(A)
    inertia = batch["inertia"]  # (B,n,6,6) canonical
    new_inertia = A_inv.transpose(-1, -2)[None] @ inertia @ A_inv[None]
    b2 = dict(batch)
    b2["inertia"] = new_inertia
    return tc, b2


def train_model(
    name: str,
    seed: int,
    train_ids: list[str],
    bundle: DataBundle,
    cfg: dict,
    ckpt_dir: Path,
    device: str = "cuda",
    *,
    epochs: int = 30,
    batch_size: int = 64,
    lr: float = 2e-3,
    patience: int = 6,
    log: list[str] | None = None,
) -> dict[str, Any]:
    torch.manual_seed(seed)
    np.random.seed(seed % (2**32 - 1))
    rng = np.random.default_rng(seed)
    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=device)
    model = build_model(name, tc, bundle.ctx_dim, cfg["model"]).to(device)
    train_ws = WindowSet(bundle.subset(train_ids), bundle.window, bundle.stride_train, device)
    val_ws = WindowSet(bundle.subset(bundle.val_ids), bundle.window, bundle.stride_train, device)
    t0 = time.time()
    n_params = int(sum(p.numel() for p in model.parameters() if p.requires_grad))
    ckpt_path = ckpt_dir / f"{name}_seed{seed}_frac{len(train_ids)}ep.pt"
    if n_params == 0:  # rnea_only
        torch.save({"state_dict": model.state_dict(), "name": name, "seed": seed, "train_ids": train_ids}, ckpt_path)
        return {"model": model, "name": model.name, "n_params": 0, "epochs_run": 0, "best_val_loss": float("nan"), "train_seconds": 0.0, "checkpoint": str(ckpt_path), "checkpoint_sha256": sha256_file(ckpt_path), "n_train_windows": len(train_ws), "history": []}
    fit_batches = [train_ws.batch(list(range(i, min(i + 256, len(train_ws))))) for i in range(0, min(len(train_ws), 1024), 256)]
    model.fit_normalizers(tc, fit_batches)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-6)
    steps_per_epoch = math.ceil(len(train_ws) / batch_size)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=max(1, epochs * steps_per_epoch), pct_start=0.15, final_div_factor=20.0)
    augmented = getattr(model, "name", "") == "chain_gnn_aug"
    tau_scale = model.tau_scale.to(device) if hasattr(model, "tau_scale") else torch.ones(bundle.n_links, device=device)
    best, best_state, bad, history = float("inf"), None, 0, []

    def loss_fn(out_delta, batch):
        target = batch["tau_meas"] - batch["tau_nom"] if getattr(model, "use_rnea", True) else batch["tau_meas"]
        return (((target - out_delta) / tau_scale) ** 2).mean()

    for epoch in range(epochs):
        model.train()
        tr_loss, nb = 0.0, 0
        for batch in train_ws.iterate(batch_size, True, rng):
            if augmented:
                tc_b, batch_b = reparameterize_batch(bundle.base_chain, batch, rng, cfg["frame_trials"], device)
                out = model(batch_b, tc_b)
            else:
                out = model(batch)
            loss = loss_fn(out.delta_tau, batch)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            try:
                sched.step()
            except ValueError:
                pass
            tr_loss += loss.item()
            nb += 1
        model.eval()
        va_loss, vb = 0.0, 0
        with torch.no_grad():
            for batch in val_ws.iterate(256, False):
                va_loss += float(loss_fn(model(batch).delta_tau, batch))
                vb += 1
        va_loss /= max(vb, 1)
        history.append({"epoch": epoch, "train_loss": tr_loss / max(nb, 1), "val_loss": va_loss, "elapsed_s": time.time() - t0})
        if log is not None:
            log.append(f"[{name} seed={seed} n_train_ep={len(train_ids)}] epoch {epoch} train {tr_loss / max(nb, 1):.4f} val {va_loss:.4f} ({time.time() - t0:.0f}s)")
        if va_loss < best - 1e-5:
            best, bad = va_loss, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    torch.save({"state_dict": model.state_dict(), "name": name, "seed": seed, "train_ids": train_ids, "history": history, "n_params": n_params}, ckpt_path)
    return {"model": model, "name": model.name, "n_params": n_params, "epochs_run": len(history), "best_val_loss": best, "train_seconds": time.time() - t0, "checkpoint": str(ckpt_path), "checkpoint_sha256": sha256_file(ckpt_path), "n_train_windows": len(train_ws), "history": history}


def load_checkpoint(name: str, ckpt_path: Path, bundle: DataBundle, cfg: dict, device: str) -> dict[str, Any]:
    """Rebuild a trained model from a checkpoint (for re-evaluation without retraining)."""
    tc = TorchChain.from_chain(bundle.base_chain, dtype=torch.float32, device=device)
    model = build_model(name, tc, bundle.ctx_dim, cfg["model"]).to(device)
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ck["state_dict"])
    model.eval()
    n_params = int(sum(p.numel() for p in model.parameters() if p.requires_grad))
    return {"model": model, "name": model.name, "n_params": n_params, "epochs_run": len(ck.get("history", [])), "best_val_loss": min((h["val_loss"] for h in ck.get("history", [])), default=float("nan")), "train_seconds": float("nan"), "checkpoint": str(ckpt_path), "checkpoint_sha256": sha256_file(ckpt_path), "n_train_windows": -1, "history": ck.get("history", []), "train_ids": ck.get("train_ids", [])}


# ---------------------------------------------------------------------- feature extraction
def _pool(x: torch.Tensor) -> torch.Tensor:
    """(B,T,...) -> (B, prod(...)*3): mean, std, absmax over T."""
    b = x.shape[0]
    flat = x.reshape(b, x.shape[1], -1)
    return torch.cat([flat.mean(1), flat.std(1), flat.abs().amax(1)], 1)


@dataclass
class WindowFeatures:
    """Pooled per-window features for one WindowSet under one model."""

    z_resid: np.ndarray  # (N, n*3)
    z_rep: np.ndarray  # (N, n*k*2) representation block (mean,std of link features)
    z_gmo: np.ndarray  # (N, n*3)
    ctx: np.ndarray  # (N, C)
    resid_ms: np.ndarray  # (N, n) mean squared post-correction residual per joint
    pre_ms: np.ndarray  # (N, n) mean squared pre-correction residual per joint
    delta_pool: np.ndarray  # (N, n*3) pooled delta_tau
    label: np.ndarray  # (N,) fault active at window end
    family: np.ndarray  # (N,) family index of the episode
    target: np.ndarray  # (N,) fault target at window end (-1 none)
    episode: np.ndarray  # (N,) episode index in ws
    start: np.ndarray  # (N,)
    rep_names: list[str] = field(default_factory=list)
    n_links: int = 7
    n_rep_feats: int = 0

    def block_slices(self, with_rep: bool) -> dict[str, slice]:
        """Per-link contiguous blocks after concatenation [z_resid_by_link | z_rep_by_link]."""
        n = self.n_links
        out = {}
        # z_resid layout from _pool: [mean(n) | std(n) | absmax(n)] -> regroup per link on build
        for i in range(n):
            out[f"link{i}"] = None
        return out


def _regroup_per_link(z: np.ndarray, n_links: int, k: int, stats: int) -> np.ndarray:
    """(N, stats*n*k) with layout [stat][link][feat] -> [link][stat][feat]."""
    N = z.shape[0]
    zz = z.reshape(N, stats, n_links, k).transpose(0, 2, 1, 3)
    return zz.reshape(N, n_links * stats * k)


@torch.no_grad()
def extract_features(model, ws: WindowSet, tc: TorchChain, device: str, batch_size: int = 384, *, inertia_override: torch.Tensor | None = None) -> WindowFeatures:
    """``inertia_override`` (n,6,6): use these link inertias for every window (single-episode
    frame-variant evaluation, where the chain and its inertias must transform together)."""
    model.eval()
    z_resid, z_rep, z_gmo, ctx, resid_ms, pre_ms, delta_pool, label, family, target, ep, start = ([] for _ in range(12))
    names: list[str] = []
    n = tc.n
    for batch in ws.iterate(batch_size, False, device=device):
        if inertia_override is not None:
            batch["inertia"] = inertia_override.to(batch["q"].dtype)[None].expand(batch["q"].shape[0], -1, -1, -1)
        out = model(batch, tc)
        resid = batch["tau_meas"] - batch["tau_nom"] - out.delta_tau  # (B,T,n)
        pre = batch["tau_meas"] - batch["tau_nom"]
        lf = out.link_features  # (B,T,n,k)
        names = out.link_feature_names
        # representation block: link features except the post-residual (already in resid block)
        keep = [i for i, nme in enumerate(names) if nme != "post_residual"]
        rep = lf[..., keep] if keep else lf[..., :0]
        b = resid.shape[0]
        z_resid.append(_regroup_per_link(_pool(resid).cpu().numpy(), n, 1, 3))
        rep_pool = torch.cat([rep.mean(1).reshape(b, -1), rep.std(1).reshape(b, -1)], 1) if rep.shape[-1] else torch.zeros(b, 0, device=device)
        z_rep.append(_regroup_per_link(rep_pool.cpu().numpy(), n, rep.shape[-1], 2) if rep.shape[-1] else rep_pool.cpu().numpy())
        z_gmo.append(_regroup_per_link(_pool(batch["r_gmo"]).cpu().numpy(), n, 1, 3))
        ctx.append(batch["ctx"].cpu().numpy())
        resid_ms.append((resid**2).mean(1).cpu().numpy())
        pre_ms.append((pre**2).mean(1).cpu().numpy())
        delta_pool.append(_regroup_per_link(_pool(out.delta_tau).cpu().numpy(), n, 1, 3))
        label.append(batch["active"][:, -1].cpu().numpy())
        family.append(batch["family"].cpu().numpy())
        target.append(batch["target"][:, -1].cpu().numpy())
        ep.append(batch["episode_index"].numpy())
        start.append(batch["start"].numpy())
    keep_names = [nme for nme in names if nme != "post_residual"]
    return WindowFeatures(
        z_resid=np.concatenate(z_resid), z_rep=np.concatenate(z_rep), z_gmo=np.concatenate(z_gmo), ctx=np.concatenate(ctx),
        resid_ms=np.concatenate(resid_ms), pre_ms=np.concatenate(pre_ms), delta_pool=np.concatenate(delta_pool),
        label=np.concatenate(label), family=np.concatenate(family), target=np.concatenate(target), episode=np.concatenate(ep), start=np.concatenate(start),
        rep_names=keep_names, n_links=n, n_rep_feats=len(keep_names),
    )


def density_input(f: WindowFeatures, variant: str) -> tuple[np.ndarray, dict[str, slice]]:
    """Assemble the density-head input ``z`` and per-link block slices for ``variant``."""
    n = f.n_links
    if variant == "residual_only":
        blocks = [f.z_resid.reshape(len(f.label), n, 3)]
    elif variant == "representation":
        parts = [f.z_resid.reshape(len(f.label), n, 3)]
        if f.n_rep_feats:
            parts.append(f.z_rep.reshape(len(f.label), n, 2 * f.n_rep_feats))
        blocks = parts
    elif variant == "gmo_only":
        blocks = [f.z_gmo.reshape(len(f.label), n, 3)]
    elif variant == "residual_plus_gmo":
        blocks = [f.z_resid.reshape(len(f.label), n, 3), f.z_gmo.reshape(len(f.label), n, 3)]
    else:
        raise ValueError(variant)
    per_link = np.concatenate(blocks, 2)  # (N, n, d)
    d = per_link.shape[2]
    z = per_link.reshape(len(f.label), n * d)
    slices = {f"link{i}": slice(i * d, (i + 1) * d) for i in range(n)}
    return z, slices
