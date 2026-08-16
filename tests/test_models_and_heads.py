"""Chain-model frame behaviour, density head, detection metrics and localization decoders.

Ported from Stage 1R-B with the LiGRA covariance (T1-T3) and covariant-basis cases removed
(Stage 2A contract §1.3). What survives is exactly what Stage 2A relies on: the chain GNN is
*not* frame covariant (which is why ``chain_gnn_aug`` trains with frame augmentation), the
conditional-Gaussian healthy head, the frozen event metrics and the localization decoders.
"""

from __future__ import annotations

import numpy as np
import pytest

from certo_fdi.anomaly.calibration import healthy_quantile_threshold
from certo_fdi.anomaly.event_detection import episode_level_auroc, event_metrics, persistence_filter, window_metrics
from certo_fdi.anomaly.gaussian_head import ConditionalGaussian
from certo_fdi.localization.link_scores import localization_metrics, rank_links
from tests.conftest import requires_sim, requires_torch

XML = "/mnt/g/CERTO-FDI/01_frozen_sources/extracted/mujoco_menagerie_franka_emika_panda_da76818/franka_emika_panda/panda_nohand.xml"


def _synthetic_batch(chain, rng, B=3, T=16, device="cpu", dtype=None):
    import torch

    n = chain.n_links
    lo, hi = chain.joint_lower, chain.joint_upper
    q = torch.as_tensor(rng.uniform(lo, hi, size=(B, T, n)), dtype=dtype)
    qd = torch.as_tensor(rng.normal(size=(B, T, n)), dtype=dtype)
    qdd = torch.as_tensor(rng.normal(size=(B, T, n)) * 2, dtype=dtype)
    tau_nom = torch.as_tensor(rng.normal(size=(B, T, n)) * 5, dtype=dtype)
    tau_meas = tau_nom + torch.as_tensor(rng.normal(size=(B, T, n)), dtype=dtype)
    ctx = torch.as_tensor(rng.normal(size=(B, 6)), dtype=dtype)
    return {"q": q, "qd": qd, "qdd": qdd, "tau_meas": tau_meas, "tau_nom": tau_nom, "ctx": ctx, "r_gmo": torch.zeros_like(q)}


@requires_sim
@requires_torch
@pytest.mark.parametrize("dtype_name,tol", [("float64", 1e-9), ("float32", 1e-4)])
def test_chain_gnn_is_not_frame_covariant(dtype_name, tol, rng):
    """The chain GNN reads raw components, so a legal link-frame change moves its correction.

    This is a *property* of the frozen baseline, not a detection-value axis: frame drift is
    never used as evidence for or against any Stage 2A decision.
    """
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.models.chain_gnn import build_model

    dtype = getattr(torch, dtype_name)
    chain = reference_chain(XML)
    chain.damping[:] = 0.5
    chain.coulomb[:] = 0.3
    payload = chain.with_payload(0.5, np.array([0.0, 0.0, 0.1]))
    for ch in (chain, payload):
        tc0 = TorchChain.from_chain(ch, dtype=dtype)
        batch = _synthetic_batch(ch, rng, dtype=dtype)
        batch["inertia"] = tc0.inertia[None].expand(3, -1, -1, -1)
        frames = sample_link_frames(ch, rng)
        new, _ = ch.reparameterize(frames)
        tc1 = TorchChain.from_chain(new, dtype=dtype)
        b1 = dict(batch)
        b1["inertia"] = tc1.inertia[None].expand(3, -1, -1, -1)
        g = build_model("chain_gnn", tc0, 6, {"scalar_hidden_dim": 32, "scalar_layers": 2}).to(dtype)
        g.fit_normalizers(tc0, [batch])
        with torch.no_grad():
            o0, o1 = g(batch, tc0), g(b1, tc1)
        assert np.abs(o1.delta_tau.numpy() - o0.delta_tau.numpy()).max() > 1e-3 * max(np.abs(o0.delta_tau.numpy()).max(), 1e-9)


