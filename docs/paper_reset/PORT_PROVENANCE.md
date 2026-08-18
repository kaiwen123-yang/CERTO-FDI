# PORT_PROVENANCE — CERTO-FDI Paper Reset

Contract: `contracts/paper_reset/15_GIT_STORAGE_AND_PR_PLAN.md`
> 只选择性迁移必要的数据接口、评价和模型代码，并建立 `PORT_PROVENANCE.md`

This file is the complete, append-only record of every line of code carried into
`stage/paper-reset-literature-public-benchmarks` from the historical Draft-PR
branches. It exists so a reviewer can tell, for any module in
`src/certo_fdi_reset/`, whether it is new work or a port — and if a port, exactly
which commit it came from and what was changed.

## Branch base

| Item | Value |
|---|---|
| Base | `origin/main` @ `37f81d7` (`chore: bootstrap CERTO-FDI stage1 repository`) |
| Branch | `stage/paper-reset-literature-public-benchmarks` |
| Created | 2026-08-18 |

The branch was cut from `main`, **not** from any stage branch. `main` at `37f81d7`
carries only the bare repository skeleton (packaging, CI, hygiene gate, a single
import test) — none of the Stage 1/1R/2A/2B code. Everything under
`src/certo_fdi/` therefore has to be an explicit, recorded port.

## Donor branches (read-only; never merged, never rewritten)

| PR | Branch | Head | Status |
|---|---|---|---|
| #1 | `stage/stage1-closedloop-certificate` | `07850ef` | Draft, untouched |
| #2 | `stage/stage1r-ligra-representation` | `4e94370` | Draft, untouched |
| #3 | `stage/stage1r-b-equivariant-capacity-audit` | `11134fb` | Draft, untouched |
| #4 | `stage/stage2a-chain-jacobian-pathway-audit` | `bcf2ad5` | Draft, untouched |
| #5 | `stage/stage2b-contact-loadpath-sequential-calibration` | `7b8ecd8` | Draft, untouched |
| #6 | `stage/stage2b-r-reproduction-gate-resolution` | `9d8d472` | Draft, untouched |
| #7 | `stage/stage2b-f-estimator-harmonization` | `52c849b` | Draft, untouched |

No `git merge`, `git cherry-pick`, `push --force`, or branch-head move touches any
of these. Ports are performed by copying file content and rewriting it under
`src/certo_fdi_reset/`, so the donor history stays independent.

## Ported so far

**Phase 0: nothing.** `src/certo_fdi_reset/` currently contains only code written
for this round (`decision.py`, `config.py`, `paths.py`, `provenance.py`).

## Port allowlist (permitted when the phase needs them)

Each of these is *candidate* for porting; nothing is pre-approved, and each
actual port gets a row in the ledger below.

| Donor module | Purpose here | Phase |
|---|---|---|
| `certo_fdi/data/windows.py` | episode-safe windowing | B2 |
| `certo_fdi/data/splits.py` | episode/operation-level split machinery | B0 |
| `certo_fdi/anomaly/gaussian_head.py` | shared anomaly head across candidates | B2/C |
| `certo_fdi/anomaly/calibration.py` | context calibration (C5) | E |
| `certo_fdi/anomaly/event_detection.py` | event/episode aggregation, detection delay | E |
| `certo_fdi/experiments/evaluation.py` | AUROC/AUPRC/FPR\@TPR90 metric code | E |
| `certo_fdi/models/ligra_chain.py` | `chain_gnn_aug` topology candidate | C |
| `certo_fdi/models/common.py`, `features.py` | shared layers/feature plumbing | C |

## Port denylist (forbidden this round)

These are simulation-only and would violate
`13_CANDIDATE_MODEL_ADAPTER_PROTOCOL.md` §3 or `03_SCOPE_AND_CLAIM_FREEZE.md` §1
if they touched public-dataset code paths:

- `certo_fdi/dynamics/**` — MuJoCo/Pinocchio backends, RNEA, nominal model.
  Public datasets have no audited URDF/inertia; running these on them would be
  invented physics. Only reachable if a dataset is graded `P3_FULL_DYNAMICS_METADATA`.
- `certo_fdi/data/fault_injection.py`, `certo_fdi/data/franka_generator.py` —
  simulation fault injection is explicitly out of scope.
- `certo_fdi/geometry/**` — SE(3)/frame reparameterisation tied to the internal
  Franka model; only reachable under a `P2`/`P3` applicability finding.
- `certo_fdi/localization/**` — contact/link localisation; Stage 2B-F closed this
  at `NO_GO_CONTACT_PRODUCT` and that verdict is not revisitable here.
- `certo_fdi/models/ligra_*` typed/equivariant variants — Stage 1R-B closed these
  at `FINAL_NO_GO_LIE_MAIN_CONTRIBUTION`.

## Port rules

1. A port copies content into `src/certo_fdi_reset/`; it never imports from
   `certo_fdi` at runtime, so the public-benchmark stage cannot silently pick up
   simulation defaults.
2. Every port records: donor branch, donor commit SHA, donor path, SHA256 of the
   donor file at that commit, destination path, and a summary of modifications.
3. Any numeric constant that came from the internal Franka model is stripped and
   replaced by a value read from public dataset metadata, or the port is refused.
4. Ports land in their own commit, separate from new work.

## Port ledger

| Date | Donor branch | Donor SHA | Donor path | Donor file SHA256 | Destination | Modifications |
|---|---|---|---|---|---|---|
| _(none yet)_ | | | | | | |
