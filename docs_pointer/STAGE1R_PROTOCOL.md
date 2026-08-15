# Stage 1R implemented protocol (pilot) and deviations from the kickoff package

Kickoff package: `CERTO_FDI_STAGE1R_LIGRA_KICKOFF_20260815.zip` (sha256 23ea2828…), frozen on the
storage root. `08_CODEX_CLAUDE_MASTER_PROMPT.md` is the execution contract.

## Implemented as specified
- Conventions `[omega; v]`, `[n; f]`, `ad* = -ad^T`; legal per-link `SE(3)` reparameterization
  of a general serial chain (`geometry/`, `dynamics/chain_model.py`).
- R0: RNEA vs SymPy-Lagrange (2R), MuJoCo `mj_inverse`, Pinocchio (API-built and MJCF-parsed);
  wrong-`ad*` mutation must fail; healthy AND faulty frame-covariance trials; torch front end
  float64/float32; model-level T1–T3 before training (`experiments/run_r0_geometry.py`,
  `experiments/r0_model_covariance.py`).
- Franka-class 7-DoF MuJoCo truth plant + Pinocchio nominal model; 1 kHz physics / 500 Hz
  control-logging; 128-sample windows; episode-level splits S0–S5; fault families F1–F6;
  automated leakage report; HDF5 storage on `G:/CERTO-FDI/03_data/stage1r/`.
- LiGRA basis-coefficient model (invariant scalar GRU with parent message, 12 analytic
  covariant wrench columns + transported child messages, exact backward coadjoint recursion,
  `dtau = S^T dF`), matched non-equivariant chain GNN (+ frame augmentation), RNEA+MLP,
  RNEA+GRU, RNEA-only, GMO threshold, ablations (free output, MLP encoder, unshared, no-RNEA).
- G0 conditional Gaussian healthy head first (no flow); healthy-only threshold calibration.
- Metrics: window/event AUROC & AUPRC, FPR@TPR90, false alarms/hour, delay, event F1,
  per-severity rows, healthy-OOD audit, S5 drift, sample-efficiency curves at 10/25/50/100%,
  localization top-1/top-2/chain distance, few-shot 5/20/50-shot macro F1 + ECE, latency/size.

## Deviations (all decided on healthy data or for correctness; documented)
1. Model and density-head context excludes configuration-region and trajectory-family ids
   (categorical, would be extrapolated on S1/S4); only declared physical context is used.
2. Density head fitted on healthy *validation* windows with LOO model selection and LOO
   thresholds (post-correction residuals on the correction model's own training episodes are
   optimistically small). See `04_KNOWN_ISSUES.md` in the review package.
3. Localization decoders: `argmax`, `distal`, `pattern` reported for all models; `pattern`
   used for the decision axis (wrench-type faults produce load-path residual patterns).
4. Healthy pilot volume raised from 48 to 96 episodes to populate S1–S4 healthy test sets;
   Cartesian/IK and diagnostic-excitation trajectory families not generated in the pilot.
5. Parameter budgets matched approximately (baselines slightly larger than LiGRA).

## Not done in the pilot (explicitly)
- Public datasets (voraus-AD, RoAD, AURSAD): not used (PIVOT-D territory; anomaly-head transfer only).
- G1 mixture / G2 flow heads: not started (G0 first, per contract).
- Relaxed physical/statistical-symmetry branch: not exercised.
- Physical-wrench identification: not attempted or claimed.
