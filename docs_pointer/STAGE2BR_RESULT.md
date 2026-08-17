# Stage 2B-R result pointer

**Integrity state: `FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH`.** No modifiers.
**Stage 2B scientific decision: `BLOCKED`, unchanged.** Phase 6 did not run and may not.

- Run `run_20260817T040732Z_7b8ecd8` → `/mnt/g/CERTO-FDI/04_runs/stage2b_r_reproduction_gate/<RUN_ID>/`
- Branch `stage/stage2b-r-reproduction-gate-resolution`, Draft PR #6, stacked on PR #5
- Protocol freeze commit `a4e2b17` — predates every score in this stage
- An earlier attempt, `run_20260817T032743Z_7b8ecd8`, ended `BLOCKED_INPUT_PROVENANCE` because the
  external storage drive was not attached. Superseded, retained.

## The answer

> The single flipped episode is **not** a numerically equivalent near tie. Stage 2A and Stage 2B
> rank the candidate links with **different estimators**, and three of the four windows that moved
> had top-two margins nine to ten orders of magnitude outside the measured tie envelope.

## Provenance — all verified

Stage 2B FULL package `20392940…` ✔ · Stage 2A FULL package `0ae32ba7…` ✔ · frozen dataset manifest
**recomputed** from 590 episode files, 0 missing → `8c2ba38b…` ✔ · 15/15 required score artifacts
present. `bee5f9b..7b8ecd8` is one commit over three files with every scientific and config tree
byte-identical → `BLOCKED_SCIENTIFIC_HEAD_MISMATCH` does not fire.

## The evidence reproduces exactly

Both runs saved the per-window per-link score arrays the gate compared, so no inference was
replayed. Joined on `(seed, episode_id, window_start)`: **72 episodes, 6 891 windows, join complete
and unique**, and **both stages' published top-1 reproduces bit-exactly on all three seeds**.

Exactly one label differs — **`F4_contact_0008`, seed 260817, truth link 1**:

| | votes (links 0–6) | predicted | margin |
|---|---|---|---|
| Stage 2A | `2 \| 37 \| 34 \| 0 \| 0 \| 0 \| 0` | link **1** (correct) | 3 |
| Stage 2B | `2 \| 35 \| 36 \| 0 \| 0 \| 0 \| 0` | link **2** (wrong) | 1 |

Four of 73 windows moved — enough to overturn a three-vote lead. The confusion matrix changes in
exactly one cell pair.

## Why it is not a tie

The two stages **never once computed the same number**: 0 of 48 237 score pairs bit-identical,
median relative gap 1.27e-10, p99 1.34e-02, max 1.79e-01, 96.8 % outside the roundoff floor — and
outside the frozen 1e-10 score tolerance.

Measured envelope on 400 frozen dictionary spectra: five LAPACK backends range **5.37e-14**, C/F
memory order **2.30e-15**, candidate ordering invariant, process and 1-vs-8-thread launches
identical — all inside the `1000·eps₆₄ = 2.220e-13` floor. Against a tie tolerance of ~1.15e-10:

| window | 2A margin | 2B margin | tie? |
|---|---|---|---|
| 3008 | 1.91e-11 | 8.53e-13 | yes |
| 3040 | 1.20e-01 | 4.18e-01 | **no — 3.6e9 ×** |
| 3056 | 1.69e-01 | 1.13e+00 | **no — 9.8e9 ×** |
| 3136 | 4.91e-01 | 1.57e-01 | **no — 1.4e9 ×** |

Score-level contract §6: one non-tie disagreement forces the FAIL. There are three.

`RANK_THRESHOLD_UNSTABLE` was checked and does **not** apply: 0 of 400 spectra change rank under
the 0.5×/2× sweep, all four changed windows carry the modal rank vector `[2,3,3,3,3,3,3]`, the two
link-1 rank-2 windows did not move, and Stage 2A applies no rank threshold at all.

## The mechanism

| | Stage 2A reference | Stage 2B observed |
|---|---|---|
| code | `pathways/geometry.py::batched_projection` | `stage2b/rank_aware_scores.py::project` |
| estimator | ridge normal equations, `λ = 1e-6·σ_max²` | exact orthogonal projection |
| rank | **never truncates** — all columns kept, shrunk | **truncates** at `s ≤ s₀·1e-8` |
| ranked by | residual norm | residual energy |

Norm vs energy is monotone and moves no label. The other two rows disagree completely over
`σᵢ/σ_max ∈ (1e-8, 1e-3)`. The frozen data shows exactly that signature, ordered by prefix support
(link `l` loads only joints `0..l`):

| link | support rows | median cross-stage gap |
|---|---|---|
| 0 / 1 / 2 | 8 / 16 / 24 of 56 | **2.8e-08 / 3.0e-08 / 3.7e-08** |
| 4 / 5 / 6 | 40 / 48 / 56 of 56 | 1.0e-11 / 1.1e-11 / 1.1e-11 |

~3 000× larger on the proximal links, whose short support makes their columns nearly collinear.
The flipped episode's truth link is **1**, and the contest was between links 1 and 2 — the two most
affected. Measured conditioning across 4 608 whitened dictionaries: median 4.4, p99 926, max 3 533,
none above 1e4; 0.58 % carry a singular value inside the disagreement band — rare enough that 71 of
72 episodes still agree, frequent enough that one close episode did not.

## What this does not mean

Stage 2B's science did not fail; the reproduction gate is an integrity check. The 2 % tolerance is
still finer than one episode and still cannot express what it was asked to judge. What the audit
shows is that the gate was comparing a ridge estimator against a projector and reading the
difference as a tolerance miss. `rank_aware_scores` documents `raw_projection_residual` as *"exactly
the frozen Stage 2A score"* — on this evidence it is not, and that is the defect.

The remedy is a Stage 2B-side change and is **out of scope here**: either score the audit control
with the Stage 2A ridge so the reproduction compares like with like, or restate the gate as a
comparison of two declared-different estimators. See `docs_pointer/STAGE2BR_PROTOCOL.md`.
