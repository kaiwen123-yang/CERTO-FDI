# Stage 2A result pointer — `PIVOT_CONTACT_GEOMETRY_ONLY`

Full evidence lives on the persistent storage root, never in Git:

```text
/mnt/g/CERTO-FDI/04_runs/stage2a_chain_jacobian_pathway/run_20260816T055853Z_37f81d7/
```

| item | value |
|---|---|
| decision | **`PIVOT_CONTACT_GEOMETRY_ONLY`** |
| reasons | contact detection/localization improves; the other families do not |
| run id | `run_20260816T055853Z_37f81d7` |
| git sha | `bdf02627c283b07a479512e53564572fa746c852` |
| config sha256 | `4f47625bf3cf575d8443b46c2d90c251523ed028685756cdbeef9543b9282464` |
| dataset manifest sha256 (content, post-GMO) | `8c2ba38b9262080efb981c08cfb7b5d58d2bfd037228a313edcae57f062b4100` |
| input freeze gate | `PASS` |
| baseline reproduction gate | `PASS` (worst relative deviation 0.0075) |
| offline tests | {'errors': 0, 'failures': 0, 'passed': 87, 'skipped': 0, 'tests': 87} |
| seeds | [260815, 260816, 260817] |

## Headline numbers

| quantity | baseline (`chain_gnn_aug` residual only) | primary geometry head | shuffled-time control | oracle truth point |
|---|---|---|---|---|
| F4 detection AUROC, S1/S4 mean gain | 0 (reference) | 0.0347 | 0.0250 | — |
| F4 link top-1 (episode level) | 0.161 | 0.583 | 0.542 | 0.583 |
| F4 mean chain distance (links) | 2.32 | 0.78 | — | — |
| false alarms / hour | 2036.3 | 1646.5 | — | — |
| best diagnosability abs Spearman rho | — | 0.597 | — | — |
| other families improved (of 5) | — | 0 | — | — |

## The finding in one line

Contact **link localization** improves from 0.161 to 0.583 top-1, but a control whose Jacobians come
from permuted time indices reproduces 0.90 of that gain, so the improvement is chain **load-path
structure** plus a projection formulation rather than configuration-dependent Cartesian geometry.
Detection improves by only 0.0347 AUROC on F4 and by nothing on the other five families. Two
dictionaries did not survive validation against the frozen simulator: F6 command delay (not
validated at all) and the naive instantaneous F5 encoder column (replaced by its closed-loop
steady-state form).

See `stage2a_decision_memo.md`, `stage2a_known_issues.md` and `stage2a_claim_ledger.csv` in the run
root, and the Thin/Full review packages under `/mnt/g/CERTO-FDI/06_review_exchange/to_review/`.
