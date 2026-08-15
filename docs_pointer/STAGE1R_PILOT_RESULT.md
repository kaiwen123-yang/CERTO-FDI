# Stage 1R pilot result pointer (LiGRA-FDI)

- Run id: `run_20260815T042745Z_stage1r` (profile pilot, git `85b3ed2`, config SHA256 `d9cfd05b…0ff7`)
- Run root: `G:/CERTO-FDI/04_runs/stage1r_ligra/run_20260815T042745Z_stage1r/`
- Reference copy: `G:/CERTO-FDI/05_reference_results/stage1r/run_20260815T042745Z_stage1r/`
- Decision docs: `G:/CERTO-FDI/02_research_docs/stage1r/decisions/`
- Review packages (validated PASS, index in `06_review_exchange/package_index.csv`):
  - THIN `CERTO_FDI_stage1r_ligra_PILOT_20260815T125724Z_85b3ed2_THIN.zip`
    sha256 `dc9eca8b636d7a0e7f18b4b6c184b2966d62ee83bb6289de44f9d75a50ce2111` (4.3 MB)
  - FULL `CERTO_FDI_stage1r_ligra_PILOT_20260815T125724Z_85b3ed2_FULL.zip`
    sha256 `5512cbac03c8bd5e8babcd86dd63ebb5b91bd82a1e77acabdb2c63104a833192` (29.5 MB)

## Decision: `NO_GO_LIE_MAIN_CONTRIBUTION`

Preregistered gates (kickoff 06 §2) applied without retroactive changes. LiGRA won 0/4 value
axes against the strongest matched non-equivariant structured baseline (`chain_gnn_aug`,
frame-augmented chain GNN, identical density head):

| Axis | LiGRA | chain_gnn_aug | Pass |
|---|---|---|---|
| 1 Unseen-configuration anomaly (S1 window AUROC) | 0.561 | 0.647 | no |
| 2 Sample efficiency (AUROC ALL, LiGRA@25 % vs baseline@100 %) | 0.608 | 0.720 | no |
| 3 Localization (top-1 / chain distance) | 0.292 / 1.875 | 0.400 / 1.392 | no |
| 4 Payload/context shift (mean S2,S4 AUROC) | 0.658 | 0.777 | no |

Frame-reparameterization drift ratio (baseline/LiGRA) 1.5e3 — exact covariance confirmed but,
per the hard rules, not evidence of detection value. Healthy-fit rigidity check triggered
(LiGRA RMSE ratio S0 0.60 vs 0.39; the `ligra_free_output` ablation reaches 0.32).

The NO_GO rejects the Lie-group representation as the *main contribution*; it does not reject
manipulator FDI with structured residuals (PIVOT_CHAIN_ONLY candidate: `chain_gnn_aug`).

## Provenance notes
- Pass 1 of the pilot (git `1ba4bc1`) was invalidated by target leakage (measured torque was an
  encoder input of the structured models) and archived under `pass1_leaky_archive/`; pass 2
  (this result) removed torque measurements from all correction inputs.
- Pass 2 was resumed once from per-run JSONs with `OMP_NUM_THREADS=8` because of CPU
  oversubscription by an unrelated host job (compute-resource change only; see
  `decision/KNOWN_ISSUES.md` in the run root).
- The Stage 1 strict-certificate NO-GO (Draft PR #1) was not used as evidence.
