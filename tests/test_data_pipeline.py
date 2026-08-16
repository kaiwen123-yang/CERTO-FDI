"""Data protocol tests: plan/splits/leakage, windows, fault hooks, short generator run."""

from __future__ import annotations

import numpy as np
import pytest
import yaml
from pathlib import Path

from certo_fdi.data.fault_injection import FaultInjector, sample_fault_spec
from certo_fdi.data.schema import FAULT_FAMILIES, FaultSpec
from certo_fdi.data.splits import build_plan, leakage_report, window_index
from tests.conftest import requires_sim

CFG = Path(__file__).resolve().parents[1] / "configs" / "frozen_dataset_protocol_smoke.yaml"


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load(CFG.read_text())


@pytest.mark.parametrize("profile", ["smoke", "pilot"])
def test_plan_is_deterministic_and_leak_free(cfg, profile):
    a = build_plan(cfg, profile, 260815)
    b = build_plan(cfg, profile, 260815)
    assert [p.episode_id for p in a] == [p.episode_id for p in b]
    assert [p.seed for p in a] == [p.seed for p in b]
    assert [p.context.speed_scale for p in a] == [p.context.speed_scale for p in b]
    rep = leakage_report(a)
    assert rep["all_pass"], rep
    fams = {p.family for p in a if p.kind == "fault"}
    assert fams == set(FAULT_FAMILIES[1:])
    for s in ("S0", "S1", "S2", "S3", "S4"):
        assert any(p.split == s for p in a)


def test_windows_never_cross_episode():
    idx = window_index(6000, 128, 32)
    assert idx[0] == 0 and idx[-1] + 128 <= 6000
    assert window_index(100, 128, 32).size == 0


def test_fault_hooks_respect_onset_and_profiles(cfg):
    rng = np.random.default_rng(0)
    for fam in FAULT_FAMILIES[1:]:
        for _ in range(5):
            spec = sample_fault_spec(fam, cfg["faults"], rng, 7, 12.0)
            inj = FaultInjector(spec, 7, 0.002, rng)
            assert not inj.active(spec.onset_s - 0.01)
            assert inj.actuator_gain(spec.onset_s - 0.01).tolist() == [1.0] * 7
            v, c, s = inj.friction_scales(spec.onset_s - 0.01)
            assert np.allclose(v, 1) and np.allclose(c, 1) and np.allclose(s, 1)
            if fam == "F1_actuator":
                g = inj.actuator_gain(spec.onset_s + 10.0)
                assert abs(g[spec.target] - (1 - spec.severity)) < 1e-12
    ramp = FaultSpec("F1_actuator", "efficiency", 2, 0.2, 4.0, -1.0, "ramp", 2.0)
    inj = FaultInjector(ramp, 7, 0.002, rng)
    assert abs(inj.actuator_gain(5.0)[2] - 0.9) < 1e-12


@requires_sim
def test_generate_short_episode_and_labels(cfg):
    from certo_fdi.data.franka_generator import generate_episode, make_truth_params
    from certo_fdi.data.schema import EpisodeContext

    truth = make_truth_params(cfg, 7, np.random.default_rng(1))
    ctx = EpisodeContext("computed_torque", 0.9, 1, 0.3, 0.08, 0.1, 1.0, 1, "multisine", "medium", "B", "tool_A")
    spec = FaultSpec("F1_actuator", "efficiency", 1, 0.3, 1.0, -1.0, "abrupt")
    ep = generate_episode(cfg, cfg["paths"]["mjcf_path"], truth, ctx, spec, seed=5, episode_id="t", duration_s=2.0)
    assert ep.n_samples == 1000
    lab = ep.labels
    assert lab["fault_active"][:499].sum() == 0 and lab["fault_active"][501:].all()
    assert (lab["fault_family_id"][600] == 1) and lab["fault_target"][600] == 1
    S = ep.signals
    assert np.all(np.isfinite(S["tau_nominal"]))
    # actuator loss visible in applied vs commanded torque only after onset
    assert np.allclose(S["tau_applied"][:499], S["tau_cmd"][:499])
    assert np.allclose(S["tau_applied"][600:, 1], 0.7 * S["tau_cmd"][600:, 1])
    assert ep.meta["tracking_rms_rad"] < 0.1
