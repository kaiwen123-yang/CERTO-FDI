"""CERTO-FDI Paper Reset: systematic full-text literature audit and public benchmark reproduction.

This package is deliberately separate from ``certo_fdi`` (the internal simulation
stages, PR #1-#7). Nothing here may import internal MuJoCo/Pinocchio physics
parameters into public-dataset code paths; see
``contracts/paper_reset/13_CANDIDATE_MODEL_ADAPTER_PROTOCOL.md`` section 3.
"""

__all__ = ["decision", "config", "paths", "provenance"]

STAGE = "paper_reset_literature_public_benchmarks"
