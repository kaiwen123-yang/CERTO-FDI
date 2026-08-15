# Stage 1R-B result pointer (LiGRA-v2-Typed vs chain_gnn_aug)

- Run id: `run_20260815T143902Z_4e94370` (results git `f1b00b5`, packages git `978510f`, config SHA256 `a3f61b9e…f01a`)
- Run root: `G:/CERTO-FDI/04_runs/stage1r_b_equivariant_capacity/run_20260815T143902Z_4e94370/`
- Reference copy: `G:/CERTO-FDI/05_reference_results/stage1r_b/run_20260815T143902Z_4e94370/`
- Decision docs: `G:/CERTO-FDI/02_research_docs/stage1r_b/decisions/`
- Data: frozen Stage 1R pilot (590 episodes, reused; post-GMO manifest SHA256 `97add92a9948c5ba5d49242d11252c90678222efef63c51d71a3212fc2186dfb`)
- Review packages (validated PASS; `06_review_exchange/package_index.csv`):
  - THIN `CERTO_FDI_stage1rb_typed_capacity_AUDIT_20260815T180719Z_978510f_THIN.zip`
    sha256 `96fc8e805a5772a0395771d1277f1867260ea22bbbb6a63b23b6b6da8e5ef6de` (1.95 MB)
  - FULL `CERTO_FDI_stage1rb_typed_capacity_AUDIT_20260815T180719Z_978510f_FULL.zip`
    sha256 `c7e191f518dacedbf9a0e06e03990e490c4fe4b35fc34cf115fe4b84ce3aae76` (18.8 MB)

## Decision: `NO_GO_CURRENT_LIGRA_V1 + FINAL_NO_GO_LIE_MAIN_CONTRIBUTION`

Preregistered rules (kickoff 07, precedence frozen in `decision_stage1rb.py` before any training result).
Gates: provenance PASS, R0 gate PASS (15/15), no leakage, identical input fields, parameter parity
(65,503 vs 63,047), healthy-only tuning (8 configurations each), all 3 seeds × {0.25, 1.0} complete.

| Axis (residual-only head, qdd_est, seed means) | ligra_v2_typed | chain_gnn_aug | Pass |
|---|---|---|---|
| 1 Unseen configuration (S1 window AUROC; FPR@TPR90) | 0.622 (0.887) | 0.674 (0.879) | no |
| 2 Sample efficiency (ALL AUROC v2@25 % vs base@100 %; RMSE S0) | 0.672; 0.447 N m | 0.750; 0.194 N m | no |
| 3 Localization (counterfactual top-1 / chain distance) | 0.247 / 2.05 | 0.294 / 1.79 | no |
| 4 Context shift (mean S2,S4 AUROC; FPR@TPR90) | 0.748 (0.820) | 0.819 (0.663) | no |

Axes won 0/4; the baseline leads by the preregistered margin on axes 1, 2 and 4, on every fault family
(OOD) and on every seed; healthy S0 RMSE 0.237 vs 0.194 N m (ratio 1.22 > 1.10 after fair tuning); frame
drift ratio 3.8e3 (implementation property, not a value axis); `qdd_true` does not change the ordering.

## Phase A: LiGRA-v1 12-column basis → `RETIRED_BASIS_V1` (rules 1, 2, 3 fired)

Rank ≤ 6 pointwise (root link 4; complete wrench span for links 2–7 in most windows) with ≥ 6 exact/stable
null directions per link and an exactly singular coefficient Gram; the inertial truth-vs-nominal mismatch
wrench is spanned exactly (projection residual 1e-14). Oracle A at each oracle's own regularization:
basis 0.119 vs free 0.032 N m (rule 1), but at matched effective DoF (0.2 / observation) the basis is
better (0.119 vs 0.226) and its held-out-timestep prediction is better (0.125 vs 0.197): the retirement is
on redundancy/conditioning grounds, not span capacity.

## Reading

Rejects the typed-equivariant model family (LiGRA-v1 basis head and LiGRA-v2 typed head) as the *main
contribution* under fair conditions; it does not reject manipulator FDI with structured residuals — the
frame-augmented chain GNN (and the free-output ablation) remain the strongest models. Prohibited claims
unchanged (frame drift is not detection value; internal messages are not physical wrenches; `qdd_true`
is diagnostic only). See the known-issues document in the package for the single pre-registered
optimisation fix (invariant child-message gain) and the learning-rate sensitivity of LiGRA-v2.
