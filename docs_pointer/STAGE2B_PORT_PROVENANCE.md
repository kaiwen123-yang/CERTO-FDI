# Stage 2B port provenance

Stage 2B is a **stacked branch**: it branches from
`stage/stage2a-chain-jacobian-pathway-audit` @ `bcf2ad5c978f58dc159636d64d0b5c81efb9e396`
(Draft PR #4, decision `PIVOT_CONTACT_GEOMETRY_ONLY`) rather than copying files out of it. That
is deliberate — the Stage 2A implementation was independently audited at that exact commit, and
a stacked branch keeps the reused code *byte-identical* and reviewable by `git diff` instead of
by hash comparison.

So the "port" here is: **everything from `bcf2ad5` is inherited unchanged unless listed below.**
`git diff bcf2ad5..HEAD` is the complete, authoritative list of what Stage 2B changed. This
document explains each entry and why.

PR #1/#2/#3/#4 stay Draft, are never merged, never force-pushed and never rewritten.

## 1. Inherited unchanged (reused, not copied)

These carry over from `bcf2ad5` with no edit. They were validated by the Stage 2A audit and by
the 100 inherited offline tests, which are re-run in this worktree before any Stage 2B code is
added (Phase 0 requirement §E.5).

| area | modules | what Stage 2B uses it for |
|---|---|---|
| geometry | `geometry/{se3,spatial_types,torch_ops,frame_reparameterization}.py` | SE(3)/adjoint algebra behind the Jacobians |
| dynamics | `dynamics/{chain_model,rnea,rnea_torch,mujoco_backend,pinocchio_backend,nominal_model,lagrange_reference}.py` | frozen 7-DoF chain, RNEA, truth plant |
| data | `data/{schema,episode_io,windows,splits,controllers,trajectories,fault_injection,franka_generator}.py` | frozen episode format, and the generator replayed for the new H80/H160 and F4_CAL episodes |
| encoder | `models/{chain_gnn,common,features,scalar_temporal_encoder}.py` | the **frozen** `chain_gnn_aug` (63,047 params); no new encoder is built |
| anomaly | `anomaly/{gaussian_head,calibration,event_detection,gmo}.py` | the healthy conditional-Gaussian head and the frozen window/event metric definitions |
| pathways | `pathways/{jacobians,dictionaries,whitening,geometry,window_features,fusion,localization,sensitivity}.py` | per-link point-force dictionaries, whitening, projections, principal angles |
| experiments | `experiments/{common,pipeline,evaluation,evaluation_chain_baseline,stage2a_common,stage2a_pathway_pipeline,run_stage2a_*,decision_stage2a,make_figures_stage2a}.py` | the Stage 2A pipeline, reused for the Phase 0 reproduction |
| packaging | `packaging/{build_review_package,validate_review_package,build_review_package_stage2a}.py` | Thin/Full builder and validator (topology names are already parameters) |
| tests | all 12 `tests/test_*.py` from Stage 2A/1R-B | re-run unchanged as the Phase 0 regression gate |

**Frozen and deliberately unused** (kickoff §M / §03.5): the F6 command-delay dictionary and the
instantaneous F5 encoder dictionary. Both were measured in Stage 2A to be wrong (F6 66–89° from
the closed-loop truth; instantaneous F5 52–89° off and 12–125× too large). They remain in
`pathways/dictionaries.py` for provenance but no Stage 2B code path references them, which
`tests/test_stage2b_no_leakage.py` asserts statically.

## 2. New in Stage 2B (no ancestor)

| path | purpose |
|---|---|
| `configs/stage2b_contact_loadpath.yaml` | frozen Stage 2B protocol, operating targets and decision thresholds |
| `src/certo_fdi/stage2b/__init__.py` | package docstring / module map |
| `src/certo_fdi/stage2b/decision_stage2b.py` | **pre-registered decision rules**, committed before any Stage 2B metric |
| `src/certo_fdi/stage2b/loadpath_controls.py` | the five source-of-gain controls, rank and support matched |
| `src/certo_fdi/stage2b/rank_aware_scores.py` | the five pre-registered per-link localization scores |
| `src/certo_fdi/stage2b/contact_calibration.py` | the separate `F4_CAL` partition (generation + manifest) |
| `src/certo_fdi/stage2b/selective_localization.py` | accept/defer features, thresholds and risk-coverage |
| `src/certo_fdi/stage2b/context_calibration.py` | global / Mondrian / quantile-regression / conformal thresholds |
| `src/certo_fdi/stage2b/sequential_monitor.py` | persistence, hysteresis and one-sided CUSUM wrappers |
| `src/certo_fdi/stage2b/event_accounting.py` | the frozen alarm-event, refractory, matching and delay definitions |
| `src/certo_fdi/stage2b/healthy_expansion.py` | nested H40/H80/H160 healthy datasets with a balanced design table |
| `src/certo_fdi/stage2b/metrics_stage2b.py` | episode-cluster bootstrap and the Stage 2B metric tables |
| `src/certo_fdi/experiments/run_stage2b_*.py` | the Stage 2B phase runners |
| `src/certo_fdi/experiments/make_figures_stage2b.py` | the nine required figures |
| `src/certo_fdi/packaging/build_review_package_stage2b.py` | Stage 2B Thin/Full package builder |
| `scripts/run_stage2b.sh` | phase runner |
| `tests/test_stage2b_*.py` | the twelve required Stage 2B test files |
| `docs_pointer/STAGE2B_PORT_PROVENANCE.md` | this file |
| `docs_pointer/STAGE2B_PROTOCOL.md` | the frozen protocol in prose |

## 3. Stage 2A files modified by Stage 2B

Any entry here is a real edit to inherited code and must be justified. Kept deliberately small:
Stage 2B adds new modules rather than changing audited ones.

| file | change | reason | test |
|---|---|---|---|
| `src/certo_fdi/paths.py` | `STAGE` and `RUN_SUBDIRECTORIES` gain the Stage 2B run layout; `RunLayout` gains `figures` and `root` properties | run roots are stage-scoped, and the figure/manifest writers need the two paths by name | `tests/test_paths.py` |

**That is the entire list.** `git diff --stat bcf2ad5..HEAD` shows 39 files, 38 of which are new;
`paths.py` is the only inherited file Stage 2B touched, and its edit is additive. Three edits that
were listed as *planned* in earlier drafts of this document did not turn out to be necessary and
were therefore not made: the `README.md` stage banner, Stage 2B targets in `Makefile` /
`scripts/run_stage2a.sh` (`scripts/run_stage2b.sh` is standalone), and an extra signal key in
`src/certo_fdi/data/windows.py` (the frozen episode format already carried everything the F4_CAL
and healthy-expansion replays need). Leaving the audited Stage 2A modules byte-identical was
worth more than the convenience.

## 4. Verified input provenance

Checked before any result was computed (kickoff §B, §07.1):

| input | expected | observed | status |
|---|---|---|---|
| Stage 2A FULL package sha256 | `0ae32ba745917d68b2b819e779f2d3430be535ce3d3e018dcde8baa446b04acc` | identical | **MATCH** |
| Stage 2A git SHA (local and remote) | `bcf2ad5c978f58dc159636d64d0b5c81efb9e396` | identical | **MATCH** |
| dataset content manifest sha256 | `8c2ba38b9262080efb981c08cfb7b5d58d2bfd037228a313edcae57f062b4100` | identical | **MATCH** |
| Stage 2B kickoff zip sha256 | `c8dbf315c73511f4b62569bcee395f392fddfa7311a2f2276bb9a8c66476bb9f` | identical, `unzip -t` clean, 14/14 internal sums OK | **MATCH** |

The kickoff contracts are frozen at
`/mnt/g/CERTO-FDI/02_research_docs/stage2b/contracts/` and
`/mnt/g/CERTO-FDI/01_frozen_sources/extracted/CERTO_FDI_STAGE2B_KICKOFF_20260816_c8dbf315/`
with per-file hashes in `STAGE2B_CONTRACT_HASHES.json`.
