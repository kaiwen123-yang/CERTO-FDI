# Stage 2B-F result pointer

**Integrity: `PASS_ESTIMATOR_HARMONIZATION` · Scientific: `NO_GO_CONTACT_PRODUCT`**
**Combined: `PASS_ESTIMATOR_HARMONIZATION__NO_GO_CONTACT_PRODUCT`**

**Historical Stage 2B decision: `BLOCKED`, unchanged and byte-preserved.** Stage 2B-R's
`FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH` also stands — it reported a real estimator mismatch,
and this stage fixed the mismatch rather than overturning the finding.

- Run `run_20260817T142903Z_7b8ecd8` → `/mnt/g/CERTO-FDI/04_runs/stage2b_f_estimator_harmonization/<RUN_ID>/`
- Branch `stage/stage2b-f-estimator-harmonization`, Draft PR stacked on the Stage 2B branch
- Protocol freeze `38c531e` — predates every Stage 2B-F score

## The two estimators, named apart

| | Stage 2A | Stage 2B |
|---|---|---|
| canonical name | `stage2a_ridge_residual_norm` | `truncated_svd_orthogonal_projection_rss` |
| historical name | `contact_residual` | `raw_projection_residual` |
| frozen source | `pathways/geometry.py` (`ridge_lambda`, `batched_projection`) | `stage2b/rank_aware_scores.py` (`project`) |
| per-direction gain | `σ²/(σ²+λ)`, continuous | `{0,1}`, hard at `σ>1e-8·σ₁` |
| unit | residual norm | residual energy |
| role | audit baseline (never a selection candidate) | Stage 2B candidate |

`geometry.py` is byte-identical at `bcf2ad5`, `bee5f9b` and HEAD, so importing the ridge runs
Stage 2A's own bytes. That is checked by comparing git tree hashes, not asserted.

## Reproduction — exact, not merely within tolerance

- **Stage 2A ridge**: 3 seeds × 159 936 scores **bit-identical**, max abs diff **0.0**. Candidate
  index, window label, episode votes, episode labels, confusion, per-seed top-1 and chain distance
  all exact.
- **Stage 2B SVD**: all 5 controls × 3 seeds bit-identical RSS/ESS, exact ranks, published F4_TEST
  metrics reproduced. Random control checked **per replicate** against its own `…#k` row.
- **F4_CAL selection**: exact on all 3 seeds, including bit-exact acceptance thresholds and the
  reject rule. Ridge excluded from the candidate set; F4_TEST opened nowhere in that module.

## The 2×5 matrix (episode top-1, mean over seeds)

| control | ridge | SVD | orthonormalised |
|---|---|---|---|
| `random_within_support_rankmatched` | 0.1536 | 0.1536 | **yes** |
| `support_prefix_rankmatched` | 0.1528 | 0.1528 | **yes** |
| `fixed_reference_jacobian` | 0.3194 | 0.3194 | **yes** |
| `shuffled_time_jacobian` | 0.5278 | 0.5278 | no |
| `time_aligned_jacobian` | **0.5833** | **0.5694** | no |

Three controls are orthonormalised, so the estimators agree there **by construction** — declared in
the Phase 1 freeze before the numbers existed. Only `time_aligned_jacobian` separates them, and the
separation *is* the historical discrepancy: 0.5833 is Stage 2A's published mean, 0.5694 is Stage
2B's observed mean. The 2.38 % that blocked Stage 2B is a change of estimator, not of run.

## Mechanism robustness

| contrast | top-1 (ridge / SVD) | label |
|---|---|---|
| `delta_support` | −0.0009 / −0.0009 | `DIRECTIONALLY_CONSISTENT` |
| `delta_shape` | +0.1667 / +0.1667 | `ROBUST_BOTH_ESTIMATORS` |
| `delta_trajectory` | +0.2639 / +0.2500 | `ROBUST_BOTH_ESTIMATORS` |
| `delta_alignment` | +0.0556 / +0.0417 | `DIRECTIONALLY_CONSISTENT` |

**`delta_alignment` CI crosses zero under both estimators** → a time-aligned Cartesian claim stays
forbidden, unchanged from Stage 2B.

## Decision

Evidence delta: **5 fields, 0 violations** — only the reproduction gate. The historical
`contact_reproduction` diagnosis is preserved verbatim with the resolution beside it. The frozen
`decision_stage2b.decide` was imported and called; it returned `NO_GO_CONTACT_PRODUCT` as the
default terminal state after no condition set matched.

That means the current autonomous contact product misses its pre-registered thresholds. It does
**not** mean the Cartesian subspace carries no information, and it licenses no deployment claim.

See `docs_pointer/STAGE2BF_PROTOCOL.md` and `STAGE2BF_PORT_PROVENANCE.md`.
