"""Context calibration is healthy-only, context-limited and honest about its guarantees."""

from __future__ import annotations

import inspect

import numpy as np
import yaml
from pathlib import Path

from certo_fdi.stage2b import context_calibration as CAL

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2b_contact_loadpath.yaml").read_text())
CC = CFG["calibration"]
NAMES = list(CC["context_fields"])


def _healthy(n_ep=24, per_ep=200, seed=0):
    rng = np.random.default_rng(seed)
    ctx, score, ep = [], [], []
    for e in range(n_ep):
        ctrl = e % 2
        speed = 0.5 + 0.5 * (e % 3)
        mass = [0.0, 0.3, 0.6][e % 3]
        base = 10.0 + 8.0 * ctrl + 4.0 * speed          # a real context effect
        ctx.append(np.tile([ctrl, speed, mass, 0.08, 0.0, 1.0], (per_ep, 1)))
        score.append(rng.normal(base, 1.0, per_ep))
        ep.append(np.full(per_ep, f"e{e}"))
    return np.concatenate(score), np.concatenate(ctx), np.concatenate(ep)


def test_all_four_methods_fit_and_produce_thresholds():
    s, c, e = _healthy()
    for m in CAL.METHODS:
        cal = CAL.fit(m, s, c, e, 0.99, NAMES, CC)
        thr = cal.threshold(c)
        assert thr.shape == (len(c),)
        assert np.isfinite(thr).all(), m
        assert 0.9 < float((s <= thr).mean()) <= 1.0, (m, float((s <= thr).mean()))


def test_context_fields_are_the_six_declared_ones_only():
    assert NAMES == ["controller_id", "speed_scale", "tool_mass_kg", "tool_com_z_m",
                     "temperature_proxy", "noise_level"]
    for forbidden in ("region_id", "trajectory_family", "fault", "severity", "contact_link", "target"):
        assert forbidden not in NAMES


def test_context_aware_methods_actually_vary_with_context():
    s, c, e = _healthy()
    glob = CAL.fit("global_quantile", s, c, e, 0.99, NAMES, CC).threshold(c)
    assert float(glob.std()) == 0.0
    for m in ("grouped_mondrian_backoff", "conditional_quantile_regression"):
        thr = CAL.fit(m, s, c, e, 0.99, NAMES, CC).threshold(c)
        assert float(thr.std()) > 0.5, m          # tracks the injected context effect


def test_mondrian_backs_off_when_a_leaf_is_too_small():
    s, c, e = _healthy(n_ep=6)                    # far fewer episodes than leaves
    cal = CAL.fit("grouped_mondrian_backoff", s, c, e, 0.99, NAMES, CC)
    paths = cal.backoff_path(c)
    assert len(set(paths)) >= 1
    assert any("level" in p or p == "global" for p in paths)
    d = cal.to_dict()
    assert d["min_episodes_per_leaf"] == CC["mondrian"]["min_episodes_per_leaf"]


def test_conformal_blocks_are_episodes_not_windows():
    s, c, e = _healthy()
    cal = CAL.fit("episode_blocked_conformal", s, c, e, 0.95, NAMES, CC)
    d = cal.to_dict()
    diag = cal.diagnostics
    assert diag["block_unit"] == "episode"
    assert diag["n_calibration_blocks"] == 24            # one per episode, not 4800 windows
    assert "maximum window score" in diag["nonconformity"]


def test_no_method_claims_exact_conditional_cfar():
    """The phrase may appear only inside an explicit denial, never as a claim."""
    s, c, e = _healthy()
    for m in CAL.METHODS:
        d = CAL.fit(m, s, c, e, 0.99, NAMES, CC).to_dict()
        claim = d["coverage_claim"]
        assert "marginal" in claim.lower()
        low = claim.lower()
        for banned in ("exact conditional cfar", "exact cfar", "guaranteed conditional"):
            i = low.find(banned)
            while i != -1:                       # every occurrence must be negated
                assert "not" in low[max(0, i - 30):i], (m, banned, claim)
                i = low.find(banned, i + 1)
        # nothing but coverage_claim may mention it at all
        rest = str({k: v for k, v in d.items() if k != "coverage_claim"}).lower()
        for banned in ("exact conditional cfar", "exact cfar", "guaranteed conditional"):
            assert banned not in rest, (m, banned)
    assert "FORBIDDEN_LANGUAGE" in inspect.getsource(CAL)
    assert CC["conformal"]["forbidden_language"] == "exact_conditional_CFAR"


def test_grouped_coverage_reports_marginal_and_groups():
    s, c, e = _healthy()
    cal = CAL.fit("global_quantile", s, c, e, 0.99, NAMES, CC)
    rows = CAL.grouped_coverage(cal, s, c, e, NAMES, CC)
    assert rows[0]["group"] == "MARGINAL"
    assert len(rows) > 1
    for r in rows:
        assert 0.0 <= r["empirical_coverage"] <= 1.0
        np.testing.assert_allclose(r["empirical_coverage"] + r["alarm_rate"], 1.0, atol=1e-9)


def test_fit_never_receives_fault_information():
    """The calibrator signature has no place to put a label, and the runner passes none."""
    import certo_fdi.experiments.run_stage2b_calibration as R

    sig = inspect.signature(CAL.fit).parameters
    assert set(sig) == {"method", "scores", "ctx", "episode", "quantile", "context_names", "cfg"}
    src = inspect.getsource(R)
    # the tuner is documented and implemented as healthy-validation only
    assert "healthy-validation" in src or "healthy validation" in src
    assert "val_eps" in src and "TARGET_NOT_REACHED" in src
    assert CC["tune_on_healthy_only"] is True
