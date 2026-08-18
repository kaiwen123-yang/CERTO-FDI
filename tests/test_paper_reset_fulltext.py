"""Wave A resolution tests. The property under test is that a *wrong* paper is
never accepted -- a mis-resolved neighbour would be carded as prior art."""

from __future__ import annotations

from certo_fdi_reset.literature.fulltext import (
    MIN_TITLE_OVERLAP,
    WAVE_A,
    EvidenceLevel,
    _best_title_match,
    _title_overlap,
)


def test_wave_a_has_the_fifteen_contract_targets():
    assert len(WAVE_A) == 15
    assert len({t.target_id for t in WAVE_A}) == 15
    for target in WAVE_A:
        assert target.why_wave_a, target.target_id


def test_identical_titles_score_one():
    title = "Robot Collisions: A Survey on Detection, Isolation, and Identification"
    assert _title_overlap(title, title) == 1.0


def test_unrelated_titles_are_rejected():
    """The exact false positive seen in the first run: a confidence-set FDI query
    returning a Nature Communications droplet paper."""
    score = _title_overlap(
        "A phase transition in the coalescence of a droplet",
        "Fault detection and isolation via confidence-set separation",
    )
    assert score < MIN_TITLE_OVERLAP
    assert _best_title_match(
        [{"title": "A phase transition in the coalescence of a droplet"}],
        "Fault detection and isolation via confidence-set separation",
    ) is None


def test_best_match_picks_the_closest_of_several():
    results = [
        {"title": "Deep Learning: A Comprehensive Overview", "id": "wrong"},
        {"title": "Collision Detection for Robot Manipulators Using Unsupervised Anomaly Detection Algorithms", "id": "right"},
    ]
    best = _best_title_match(results, "Collision Detection for Robot Manipulators Using Unsupervised Anomaly Detection Algorithms")
    assert best is not None and best["id"] == "right"


def test_word_order_does_not_defeat_matching():
    assert _title_overlap(
        "Confidence-set separation for fault detection and isolation",
        "Fault detection and isolation via confidence-set separation",
    ) >= MIN_TITLE_OVERLAP


def test_only_a1_a2_b1_can_support_occupancy():
    """§7.2: C and FULLTEXT_UNAVAILABLE may never carry an occupancy decision."""
    supporting = {EvidenceLevel.A1, EvidenceLevel.A2, EvidenceLevel.B1}
    assert EvidenceLevel.C not in supporting
    assert EvidenceLevel.NONE not in supporting


def test_control_characters_are_stripped_but_layout_survives():
    """NULs from PDF extraction make the file binary to grep; newlines must stay."""
    from certo_fdi_reset.literature.fulltext import strip_control_characters

    raw = "quadruped\x00 robot\n<<<PAGE 2>>>\nnext\tcol\x07umn"
    cleaned = strip_control_characters(raw)
    assert "\x00" not in cleaned and "\x07" not in cleaned
    assert "\n" in cleaned and "\t" in cleaned
    assert "quadruped robot" in cleaned
    assert "<<<PAGE 2>>>" in cleaned
