# CERTO-FDI

**Stage 2A: chain-structured healthy residual learning and joint–Cartesian fault-pathway
geometry audit (7-DoF Franka Emika Panda, simulation).**

## Scientific status

- Frozen main baseline: **`chain_gnn_aug`** (chain-structured healthy residual correction).
- Frozen historical conclusions, **not reopened in this stage**:
  - mechanical faults do *not* break per-link frame/gauge covariance — healthy and faulty
    samples obey the same `Ad`/`Ad^{-T}` laws (Stage 1R R0);
  - the Stage 1 strict set-certificate route is **NO-GO**;
  - LiGRA-v1 is **0/4 value axes** (Stage 1R, Draft PR #2);
  - after information, parameter and tuning-budget matching, LiGRA-v2-Typed still trails
    `chain_gnn_aug` — **`FINAL_NO_GO_LIE_MAIN_CONTRIBUTION`** (Stage 1R-B, Draft PR #3).
  - Lie groups, spatial vectors, adjoint/coadjoint transport and RNEA remain the *correctness
    basis* of the geometric dynamics, **not** a fault score and not the paper's main claim.
- This stage answers exactly one question: with `chain_gnn_aug` frozen as the healthy-residual
  front end, does an **explicitly constructed joint–Cartesian fault-pathway geometry**
  (per-link `J^T` contact dictionaries plus actuator / friction / load / sensor / delay
  sensitivity dictionaries) measurably improve fault detection, coarse attribution, link
  localization, rejection and trajectory-conditioned interpretability over the purely neural
  residual?
- Candidate novelty status until both experiment and literature support it:
  **`PLAUSIBLY_OPEN / NOT_ESTABLISHED`**. Forbidden claims are listed in
  `configs/stage2a_pathway_audit.yaml::claims.forbidden`.

## What lives where

| Content | Location |
|---|---|
| Active code, tests, configs, CI, `.venv` | this repository (Linux-local worktree) |
| Research documents, decisions, claim ledgers | `/mnt/g/CERTO-FDI/02_research_docs/stage2a/` |
| Frozen dataset (590 episodes, never regenerated) | `/mnt/g/CERTO-FDI/03_data/stage1r/pilot_seed260815/` |
| Run outputs, checkpoints, CSV/JSON, figures, logs | `/mnt/g/CERTO-FDI/04_runs/stage2a_chain_jacobian_pathway/<RUN_ID>/` |
| Reference copies of accepted results | `/mnt/g/CERTO-FDI/05_reference_results/stage2a/<RUN_ID>/` |
| Thin/Full review packages | `/mnt/g/CERTO-FDI/06_review_exchange/to_review/{thin,full}/` |

No data, checkpoint, result CSV, figure or review ZIP is ever committed to Git
(`scripts/check_repo_hygiene.sh` enforces this).

## Pipeline

```
proprioceptive signals
  -> RNEA / momentum residual
  -> frozen chain_gnn_aug healthy residual correction
  -> corrected joint residual  e_tau = tau_meas - tau_nom - d_chain
  -> context-conditional whitening  z_W = Sigma_0(C_W)^{-1/2} (E_W - mu_0(C_W))
  -> F1-F6 joint-Cartesian fault-pathway dictionaries  Dbar_j,W = W_0 D_j,W
  -> geometry scores / pathway projection / ambiguity metrics
  -> detection, coarse attribution, link localization, rejection
  -> trajectory-conditioned diagnosability audit
```

The healthy correction never sees `tau_meas`, `e_tau`, a fault label, a fault severity, a
fault location or a truth-only simulator state; `tau_meas` appears only as a training target
and in the final residual (`tests/test_stage2a_no_leakage.py`).

## Running

```bash
make venv && make install
make test                              # offline unit tests
RUN_ID=run_<UTC>_<sha> make freeze      # Phase 0: environment, data and provenance freeze
RUN_ID=... make baseline                # Phase 2: frozen chain_gnn_aug reproduction gate
RUN_ID=... make dictionaries            # Phase 3/4: pathway dictionaries + correctness tests
RUN_ID=... make ablations               # Phase 5
RUN_ID=... make metrics                 # Phase 6
RUN_ID=... make decide                  # Phase 7 (pre-registered rules)
RUN_ID=... make review-packages         # Phase 8
```

`CERTO_STORAGE_ROOT` (or `--storage-root`) must point at `/mnt/g/CERTO-FDI`; persistent
outputs are refused inside the Git worktree.

## Provenance

- `docs_pointer/STAGE2A_PORT_PROVENANCE.md` — every ported file, its source commit and hash,
  whether it was copied verbatim, and what was deliberately **not** ported.
- `docs_pointer/STAGE2A_PROTOCOL.md` — the frozen Stage 2A protocol and decision rules.
- `src/certo_fdi/experiments/decision_stage2a.py` — the pre-registered decision code,
  committed before any Stage 2A model result existed.
