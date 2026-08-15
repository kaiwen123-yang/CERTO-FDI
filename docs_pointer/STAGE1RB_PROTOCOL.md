# Stage 1R-B — typed-equivariant capacity audit (LiGRA-v2-Typed) — protocol pointer

Stacked on `stage/stage1r-ligra-representation` (PR #2, Draft, untouched). This branch adds an
incremental audit; it never modifies the Stage 1R pilot data, results or the PR #2 decision
(`NO_GO_LIE_MAIN_CONTRIBUTION` for LiGRA-v1 stays valid).

## Frozen inputs (hashes verified at start-up)

| input | SHA256 |
|---|---|
| Stage 1R-B kickoff ZIP `CERTO_FDI_STAGE1RB_EQUIVARIANT_CAPACITY_KICKOFF_20260815.zip` | `6793482a351f6eb8d4a48d6cda5ad140395b138b3520b479f89ec1ea779dd7e1` |
| Stage 1R pilot FULL review package | `5512cbac03c8bd5e8babcd86dd63ebb5b91bd82a1e77acabdb2c63104a833192` |
| pilot data-generating config (`4280d2f:configs/stage1r_pilot.yaml` = `dataset_manifest.json:config_sha256`) | `24e57b244e83ddc647bccbd978f457947e9c5d632768a0d6e3780d8358ce1ea3` |
| Franka MJCF `panda_nohand.xml` (menagerie da76818) | `e7090a5e2384b18a223ef532d98bf914f7f9a6b74dc8bc9f74c8291201074071` |

Contracts (frozen, not committed): `G:/CERTO-FDI/01_frozen_sources/extracted/CERTO_FDI_STAGE1RB_EQUIVARIANT_CAPACITY_KICKOFF_20260815_6793482a/`
(`03_SCOPE_AND_BASELINE_FREEZE.md`, `04_TYPED_EQUIVARIANT_ARCHITECTURE_CONTRACT.md`,
`05_CAPACITY_AUDIT_AND_ORACLE_PROTOCOL.md`, `06_FAIR_TUNING_AND_EVALUATION_PROTOCOL.md`,
`07_DECISION_RULES.md`, `08_REPOSITORY_STORAGE_AND_PR_PLAN.md`, `09_REVIEW_PACKAGE_CONTRACT.md`).

## Single question

After matching input information, parameter count, healthy training data, time window, anomaly
head and tuning budget: does `ligra_v2_typed` (exact link-frame typed equivariance, full
scalar/twist/wrench information) produce real value over `chain_gnn_aug` (non-equivariant chain
GNN with random legal frame augmentation) on unseen configurations, healthy sample efficiency,
context shift and localization? Diagnostics only: `rnea_gru`, `ligra_free_output`.

## Phases

- **A** — capacity/conditioning audit of the LiGRA-v1 12-column basis (`certo_fdi.models.basis_capacity_audit`,
  `certo_fdi.experiments.run_stage1rb_basis_audit`): gauge-invariant Gram, oracle torque ceilings
  (basis vs free local wrench, block-tridiagonal exact solves, effective DoF), analytic mismatch
  wrench projection, frozen retirement rules → `RETIRED_BASIS_V1` / `BASIS_CAPACITY_NOT_REJECTED`.
  LiGRA-v1 is not retrained regardless.
- **B** — LiGRA-v2-Typed (`typed_channels`, `typed_equivariant_layers`, `typed_temporal`, `ligra_v2_typed`).
- **R0** — 15-item correctness gate (typed covariance, invariance, leakage, parity) → BLOCKED if any fails.
- **C** — healthy-only fair tuning (8 configs per primary model, seed 260815) → 3 seeds × {0.25, 1.00}.
- **D/E** — four-axis evaluation, counterfactual link masking localization, `decision_stage1rb.py`.

## Data provenance note (recorded in `<RUN_ROOT>/provenance/dataset_verification.json`)

The pilot `episode_index.csv` SHA256 values were recorded at generation time; the PR #2 pipeline
(`precompute_gmo.py`) later appended `signals/r_gmo` to every HDF5 file in place, so the current
bytes differ from the index for every file by construction (episode mtimes 05:05Z, before the PR #2
pass-2 launch at 08:52Z — these are exactly the files the pilot trained on). Stage 1R-B verified
the *content* (schema/finiteness of all 590 files; `tau_nominal` and `r_gmo` re-derived from the
frozen MJCF + config on a stratified sample to ≤4e-6 N m / ≤1e-7) and records a fresh post-GMO
manifest (`episode_sha256_postgmo_manifest.csv`, SHA256 `97add92a9948c5ba5d49242d11252c90678222efef63c51d71a3212fc2186dfb`)
that every result table references as `dataset_sha256_or_manifest_sha`. No data was regenerated.

## Storage

`G:/CERTO-FDI/04_runs/stage1r_b_equivariant_capacity/<RUN_ID>/` (results/, checkpoints/, logs/, figures/, provenance/),
reference copy under `05_reference_results/stage1r_b/`, decision docs under `02_research_docs/stage1r_b/`,
review packages under `06_review_exchange/to_review/{thin,full}/`.
