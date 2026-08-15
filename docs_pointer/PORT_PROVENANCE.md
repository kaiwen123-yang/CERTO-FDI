# Selective port provenance from `stage/stage1-closedloop-certificate` (07850ef)

Only validated, reusable, non-certificate code was ported. Every ported unit was re-tested in
Stage 1R (`tests/`). No strict-certificate decision logic (tubes, QP distances, certificate
gates, closed-loop operators) enters the Stage 1R core.

| Stage 1 source (07850ef) | Stage 1R destination | Change | Re-test |
|---|---|---|---|
| `src/certo_fdi/dynamics/lagrange_reference.py` | `src/certo_fdi/dynamics/lagrange_reference.py` | JAX `TwoLinkParams` replaced by explicit scalars | `tests/test_rnea_2r_oracle.py` |
| `src/certo_fdi/dynamics/spatial_rnea.py` (conventions, `ad_force=-ad_motion.T`, spatial inertia, 2R chain) | `src/certo_fdi/geometry/se3.py`, `geometry/spatial_types.py`, `dynamics/chain_model.py::make_planar_2r`, `dynamics/rnea.py` | generalized from a hard-coded 2R to an arbitrary serial chain with reparameterizable link frames | `tests/test_se3.py`, `tests/test_rnea_2r_oracle.py`, `tests/test_frame_reparameterization.py` |
| `tests/test_dynamics.py` (SymPy oracle, wrong-`ad*` mutation, Mdot-2C skew) | `tests/test_rnea_2r_oracle.py` | adapted to the general RNEA API | itself |
| `src/certo_fdi/paths.py` | `src/certo_fdi/paths.py` | stage name, run subdirectories, resumable runs | `tests/test_paths.py` |
| `scripts/capture_environment.py` | `src/certo_fdi/experiments/common.py::capture_environment` | folded into experiment utilities; adds GPU/torch/mujoco/pin versions | R0 environment capture |
| `src/certo_fdi/packaging/build_review_package.py`, `validate_review_package.py` | `src/certo_fdi/packaging/` | Stage 1R required-file topology, decision keywords, run layout | `tests/test_review_package.py` |
| `scripts/check_repo_hygiene.sh` | `scripts/check_repo_hygiene.sh` | unchanged | CI |
| `.github/workflows/ci.yml` | `.github/workflows/ci.yml` | torch/mujoco/pin optional; sim tests skipped in CI | CI |

Not ported (certificate-specific or superseded): `certificates/*`, `healthy_sets/*`,
`operators/*`, `sets/*`, `closed_loop/model.py`, `experiments/stage1_pipeline.py`,
`faults/layout.py` (2R JAX layout; the 7-DoF fault protocol is re-implemented in
`data/fault_injection.py`), `control/*` (re-implemented for the 7-DoF MuJoCo plant),
`sensing/encoder.py`, `observers/momentum.py` (re-implemented in `anomaly/gmo.py`).
