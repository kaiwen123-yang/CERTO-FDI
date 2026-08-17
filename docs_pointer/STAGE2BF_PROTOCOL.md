# Stage 2B-F protocol, in prose

The machine-readable version is `configs/stage2bf_estimator_harmonization.yaml`; the rules are
`src/certo_fdi/stage2bf/decision_stage2bf.py` and `estimator_identity.py`. All were committed
before any Stage 2B-F score existed. This document says *why*, which the YAML cannot.

## The error being corrected

Stage 2B's `rank_aware_scores` docstring says its `raw_projection_residual` "is exactly the frozen
Stage 2A score". It is not. Stage 2A ranked candidate links by a **ridge-regularised least-squares
residual norm**; `raw_projection_residual` is a **rank-truncated SVD orthogonal-projection RSS**.
Stage 2B-R established this at score level over 48 237 pairs, ruled out floating point, backend,
memory order, candidate order, thread count and rank instability, and returned
`FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH`.

One name over two estimators is not a typo. It made a reproduction gate compare unlike things and
then read the difference as a 2.38 % tolerance miss.

## What the two estimators actually are

Both act on a whitened residual `z ∈ R^d` and a candidate dictionary `D ∈ R^{d×p}`.

**`stage2a_ridge_residual_norm`** — `λ = max(1e-6·σ_max², σ_max²/1e6, 1e-12)`,
`θ = (DᵀD + λI)⁻¹Dᵀz`, score `‖z − Dθ‖₂`. Frozen in `pathways/geometry.py`.

**`truncated_svd_orthogonal_projection_rss`** — `K = {i : σᵢ > 1e-8·σ₁}`, `P_D = U_K U_Kᵀ`,
score `‖(I − P_D)z‖₂²`. Frozen in `stage2b/rank_aware_scores.py`.

The norm-versus-square is monotone and moves no `argmin`; it matters only for units. The real
difference is the per-direction gain:

```
ridge:  g_i = σ_i² / (σ_i² + λ)     continuous shrinkage, never 0, never exactly 1
svd:    g_i ∈ {0, 1}                hard keep or discard
```

These disagree over `σᵢ/σ_max ∈ (1e-8, 1e-3)` — five decades. On this arm that band is populated
precisely where the serial chain gives a link the fewest support rows, so the disagreement
concentrates on the proximal links.

## Why the ridge must be imported, not rewritten

A stage whose whole subject is "someone reimplemented a score and called it the original" cannot
itself reimplement that score from its formula. `stage2a_ridge_residual_norm` is a thin wrapper
around `ridge_lambda` and `batched_projection`, changing no dtype, no lambda, no candidate
reduction and no unit. `geometry.py` is byte-identical at `bcf2ad5`, `bee5f9b` and this HEAD, which
a test asserts rather than assumes.

## The hard gates

The Stage 2A ridge reproduction must match at **every** level, not on average:

1. join complete and unique; 2. `|Δ| ≤ 1e-12 + 1e-10·|ref|` on every score; 3. candidate-point
index exact; 4. per-window label exact; 5. episode vote vectors exact; 6. episode labels exact;
7. confusion matrices exact; 8. per-seed top-1 and chain distance exact.

If the frozen arrays lack the precision or schema for value-by-value comparison, the answer is
`BLOCKED_MISSING_REFERENCE_SCORE_PRECISION` — **not** a fallback to comparing 2 % seed means. That
fallback is what made the original gate uninformative and it is not available here.

The Stage 2B SVD reproduction must match on per-window RSS, rank, best hypothesis, all five
candidate scores, the F4_CAL selection per seed, the accept/defer threshold, and every F4_TEST
metric. Failure is `BLOCKED_STAGE2B_SVD_REPRODUCTION`.

## Selection discipline

The ridge is an **audit baseline**. It is `is_audit_baseline = true`, `is_selection_candidate =
false`, and it may not enter the F4_CAL candidate set — its five members are exactly Stage 2B's,
renamed. F4_TEST selects nothing, and the selection artifacts must be on disk before any F4_TEST
metric is read. A ridge that happens to score better on the test set is not a reason to pick it;
that is the definition of the leak this project forbids.

## The 2×5 matrix, and one honest caveat about it

Two estimators × five load-path controls, on identical residuals, whitening, dictionaries and
episode pairing. Contrasts:

```
Δ_support    = M_support  − M_random      does the support mask carry it?
Δ_shape      = M_fixedJ   − M_support     does Cartesian subspace shape add anything?
Δ_trajectory = M_alignedJ − M_fixedJ      does the episode's own configuration distribution?
Δ_alignment  = M_alignedJ − M_shuffledJ   does time alignment specifically?
```

Each gets a paired episode-cluster bootstrap CI — episode is the independent unit, and no
window-level IID bootstrap exists anywhere in this codebase. Labels: `ROBUST_BOTH_ESTIMATORS` only
when both estimators agree in direction *and* both CIs exclude zero; `DIRECTIONALLY_CONSISTENT`
when they agree but a CI crosses; `ESTIMATOR_SENSITIVE` when they disagree in sign;
`NOT_IDENTIFIABLE` when the evidence cannot support any of these.

**The caveat.** Three of the five controls — `support_prefix_rankmatched`,
`random_within_support_rankmatched`, `fixed_reference_jacobian` — are built from *orthonormal*
bases, because that is how rank-matching is made exact. On an orthonormal dictionary every `σᵢ = 1`,
so ridge's gain is `1/(1+1e-6)` and truncated SVD's is `1`: the two estimators agree to about
`1e-6` **by construction**. Only `time_aligned_jacobian` and `shuffled_time_jacobian` use raw
dictionaries where the estimators can genuinely differ.

So the matrix is not ten independent cells, and any report that presents it as ten would be
overstating. Estimator sensitivity can only appear in the two raw-dictionary columns and in the
contrasts that involve them — `Δ_trajectory` and `Δ_alignment`. This is stated up front rather than
discovered in the numbers, so it cannot be used selectively afterwards.

## What the decision may and may not change

Stage 2B-F deep-copies the historical Stage 2B decision evidence and changes the reproduction gate
from FAIL to PASS. Nothing else numeric may move. Detection, sequential, localization, selective,
load-path and healthy-expansion metrics, the thresholds and the decision order are all forbidden;
name migration is a schema change and must leave every value identical. Every difference is
enumerated in `stage2bf_evidence_delta.json`, and an unexplained numeric change blocks.

The terminal state is whatever `decision_stage2b.decide` returns. It is imported and called; no
logic is copied, no outcome is written by hand, and the wrapper refuses to call it at all unless
integrity passed. The historical Stage 2B `BLOCKED` record stays exactly where it is.

## What a PASS would and would not license

`PASS_ESTIMATOR_HARMONIZATION` means the two pipelines reproduce and the estimators are now named
apart. It does not mean the original Stage 2B run passed — that run is still `BLOCKED`. If the
frozen decision function returns `NO_GO_CONTACT_PRODUCT`, the only sentence available is that the
current autonomous contact product misses its pre-registered thresholds; it says nothing about
whether the Cartesian subspace carries information. And no mechanism claim may rest on one
estimator.
