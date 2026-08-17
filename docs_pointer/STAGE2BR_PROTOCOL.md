# Stage 2B-R protocol, in prose

The machine-readable version is `configs/stage2br_reproduction_gate.yaml`; the decision rules are
`src/certo_fdi/stage2br/decision_stage2br.py`. Both were committed before any Stage 2B-R score
existed. This document says *why* each rule is there, which the YAML cannot.

## The question

Stage 2B ended `BLOCKED`. Not because the science failed a threshold — because a §1 integrity
gate fired. Re-running the frozen Stage 2A contact localizer inside the Stage 2B pipeline
reproduced two of three seeds bit-exactly and missed the third by **one episode out of 24**,
entirely inside truth link 1. That moved the seed mean by 2.38 %, past a pre-registered 2 %
relative tolerance.

Stage 2B-R asks one question and is forbidden from asking any other:

> Did that single label difference come from a numerically equivalent near tie, or from a real
> difference in frozen inputs, score computation, rank handling, candidate ordering, aggregation,
> or implementation?

It may not improve the localizer, retrain anything, regenerate an episode, relax the old 2 %
tolerance and declare the original run passed, or edit the historical Stage 2B `BLOCKED` record.

## 1. Why top-1 percentage is the wrong integrity object

With 24 episodes per seed the metric is quantised to `1/24 = 4.1667` points. Against a reference
of `0.5833333`, one vote is a `7.14 %` relative change. A `2 %` relative tolerance is therefore
**finer than the metric's own resolution**: no run that differs by a single episode can pass it,
and no run that differs by zero episodes can fail it. The gate as written can only ever return
"bit-exact" or "blocked".

That does not make the gate wrong, and Stage 2B-R does not edit it. It makes it uninformative
about the thing an integrity gate is supposed to catch — whether the *computation* changed. So
Stage 2B-R introduces a second, finer test, one level below the metric: compare the **scores**.

The rule is frozen here, before the scores are looked at, precisely because the ordering matters.
A tie tolerance chosen after seeing the margin is not a tolerance, it is a conclusion.

## 2. What "the score" means, exactly

The frozen localizer is not a single formula, it is a five-step chain, and a reproduction claim
has to hold at every step. Restated from `certo_fdi.stage2b.rank_aware_scores` and
`certo_fdi.experiments.run_stage2b_loadpath` (read-only — Stage 2B-R changes none of it):

1. **Whitened residual.** Each window contributes `z ∈ R^d`.
2. **Projection.** For each link `l` and each candidate contact point `h`, the dictionary
   `D_{l,h}` is factorised `U, s = svd(D, full_matrices=False)`; columns are retained where
   `s > max(s_0 · 1e-8, 1e-300)`; `ESS = Σ (Uᵀz)²` over retained columns; `RSS = max(‖z‖² − ESS, 0)`.
   The rank is the number retained.
3. **Candidate reduction.** Per link, the candidate point with the smallest `RSS` wins.
4. **Window label.** `argmin_l RSS_l` — the frozen Stage 2A audit-control score
   `raw_projection_residual`.
5. **Episode label.** Majority vote over that episode's faulty F4 windows,
   `np.bincount(pred, minlength=7).argmax()`.

Two of those steps hide a tie-break, and both resolve to **the lowest link index**, because NumPy's
`argmin`/`argmax` return the first extremum. That is the mechanism a near tie would exploit, and it
is why the audit has to reach window level: `bincount(...).argmax()` is a deterministic function of
the vote counts, so if an episode label moved, **some window's `argmin` moved first**. An episode
whose label changed without any window changing would not be a tie — it would be a bug.

## 3. Raw-input equivalence comes before score equivalence

Before any tie can be discussed, Stage 2A and Stage 2B must be shown to have been handed the same
numbers: residual vectors, whitening matrix, dictionary matrices, candidate-point order, window
membership and order, ranks and singular values, and aggregation votes. Bit-identical where that
is expected; otherwise inside `1e-12 · max(1, |reference|)` absolute and `1e-10` relative.

