# Stage 2A protocol (frozen)

Config: `configs/stage2a_pathway_audit.yaml`. Decision code:
`src/certo_fdi/experiments/decision_stage2a.py` (+ `tests/test_stage2a_decision_rules.py`),
both committed **before** any Stage 2A model result existed.

## 1. Scientific object

With `chain_gnn_aug` frozen as the healthy-residual front end, the corrected joint residual is

```
e_tau(t) = tau_meas(t) - tau_nom(t) - d_chain(t)
```

and the window residual `E_W = vec(e_tau(t_1..t_M))` is whitened conditionally on declared
physical context `C_W` (controller, speed scale, tool mass, tool CoM z, temperature proxy,
noise level — never region id, never trajectory-family id, never fault information):

```
z_W = Sigma_0(C_W)^{-1/2} ( E_W - mu_0(C_W) ),   W_0 = Sigma_0^{-1/2}
```

`mu_0` and `Sigma_0` are estimated on **healthy train + validation windows only**.

### Window sub-sampling (declared numerical choice)

The frozen evaluation window is 128 samples at 500 Hz. Stacking all of them makes `E_W` an
896-vector, whose covariance ~8.8k healthy windows cannot estimate. Stage 2A therefore
sub-samples the window at a fixed stride to `M = 8` time points (`E_W` has 56 entries,
>150 healthy windows per covariance dimension). The identical sub-sample is applied to the
residual and to every dictionary column, so no geometry is discarded relative to the residual
it is fitted against. The covariance regularisation, effective rank and condition number are
recorded in `stage2a_pathway_dictionary_audit.csv`.

## 2. Fault-pathway dictionaries

Each column is `d E_W / d theta` with `theta` the **physical** fault parameter, evaluated on
the observed trajectory with the nominal model.

| key | columns | parameter units | construction |
|---|---|---|---|
| `F1_actuator` | 7 | efficiency-loss fraction | `Diag(tau_cmd(t))` |
| `F2_viscous` | 7 | N m s/rad | `Diag(qdot(t))` |
| `F2_coulomb` | 7 | N m | `Diag(tanh(qdot/eps))` |
| `F2_stribeck` | 7 | N m | `Diag(exp(-(qdot/v_s)^2) tanh(qdot/eps))` |
| `F3_payload` | 10 | kg, kg m, kg m² | exact typed-RNEA payload regressor `Y_load` |
| `F4_contact_link{l}` | 6 | N m, N | `-J_l(q(t))^T` (point-agnostic body wrench) |
| `F4_contact_link{l}_{pt}` | 3 | N | `-J_{l,p}(q(t))^T` (point force at a candidate point) |
| `F5_encoder_q` | 7 | rad | symmetric FD through controller + RNEA + estimator paths |
| `F5_encoder_qd` | 7 | rad/s | symmetric FD through controller + RNEA + estimator paths |
| `F6_delay` | 1 | s | explicit command-buffer fractional-delay FD |

Sign convention: `theta` is the physical parameter, so a fitted coefficient reads directly in
physical units. The contract writes several columns with the opposite sign; those span the
identical subspace and change no principal angle, projection residual or explained energy.

Friction is split into **three separate** column groups so the audit never assumes that
viscous + Coulomb span all friction anomalies.

The F4 form is the **3-D point force**, because the frozen simulator injects contact as
`xfrc = [f; r x f]` at the body origin — algebraically a pure force at a point
(`tests/test_stage2a_jacobians.py::test_simulator_contact_wrench_equals_point_force_dictionary`).
3-D and 6-D forms are never mixed inside one dictionary.

Three F4 dictionary forms are built and compared, as required: end-effector only, all-link
instantaneous, all-link window-stacked.

### Deployment vs oracle

