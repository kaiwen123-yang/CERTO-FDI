# Stage 2B protocol, in prose

The machine-readable version is `configs/stage2b_contact_loadpath.yaml`; the decision rules are
`src/certo_fdi/stage2b/decision_stage2b.py`. Both were committed before any Stage 2B metric
existed. This document says *why* each rule is there, which the YAML cannot.

## The question

`chain_gnn_aug` is frozen — same 63,047 parameters, same hyperparameters, no new encoder anywhere
in this stage. Given that front end:

1. how much of the contact-link localization signal is serial-chain **load-path support**, and how
   much is **Cartesian subspace geometry**?
2. does **rank-aware** subspace scoring beat the raw projection residual?
3. does an **ambiguity-aware accept/defer** rule reduce localization error on the answers it keeps?
4. can **healthy-only context calibration** plus **sequential monitoring** reach 50 event false
   alarms per hour?
5. does scaling the healthy training set 40 → 80 → 160 change any of the above?

Stage 2A answered a narrower version of (1) and got it wrong. Stage 2B exists mostly to find that
out.

## 1. Why the load-path controls are built the way they are

Stage 2A concluded that the localization gain came from chain load-path structure rather than
Cartesian geometry, because a control that **shuffled the time indices** of the Jacobians within an
episode reproduced about ninety percent of the gain. The inference was: if the exact configuration
does not matter, the geometry does not matter.

That inference does not hold. Shuffling time keeps the episode's *real* Jacobians — every column is
still `−J_{l,p}(q_t)^T` for some genuine configuration `q_t` the arm actually visited. The control
destroys the time correspondence and nothing else. The Cartesian subspace shape survives it intact.

So Stage 2B adds a control that is genuinely geometry-free:

| control | support mask | rank | uses real configurations? |
|---|---|---|---|
| `random_within_support_rankmatched` | yes | matched | no — a fixed-seed random orthonormal frame |
| `support_prefix_rankmatched` | yes | matched | no — a DCT-II basis inside the prefix rows |
| `fixed_reference_jacobian` | yes | intrinsic | one configuration, the median healthy training pose |
| `shuffled_time_jacobian` | yes | matched | yes, wrong instants |
| `time_aligned_jacobian` | yes | matched | yes, right instants |

Reading down the table, each row adds exactly one ingredient, so the differences are interpretable:

- `support − random` — does the serial-chain prefix mask beat a random frame of the same rank?
- `fixed − support` — does one real Jacobian beat the bare mask? (**subspace shape**)
- `aligned − fixed` — do the episode's own configurations beat a single reference? (**trajectory geometry**)
- `aligned − shuffled` — does exact per-window time correspondence matter? (**time alignment**)

**Rank matching is not optional.** A hypothesis with more free dimensions can only fit a residual
better, so an unmatched control would confound "more geometry" with "more rank". Every synthetic
control realises the same numerical rank per link as the aligned run, and
`tests/test_stage2b_rank_matching.py` asserts it. `fixed_reference_jacobian` is the one exception:
its rank is intrinsic to a single configuration and cannot be matched without changing what it is,
so it is reported with its own rank and never used as the rank-matched control.

**The claim rule, fixed in advance (§04.4):** a time-aligned Cartesian geometry claim requires the
aligned method to beat *both* the fixed-reference and the shuffled-time control with an
episode-cluster confidence interval excluding zero. Beating one is not enough.

## 2. Why there is a separate `F4_CAL` partition

Stage 2A selected nothing on contact data — its localizer was pre-registered. Stage 2B *does*
select: one score out of five, and an accept/defer threshold. Doing that on the final F4 test
episodes would invalidate every number downstream.

So a new contact partition is generated: 12 episodes per truth link over links 1, 3, 5, 6, with
seeds provably disjoint from every frozen episode seed and from the healthy-expansion seeds. Its
context law mirrors the frozen split structure (S0 plus the four OOD splits) so it is not a
narrower distribution than deployment. It may do exactly two things — choose the score and
calibrate the accept/defer threshold — and it may never train the encoder or move a detection
threshold.

The disjointness guard is not decorative: an earlier seed layout collided with the
healthy-expansion root and the guard blocked the run rather than producing quietly contaminated
numbers.

## 3. Why the episode is the unit of independence

