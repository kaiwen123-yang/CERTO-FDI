"""Parity must refuse to call a noisy comparison a pass, in either direction."""

from __future__ import annotations

from certo_fdi_reset.baselines import parity

ABS, REL = 0.01, 0.02


def sweep(track, seed_to_finals, epoch0=0.311):
    """Build a sweep payload; each seed's trace starts at ``epoch0``."""
    return {
        "track": track,
        "epochs_per_run": 10,
        "runs": [
            {
                "seed": seed,
                "final_auroc_mean": final,
                "best_auroc_mean": final,
                "epochs": [{"epoch": 0, "auroc_mean": epoch0}, {"epoch": 1, "auroc_mean": final}],
            }
            for seed, final in seed_to_finals.items()
        ],
    }


def test_tight_agreement_passes():
    a = sweep("A", {1: 0.800, 2: 0.802, 3: 0.801})
    b = sweep("B", {1: 0.801, 2: 0.803, 3: 0.800})
    result = parity.compare(a, b, ABS, REL)
    assert result["verdict"] == "PARITY_PASS"
    assert result["epoch0_agreement"] is True


def test_large_seed_spread_is_never_a_pass():
    """A spread wider than the tolerance makes agreement luck, not evidence."""
    a = sweep("A", {1: 0.60, 2: 0.80, 3: 0.95})
    b = sweep("B", {1: 0.61, 2: 0.79, 3: 0.94})
    result = parity.compare(a, b, ABS, REL)
    assert result["underpowered"] is True
    assert result["verdict"] == "PIPELINE_PARITY_CONFIRMED_METRIC_INCONCLUSIVE"
    assert "not yet cleared" in parity.VERDICT_MEANING[result["verdict"]]


def test_nothing_agreeing_anywhere_is_inconclusive():
    """Neither the pipeline anchor nor the attainable metric agrees: no signal at all."""
    a = {
        "seeds": [1, 2, 3], "epochs_per_run": 10,
        "runs": [
            {"seed": 1, "final_auroc_mean": 0.60, "best_auroc_mean": 0.62,
             "epochs": [{"epoch": 0, "auroc_mean": 0.311}]},
            {"seed": 2, "final_auroc_mean": 0.80, "best_auroc_mean": 0.82,
             "epochs": [{"epoch": 0, "auroc_mean": 0.311}]},
            {"seed": 3, "final_auroc_mean": 0.95, "best_auroc_mean": 0.96,
             "epochs": [{"epoch": 0, "auroc_mean": 0.311}]},
        ],
    }
    b = {
        "seeds": [1, 2, 3], "epochs_per_run": 10,
        "runs": [
            {"seed": 1, "final_auroc_mean": 0.61, "best_auroc_mean": 0.40,
             "epochs": [{"epoch": 0, "auroc_mean": 0.700}]},
            {"seed": 2, "final_auroc_mean": 0.79, "best_auroc_mean": 0.55,
             "epochs": [{"epoch": 0, "auroc_mean": 0.700}]},
            {"seed": 3, "final_auroc_mean": 0.94, "best_auroc_mean": 0.70,
             "epochs": [{"epoch": 0, "auroc_mean": 0.700}]},
        ],
    }
    result = parity.compare(a, b, ABS, REL)
    assert result["epoch0_agreement"] is False
    assert result["best_auroc_agreement"] is False
    assert result["verdict"] == "INCONCLUSIVE_UNDERPOWERED"


def test_real_disagreement_with_tight_spread_fails():
    a = sweep("A", {1: 0.800, 2: 0.801, 3: 0.802})
    b = sweep("B", {1: 0.600, 2: 0.601, 3: 0.602}, epoch0=0.311)
    result = parity.compare(a, b, ABS, REL)
    assert result["verdict"] == "PARITY_FAIL"


def test_relative_tolerance_is_honoured_near_one():
    """abs alone is unreasonable for a metric near 1.0; either bound may satisfy."""
    row = parity._row("q", 1, 0.900, 0.885, ABS, REL)
    assert row["abs_delta"] > ABS
    assert row["rel_delta"] < REL
    assert row["within_tolerance"] == "true"


def test_no_shared_seeds_is_blocked():
    result = parity.compare(sweep("A", {1: 0.8}), sweep("B", {2: 0.8}), ABS, REL)
    assert result["verdict"] == "BLOCKED_NO_SHARED_SEEDS"
    assert result["rows"] == []


def test_every_verdict_has_a_stated_meaning():
    for verdict in ("PARITY_PASS", "PIPELINE_PARITY_CONFIRMED_METRIC_INCONCLUSIVE",
                    "INCONCLUSIVE_UNDERPOWERED", "PARITY_FAIL", "BLOCKED_NO_SHARED_SEEDS"):
        assert parity.VERDICT_MEANING[verdict].strip()


def test_best_metric_agreement_is_distinguished_from_no_agreement():
    """Reaching the same performance but stopping elsewhere is its own verdict."""
    a = {
        "seeds": [1, 2], "epochs_per_run": 10,
        "runs": [
            {"seed": 1, "final_auroc_mean": 0.807, "best_auroc_mean": 0.807,
             "epochs": [{"epoch": 0, "auroc_mean": 0.30}]},
            {"seed": 2, "final_auroc_mean": 0.772, "best_auroc_mean": 0.785,
             "epochs": [{"epoch": 0, "auroc_mean": 0.34}]},
        ],
    }
    b = {
        "seeds": [1, 2], "epochs_per_run": 10,
        "runs": [
            {"seed": 1, "final_auroc_mean": 0.773, "best_auroc_mean": 0.811,
             "epochs": [{"epoch": 0, "auroc_mean": 0.30}]},
            {"seed": 2, "final_auroc_mean": 0.681, "best_auroc_mean": 0.794,
             "epochs": [{"epoch": 0, "auroc_mean": 0.33}]},
        ],
    }
    result = parity.compare(a, b, ABS, REL)
    assert result["best_auroc_agreement"] is True
    assert result["epoch0_agreement"] is False
    assert result["verdict"] == "ATTAINABLE_METRIC_AGREES_STOPPING_POINT_INCONCLUSIVE"
    assert parity.VERDICT_MEANING[result["verdict"]].strip()


def test_config_as_run_absent_reads_as_unknown_not_as_match():
    a = sweep("A", {1: 0.80})
    b = sweep("B", {1: 0.80})
    assert parity._same_config_as_run(a, b) is None
