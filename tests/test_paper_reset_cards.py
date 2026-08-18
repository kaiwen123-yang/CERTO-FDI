"""Method-card roll-up tests: the occupancy view must not outrun the evidence."""

from __future__ import annotations

from certo_fdi_reset.literature.cards import (
    CLAIMS,
    OCCUPANCY_CAPABLE_LEVELS,
    evidence_rows,
    load_cards,
    strongest,
)

CARD = """# Method card — x

```yaml
paper_id: demo
evidence_level: A2
venue: Demo
year: 2024
fixed_or_floating_base: fixed
training:
  healthy_only: true
killer_status: DEMO
killer_for_fdi_story: false
novelty_status: PARTIALLY_OCCUPIED
confidence: high
pages_actually_read: "1-5"
collision_with_claims:
  C1: OCCUPIED
  C2: PLAUSIBLY_OPEN
```
"""


def test_only_a1_a2_b1_are_occupancy_capable():
    assert OCCUPANCY_CAPABLE_LEVELS == {"A1", "A2", "B1"}
    assert "C" not in OCCUPANCY_CAPABLE_LEVELS
    assert "FULLTEXT_UNAVAILABLE" not in OCCUPANCY_CAPABLE_LEVELS


def test_strongest_verdict_wins():
    """One occupying paper occupies the claim, however many say otherwise."""
    assert strongest(["PLAUSIBLY_OPEN", "OCCUPIED", "PARTIALLY_OCCUPIED"]) == "OCCUPIED"
    assert strongest(["PLAUSIBLY_OPEN", "PARTIALLY_OCCUPIED"]) == "PARTIALLY_OCCUPIED"
    assert strongest([]) == "UNKNOWN"
    assert strongest(["nonsense"]) == "UNKNOWN"


def test_card_parsing_requires_a_closed_yaml_fence(tmp_path):
    """An unterminated fence must yield no card, not a silently empty one."""
    (tmp_path / "good.md").write_text(CARD, encoding="utf-8")
    (tmp_path / "unterminated.md").write_text(CARD.replace("\n```\n", "\n", 1)[:-4], encoding="utf-8")
    cards = load_cards(tmp_path)
    assert [c["paper_id"] for c in cards] == ["demo"]


def test_evidence_row_flags_capability_and_claims(tmp_path):
    (tmp_path / "demo.md").write_text(CARD, encoding="utf-8")
    row = evidence_rows(load_cards(tmp_path))[0]
    assert row["occupancy_capable"] == "true"
    assert row["C1"] == "OCCUPIED"
    assert row["C2"] == "PLAUSIBLY_OPEN"
    assert all(claim in row for claim in CLAIMS)


def test_level_c_card_is_not_occupancy_capable(tmp_path):
    (tmp_path / "weak.md").write_text(CARD.replace("evidence_level: A2", "evidence_level: C"), encoding="utf-8")
    assert evidence_rows(load_cards(tmp_path))[0]["occupancy_capable"] == "false"
