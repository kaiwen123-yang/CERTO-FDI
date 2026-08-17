"""The Phase 2/3 evidence path: joins, votes, margins, and the frozen-run reproduction.

The synthetic tests pin the aggregation arithmetic and run anywhere. The tests marked
``requires_frozen_runs`` read the actual frozen Stage 2A/2B score arrays and are the ones that
matter for the audit's claim: they assert the join is complete and unique, that both stages'
*published* top-1 is reproduced bit-exactly from those arrays, and that exactly one episode label
differs. They skip cleanly when the storage root is not mounted.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import yaml

from certo_fdi.stage2br import evidence as EV

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "stage2br_reproduction_gate.yaml").read_text())
A_RUN = Path(os.path.expanduser(CFG["paths"]["stage2a_run_root"]))
B_RUN = Path(os.path.expanduser(CFG["paths"]["stage2b_run_root"]))
SEEDS = list(CFG["historical_reproduction"]["seeds"])

requires_frozen_runs = pytest.mark.skipif(
    not (A_RUN / "p5_ablations" / f"scores_seed{SEEDS[0]}.npz").is_file()
    or not (B_RUN / "p1_loadpath" / f"controls_seed{SEEDS[0]}.npz").is_file(),
    reason="frozen Stage 2A/2B run roots are not mounted",
)


# --------------------------------------------------------------------- aggregation arithmetic
def test_episode_vote_matches_both_stages_frozen_implementations():
    from certo_fdi.experiments.run_stage2b_loadpath import _episode_vote as vote_2b
    from certo_fdi.experiments.run_stage2a_metrics import _episode_vote as vote_2a

    rng = np.random.default_rng(99)
    for _ in range(60):
        p = rng.integers(0, 7, size=int(rng.integers(1, 40)))
        assert EV.episode_vote(p) == vote_2a(p) == vote_2b(p)


def test_episode_vote_breaks_a_count_tie_to_the_lowest_link():
    assert EV.episode_vote(np.array([2, 2, 5, 5])) == 2
    d = EV.vote_detail(np.array([2, 2, 5, 5]))
    assert d["is_vote_tie"] is True and d["vote_margin"] == 0


def test_episode_vote_ignores_negative_predictions():
    assert EV.vote_detail(np.array([-1, -1, 3, 3, 3]))["n_windows"] == 3


def test_window_predictions_is_argmin_with_first_minimum_wins():
    s = np.array([[5.0, 3.0, 3.0, 9.0]])
    pred, margin, order = EV.window_predictions(s)
    assert pred[0] == 1 and margin[0] == 0.0 and order[0, 0] == 1


def test_window_predictions_margin_is_second_minus_best():
    pred, margin, _ = EV.window_predictions(np.array([[5.0, 3.0, 4.0, 9.0]]))
    assert pred[0] == 1 and margin[0] == pytest.approx(1.0)


def test_window_predictions_marks_non_finite_rows_invalid():
    pred, _, _ = EV.window_predictions(np.array([[1.0, np.nan, 2.0]]))
    assert pred[0] == -1


def test_confusion_counts_truth_by_prediction():
    c = EV.confusion(np.array([1, 2, 1]), np.array([1, 1, 1]))
    assert c[1, 1] == 2 and c[1, 2] == 1


# --------------------------------------------------------------------- the frozen runs
@requires_frozen_runs
@pytest.mark.parametrize("seed", SEEDS)
def test_join_is_complete_and_unique(seed):
    """Master prompt §11.5."""
    p = EV.load_pair(A_RUN, B_RUN, seed)
    assert p["join_complete"], (p["windows_a_only"], p["windows_b_only"])
    assert p["n_common"] > 0
    assert len(set(p["key"].tolist())) == len(p["key"])


@requires_frozen_runs
@pytest.mark.parametrize("seed", SEEDS)
def test_frozen_arrays_reproduce_both_published_top1_bit_exactly(seed):
    """The audit's foundation: the numbers the gate compared come out of these arrays exactly."""
    ref = dict(zip(SEEDS, CFG["historical_reproduction"]["stage2a_top1_by_seed"]))
    obs = dict(zip(SEEDS, CFG["historical_reproduction"]["stage2b_top1_by_seed"]))
    rows = EV.episode_table(EV.load_pair(A_RUN, B_RUN, seed))
    assert len(rows) == CFG["historical_reproduction"]["episodes_per_seed"]
    top1_a = float(np.mean([r["stage2a_correct"] for r in rows]))
    top1_b = float(np.mean([r["stage2b_correct"] for r in rows]))
    assert top1_a == ref[seed]
    assert top1_b == obs[seed]