Deployed dictionaries are functions of **measured signals and the nominal model only**. The
*oracle* forms — symmetric finite differences through the frozen truth simulator, and the
truth contact point — exist only for correctness tests and upper bounds, and are never inside
a deployed head. If the geometry works only with the truth contact point, the pre-registered
rules force `NO_GO_JACOBIAN_PATHWAY_HEAD` (integrity trigger t4).

## 3. Geometry statistics

Ridge weighted least squares with a **purely numerical** ridge (no data fitting at all):

```
lambda_j = max(1e-6 * sigma_max(Dbar_j)^2, sigma_max(Dbar_j)^2 / 1e6)
```

Outputs per window and family: `projection_residual`, `explained_energy`,
`explained_fraction`, `coefficient_norm`; per pair: principal angles, minimum principal angle,
subspace overlap; per contact link: `sigma_min_positive`, condition number, Fisher information
`I = Dbar^T Dbar` and its smallest positive eigenvalue; end-effector/joint-null energy split.

A large `joint_null_energy` means only "not explainable by a single end-effector wrench". It
is **not** evidence of an actuator fault.

## 4. Models and ablations

`rnea_threshold`, `rnea_gru`, `chain_gnn_aug_residual_only` (main baseline), `geometry_only`,
`chain + ee_jacobian`, `chain + all_link_instantaneous_jacobian`,
`chain + all_link_window_jacobian` (primary geometry head),
`chain + full_pathway_dictionary`, plus two controls:

- `chain + shuffled_jacobian_control` — identical feature count, Jacobians evaluated at
  time-shuffled configurations of the same episode. Isolates "geometry" from "more features".
- `chain + all_link_window_jacobian_oracle_point` — the truth contact point, oracle upper
  bound only.

Every head uses the **same** conditional-Gaussian healthy density, the same LOO candidate
selection and the same 0.995 healthy-validation threshold; only the feature vector changes.
No fault data enters any primary detection decision. Any fault-label-trained fuser is a
clearly separated *secondary supervised attribution* experiment on the disjoint `calib`
partition.

## 5. Splits, families, seeds

Frozen S0–S4 from the dataset manifest (S0 IID, S1 unseen configuration region, S2 unseen
tool/payload, S3 unseen speed band, S4 joint context OOD). The contract's "S5" refers to the
frame-reparameterization stress protocol, which is an implementation property and is **not** a
data partition and **not** a detection-value axis. Fault families F1–F6, seeds
`[260815, 260816, 260817]`.

Data-volume diagnostic: the frozen pilot has 40 healthy train episodes, so the learning curve
runs at `{10, 20, 40}` episodes; the requested 80-episode point is **NOT AVAILABLE** and is
recorded as such rather than extrapolated.

## 6. Gates

- **Reproduction gate (§6.4).** The frozen `chain_gnn_aug` healthy RMSE, ALL/S1/S2/S4 AUROC,
  localization metrics, parameter count, input fields and leakage tests must reproduce within
  2 % relative of the Stage 1R-B frozen values, or the run stops and diagnoses.
- **Leakage scan (§7.3).** No encoder or fuser input may contain `tau_meas`, the raw residual,
  a fault label, severity, fault link id or a truth-only state.
- **Mutation tests (§7.4).** Transposed Jacobian, untransformed wrench frame, link index off by
  one, flipped residual sign and wrong-link contact Jacobian must all be caught.

## 7. Decision

See `src/certo_fdi/experiments/decision_stage2a.py`. Terminal states and evaluation order:

```
BLOCKED
  > NO_GO (integrity triggers t4, t6)
  > GO_JACOBIAN_PATHWAY_HEAD
  > PIVOT_CONTACT_GEOMETRY_ONLY
  > PIVOT_COARSE_EQUIVALENCE_CLASSES
  > PIVOT_CALIBRATION_SEQUENTIAL
  > NO_GO (performance triggers t1, t2, t3, t5)
  > NO_GO (default)
```

Thresholds are project decision thresholds, not theorems. Post-hoc threshold changes to
rescue an outcome are forbidden; all raw results are retained regardless of the outcome.
