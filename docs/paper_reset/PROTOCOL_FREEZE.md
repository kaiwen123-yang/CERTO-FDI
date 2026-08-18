# PROTOCOL FREEZE — CERTO-FDI Paper Reset

**RUN_ID** `run_20260818T124611Z_paper_reset`
**Freeze UTC** 2026-08-18T12:46:11Z
**Contract package** `CERTO_FDI_LITERATURE_PUBLIC_BENCHMARK_RESET_KICKOFF_20260818.zip`
**Package SHA256** `dbb066041c50f7020b59a16a2a282d143844df2e64f0b478cd385b6f01b8e245`

Everything below is fixed **before** any full search count or test metric exists
(`01_MASTER_PROMPT.md` §4). Later phases read these values; they do not set them.
Amendments require a separate commit restating the old value, the new value, and
the reason.

## 1. Contract provenance

| Step | Result |
|---|---|
| Located | `/mnt/c/Users/ykw/Downloads/…_20260818.zip` (38 206 B, 2026-08-18 20:38:48 +0800) |
| `unzip -t` | 26/26 entries OK, no errors |
| Internal `SHA256SUMS.txt` | 26/26 OK |
| Extracted to | `/tmp/certo_paper_reset_20260818T123953Z/` |
| Frozen in repo at | `contracts/paper_reset/` (checksums re-verified by `tests/test_paper_reset_freeze.py`) |

## 2. Literature freeze

| Parameter | Frozen value |
|---|---|
| Search execution date | 2026-08-18 |
| Monitored window | 2020-08-18 → 2026-08-18 (classics unrestricted) |
| Discovery, deduplicated | ≥ 250 |
| Title/abstract screened | ≥ 120 |
| Full texts actually read | ≥ 60 |
| Direct-neighbour full texts | ≥ 25 |
| Killer-paper dossiers | ≥ 10 |
| Citation chains | ≥ 8 |
| 2025–2026 directly relevant full texts | ≥ 15 |
| Public data/code paper full texts | ≥ 12 |
| Occupancy-supporting evidence levels | A1, A2, B1 |
| Discovery-only evidence levels | B2, C |

Query set is frozen as `contracts/paper_reset/05_LITERATURE_SEARCH_STRINGS.md`.
Synonym revisions during execution are allowed but must be versioned with a
reason in `literature_search_log.csv` (`04_SYSTEMATIC_FULLTEXT_LITERATURE_PROTOCOL.md` §D.1).

### Database access, measured at freeze time

| Source | HTTP | Usable for |
|---|---|---|
| arXiv | 200 | B1 full text, preprint status |
| Crossref API | 200 | metadata, DOI resolution, forward/backward chains |
| OpenAlex API | 200 | discovery, citation chains |
| Semantic Scholar | 200 | discovery, citation chains |
| DBLP | 200 | formal venue/version verification |
| SpringerLink | 200 | A1 where OA |
| Unpaywall API | 200 | OA-location resolution (verified on the voraus-AD DOI) |
| Google Scholar | 200 | discovery only; captcha expected under load |
| **IEEE Xplore** | **418** | **blocked — no institutional access** |
| **ScienceDirect** | **403** | **blocked** |
| **ACM DL** | **403** | **blocked** |
| Scopus / Web of Science | no subscription | unavailable |

Consequence, recorded now rather than discovered later: a large share of the
T-RO / ICRA / IROS / T-Mech nearest-neighbour set is not reachable at evidence
level A1. The audit routes those through A2 (author accepted manuscript,
institutional repository, author homepage) and B1 (arXiv full text with formal
version cross-check), both of which `04_…§E` accepts for occupancy claims.
Anything still unreachable is recorded `FULLTEXT_UNAVAILABLE` and may not be
used to argue either OCCUPIED or OPEN. Unavailable databases are logged as
unavailable and are never backfilled from memory (`01_MASTER_PROMPT.md` §5).

If the ≥60 full-text threshold cannot be met through A2/B1, the literature gate
resolves to `LITERATURE_UNKNOWN_INSUFFICIENT_FULLTEXT` — not to a convenient
`PLAUSIBLY_OPEN`.

## 3. Dataset freeze

Mandatory: `voraus_ad`, `road`, `aursad`.
Supplementary: `ur5e_graabaek`, `pyscrew`.
Healthy-dynamics-only, never fault evidence: `sarcos`.

Registry frozen as `contracts/paper_reset/08_PUBLIC_DATASET_REGISTRY.csv`. All
`physics_level` values enter Phase D0 as `TO_BE_AUDITED`; the P0–P3 grade is an
output of the feasibility card, never an assumption.

### Data-source access, measured at freeze time

| Source | HTTP | Note |
|---|---|---|
| GitHub (`vorausrobotik/voraus-ad-dataset`, `nikolaiwest/pyscrew`) | 200 | reachable |
| GitLab (`AlessioMascolini/roaddataset`) | 200 | reachable |
| Zenodo HTML (`/records/…`) | **403** | anti-bot block on the web UI |
| Zenodo **API** (`/api/records/…`) | **200** | usable — verified against AURSAD record 4559556 |
| PyPI | 200 | reachable |

AURSAD / UR5e / PyScrew are therefore reachable via the Zenodo REST API rather
than the web UI. This is an access route, not a licence decision: licences are
resolved per dataset in Phase D0 against `24_DATASET_LICENSE_AND_ACCESS_CHECKLIST.md`.

## 4. Baseline registry freeze

Frozen as `contracts/paper_reset/10_BASELINE_REGISTRY.csv`, mirrored into
`configs/paper_reset.yaml::baseline_tiers`. `tests/test_paper_reset_freeze.py`
fails if any registry id is missing from the config.

