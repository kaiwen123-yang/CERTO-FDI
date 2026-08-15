# CERTO-FDI

**Stage 1R — LiGRA-FDI: Lie-Group Recursive Anomaly Representation for manipulator fault
detection and identification** (branch `stage/stage1r-ligra-representation`).

## Scientific status

- Stage 1 (2R strict closed-loop certificate) ended in a preregistered **NO-GO** for that
  specific certificate contract; it is archived unmerged in Draft PR #1 and is **not**
  evidence for or against Stage 1R.
- Stage 1R asks whether a **link-frame-covariant, RNEA-structured healthy-dynamics
  representation** gives measurable value (sample efficiency, unseen-configuration
  robustness, localization) for healthy-only anomaly detection on a Franka-class 7-DoF arm.
- The exact gauge covariance ``prod_i SE(3)_i`` of link frames is an **architectural
  correctness constraint** verified numerically (R0). Healthy and faulty samples obey the
  same law; **faults never "break" covariance** and gauge-equivariance error is never used as
  a fault score. The anomaly is a shift of invariant healthy-representation statistics.
- Internal 6-D messages are *latent wrench-like messages*, not identified physical wrenches.

## Layout

| Content | Location |
|---|---|
| Active code, tests, configs, CI | this repository (Linux ext4 worktree) |
| Kickoff package, contracts, ledgers | `G:/CERTO-FDI/02_research_docs/stage1r/` |
| 7-DoF episodes (HDF5), manifests | `G:/CERTO-FDI/03_data/stage1r/` |
| Runs, checkpoints, results, memos | `G:/CERTO-FDI/04_runs/stage1r_ligra/<RUN_ID>/` |
| Thin/Full review ZIPs | `G:/CERTO-FDI/06_review_exchange/to_review/{thin,full}/` |
| Frozen inputs (menagerie model, packages) | `G:/CERTO-FDI/01_frozen_sources/` |

Experiment outputs are always written to an external storage root (`CERTO_STORAGE_ROOT`);
the hygiene check rejects committed results.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev,sim,learn]'
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; unset PYTHONPATH   # avoid ROS plugin autoload
.venv/bin/python -m pytest -q -m "not slow"
scripts/run_r0.sh configs/stage1r_pilot.yaml <RUN_ID>          # geometry gate (no training)
scripts/run_stage1r.sh configs/stage1r_smoke.yaml <RUN_ID>     # smoke pipeline
```

## Conventions (frozen)

`V=[omega; v]`, `F=[n; f]`, `ad*_V = -ad_V^T`, `X_{i<-p} = Ad(T_{p,i}(q))^{-1}`; link-frame
reparameterization by `H_i` acts as `V'=A V`, `F'=A^{-T}F`, `I'=A^{-T} I A^{-1}`, `S'=A S`,
`X'=A_i X A_p^{-1}` with `A=Ad_H` (see `02_MATHEMATICAL_CONTRACT.md`).

## License

License decision pending; all rights reserved until the owner decides otherwise.
