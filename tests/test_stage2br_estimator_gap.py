"""The two sides of the Stage 2B contact reproduction gate are different estimators.

This is the load-bearing finding of Stage 2B-R and it is established from the frozen code, so it
is tested rather than asserted. Both functions under test are the repository's own frozen ones:

* ``pathways.geometry.batched_projection``  -- what Stage 2A's ``contact_projection_residual``
  localizer used: a ridge normal-equations solve, no rank truncation.
* ``stage2b.rank_aware_scores.project``     -- what Stage 2B's ``time_aligned_jacobian`` control
  used: an exact orthogonal projection truncated at ``s <= s_0 * 1e-8``.

The gate compared a number produced by the first against a number produced by the second and read
the difference as a 2.38 % near-miss on a tolerance. These tests measure what the difference
actually is.

Nothing here changes a scientific quantity; it is a diagnostic over two frozen implementations.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from certo_fdi.pathways.geometry import CONDITION_MAX, LAMBDA_RELATIVE, batched_projection
from certo_fdi.stage2b.rank_aware_scores import RANK_RTOL
from certo_fdi.stage2br.estimator_gap import (
    EPS64,
    ROUNDOFF_FACTOR,
    conditioned_dictionary,
    gap_report,
    label_disagreement,
    stage2a_residual_energy,
    stage2b_residual_energy,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "stage2br_reproduction_gate.yaml").read_text())
ROUNDOFF_FLOOR_REL = ROUNDOFF_FACTOR * EPS64          # 2.220e-13
D_REAL, P_REAL = 56, 3                                # n_dof(7) * M(8) rows, point-force columns


# --------------------------------------------------------------- the two rules, as frozen
def test_the_frozen_ridge_rule_is_what_stage2a_used():
    assert LAMBDA_RELATIVE == 1e-6 and CONDITION_MAX == 1e6
    # both terms of the max coincide, so lambda = 1e-6 * sigma_max^2 above the absolute floor
    assert LAMBDA_RELATIVE == 1.0 / CONDITION_MAX


def test_the_frozen_truncation_rule_is_what_stage2b_used():
    assert RANK_RTOL == 1e-8
    assert CFG["frozen_localizer"]["rank_relative_tolerance"] == RANK_RTOL


def test_stage2a_never_truncates_and_stage2b_always_can():
    """A dictionary with a direction below the cutoff is handled oppositely by the two rules."""
    d = 16
    U = np.linalg.qr(np.random.default_rng(0).normal(size=(d, d)))[0]
    D = (U[:, :2] * np.array([1.0, 1e-10]))[None]      # second direction below s_0 * 1e-8
    z = (U[:, 1] * 3.0)[None]                          # residual lies entirely IN that direction
    # Stage 2B discards the direction outright: nothing is explained
    assert stage2b_residual_energy(D, z)[0] == pytest.approx(float(z[0] @ z[0]))
    # Stage 2A keeps it, but the ridge shrinks it to nothing -- same answer here, by a different
    # mechanism. The two rules only diverge in the band between the two scales, tested below.
    assert stage2a_residual_energy(D, z)[0] == pytest.approx(float(z[0] @ z[0]), rel=1e-6)


# --------------------------------------------------------------- the disagreement band
@pytest.mark.parametrize(("exponent", "expect_disagreement"), [
    (-1, False),      # sigma well above the ridge scale: both keep the direction
    (-2, False),
    (-3, True),       # ridge keeps 3/4 of it, the projector keeps all of it
    (-4, True),       # ridge keeps 2 %
    (-6, True),       # ridge keeps essentially none, the projector still keeps all
    (-9, False),      # below the truncation cutoff: both discard it
])
def test_the_two_rules_disagree_over_a_five_decade_band(exponent, expect_disagreement):
    """``sigma_i / sigma_max`` in ``(1e-8, 1e-3)`` is where a whole direction is treated oppositely.

    The gap is measured as a fraction of the residual's own energy. Relative-to-RSS is useless
    here by construction: ``z`` is chosen to lie inside ``range(D)``, so the exact projector drives
    RSS to zero and any ratio against it diverges. Energy fraction is the physical quantity -- how
    much of the residual the two rules disagree about explaining.
    """
    d = 32
    U = np.linalg.qr(np.random.default_rng(3).normal(size=(d, d)))[0]
    r = 10.0 ** exponent
    D = (U[:, :2] * np.array([1.0, r]))[None]
    z = (U[:, 0] * 1.0 + U[:, 1] * 1.0)[None]          # equal energy in both directions
    a, b = stage2a_residual_energy(D, z)[0], stage2b_residual_energy(D, z)[0]
    frac = abs(a - b) / float(z[0] @ z[0])
    if expect_disagreement:
        assert frac > 0.1, f"expected an O(1) disagreement at 1e{exponent}, got {frac:.3e}"
    else:
        assert frac < 1e-3, f"expected agreement at 1e{exponent}, got {frac:.3e}"


def test_perfectly_conditioned_dictionaries_agree_to_roundoff():
    """The one regime in which the gate's comparison would have been sound."""
    rng = np.random.default_rng(5)
    D = conditioned_dictionary(rng, 500, D_REAL, P_REAL, condition=1.0)
    z = rng.normal(size=(500, D_REAL))
    g = gap_report(D, z)
    assert np.median(g["gap_over_roundoff_floor"]) < 1.0


