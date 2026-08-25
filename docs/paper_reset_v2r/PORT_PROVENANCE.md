# Paper Reset V2-R — Port Provenance

| Inherited artifact | Source | Trust label / V2-R use |
|---|---|---|
| V2 Full review package | `06_review_exchange/to_review/full/CERTO_FDI_V2_FULL_REVIEW_20260824T065812Z.zip` (sha256 verified) | FROZEN_HISTORICAL_EVIDENCE — read-only input to R1 |
| V2 decision code | `src/certo_fdi_reset_v2/decision.py` v2.0.0 (in-tree at base head) | used to RECOMPUTE the historical state (5.1); never edited |
| V2 benchmark harness | `src/certo_fdi_reset_v2/benchmarks/{models,voraus_unified,aursad_unified,road_reverify,road_native}.py` | REUSED for CORE-8 parity; CORE-8 deltas implemented in v2r modules |
| CC-layer | `src/certo_fdi_reset_v2/candidate/context_calibration.py` | REUSED as a context-calibration front (10.2 gate needs >=3 front-ends) |
| V2 result JSONs | `<v2run>/b_voraus, b_aursad, b_road, explore, confirm` | quotable with per-cell seed semantics re-labeled per matrix-truth rules; RoAD R1–R5 re-used as controlled audit |
| 94 V2 + 10 V1 method cards, 16 dossiers | `02_research_docs/paper_reset_v2/literature/`, `.../paper_reset/literature/` | copied INTO the self-contained V2-R package (5.3); V1 cards re-labeled inherited |
| voraus official checkouts | `~/research/CERTO-FDI-BASELINES/…` | unchanged official code |
| AURSAD H5, RoAD frozen repo, voraus parquet | `03_data/public/…` | unchanged |
| ME-AD | Zenodo 20817531 v1 (downloading) | NEW mandatory dataset this round |

Explicitly NOT inherited: any V2 summary phrase struck by §14.3 (first / three
principal / 8×3×3 / surveys-cite-none / deployable calibration) — each must be
re-derived or deleted in S0.

`<v2run>` = /mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2
