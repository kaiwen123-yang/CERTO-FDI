# Stage 2B-R result pointer

**Integrity state: `BLOCKED_INPUT_PROVENANCE`.**
**Stage 2B scientific decision: `BLOCKED`, unchanged.** No historical artifact was modified.

- Run `run_20260817T032743Z_7b8ecd8`
- Branch `stage/stage2b-r-reproduction-gate-resolution`, Draft PR #6, stacked on PR #5
- Protocol freeze commit `a4e2b17` — predates every score in this stage
- Artifacts: `<STORAGE_ROOT>/04_runs/stage2b_r_reproduction_gate/run_20260817T032743Z_7b8ecd8/`
  (this run used the local staging root; the canonical root is `/mnt/g/CERTO-FDI`)

## Why blocked

`/mnt/g/CERTO-FDI` is not attached to the host: `/mnt/g` is a stale empty directory, Windows
exposes no G: volume, and `Get-Disk` shows no file-backed virtual disk to re-attach. The registry
records G: as an MBR external disk (signature `0x4FEA75BE`) that is physically disconnected.

8 of 8 frozen inputs absent, 0 hash-verified, 0 of 8 required score-level artifacts present. No
score array is carried in Git. Reconnecting the drive lifts this entirely.

## The finding that did not need the drive

The reproduction gate compares two numbers that are **not the same statistic**:

| | Stage 2A reference | Stage 2B observed |
|---|---|---|
| code | `pathways/geometry.py::batched_projection` | `stage2b/rank_aware_scores.py::project` |
| estimator | ridge normal equations, `λ = 1e-6·σ_max²` | exact orthogonal projection |
| rank handling | **none** — every column kept, shrunk | **truncates** at `s ≤ s₀·1e-8` |
| ranked by | residual norm | residual energy |

Norm versus energy is monotone and cannot move an `argmin`. The other two rows can, and do:
for `σᵢ/σ_max ∈ (1e-8, 1e-3)` — a five-decade band — the ridge shrinks a singular direction away
while the projector keeps it in full.

Measured against the frozen roundoff floor `1000·eps₆₄ = 2.220e-13`:

- same estimator, five independent LAPACK backends: **≤ 1.69e-13** (0.76× the floor)
- same estimator, batched+einsum vs single+matmul: **6.28e-16** (2.8 ULP, 0.003× the floor)
- ridge vs exact projection at condition 1e2 / 3e2 / 1e3: **8.2e-7 / 6.5e-5 / 2.2e-3**
  (3.7e6× / 2.9e8× / 1.0e10× the floor)

Real numerical noise sits inside the floor; the estimator difference exceeds it by six to ten
orders of magnitude. A margin that large cannot satisfy `margin ≤ tie_tolerance`.

**So the single flipped episode is indicated to be an implementation difference, not a
floating-point tie.** `FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH` is deliberately *withheld*:
`BLOCKED_INPUT_PROVENANCE` outranks it, and issuing a FAIL over inputs that could not be verified
would be the same error as issuing a PASS over them.

Note that `rank_aware_scores`' own docstring claims `raw_projection_residual` "is exactly the
frozen Stage 2A score". On this reading it is not, and that claim is what let the gate be
interpreted as a 2.38 % near-miss on a tolerance rather than as a change of estimator.

## The prediction that settles it

A calibrated serial-chain simulation at the real difficulty (top-1 ≈ 0.58–0.65) gives the
episode-level disagreement rate between the two estimators against dictionary conditioning:

| cond(D) | ≤1e2 | 3e2 | 1e3 | 1e4 |
|---|---|---|---|---|
| episode flips | 0.0 % | 0.7 % | 20.3 % | 37.3 % |

Observed: **1 of 72 = 1.4 %**. Consistent with conditioning of order 1e2–1e3; strongly inconsistent
with ≥1e4. `stage2a_dictionary_spectrum.csv` and `stage2b_rank_audit.csv` decide it directly once
the drive is back.

## To finish

```
run_stage2br_audit.py --config configs/stage2br_reproduction_gate.yaml \
  --storage-root /mnt/g/CERTO-FDI --run-id <RUN_ID> --repo-root <worktree>
```

Phase 0 verifies the hashes; Phases 2/4/5 extract the per-window scores and classify the flipped
episode against the envelope frozen in `a4e2b17`. See `docs_pointer/STAGE2BR_PROTOCOL.md`.