@requires_frozen_runs
def test_exactly_one_episode_label_differs_across_all_seeds():
    """The kickoff records one difference; assert it rather than assume it."""
    changed = []
    for seed in SEEDS:
        changed += [r for r in EV.episode_table(EV.load_pair(A_RUN, B_RUN, seed)) if r["label_changed"]]
    assert len(changed) == CFG["historical_reproduction"]["expected_differing_predictions"]
    r = changed[0]
    assert r["seed"] == CFG["historical_reproduction"]["expected_differing_seed"]
    assert r["truth_link"] == CFG["historical_reproduction"]["expected_differing_truth_link"]
    assert r["stage2a_correct"] == 1 and r["stage2b_correct"] == 0


@requires_frozen_runs
def test_the_two_stages_never_produce_a_bit_identical_score():
    """If they computed the same statistic, some pair would agree exactly. None does."""
    n_ident = n_total = 0
    for seed in SEEDS:
        p = EV.load_pair(A_RUN, B_RUN, seed)
        n_ident += int((p["score_a"] == p["score_b"]).sum())
        n_total += int(p["score_a"].size)
    assert n_total > 40000
    assert n_ident == 0


@requires_frozen_runs
def test_score_disagreement_exceeds_the_frozen_score_tolerance():
    """Contract §3: independent implementations of one score must agree to 1e-10 relative."""
    tol = float(CFG["score_equivalence"]["score_relative_tolerance"])
    worst = 0.0
    for seed in SEEDS:
        p = EV.load_pair(A_RUN, B_RUN, seed)
        g = np.abs(p["score_a"] - p["score_b"]) / np.maximum(np.abs(p["score_b"]), 1e-300)
        worst = max(worst, float(g.max()))
    assert worst > tol, "if this ever passes, the two stages agree and the finding must be revisited"
    assert worst > 1e-3


@requires_frozen_runs
def test_the_gap_is_largest_on_the_shortest_support_links():
    """The mechanism: link l loads joints 0..l, so proximal dictionaries are the ill-conditioned ones."""
    med = []
    for l in range(EV.N_LINKS):
        g = []
        for seed in SEEDS:
            p = EV.load_pair(A_RUN, B_RUN, seed)
            g.append(np.abs(p["score_a"][:, l] - p["score_b"][:, l])
                     / np.maximum(np.abs(p["score_b"][:, l]), 1e-300))
        med.append(float(np.median(np.concatenate(g))))
    # the three proximal links sit orders of magnitude above the three distal ones
    assert min(med[0:3]) > 100 * max(med[4:7])


@requires_frozen_runs
def test_the_flipped_episode_has_three_non_tie_window_disagreements():
    """The classification hinges on this: a non-tie disagreement forbids the tie pass."""
    p = EV.load_pair(A_RUN, B_RUN, CFG["historical_reproduction"]["expected_differing_seed"])
    tr = EV.flipped_episode_trace(p, "F4_contact_0008")
    assert tr["n_windows_changed"] == 4
    floor = float(CFG["score_equivalence"]["roundoff_factor"]) * np.finfo(float).eps
    mult = float(CFG["score_equivalence"]["tie_multiplier"])
    non_tie = 0
    for w in tr["changed_windows"]:
        scale = max(1.0, float(np.max(np.abs(w["stage2b_scores"]))))
        tol = mult * floor * scale
        if w["stage2b_margin"] > tol and w["stage2a_margin"] > tol:
            non_tie += 1
    assert non_tie == 3


@requires_frozen_runs
def test_rank_is_not_implicated_in_the_flip():
    """All four changed windows carry the modal rank vector; the rank-2 windows are not among them."""
    p = EV.load_pair(A_RUN, B_RUN, CFG["historical_reproduction"]["expected_differing_seed"])
    m = p["episode"] == "F4_contact_0008"
    rk = p["rank_b"][m]
    pa, _, _ = EV.window_predictions(p["score_a"][m])
    pb, _, _ = EV.window_predictions(p["score_b"][m])
    changed = pa != pb
    assert (rk[changed, 1] == 3).all(), "changed windows should carry the modal link-1 rank"
    assert not (changed & (rk[:, 1] != 3)).any(), "the rank-2 windows are not the ones that moved"


@requires_frozen_runs
def test_truth_links_agree_between_the_frozen_runs():
    for seed in SEEDS:
        EV.load_pair(A_RUN, B_RUN, seed)      # raises if the truth links disagree


@requires_frozen_runs
def test_residual_energy_is_consistent_across_links():
    """RSS + ESS must reconstruct one residual energy per window, whatever the link."""
    for seed in SEEDS:
        p = EV.load_pair(A_RUN, B_RUN, seed)
        assert p["z_energy_link_spread"] < 1e-6
