"""Parse the frozen query set out of 05_LITERATURE_SEARCH_STRINGS.md.

The contract file is the single source of truth for queries: parsing it (rather
than re-typing the strings) means a query cannot silently drift from the frozen
contract. Revisions during execution are allowed by
``04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md`` §D.1 but must bump
``QUERY_SET_VERSION`` and be logged with a reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

QUERY_SET_VERSION = "1.0.0"

_WORD = re.compile(r"[A-Za-z0-9\-]+")
_OPERATORS = {"AND", "OR", "NOT"}

_LINEAGE_BY_HEADING = {
    "Manipulator FDI / proprioception": "L2_manipulator_actuator_sensor_fdi",
    "Momentum observer / uncertainty learning": "L3_learned_momentum_observer",
    "Structured / chain / graph dynamics learning": "L4_structured_chain_graph_dynamics",
    "Lie / geometry-aware representations": "L5_lie_geometry_equivariant",
    "Contact / collision localization": "L6_contact_collision_localization",
    "Public anomaly benchmarks": "L8_public_benchmarks_transfer",
    "Context / OOD / sequential": "L7_mtsad_context_ood_sequential",
    "Recent monitoring": "L_recent_2025_2026",
    "Killer-paper precision queries": "L_killer_precision",
}


@dataclass(frozen=True)
class Query:
    query_id: str
    section: str
    lineage: str
    text: str

    @property
    def is_phrase_heavy(self) -> bool:
        """True when the query leans on quoted phrases (needs exact-phrase support)."""
        return '"' in self.text

    def plain_terms(self) -> str:
        """Query with boolean/quoting syntax stripped, for APIs without a query DSL."""
        stripped = self.text.replace('"', " ")
        stripped = re.sub(r"\b(AND|OR|NOT)\b", " ", stripped)
        stripped = stripped.replace("(", " ").replace(")", " ")
        return re.sub(r"\s+", " ", stripped).strip()

    def and_groups(self) -> list[list[str]]:
        """Parse the query into AND-groups, each a list of OR-alternatives.

        ``("robot manipulator" OR "serial manipulator") AND (fault detection OR
        fault isolation)`` becomes
        ``[["robot manipulator", "serial manipulator"], ["fault detection", "fault isolation"]]``.

        Keeping OR-alternatives together matters: flattening would AND
        "robot manipulator" with "serial manipulator", and no paper says both.
        A query with no explicit operators is an implicit AND, with each quoted
        phrase kept whole and each bare word its own group.
        """
        parts = self._split_top_level_and(self.text.strip())
        groups: list[list[str]] = []
        for part in parts:
            part = part.strip()
            while part.startswith("(") and part.endswith(")"):
                part = part[1:-1].strip()
            if not part:
                continue
            alternatives = [a.strip() for a in re.split(r"\bOR\b", part) if a.strip()]
            if len(alternatives) > 1:
                groups.append([a.strip('"').strip() for a in alternatives])
                continue
            single = alternatives[0]
            for phrase in re.findall(r'"([^"]+)"', single):
                if phrase.strip():
                    groups.append([phrase.strip()])
            for word in re.sub(r'"[^"]*"', " ", single).split():
                if word not in _OPERATORS:
                    groups.append([word])
        return [g for g in groups if any(g)]

    @staticmethod
    def _split_top_level_and(text: str) -> list[str]:
        """Split on AND that is outside both parentheses and quotes."""
        parts: list[str] = []
        buf: list[str] = []
        depth = 0
        in_quote = False
        for token in re.findall(r'"|\(|\)|\s+|[^\s()"]+', text):
            if token == '"':
                in_quote = not in_quote
            elif not in_quote:
                if token == "(":
                    depth += 1
                elif token == ")":
                    depth -= 1
                elif token == "AND" and depth == 0:
                    parts.append("".join(buf))
                    buf = []
                    continue
            buf.append(token)
        parts.append("".join(buf))
        return parts

    def term_groups(self) -> list[str]:
        """Flat view of :meth:`and_groups`: the first alternative of each group."""
        return [g[0] for g in self.and_groups()]


def load_queries(path: str | Path) -> list[Query]:
    """Read every ``- `query`` bullet under every ``## section`` heading."""
    text = Path(path).read_text(encoding="utf-8")
    queries: list[Query] = []
    section = "UNSECTIONED"
    counter = 0
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.*\S)\s*$", line)
        if heading:
            section = heading.group(1)
            continue
        bullet = re.match(r"^-\s+`(.+)`\s*$", line)
        if bullet:
            counter += 1
            queries.append(
                Query(
                    query_id=f"Q{counter:03d}",
                    section=section,
                    lineage=_LINEAGE_BY_HEADING.get(section, "UNMAPPED"),
                    text=bullet.group(1).strip(),
                )
            )
    return queries


def token_document_frequency(queries: list[Query]) -> dict[str, int]:
    """How many of the frozen queries each token appears in.

    Used to rank group specificity. Tokens common across the contract's own query
    set ("robot", "detection") are generic here; rare ones ("conformal", "RNEA")
    are discriminative. Deriving this from the frozen query set rather than a
    hand-written stoplist keeps the ranking reproducible and auditable.
    """
    df: dict[str, int] = {}
    for query in queries:
        seen = {w.lower() for w in _WORD.findall(query.text) if w not in _OPERATORS}
        for token in seen:
            df[token] = df.get(token, 0) + 1
    return df


def rank_groups(query: Query, df: dict[str, int], budget: int) -> list[list[str]]:
    """The ``budget`` most discriminative AND-groups, in original order.

    Multi-word phrases outrank single words; among equals the rarer token wins.
    Needed because arXiv and DBLP AND every token and collapse to 0-1 hits on a
    six-token contract query.
    """
    groups = query.and_groups()
    if len(groups) <= budget:
        return groups

    def score(group: list[str]) -> tuple[int, int]:
        is_phrase = any(" " in alt for alt in group)
        rarity = min(
            (df.get(w.lower(), 1) for alt in group for w in _WORD.findall(alt)),
            default=1,
        )
        return (0 if is_phrase else 1, rarity)

    keep = sorted(sorted(range(len(groups)), key=lambda i: score(groups[i]))[:budget])
    return [groups[i] for i in keep]
