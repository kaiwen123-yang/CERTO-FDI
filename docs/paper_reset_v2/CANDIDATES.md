# Phase CANDIDATES — frozen shortlist (2026-08-24)

Generated 4, kept 2 (contract 9.1 max). Full cards + collision matrix on the persistent root:
`/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2/candidates/`
(K1_context_calibrated_decision.md, K5_benchmark_protocol_audit.md,
K3_approx_equiv_structure.md [REJECTED], K4_cross_embodiment_healthy.md [FOLDED],
16_candidate_collision_matrix.md).

- **K1 CC-FDI (primary)** — context-conditioned calibrated anomaly decisions over frozen healthy-only
  score front-ends; targets the locally-evidenced fault-vs-context confusion (AURSAD probe, UR5e
  findings) and undeployable false alarms (RoAD R5). Decision layer only: no new networks, no Lie
  claims, contexts are official dataset columns.
- **K5 HP-Audit (fallback)** — honest-protocol benchmark audit; maps to PIVOT_BENCHMARK_DATASET_PAPER;
  merges into K1's evaluation half if K1 survives.
- K3 (approx-equivariance structure selection): rejected by our own R1 + missing public link-frame data.
- K4 (cross-dataset healthy transfer): folded into K1; the contract's RoAD+voraus→AURSAD template is
  channel-illegal (RoAD shares no modality with either) — legal pair is voraus↔AURSAD.

Exploration protocol (front-ends, contexts, calibrators, dev metrics, controls incl. context-permuted
conditioning and the <40-window small-cell fallback, seeds, AURSAD c1-dev/c2-c3-holdout) is frozen in the
collision matrix BEFORE any exploration result. Implementation: `src/certo_fdi_reset_v2/candidate/`.
