# Stage 1 code interfaces

- `closed_loop_step(x, t, healthy_parameters, fault_parameters, config)` is the sole trusted
  step implementation.
- Window row block `a` is residual `r[k0+a+1]`; column block `b` is the fault applied on
  interval `[k0+b, k0+b+1]`.
- `build_physical_healthy_basis` uses the same closed-loop AD graph as fault operators.
- `detection_distance` and `isolation_distance` cross-check SciPy and CVXPY/OSQP joint QPs.
- `run_stage1` writes only to an external `CERTO_RUN_ROOT` and preserves status columns.

Long research documents, results, ledgers, decision memos, and review ZIP files remain on the
external storage root and are intentionally excluded from Git.
