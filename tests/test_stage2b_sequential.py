"""Sequential wrappers are causal, episode-local and parameterised only from a frozen grid."""

from __future__ import annotations

import numpy as np
import yaml
from pathlib import Path

from certo_fdi.stage2b import sequential_monitor as SEQ

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2b_contact_loadpath.yaml").read_text())


def test_k_of_n_is_causal():
    """The decision at window i may depend only on windows <= i."""
    rng = np.random.default_rng(0)
    a = rng.random(200) > 0.7
    for k, n in ((3, 3), (2, 3), (3, 4), (3, 5)):
        out = SEQ.k_of_n(a, k, n)
        for i in range(0, 200, 17):
            b = a.copy()
            b[i + 1:] = ~b[i + 1:]                    # change only the future
            assert SEQ.k_of_n(b, k, n)[i] == out[i], (k, n, i)


def test_k_of_n_matches_a_direct_definition():
    rng = np.random.default_rng(1)
    a = rng.random(120) > 0.6
    for k, n in ((3, 3), (2, 3), (3, 5)):
        out = SEQ.k_of_n(a, k, n)
        for i in range(len(a)):
            lo = max(0, i + 1 - n)
            assert out[i] == (a[lo:i + 1].sum() >= k), (k, n, i)


def test_persistence_reduces_isolated_alarms():
    a = np.zeros(100, bool)
    a[[5, 20, 40, 60]] = True                          # isolated single-window spikes
    assert SEQ.k_of_n(a, 3, 3).sum() == 0
    a[70:73] = True                                    # a genuine 3-window run
    assert SEQ.k_of_n(a, 3, 3).sum() >= 1


def test_hysteresis_latches_and_releases():
    sc = np.array([0., 3., 2.5, 1.2, 0.5, 0.4, 3.0, 0.2])
    out = SEQ.hysteresis(sc, 2.0, 1.0)
    assert out.tolist() == [False, True, True, True, False, False, True, False]


def test_hysteresis_accepts_per_window_thresholds():
    """A context-varying threshold must drive the latch, not a global level."""
    sc = np.array([1.0, 1.0, 1.0, 1.0])
    hi = np.array([2.0, 0.5, 2.0, 2.0])                # only window 1 has a low enough bar to raise
    lo = np.array([1.6, 0.4, 0.4, 0.4])
    assert SEQ.hysteresis(sc, hi, lo).tolist() == [False, True, True, True]
    # releasing early if the lower threshold rises above the score
    assert SEQ.hysteresis(sc, hi, np.array([1.6, 0.4, 1.6, 0.4])).tolist() == [False, True, False, False]
    # a scalar pair still works and matches the constant-array form
    np.testing.assert_array_equal(SEQ.hysteresis(sc, 0.5, 0.4), SEQ.hysteresis(sc, np.full(4, 0.5), np.full(4, 0.4)))


def test_cusum_accumulates_and_resets_after_an_alarm():
    excess = np.array([1.0] * 10)
    alarm, S = SEQ.one_sided_cusum(excess, drift=0.5, threshold=1.2)
    assert alarm.sum() >= 2                              # repeated alarms, not one latch
    assert S[np.where(alarm)[0][0]] == 0.0                # statistic resets on alarm
    quiet, Sq = SEQ.one_sided_cusum(np.full(10, -1.0), drift=0.5, threshold=1.2)
    assert quiet.sum() == 0 and (Sq == 0).all()           # never goes negative


def test_candidate_grid_matches_the_frozen_config():
    specs = SEQ.candidate_specs(CFG)
    fams = {SEQ.family_of(s) for s in specs}
    assert fams == {"none", "persistence_3_of_3", "persistence_grid", "hysteresis", "one_sided_cusum"}
    n_expected = (1 + 1 + len(CFG["sequential"]["persistence_grid"])
                  + len(CFG["sequential"]["hysteresis_high_low_ratio_grid"])
                  + len(CFG["sequential"]["cusum_drift_grid"]) * len(CFG["sequential"]["cusum_threshold_grid"]))
    assert len(specs) == n_expected
    for s in specs:                                      # every spec is fully determined
        assert s.to_dict()["method"] == s.method


def test_apply_is_deterministic_and_uses_the_threshold():
    spec = SEQ.SequentialSpec("persistence_2_of_3", {"k": 2, "n": 3})
    score = np.array([1.0, 5.0, 5.0, 1.0, 1.0])
    thr = np.full(5, 3.0)
    a = spec.apply(score, thr)
    # windows 2 and 3 each see 2 exceedances in their trailing 3-window window
    assert a.tolist() == [False, False, True, True, False]
    assert np.array_equal(a, spec.apply(score, thr))
    assert spec.apply(score, np.full(5, 99.0)).sum() == 0