- **Native**: `dataset_native_mvt_flow`, `dataset_native_varade`, `aursad_paper_baselines`
- **Universal**: `pca_spe_t2`, `ocsvm`, `isolation_forest`, `autoencoder`,
  `gru_autoencoder`, `mvt_flow_adapted`, `recent_mtsad_1`
- **Candidate**: `joint_gru_public`, `chain_gnn_public`, `geometry_aware_chain_public`
- **Conditional physics**: `frame_aug_chain_public`, `rnea_gmo_public`, `mobnet_like_public`

`recent_mtsad_1` is deliberately unresolved: it is selected after a full-text and
code audit and **frozen before any test result is computed**
(`01_MASTER_PROMPT.md` §9).

## 5. Metric freeze

- Primary: `episode_auroc`, `episode_auprc`, `fpr_at_tpr90`
- Secondary: `window_auroc`, `window_auprc`, `event_f1`, `false_alarms_per_hour`, `detection_delay`
- Bootstrap unit: episode; 2000 resamples; 95% CI
- Seeds: `260818`, `260819`, `260820`
- Healthy fractions: 0.10, 0.25, 0.50, 1.00
- Split unit: episode or operation; windows never cross a split

Windows are not treated as independent samples for significance
(`12_CROSS_DATASET_FAIRNESS_AND_METRICS.md` §3).

## 6. Reproduction tolerance freeze

Deterministic split with a single reported value: |Δ| ≤ 0.01 **or** relative
≤ 2%, whichever is wider; sample/episode counts must match exactly. Paper reports
mean only, no standard deviation: label `FAITHFUL_NOT_NUMERICALLY_VERIFIED`
rather than forcing the 2% gate.

## 7. Candidate survival freeze

On ≥ 2 mandatory datasets versus the strongest faithful baseline: AUROC gain
≥ 0.03 **or** AUPRC gain ≥ 0.05; FPR\@TPR90 must not worsen by more than 10%;
≥ 2 anomaly classes/contexts and ≥ 2 seeds must agree in direction; or match the
baseline's 100%-data performance using 25% healthy data. A simulation-only result
does not satisfy this.

## 8. Decision code freeze

`src/certo_fdi_reset/decision.py`, version `1.0.0`, committed in this milestone
before any full-scale result exists. `resolve_final_state` is a pure function
over pre-declared evidence fields and returns exactly one terminal state by the
priority order of `14_DECISION_RULES.md`.

Two overlap resolutions are recorded explicitly, because both predicates can fire
at once and the priority list — not a later judgement call — settles them:

1. `CANDIDATE_NO_VALUE` + no geometry increment + a high-quality benchmark →
   `NO_GO_CURRENT_METHOD_PUBLIC_DATA` outranks `PIVOT_PUBLIC_ANOMALY_BENCHMARK`.
   The benchmark pivot stays reachable through `CANDIDATE_SIMULATION_ONLY` and
   `CANDIDATE_NOT_APPLICABLE`.
2. `PIVOT_CONTACT_SPECIALIST` outranks `PAPER_CANDIDATE_READY_FOR_REAL_ROBOT`,
   per the declared order.

`tests/test_paper_reset_decision.py` pins the priority order, proves every
`PAPER_CANDIDATE_READY_FOR_REAL_ROBOT` precondition is load-bearing, and
exhaustively checks that all seven terminal states remain reachable over the full
gate cross-product.

## 9. Non-revisitable historical verdicts

Carried in from `03_SCOPE_AND_CLAIM_FREEZE.md` §4. These do **not** roll back if
public benchmark results disappoint:

- Faults do not generally break per-link frame/gauge covariance.
- Gauge-equivariance error is not a general mechanical fault score.
- LiGRA-v1/v2 is not a primary performance contribution (`FINAL_NO_GO_LIE_MAIN_CONTRIBUTION`).
- The old strict closed-loop set certificate is NO-GO.
- Stage 2B-F's `NO_GO_CONTACT_PRODUCT` stands.

## 10. Claim ledger

C1–C6 all start `UNKNOWN` (`21_CLAIM_LEDGER_TEMPLATE.csv`). Statuses may only
become one of `OCCUPIED`, `PARTIALLY_OCCUPIED`, `PLAUSIBLY_OPEN`, `UNKNOWN`,
`FALSELY_FRAMED`, and only on A1/A2/B1 evidence.

## 11. Storage

Contract default is `/mnt/g/CERTO-FDI` (`15_GIT_STORAGE_AND_PR_PLAN.md`), with
`CERTO_PERSIST_ROOT` as the sanctioned override, recorded in every manifest.

**Open deviation at freeze time:** `/mnt/g` is not a real mountpoint. The G:
volume exists in Windows (931.5 GB, 114.3 GB free, fixed disk) but WSL never
automounted it, so `/mnt/g` is an empty directory on the ext4 root and
`22_BOOTSTRAP_FROM_ZERO.sh` exits 2 at its `mountpoint -q` gate. `sudo` on this
host requires a password, so the agent cannot mount it. Resolution chosen by the
project owner: mount G: manually and keep the contract default. The persist tree
is created only after `is_real_mountpoint('/mnt/g')` returns true; until then no
phase that writes to the persist root may run. This deviation and its resolution
are recorded in `run_manifest.json`.

## 12. Git

Base `main` @ `37f81d7`, clean. Branch
`stage/paper-reset-literature-public-benchmarks`, worktree
`~/research/CERTO-FDI-WORKTREES/paper-reset-literature-public-benchmarks`.
PRs #1–#7 stay Draft, unmerged, heads unmoved; a new Draft PR is opened against
`main`. No auto-merge. Literature PDFs, datasets, checkpoints, and results never
enter git.
