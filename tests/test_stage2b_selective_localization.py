"""Accept/defer must be selected on F4_CAL and must actually reduce error when it claims to."""

from __future__ import annotations

import inspect

import numpy as np
import yaml
from pathlib import Path

from certo_fdi.stage2b import selective_localization as SL

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2b_contact_loadpath.yaml").read_text())
COVS = [float(c) for c in CFG["localization"]["selective_coverages"]]


def _conf(n=40, seed=0, informative=True):
    """Episodes whose confidence feature is (or is not) related to correctness."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        correct = i % 3 != 0                                   # 2/3 correct overall
        c = rng.uniform(0.6, 1.0) if (correct and informative) else rng.uniform(0.0, 0.4)
        if not informative:
            c = rng.uniform(0.0, 1.0)
        tgt = 3
        out.append(SL.EpisodeConfidence(f"e{i}", predicted_link=tgt if correct else 5, target_link=tgt,
                                        features={f: c for f in SL.FEATURES}, n_windows=100, split="S0"))
    return out


def test_five_frozen_features_and_no_truth_inputs():
    assert set(SL.FEATURES) == set(CFG["localization"]["reject_features"])
    assert len(SL.FEATURES) == 5
    src = inspect.getsource(SL)
    # the feature computers never see a label: check their signatures
    for fn in (SL.subwindow_stability, SL.perturbation_stability):
        assert "target" not in inspect.signature(fn).parameters
        assert "label" not in inspect.signature(fn).parameters
    assert "no fault label" in src and "no test episode" in src


def test_the_unit_of_deferral_is_the_episode():
    conf = _conf(12)
    rows = SL.risk_coverage(conf, "best_second_margin", [0.5])
    assert rows[0]["n_total"] == 12                            # episodes, not windows
    assert rows[0]["n_accepted"] == 6
    assert all(c.n_windows == 100 for c in conf)               # windows exist but are not the unit


def test_coverage_decreases_monotonically_with_a_tighter_threshold():
    conf = _conf(40)
    thr = sorted({r["accept_threshold"] for r in SL.risk_coverage(conf, "best_second_margin", COVS)})
    covs = [SL.apply_threshold(conf, "best_second_margin", t).mean() for t in thr]
    assert all(a >= b for a, b in zip(covs, covs[1:]))


def test_an_informative_feature_beats_full_coverage_and_a_useless_one_does_not():
    good = SL.risk_coverage(_conf(60, informative=True), "best_second_margin", [0.7])[0]
    assert good["selective_top1"] > good["full_top1"] + 0.05
    bad = [SL.risk_coverage(_conf(60, seed=s, informative=False), "best_second_margin", [0.7])[0]
           for s in range(8)]
    assert np.mean([b["top1_gain_over_full"] for b in bad]) < 0.05


def test_reduces_error_is_a_strict_comparison_not_an_assertion():
    conf = _conf(30, informative=False, seed=3)
    all_accept = np.ones(len(conf), bool)
    m = SL.selective_metrics(conf, all_accept)
    assert m["coverage"] == 1.0
    assert m["reduces_error"] is False                          # full coverage can never "reduce" error
    np.testing.assert_allclose(m["selective_top1"], m["full_top1"])


def test_empty_acceptance_is_reported_not_silently_perfect():
    conf = _conf(10)
    m = SL.selective_metrics(conf, np.zeros(len(conf), bool))
    assert m["n_accepted"] == 0 and m["coverage"] == 0.0
    assert m["selective_top1"] != m["selective_top1"]           # NaN, never 1.0
    assert m["reduces_error"] is False


def test_selection_is_deterministic_and_respects_the_minimum_coverage():
    conf = _conf(50)
    a = SL.select_feature_and_threshold(conf, COVS, min_coverage=0.7)
    b = SL.select_feature_and_threshold(conf, COVS, min_coverage=0.7)
    assert a["selected"] == b["selected"]
    assert a["selected"]["calibration_coverage"] >= 0.7 - 1e-9
    assert a["partition"] == "F4_CAL only"
    impossible = SL.select_feature_and_threshold(conf, [0.5], min_coverage=0.95)
    assert impossible["selected"] is None                        # never silently relaxes the floor


def test_a_calibration_threshold_transfers_unchanged_to_the_test_partition():
    """The selected number is applied, not re-derived, on test episodes."""
    cal = _conf(50, seed=1)
    sel = SL.select_feature_and_threshold(cal, COVS, min_coverage=0.7)["selected"]
    test = _conf(24, seed=99)
    acc = SL.apply_threshold(test, sel["feature"], sel["threshold"])
    m = SL.selective_metrics(test, acc)
    assert 0.0 <= m["coverage"] <= 1.0
    # applying the same frozen threshold twice gives the identical mask
    np.testing.assert_array_equal(acc, SL.apply_threshold(test, sel["feature"], sel["threshold"]))


def test_runner_selects_on_f4_cal_and_evaluates_on_the_test_partition():
    import certo_fdi.experiments.run_stage2b_localization as R

    src = inspect.getsource(R)
    assert "F4_CAL" in src
    assert "select_feature_and_threshold" in src and "apply_threshold" in src
    assert CFG["localization"]["selection_partition"] == "F4_CAL"
    assert CFG["localization"]["rejection_selection_partition"] == "F4_CAL"
    # selection reads F4_CAL; the final F4 test set only ever has a frozen threshold applied to it
    i_sel = src.index("select_feature_and_threshold")
    i_apply = src.index("SL.apply_threshold")
    assert i_sel < i_apply, "the threshold must be selected before it is applied"
    assert "F4_TEST" in src
    assert "thresholds frozen on F4_CAL and applied unchanged to F4_TEST" in src
