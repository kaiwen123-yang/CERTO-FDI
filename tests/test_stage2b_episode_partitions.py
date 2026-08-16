"""The episode is the independent statistical unit (kickoff §05.3, §07.1).

Window-level IID bootstrap is an integrity failure in this stage, so the only resampler
implemented resamples whole episodes and that is asserted here.
"""

from __future__ import annotations

import inspect

import numpy as np
import yaml
from pathlib import Path

from certo_fdi.experiments import stage2b_common as SC

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2b_contact_loadpath.yaml").read_text())


def test_config_declares_the_episode_as_the_unit():
    assert CFG["statistics"]["independent_unit"] == "episode"
    assert CFG["statistics"]["bootstrap"] == "episode_cluster"


def test_bootstrap_resamples_whole_episodes():
    """Rows from one episode are always drawn together, never individually."""
    rng = np.random.default_rng(0)
    # three episodes with wildly different but internally tight means. A window-level IID
    # bootstrap would report a very tight CI (n = 900 "independent" rows); an episode-cluster
    # bootstrap must report a wide one, because there are only three independent units.
    ep = np.repeat(["a", "b", "c"], 300)
    v = np.concatenate([rng.normal(0.0, 0.01, 300), rng.normal(1.0, 0.01, 300), rng.normal(2.0, 0.01, 300)])
    out = SC.episode_cluster_bootstrap(ep, v, lambda x: float(np.mean(x)), n_resamples=500, alpha=0.05)
    assert out["unit"] == "episode"
    assert out["n_episodes"] == 3
    assert out["n_rows"] == 900
    assert out["ci_high"] - out["ci_low"] > 0.8            # a window-level bootstrap would give ~0.002
    naive = 1.96 * float(np.std(v)) / np.sqrt(len(v)) * 2  # what an IID interval would have been
    assert (out["ci_high"] - out["ci_low"]) > 10 * naive


def test_bootstrap_ci_narrows_with_more_episodes():
    rng = np.random.default_rng(1)
    widths = []
    for n_ep in (4, 40):
        ep = np.repeat([f"e{i}" for i in range(n_ep)], 25)
        v = np.repeat(rng.normal(0.0, 1.0, n_ep), 25)
        out = SC.episode_cluster_bootstrap(ep, v, lambda x: float(np.mean(x)), n_resamples=500)
        widths.append(out["ci_high"] - out["ci_low"])
    assert widths[1] < widths[0]


def test_paired_bootstrap_is_also_episode_clustered():
    rng = np.random.default_rng(2)
    ep = np.repeat([f"e{i}" for i in range(12)], 30)
    a = rng.normal(1.0, 0.1, len(ep))
    b = rng.normal(0.0, 0.1, len(ep))
    out = SC.paired_episode_bootstrap(ep, a, b, n_resamples=500)
    assert out["unit"] == "episode" and out["n_episodes"] == 12
    assert out["ci_excludes_zero"] is True
    assert 0.8 < out["point"] < 1.2


def test_too_few_episodes_yields_no_ci_rather_than_a_fake_one():
    ep = np.array(["a"] * 10 + ["b"] * 10)
    out = SC.episode_cluster_bootstrap(ep, np.arange(20.0), lambda x: float(np.mean(x)), n_resamples=100)
    assert out["n_episodes"] == 2
    out1 = SC.episode_cluster_bootstrap(np.array(["a"] * 10), np.arange(10.0), lambda x: float(np.mean(x)))
    assert out1["ci_low"] != out1["ci_low"]        # NaN, not a fabricated interval


def test_no_window_level_bootstrap_exists_anywhere():
    """There must be no resampler that draws individual rows."""
    import certo_fdi.experiments.run_stage2b_loadpath as L
    import certo_fdi.experiments.run_stage2b_localization as LOC
    import certo_fdi.stage2b.selective_localization as SL

    for m in (SC, L, LOC, SL):
        src = inspect.getsource(m)
        for bad in ("window_bootstrap", "iid_bootstrap", "bootstrap_windows"):
            assert bad not in src, (m.__name__, bad)
    # the only bootstrap entry points are the episode-clustered ones
    names = [n for n in dir(SC) if "bootstrap" in n]
    assert set(names) == {"episode_cluster_bootstrap", "paired_episode_bootstrap"}


def test_seedwise_summary_reports_every_seed():
    out = SC.seedwise({260815: 0.1, 260816: -0.2, 260817: float("nan")})
    assert out["n_seeds"] == 2
    assert out["n_seeds_positive"] == 1 and out["n_seeds_negative"] == 1
    assert set(out["by_seed"]) == {"260815", "260816", "260817"}
    assert out["by_seed"]["260817"] is None