@requires_sim
@requires_torch
def test_link_physical_descriptors_are_frame_invariant(rng):
    """The 8 link descriptors fed to every chain model are invariants of the physical link."""
    import torch

    from certo_fdi.data.franka_generator import reference_chain
    from certo_fdi.dynamics.rnea_torch import TorchChain
    from certo_fdi.geometry.frame_reparameterization import sample_link_frames
    from certo_fdi.models.features import link_physical_features

    ch = reference_chain(XML)
    tc0 = TorchChain.from_chain(ch, dtype=torch.float64)
    frames = sample_link_frames(ch, rng)
    new, _ = ch.reparameterize(frames)
    tc1 = TorchChain.from_chain(new, dtype=torch.float64)
    p0, p1 = link_physical_features(tc0).numpy(), link_physical_features(tc1).numpy()
    np.testing.assert_allclose(p0, p1, atol=1e-9)


def test_conditional_gaussian_scores_shift(rng):
    n, d, c = 2000, 12, 3
    C = rng.normal(size=(n, c))
    W = rng.normal(size=(c, d))
    z = C @ W + rng.normal(size=(n, d)) * 0.5
    head = ConditionalGaussian(conditional=True, covariance="lowrank", rank=3).fit(z, C, {"a": slice(0, 6), "b": slice(6, 12)})
    s_h = head.nll(z, C)
    z_f = z.copy()
    z_f[:, 6:] += 3.0
    s_f = head.nll(z_f, C)
    assert np.median(s_f) > np.median(s_h)
    blocks = head.block_nll(z_f, C)
    assert np.median(blocks["b"]) > np.median(blocks["a"])
    thr = healthy_quantile_threshold(s_h, 0.995)
    assert 0.003 < (s_h > thr).mean() < 0.01
    # clipping: far-OOD context does not explode the conditional mean
    s_ood = head.nll(z[:10], C[:10] + 100.0)
    assert np.all(np.isfinite(s_ood))
    unc = ConditionalGaussian(conditional=False, covariance="diag").fit(z, C)
    assert unc.nll(z, C).mean() > head.nll(z, C).mean()


def test_event_metrics_and_persistence():
    scores = np.array([0, 0, 5, 0, 0, 0, 5, 5, 5, 5], dtype=float)
    labels = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    t = np.arange(10) * 0.032 + 0.256
    ep = {"scores": scores, "labels": labels, "t_end": t, "is_fault_episode": True, "onset_s": t[5] - 0.01}
    em = event_metrics([ep], 1.0, 0.032)
    assert em["event_tpr"] == 1.0 and em["false_alarms_per_hour"] > 0
    em3 = event_metrics([ep], 1.0, 0.032, persistence=3)
    assert em3["false_alarms_per_hour"] == 0.0 and em3["event_tpr"] == 1.0 and em3["detection_delay_median_s"] > em["detection_delay_median_s"]
    assert persistence_filter(np.array([1, 1, 0, 1, 1, 1], dtype=bool), 3).tolist() == [False, False, False, False, False, True]
    wm = window_metrics(labels, scores, 1.0)
    assert 0.5 < wm["auroc"] <= 1.0
    # pre-onset spike (index 2) is a negative with a high score -> tie with the positive -> 0.75
    assert episode_level_auroc([ep, {"scores": np.zeros(5), "labels": np.zeros(5), "t_end": t[:5], "is_fault_episode": False, "onset_s": 0}]) == 0.75


def test_localization_metrics():
    pred = rank_links(np.array([[0.1, 0.9, 0.3], [0.8, 0.1, 0.2]]))
    m = localization_metrics(pred, np.array([1, 2]), 3, k=2)
    assert m["top1"] == 0.5 and m["top2"] == 1.0 and m["mean_chain_distance"] == 1.0


def test_localization_decoders():
    from certo_fdi.localization.link_scores import decode_localization

    # cumulative load-path pattern (contact on link 4 -> joints 0..4 loaded): distal/pattern -> 4, argmax -> 1
    e = np.array([6.0, 8.0, 5.0, 4.5, 3.0, 0.2, 0.1])
    assert decode_localization(e, "argmax")[0] == 1
    assert decode_localization(e, "distal")[0] == 4
    assert decode_localization(e, "pattern")[0] == 4
    # peaked pattern (joint-local fault on joint 3): all rules -> 3 except distal if a distal link is significant
    e2 = np.array([0.5, 0.8, 1.0, 9.0, 1.2, 0.4, 0.3])
    assert decode_localization(e2, "argmax")[0] == 3
    assert decode_localization(e2, "pattern")[0] == 3
    assert decode_localization(e2, "distal")[0] == 3