A difference here is an implementation mismatch. It is never a tie, however small it is — a tie is
a statement about two *links* being indistinguishable under one computation, not about two
computations disagreeing.

## 4. The numerical envelope is measured, not assumed

The tie tolerance is not a number someone picked. For each episode/link score:

```
backend_range   = max over {numpy_svd, scipy gesdd, scipy gesvd, scipy gelsd, scipy gelsy} − min
roundoff_floor  = 1000 · eps64 · max(1, max|score| in this episode)
envelope        = max(backend_range, roundoff_floor)
```

and for the episode's best and second-best links,

```
tie_tolerance = 2 · max(envelope_best, envelope_second)
margin        = score_second − score_best
```

A near tie requires `margin ≤ tie_tolerance`. The `roundoff_floor` is unconditional: five backends
agreeing bit-for-bit is a fact about five LAPACK paths, not proof that the quantity is stable, so
the floor applies even then.

The backends are diagnostics for the *envelope*. They are not five candidate methods and the audit
never picks among them.

## 5. Rank instability is not a tie, and must be named

The frozen rank rule keeps singular values above `s_0 · 1e-8`. A singular value sitting near that
threshold is a discontinuity, not a rounding error: cross it and the projector gains or loses a
whole dimension, and `RSS` jumps by the energy in that direction.

So a diagnostic sweep at `{0.5, 1, 2} × tol` is mandatory. If the flipped episode's label moves
under that sweep, the finding is `RANK_THRESHOLD_UNSTABLE` and the tie pass is forbidden — the run
falls through to `FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH`. The sweep is a diagnostic only; it
may not be used to choose a better threshold, and `1e-8` stays.

## 6. Every non-tie episode must reproduce exactly

`margin > tie_tolerance` means the two links were distinguishable. If such an episode's label
changed, something in the computation changed, and one is enough for
`FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH`. There is no budget of allowed disagreements.

## 7. Tie sets are evidence, never a metric

For audit reporting the tie set is `{l : score_l − min score ≤ tie_tolerance}`. It exists so a
reader can see how wide the ambiguity was, and so a *future* stage could argue for a deterministic
`AMBIGUOUS_LINK_SET` return. It is not applied retroactively: Stage 2A and Stage 2B keep their
unique-label top-1, and no historical number is re-scored with tie-aware credit. Doing so would
turn an integrity audit into a favourable re-evaluation, which is exactly what this stage is not.

## 8. Terminal states, and what a PASS does not mean

Precedence is strict and evaluated in order (`decision_stage2br.integrity_state`):

```
BLOCKED_INPUT_PROVENANCE
BLOCKED_SCIENTIFIC_HEAD_MISMATCH
BLOCKED_MISSING_REFERENCE_EVIDENCE
BLOCKED_UNRESOLVABLE_SCORE_HISTORY
FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH
PASS_NUMERICALLY_EQUIVALENT_TIE_FLIP
PASS_EXACT_REPRODUCTION
```

The blocked states come first on purpose. Missing evidence must never be reported as a clean
result, and the cheapest way to manufacture a false PASS is to be unable to check something and
call it fine. If the frozen score arrays cannot be reached, the honest answer is
`BLOCKED_MISSING_REFERENCE_EVIDENCE`, not an inference from summary counts.

If the state is a PASS, Phase 6 re-executes the **original** frozen `decision_stage2b.decide` on
the **original** frozen evidence with exactly one input changed — the reproduction-gate Boolean —
and writes the result under new Stage 2B-R filenames. Every other metric, threshold, condition and
word of vocabulary is byte-identical, and the historical Stage 2B artifacts are not touched. The
outcome is whatever that function returns; it is not predicted here.

A PASS means *the reproduction gate is no longer a reason to block Stage 2B*. It does not mean
Stage 2B passed, and the reports may not say so.
