# Stage 2A port provenance

Every file below was taken from the **frozen** Stage 1R-B branch
`stage/stage1r-b-equivariant-capacity-audit` @ `11134fb695b1c70c9664150d8d70a9670b95de51` (Draft PR #3, decision
`FINAL_NO_GO_LIE_MAIN_CONTRIBUTION`). PR #1/#2/#3 are historical negative/audit results:
they stay Draft, are never merged, never force-pushed and never rewritten. Stage 2A only
*reads* their code and provenance.

`source_sha256` is the hash of the file **in the source branch**; `new_sha256` is the hash of
the file as it now stands in this worktree. They are equal exactly for the verbatim copies,
which is how a reviewer can check that nothing was silently edited.

## Ported files

| # | source path | new path | verbatim | reason / modification | tests | source sha256 | new sha256 |
|---|---|---|---|---|---|---|---|
| 1 | `.github/workflows/ci.yml` | `.github/workflows/ci.yml` | yes | CI runs the same offline unit tests | CI | `6b19d7c1d78b84dc` | `6b19d7c1d78b84dc` |
| 2 | `.gitignore` | `.gitignore` | **no** | add Stage 2A artefact patterns | scripts/check_repo_hygiene.sh | `f30fd765723b2059` | `89de85ab83ac4056` |
| 3 | `Makefile` | `Makefile` | **no** | Stage 2A targets | make test | `4eaf31678bd35d14` | `a6db98d7ca79d8fd` |
| 4 | `pyproject.toml` | `pyproject.toml` | **no** | package name/description unchanged, Stage 2A description | pip install -e . | `b5b3bb97915aea2e` | `9a868fe4f72be721` |
| 5 | `scripts/check_repo_hygiene.sh` | `scripts/check_repo_hygiene.sh` | yes | same no-large-artefact policy | manual | `907aceff20b7bae5` | `907aceff20b7bae5` |
| 6 | `configs/paths.example.env` | `configs/paths.example.env` | yes | same storage-root contract | tests/test_paths.py | `e2995a5b0955ba59` | `e2995a5b0955ba59` |
| 7 | `tests/conftest.py` | `tests/conftest.py` | yes | same offline/slow markers | pytest | `f12744a33b40c7c4` | `f12744a33b40c7c4` |
| 8 | `src/certo_fdi/geometry/__init__.py` | `src/certo_fdi/geometry/__init__.py` | yes | verified in PR #2/#3 R0 | tests/test_se3.py | `4cfd89caf93cd28c` | `4cfd89caf93cd28c` |
| 9 | `src/certo_fdi/geometry/se3.py` | `src/certo_fdi/geometry/se3.py` | yes | verified SE(3)/Ad implementation | tests/test_se3.py | `47ce978e4e0427c3` | `47ce978e4e0427c3` |
| 10 | `src/certo_fdi/geometry/spatial_types.py` | `src/certo_fdi/geometry/spatial_types.py` | yes | verified spatial inertia / type algebra | tests/test_se3.py | `420934b7f3b0ee47` | `420934b7f3b0ee47` |
| 11 | `src/certo_fdi/geometry/torch_ops.py` | `src/certo_fdi/geometry/torch_ops.py` | yes | verified torch adjoints | tests/test_dynamics_7dof.py | `cbc2ea9dc0ec8565` | `cbc2ea9dc0ec8565` |
| 12 | `src/certo_fdi/geometry/frame_reparameterization.py` | `src/certo_fdi/geometry/frame_reparameterization.py` | yes | legal link-frame sampling used by chain_gnn_aug training | tests/test_frame_reparameterization.py | `b9e8ef3dc22a34c6` | `b9e8ef3dc22a34c6` |
| 13 | `src/certo_fdi/dynamics/__init__.py` | `src/certo_fdi/dynamics/__init__.py` | yes | verified | tests/test_dynamics_7dof.py | `01ff18c4e9e8c8ca` | `01ff18c4e9e8c8ca` |
| 14 | `src/certo_fdi/dynamics/chain_model.py` | `src/certo_fdi/dynamics/chain_model.py` | yes | verified serial-chain description (Jacobian source of truth) | tests/test_dynamics_7dof.py, tests/test_stage2a_jacobians.py | `c0bbc0762d709c9f` | `c0bbc0762d709c9f` |
| 15 | `src/certo_fdi/dynamics/rnea.py` | `src/certo_fdi/dynamics/rnea.py` | yes | verified NumPy RNEA | tests/test_rnea_2r_oracle.py | `6bc87280b72c6bc9` | `6bc87280b72c6bc9` |
| 16 | `src/certo_fdi/dynamics/rnea_torch.py` | `src/certo_fdi/dynamics/rnea_torch.py` | yes | verified batched typed RNEA front end | tests/test_dynamics_7dof.py | `a76daa5016ff6572` | `a76daa5016ff6572` |
| 17 | `src/certo_fdi/dynamics/mujoco_backend.py` | `src/certo_fdi/dynamics/mujoco_backend.py` | yes | frozen truth plant + MJCF audit | tests/test_dynamics_7dof.py | `6d27b3cd428a8784` | `6d27b3cd428a8784` |
| 18 | `src/certo_fdi/dynamics/pinocchio_backend.py` | `src/certo_fdi/dynamics/pinocchio_backend.py` | yes | independent RNEA cross-check | tests/test_dynamics_7dof.py | `8d594d8fbdebb782` | `8d594d8fbdebb782` |
| 19 | `src/certo_fdi/dynamics/nominal_model.py` | `src/certo_fdi/dynamics/nominal_model.py` | yes | nominal torque used by tau_nominal and controllers | tests/test_dynamics_7dof.py | `a9627bbdc0758907` | `a9627bbdc0758907` |
| 20 | `src/certo_fdi/dynamics/lagrange_reference.py` | `src/certo_fdi/dynamics/lagrange_reference.py` | yes | 2R closed-form oracle for the RNEA unit test | tests/test_rnea_2r_oracle.py | `1c5be5ddbf1c2e6e` | `1c5be5ddbf1c2e6e` |
| 21 | `src/certo_fdi/data/__init__.py` | `src/certo_fdi/data/__init__.py` | yes | verified | tests/test_data_pipeline.py | `334839a03ba6b617` | `334839a03ba6b617` |
| 22 | `src/certo_fdi/data/schema.py` | `src/certo_fdi/data/schema.py` | yes | frozen episode schema; must not change | tests/test_data_pipeline.py | `0bc3e099268ad16a` | `0bc3e099268ad16a` |
| 23 | `src/certo_fdi/data/episode_io.py` | `src/certo_fdi/data/episode_io.py` | yes | frozen HDF5 layout | tests/test_data_pipeline.py | `ffe3d9ab4a8f51e0` | `ffe3d9ab4a8f51e0` |
| 24 | `src/certo_fdi/data/splits.py` | `src/certo_fdi/data/splits.py` | yes | frozen S0-S4 split logic + leakage report | tests/test_data_pipeline.py | `19ed8fa8510fe892` | `19ed8fa8510fe892` |
| 25 | `src/certo_fdi/data/windows.py` | `src/certo_fdi/data/windows.py` | **no** | add tau_cmd to SIGNAL_KEYS (controller's own command, needed by the F1/F6 pathway dictionaries) and expose window time indices | tests/test_stage2a_no_leakage.py | `31a8e797303936ea` | `9770be180d9f3735` |
| 26 | `src/certo_fdi/data/controllers.py` | `src/certo_fdi/data/controllers.py` | yes | frozen controllers, needed for closed-loop F5/F6 sensitivities | tests/test_stage2a_sensitivity.py | `40aee43910013cf7` | `40aee43910013cf7` |
| 27 | `src/certo_fdi/data/trajectories.py` | `src/certo_fdi/data/trajectories.py` | yes | frozen trajectory generator (closed-loop replay) | tests/test_stage2a_sensitivity.py | `60f4ff5094abc13e` | `60f4ff5094abc13e` |
| 28 | `src/certo_fdi/data/fault_injection.py` | `src/certo_fdi/data/fault_injection.py` | yes | frozen fault hooks; the pathway dictionaries are validated against these | tests/test_stage2a_sensitivity.py | `811a8191df137294` | `811a8191df137294` |
| 29 | `src/certo_fdi/data/franka_generator.py` | `src/certo_fdi/data/franka_generator.py` | yes | frozen episode generator; replayed (never regenerated into the dataset) for closed-loop sensitivities | tests/test_stage2a_sensitivity.py | `50fdfa9c8c73e463` | `50fdfa9c8c73e463` |
| 30 | `src/certo_fdi/models/__init__.py` | `src/certo_fdi/models/__init__.py` | yes | verified | tests/test_import.py | `f04a17c4f334b523` | `f04a17c4f334b523` |
| 31 | `src/certo_fdi/models/common.py` | `src/certo_fdi/models/common.py` | yes | Standardizer/mlp shared by the chain models | tests/test_models_and_heads.py | `a5a51fc6e5e330b3` | `a5a51fc6e5e330b3` |
| 32 | `src/certo_fdi/models/features.py` | `src/certo_fdi/models/features.py` | **no** | keep only the raw (chain-GNN) feature path + link descriptors; the LiGRA invariant feature list is retained unused for the R0 cross-check and marked historical | tests/test_stage2a_no_leakage.py | `bbc1a694eb090c90` | `e4ea5279375cd256` |
| 33 | `src/certo_fdi/models/scalar_temporal_encoder.py` | `src/certo_fdi/models/scalar_temporal_encoder.py` | yes | chain-recursive GRU encoder of chain_gnn_aug | tests/test_models_and_heads.py | `98381a21e831419f` | `98381a21e831419f` |
| 34 | `src/certo_fdi/anomaly/__init__.py` | `src/certo_fdi/anomaly/__init__.py` | yes | verified | tests/test_import.py | `4cceb852ab637e9b` | `4cceb852ab637e9b` |
| 35 | `src/certo_fdi/anomaly/gaussian_head.py` | `src/certo_fdi/anomaly/gaussian_head.py` | yes | frozen conditional-Gaussian healthy density (identical head for every representation) | tests/test_models_and_heads.py | `e70e1856c7c02ae2` | `e70e1856c7c02ae2` |
| 36 | `src/certo_fdi/anomaly/calibration.py` | `src/certo_fdi/anomaly/calibration.py` | yes | healthy-only threshold protocol | tests/test_models_and_heads.py | `c88a984c1e33989a` | `c88a984c1e33989a` |
| 37 | `src/certo_fdi/anomaly/event_detection.py` | `src/certo_fdi/anomaly/event_detection.py` | yes | frozen window/event metric definitions | tests/test_models_and_heads.py | `70343b360656f2b5` | `70343b360656f2b5` |
| 38 | `src/certo_fdi/anomaly/gmo.py` | `src/certo_fdi/anomaly/gmo.py` | yes | generalised momentum observer (physics baseline) | tests/test_data_pipeline.py | `3113b03143edeb75` | `3113b03143edeb75` |
| 39 | `src/certo_fdi/localization/__init__.py` | `src/certo_fdi/localization/__init__.py` | yes | verified | tests/test_import.py | `1be2b9db158fbd30` | `1be2b9db158fbd30` |
| 40 | `src/certo_fdi/localization/link_scores.py` | `src/certo_fdi/localization/link_scores.py` | yes | frozen top-k / chain-distance metrics | tests/test_counterfactual_localization.py | `b9df6b3ec26f67cd` | `b9df6b3ec26f67cd` |
| 41 | `src/certo_fdi/localization/counterfactual.py` | `src/certo_fdi/localization/counterfactual.py` | yes | frozen Stage 1R-B primary localizer (baseline reproduction) | tests/test_counterfactual_localization.py | `88e92c1ab1aee186` | `a8e03addb636f5b3` |
| 42 | `src/certo_fdi/localization/fewshot_head.py` | `src/certo_fdi/localization/fewshot_head.py` | yes | secondary supervised attribution only | tests/test_models_and_heads.py | `b336318727d1498e` | `b336318727d1498e` |
| 43 | `src/certo_fdi/experiments/__init__.py` | `src/certo_fdi/experiments/__init__.py` | yes | verified | tests/test_import.py | `3916b4a5b437f59b` | `3916b4a5b437f59b` |
| 44 | `src/certo_fdi/experiments/common.py` | `src/certo_fdi/experiments/common.py` | yes | config loading, sha256, environment capture, CSV/JSON writers | tests/test_paths.py | `54fea1ff56a261b2` | `54fea1ff56a261b2` |
| 45 | `src/certo_fdi/experiments/pipeline.py` | `src/certo_fdi/experiments/pipeline.py` | **no** | import build_model from models.chain_gnn (LiGRA module not ported); everything else verbatim | tests/test_models_and_heads.py | `cea654217b7813c9` | `e0f4ca058b8c480a` |
| 46 | `src/certo_fdi/experiments/r0_model_covariance.py` | `src/certo_fdi/experiments/r0_model_covariance.py` | yes | tool_chain helper used by the evaluation path | tests/test_dynamics_7dof.py | `a8f8a2c4270501e7` | `a8f8a2c4270501e7` |
| 47 | `src/certo_fdi/experiments/evaluation.py` | `src/certo_fdi/experiments/evaluation.py` | **no** | import from models.chain_gnn; otherwise verbatim (frozen metric definitions) | tests/test_models_and_heads.py | `24b858738bb3457b` | `24b858738bb3457b` |
| 48 | `src/certo_fdi/experiments/evaluation_stage1rb.py` | `src/certo_fdi/experiments/evaluation_chain_baseline.py` | **no** | renamed; imports run_front_end from models.chain_gnn; used only to reproduce the frozen baseline | stage2a_baseline_reproduction.csv | `862135657ba334f7` | `3d47f63f1fba4a34` |
| 49 | `src/certo_fdi/experiments/physics_baselines.py` | `src/certo_fdi/experiments/physics_baselines.py` | yes | rnea_threshold / momentum-residual baselines | tests/test_models_and_heads.py | `74903ada04d1db09` | `74903ada04d1db09` |
| 50 | `src/certo_fdi/experiments/precompute_gmo.py` | `src/certo_fdi/experiments/precompute_gmo.py` | yes | reads the already-appended r_gmo column; never re-appends (dataset is frozen) | manual | `803b381cae6a2db1` | `803b381cae6a2db1` |
| 51 | `src/certo_fdi/packaging/__init__.py` | `src/certo_fdi/packaging/__init__.py` | yes | verified | tests/test_import.py | `452f2860608389d0` | `452f2860608389d0` |
| 52 | `src/certo_fdi/packaging/validate_review_package.py` | `src/certo_fdi/packaging/validate_review_package.py` | yes | frozen package validator (CRC, SHA, topology, secrets) | tests/test_review_package.py | `8ab2c74db21c9846` | `521cec07a578657d` |
| 53 | `src/certo_fdi/packaging/build_review_package.py` | `src/certo_fdi/packaging/build_review_package.py` | yes | generic Thin/Full builder; Stage 2A adds its own manifest layer | tests/test_review_package.py | `8bf7d208372761fa` | `8bf7d208372761fa` |
| 54 | `src/certo_fdi/__init__.py` | `src/certo_fdi/__init__.py` | yes | package root | tests/test_import.py | `030840b87b2b197a` | `030840b87b2b197a` |
| 55 | `src/certo_fdi/paths.py` | `src/certo_fdi/paths.py` | **no** | STAGE and RUN_SUBDIRECTORIES retargeted to Stage 2A phases | tests/test_paths.py | `c56a8cd4d526fd6a` | `8c21b483a1379301` |
| 56 | `tests/test_import.py` | `tests/test_import.py` | yes | package import smoke test | self | `491c04b0d062d895` | `491c04b0d062d895` |
| 57 | `tests/test_paths.py` | `tests/test_paths.py` | yes | external-storage discipline | self | `d3ef7dd7c02ce972` | `f087bd1881fb02b5` |
| 58 | `tests/test_se3.py` | `tests/test_se3.py` | yes | SE(3)/adjoint correctness | self | `008140bcfc0b1e06` | `008140bcfc0b1e06` |
| 59 | `tests/test_dynamics_7dof.py` | `tests/test_dynamics_7dof.py` | yes | MuJoCo/Pinocchio/RNEA cross-check | self | `e09953407bf4ed6a` | `e09953407bf4ed6a` |
| 60 | `tests/test_rnea_2r_oracle.py` | `tests/test_rnea_2r_oracle.py` | yes | closed-form 2R oracle | self | `c44176a504ec1d8b` | `c44176a504ec1d8b` |
| 61 | `tests/test_data_pipeline.py` | `tests/test_data_pipeline.py` | yes | episode IO / splits / leakage report | self | `aea748416f3efbae` | `8b7045ee8ca87940` |
| 62 | `tests/test_frame_reparameterization.py` | `tests/test_frame_reparameterization.py` | yes | legal frame sampling | self | `3c7e3182a072dc79` | `3c7e3182a072dc79` |
| 63 | `tests/test_counterfactual_localization.py` | `tests/test_counterfactual_localization.py` | yes | frozen localizer metrics | self | `b7799ada3bebba8c` | `2d45db3f161b965c` |
| 64 | `tests/test_review_package.py` | `tests/test_review_package.py` | yes | package validator | self | `a0a84212e6a4dcfa` | `a0a84212e6a4dcfa` |
| 65 | `tests/test_models_and_heads.py` | `tests/test_models_and_heads.py` | **no** | LiGRA-specific cases removed; chain_gnn / rnea_gru / head cases kept | self | `b661c9c8513c78c7` | `9029828a97065cee` |
| 66 | `configs/stage1r_pilot.yaml` | `configs/frozen_dataset_protocol.yaml` | yes | the frozen config that GENERATED the 590-episode dataset; kept read-only for provenance and for the closed-loop oracle replay | tests/test_stage2a_replay.py | `n/a` | `d9cfd05b71d53d0d` |
| 67 | `configs/stage1r_smoke.yaml` | `configs/frozen_dataset_protocol_smoke.yaml` | yes | smoke variant used by tests/test_data_pipeline.py | tests/test_data_pipeline.py | `n/a` | `4ec4ea9911dc8372` |
| 68 | `src/certo_fdi/models/ligra_chain.py (ChainGNN / JointSpaceCorrection / RNEAOnly / run_front_end / backward_recursion / typed_link_features only)` | `src/certo_fdi/models/chain_gnn.py` | **no** | re-homed verbatim so the frozen chain_gnn_aug checkpoints load bit-for-bit; the LiGRA-v1 class, the covariant basis and the LiGRA build_model entries are NOT ported | tests/test_models_and_heads.py, tests/test_counterfactual_localization.py, stage2a_baseline_reproduction.csv | `n/a` | `6decd8b20af38739` |

## Deliberately NOT ported

| source | why |
|---|---|
| `src/certo_fdi/models/ligra_chain.py` | LiGRA-v1 model (frozen NO-GO). Its ChainGNN/JointSpaceCorrection/RNEAOnly classes are re-homed verbatim in models/chain_gnn.py; the LiGRA class itself is not ported. |
| `src/certo_fdi/models/ligra_v2_typed.py` | LiGRA-v2-Typed (frozen FINAL_NO_GO_LIE_MAIN_CONTRIBUTION) |
| `src/certo_fdi/models/typed_channels.py` | LiGRA-v2 typed channels |
| `src/certo_fdi/models/typed_equivariant_layers.py` | LiGRA-v2 typed layers |
| `src/certo_fdi/models/typed_temporal.py` | LiGRA-v2 typed temporal block |
| `src/certo_fdi/models/covariant_basis.py` | LiGRA-v1 covariant wrench basis (RETIRED_BASIS_V1) |
| `src/certo_fdi/models/basis_capacity_audit.py` | Stage 1R-B Phase A basis audit (closed) |
| `src/certo_fdi/experiments/decision.py` | Stage 1R decision rules (different vocabulary) |
| `src/certo_fdi/experiments/decision_stage1rb.py` | Stage 1R-B decision rules (different vocabulary) |
| `src/certo_fdi/experiments/run_stage1r*.py` | Stage 1R/1R-B runners (LiGRA pipeline) |
| `src/certo_fdi/experiments/stage1rb_common.py` | Stage 1R-B runner plumbing; Stage 2A has its own (stage2a_common.py) without the LiGRA model list |
| `src/certo_fdi/experiments/run_r0_geometry.py` | Stage 1R R0 runner (frame-drift value axis retired) |
| `src/certo_fdi/experiments/make_figures*.py` | stage-specific figures |
| `src/certo_fdi/packaging/build_review_package_stage1rb.py` | stage-specific package builder |
| `src/certo_fdi/experiments/run_generate_data.py` | data generation (dataset is frozen and must not be regenerated) |
| `tests/test_ligra_v2_invariance.py` | LiGRA-v2 test |
| `tests/test_typed_layers_covariance.py` | LiGRA-v2 test |
| `tests/test_basis_gram_invariance.py` | LiGRA-v1 basis test |
| `tests/test_stage1rb_*.py` | Stage 1R-B contract tests (replaced by Stage 2A equivalents) |
| `internal wrench anomaly head` | never ported: network-internal messages are not physical wrenches |
| `frame-drift-as-detection-value logic` | never ported: frame consistency is an implementation property |

## New in Stage 2A (no ancestor)

| path | purpose |
|---|---|
| `src/certo_fdi/pathways/jacobians.py` | per-link / per-point Jacobians of the frozen chain (checked against MuJoCo `mj_jac` / `mj_applyFT`) |
| `src/certo_fdi/pathways/dictionaries.py` | F1-F6 fault-pathway window dictionaries |
| `src/certo_fdi/pathways/whitening.py` | context-conditional healthy whitening of the window residual |
| `src/certo_fdi/pathways/geometry.py` | ridge projections, principal angles, Fisher information, ee/null split |
| `src/certo_fdi/pathways/sensitivity.py` | closed-loop oracle finite differences through the frozen truth simulator |
| `src/certo_fdi/pathways/localization.py` | zero-shot per-link contact localization with rejection |
| `src/certo_fdi/pathways/fusion.py` | the small auditable fusers used by the ablations |
| `src/certo_fdi/experiments/decision_stage2a.py` | pre-registered decision rules (committed before any result) |
| `src/certo_fdi/experiments/stage2a_*.py` | Stage 2A phase runners |
| `configs/stage2a_pathway_audit.yaml` | frozen Stage 2A protocol and decision thresholds |

