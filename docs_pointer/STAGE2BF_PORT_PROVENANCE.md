# Stage 2B-F selective port provenance

Stage 2B-R's branch is **not** merged. Files were carried over one at a time, and each is listed
here with its source commit, source path, destination and what changed. Anything not in this table
was written fresh for Stage 2B-F.

| source commit | source path | destination | change | why |
|---|---|---|---|---|
| `9d8d472` (Stage 2B-R) | `src/certo_fdi/stage2br/evidence.py` | `src/certo_fdi/stage2bf/frozen_evidence.py` | join/vote/margin helpers kept; Stage 2A key made a parameter so the ridge and SVD arrays can share one reader | the `(seed, episode_id, window_start)` join and the frozen vote were already audited in Stage 2B-R; rewriting them would re-introduce the risk they were built to remove |
| `9d8d472` (Stage 2B-R) | `src/certo_fdi/experiments/run_stage2br_audit.py` | `src/certo_fdi/experiments/run_stage2bf_provenance.py` | package/manifest verification reused; evidence inventory retargeted at Stage 2B-F inputs, three packages instead of one | Phase 0 asks for the same disk-level verification, against more packages |
| `9d8d472` (Stage 2B-R) | `src/certo_fdi/packaging/build_review_package_stage2br.py` | `src/certo_fdi/packaging/build_review_package_stage2bf.py` | topology renumbered to the Stage 2B-F contract (`08_REVIEW_PACKAGE_CONTRACT.md`); smoke rewritten for the integrity/scientific pair | the drvfs staging fix and the credential-shaped secret scan are worth keeping verbatim |
| `9d8d472` (Stage 2B-R) | `tests/test_stage2br_evidence.py` | `tests/test_stage2bf_reproduction.py` | join/vote assertions kept; reproduction assertions rewritten for the two-estimator hard gates | same reason as the evidence module |

## Imported, never copied

These are used by direct import from the frozen modules. No logic is duplicated into Stage 2B-F:

| frozen module | what Stage 2B-F calls | pinned by |
|---|---|---|
| `certo_fdi.pathways.geometry` | `ridge_lambda`, `batched_projection` | byte-identical at `bcf2ad5`, `bee5f9b` and this HEAD |
| `certo_fdi.stage2b.rank_aware_scores` | `project`, `best_hypothesis_stats`, `stack_links`, `score_matrix`, `predict_link`, `RANK_RTOL` | byte-identical at `bee5f9b` |
| `certo_fdi.stage2b.decision_stage2b` | `decide` | byte-identical at `bee5f9b` |
| `certo_fdi.stage2b.contact_calibration` | selection/acceptance helpers | byte-identical at `bee5f9b` |
| `certo_fdi.experiments.stage2b_common` | `episode_cluster_bootstrap`, `paired_episode_bootstrap` | episode is the independent unit; window-level IID bootstrap is not implemented anywhere |

The first row of the second table is the one that matters most: `geometry.py` is byte-identical at
Stage 2A's own commit `bcf2ad5`, so importing `ridge_lambda`/`batched_projection` from this branch
*is* reusing Stage 2A's frozen code. That is checked by a test, not asserted.