Windows inside an episode overlap and share a trajectory, a controller and a payload. Treating
them as independent would shrink every confidence interval by roughly the square root of the
windows-per-episode ratio and would make almost any difference look significant. Every interval in
Stage 2B is a **percentile bootstrap over whole episodes**; a window-level IID bootstrap anywhere is
a §1 integrity failure, not a stylistic preference. With fewer than three distinct episodes the
bootstrap returns `nan` rather than a falsely narrow interval.

## 4. Why calibration is healthy-only, and what it is allowed to claim

Context is the six declared physical fields available at deployment — controller id, speed scale,
tool mass, tool CoM, temperature proxy, noise level. Region id, trajectory family, fault labels,
contact link, severity and any truth state are excluded by construction: `CAL.fit` has no
parameter a label could be passed through.

Four calibrators are compared: a global quantile (the historical baseline), a Mondrian grouped
quantile with an explicit backoff path, a small quantile regressor, and episode-blocked conformal
calibration. The conformal variant uses **whole episodes** as the exchangeability blocks, so its
nonconformity score is the per-episode maximum, not a window score.

The language rule is absolute: coverage is reported as **marginal or grouped empirical** only.
Nothing here is an exact conditional CFAR guarantee — the whitener and the density head are both
estimated from finite healthy data, and the windows within an episode are strongly dependent. The
code carries the forbidden phrases in a constant so a test can check that no calibrator's own
description uses them except inside an explicit denial.

## 5. Why alarm events, not alarm windows

A per-window alarm rate is not an operational quantity. What matters is how often an operator is
interrupted, so the headline is **event false alarms per hour**, with the window rate reported
separately and never as the headline. Everything that makes an event well defined is frozen before
evaluation: a 1.0 s refractory, a 0.50 s event-match tolerance, a 32 ms window stride, delay
measured from fault onset, missed events left as `nan` rather than imputed, and sequential state
reset at every episode boundary. Alarms before fault onset are false alarms, never early
detections.

## 6. Why healthy expansion is nested

H40 ⊂ H80 ⊂ H160, with the frozen 40 training episodes as the base and new episodes added on a
deterministic, context-balanced table fixed before any fault performance was looked at. Nesting is
what makes a difference across scales attributable to *size* rather than to a different episode
mix. The encoder and its hyperparameters do not change; only calibration layers are refitted per
scale. No frozen episode is regenerated or overwritten, the fault tests stay byte-identical, and
extrapolation beyond H160 is forbidden.

## 7. Why the decision rules look the way they do

Seven terminal states, evaluated in a fixed order:

```
BLOCKED > GO_CONTACT_LOADPATH_MONITOR > PIVOT_SUPPORT_ONLY_LOCALIZER
  > PIVOT_LOADPATH_LOCALIZATION_ONLY > PIVOT_SEQUENTIAL_DETECTION_ONLY
  > PIVOT_CONTEXT_CALIBRATION_ONLY > NO_GO_CONTACT_PRODUCT(≥2 conditions)
  > NO_GO_CONTACT_PRODUCT(default)
```

`BLOCKED` dominates because an integrity failure is explicitly *not* a scientific verdict — a hash
mismatch says nothing about whether the idea works. `PIVOT_SUPPORT_ONLY_LOCALIZER` is checked
before the partial-failure pivots because it is a **naming** refinement of a passing localizer: a
support-only method that meets the localization bar is still a working localizer, it just may not
be called Cartesian geometry. `NO_GO_CONTACT_PRODUCT` under §8 requires *two* independent failure
conditions and a completed H160 arm, so it can never fire merely because a run was cut short; that
case falls through to the explicit default.

The default matters. A run where every axis works partially and none reaches its threshold is not
a strong no-go, and the rules are written so that this case is *reported as the default* rather
than talked up into a pivot it does not qualify for.

## 8. Claims this stage may not make

- no exact conditional CFAR;
- no physical wrench recovered from network-internal messages;
- no universal link identifiability;
- no "first" anything — the bounded literature search found that the serial-chain prefix-support
  isolation rule and Jacobian-transpose projection are standard prior art, so that novelty claim is
  retired;
- no Cartesian-geometry naming if a support-only control explains the result;
- no window-level IID bootstrap;
- no automatic merge, and no entry into a hardware or public-data stage.