@pytest.mark.parametrize(("condition", "min_multiple_of_floor"), [
    (1e2, 1e5),
    (1e3, 1e8),
    (1e5, 1e9),
])
def test_realistic_conditioning_puts_the_gap_far_outside_any_tie_envelope(condition, min_multiple_of_floor):
    """The gap is not a rounding effect: it exceeds the roundoff floor by many decades."""
    rng = np.random.default_rng(int(condition) % 9973 + 1)
    D = conditioned_dictionary(rng, 800, D_REAL, P_REAL, condition=condition)
    z = rng.normal(size=(800, D_REAL))
    g = gap_report(D, z)
    assert np.median(g["gap_over_roundoff_floor"]) > min_multiple_of_floor


def test_the_gap_dwarfs_genuine_implementation_noise():
    """Same estimator across backends: a few ULP. Different estimators: 8 orders more."""
    from certo_fdi.stage2br import canonical_scores as CS

    rng = np.random.default_rng(21)
    D = conditioned_dictionary(rng, 300, D_REAL, P_REAL, condition=3e2)
    z = rng.normal(size=(300, D_REAL))
    estimator_gap = float(np.median(gap_report(D, z)["rel_gap"]))
    noise = 0.0
    for i in range(50):
        ref = CS.project(D[i], z[i], "frozen_batched").rss
        for b in CS.BACKENDS:
            v = CS.project(D[i], z[i], b)
            if v.rank_matches_frozen:
                noise = max(noise, abs(v.rss - ref) / max(abs(ref), 1e-300))
    assert noise < ROUNDOFF_FLOOR_REL, "backend noise should sit inside the roundoff floor"
    assert estimator_gap > 1e5 * ROUNDOFF_FLOOR_REL
    assert estimator_gap > 1e5 * max(noise, EPS64)


# --------------------------------------------------------------- consequences for labels
def test_the_norm_versus_energy_difference_cannot_change_a_label():
    """Stage 2A ranks by the residual norm, Stage 2B by its square: monotone, so argmin is safe."""
    rng = np.random.default_rng(8)
    v = rng.random((200, 7)) + 0.1
    assert np.array_equal(np.argmin(v, axis=1), np.argmin(v ** 2, axis=1))


def test_well_conditioned_dictionaries_produce_identical_labels():
    rng = np.random.default_rng(13)
    links = [conditioned_dictionary(rng, 300, D_REAL, P_REAL, condition=1.0) for _ in range(7)]
    z = rng.normal(size=(300, D_REAL))
    assert label_disagreement(links, z)["n_differ"] == 0


def test_ill_conditioned_dictionaries_produce_different_labels():
    """The estimator difference is not academic: it moves window predictions."""
    rng = np.random.default_rng(17)
    links = [conditioned_dictionary(rng, 400, D_REAL, P_REAL, condition=1e5) for _ in range(7)]
    z = rng.normal(size=(400, D_REAL))
    out = label_disagreement(links, z)
    assert out["n_differ"] > 0
    assert out["fraction_differ"] > 0.01


def test_gap_report_is_self_consistent():
    rng = np.random.default_rng(29)
    D = conditioned_dictionary(rng, 50, D_REAL, P_REAL, condition=1e3)
    z = rng.normal(size=(50, D_REAL))
    g = gap_report(D, z)
    assert np.allclose(g["abs_gap"], np.abs(g["stage2a_rss"] - g["stage2b_rss"]))
    assert np.all(g["stage2a_rss"] >= 0) and np.all(g["stage2b_rss"] >= 0)
    # the ridge can only explain less than the exact projector, so its residual is never smaller
    assert np.all(g["stage2a_rss"] >= g["stage2b_rss"] - 1e-9 * np.maximum(1.0, g["stage2b_rss"]))


def test_batched_projection_is_still_the_stage2a_path():
    """Guard: if window_features stops using the ridge, this whole finding must be revisited."""
    src = (ROOT / "src" / "certo_fdi" / "pathways" / "window_features.py").read_text()
    assert "batched_projection(D, z)" in src
    assert "projection_residual" in src
    out = batched_projection(np.ones((2, 4, 2)), np.ones((2, 4)))
    assert "ridge_lambda" in out and "projection_residual_energy" in out
