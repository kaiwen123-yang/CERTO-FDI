# Paper Reset V2 — FINAL DECISION (2026-08-24)

**Terminal state: `PIVOT_BENCHMARK_DATASET_PAPER`**, resolved by the frozen
`certo_fdi_reset_v2.decision` v2.0.0 (predicate trace:
`<run>/decision/24_decision_evidence.json`;
`<run>` = `/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2`).

- Literature gate: **PASS** — 680 screened / 103 full texts (104 cards) / 40 neighbours /
  16 killer dossiers / 29 recent / 21 data-code / ≥10 citation chains; no killer occupies the
  final story; conservative occupancy for the two unavailable killers.
- Benchmark gate: **PARTIAL** — voraus dual-track reproduction PASS (CPU 0.9374, GPU seed177
  0.9319 vs paper 0.936); RoAD Table-IV partial non-reproduction documented; AURSAD native
  protocol audited leakage-prone (native supervised baselines deliberately not rerun);
  unified matrices complete (8 models × 3 seeds × 3 datasets).
- RoAD sandbox claims: **re-derived locally** (R1 chain-order no advantage; R2 split
  sensitivity; R3 SO(3) no stable benefit; R4 partially — model-dependent; R5 event-level
  undeployable).
- Method survival gate: **FAIL** — the kept candidate (context-conditioned calibration) fixes
  the false-alarm channel (AURSAD movement probe 0.81→0.33, 3 fe × 3 seeds, controls clean;
  voraus FPR@TPR90 0.32→0.20 with +5.6pp AUROC for static scores, stable from 5% healthy data)
  but reaches ΔAUROC≥0.03 with front-end independence on 0/3 mandatory datasets; per contract
  §15.7 it was downgraded without patching.
- Surviving paper: the honest-protocol benchmark audit
  (title/abstract/contributions: `<run>/decision/20_…md`; venue RA-L/ICRA benchmark track).

All 26 §12 deliverables present (`<run>/decision/PACKAGE_INDEX.md`); GO-only files 26–28 not
required for a PIVOT. Exploration deviations recorded pre-result in
`<run>/explore/EXPLORATION_LOG.md` (A1).
