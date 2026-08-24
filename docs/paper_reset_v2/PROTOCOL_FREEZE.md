# Paper Reset V2 — Protocol Freeze

Frozen 2026-08-24 (UTC), before any V2 screening count, full-text card,
benchmark number, candidate result, or story choice exists.

## What this round is

One execution contract:
`contracts/paper_reset_v2/01_MASTER_PROMPT.md` (SHA256-pinned in
`contracts/paper_reset_v2/SHA256SUMS.txt`; shipping ZIP
`CERTO_FDI_CLAUDE_FULL_LITERATURE_BENCHMARK_INNOVATION_CONVERGENCE_20260824.zip`,
SHA256 `a822d62a9167bce97602894249bb4b893a6ac26989f2b03e3206fdfc648f4413`).

Hard goals: 500 papers actually screened, 100 full texts actually read,
35 direct nearest neighbours, 15 killer-paper dossiers, voraus-AD + RoAD +
AURSAD completed with native and unified baselines, at most two candidate
stories, and exactly one final terminal state from
`src/certo_fdi_reset_v2/decision.py` (v2.0.0).

## Fixed identifiers

| Item | Value |
|---|---|
| RUN_ID | `run_20260824T023044Z_paper_reset_v2` |
| Branch | `stage/paper-reset-v2-500x100-public-story-convergence` |
| Base branch | `stage/paper-reset-literature-public-benchmarks` |
| Base head at freeze | `bf8c70aacddfe050adf41e42229f0fe612ccc169` (== PR #8 head, verified) |
| Run root | `/mnt/g/CERTO-FDI/04_runs/paper_reset_v2/run_20260824T023044Z_paper_reset_v2` |
| Literature root | `/mnt/g/CERTO-FDI/02_research_docs/paper_reset_v2/literature` |

## Verified state at freeze (Phase V0)

- `/mnt/g` is a real drvfs mount, writable; 147 GiB free (red line 50 GiB);
  WSL root 787 GiB free (red line 20 GiB).
- PR #1–#8 all OPEN Draft, heads unmoved; PR #8 head equals the contract's
  expected `bf8c70a…`.
- Existing deduplicated discovery library: **5470 records**
  (`…/L1_discovery/literature_deduplicated_library.csv`; the contract's
  "约 5,303" undercounts the same file).
- Existing full texts: **10 PDFs** with page-marked text extractions and
  10 method cards; 5 Wave A targets remain `FULLTEXT_UNAVAILABLE` after the
  full access ladder.
- Public data on G: voraus-AD 100 Hz parquet (1.1G), AURSAD.h5 (6.0G),
  RoAD frozen repo incl. dataset (406M, commit `8d33669…`), UR5e (2.5G),
  PyScrew s03 (13M), SARCOS (12M).
- voraus baselines: Track A EXACT_OFFICIAL_CPU smoke passed; Track B GPU port
  numerically parity-checked but only 10-epoch smoke — **not** usable as final
  (contract §5.4 forbids 10-epoch results as final).
- VARADE audit complete: `POLICY_BASELINE`, 11 findings.

## Deviations recorded at freeze

1. **Sandbox result packages absent.** Neither
   `ROAD_SANDBOX_FULL_BENCHMARK_20260820.zip` nor
   `ROAD_SANDBOX_EXTENDED_AUDIT_20260821.zip` exists anywhere on this host
   (Windows Downloads/Desktop/Documents, G-drive inbox, review exchange, all
   searched by exact name and pattern). Only the *outbound* handoff ZIP is
   present. Consequence, frozen here: every §1.4 sandbox claim is treated as a
   quoted, unverified external statement; Phase B-RoAD must re-derive each
   load-bearing claim locally (true-order vs shuffled controls, healthy-split
   sensitivity, channel ablation, event-level false alarms) before any claim
   can gate a decision. The claims still carry their contractual *negative*
   force: the current Chain/SO(3) model stays disqualified as a default
   candidate unless local evidence overturns that.
2. **Contract's "5,303" vs actual 5470**: the frozen dedup library holds 5470
   rows; the 500-screen quota draws from this pool (larger pool, same gate).

## Non-negotiables restated

- PR #1–#8: Draft, no merge, no force-push, no history rewrite, heads unmoved.
- No third LiGRA; no revival of "fault breaks gauge covariance"; no further
  internal 590-episode tuning; RoAD Chain/SO(3) is not an established
  candidate; no test-anomaly tuning; no fabricated physical quantities;
  `FULLTEXT_UNAVAILABLE` never supports OPEN/OCCUPIED.
- Git carries code/configs/small tables/docs/pointers/hashes only; PDFs, raw
  data, checkpoints, big results, review ZIPs live under `/mnt/g/CERTO-FDI`.
- Candidate design starts only after ≥40 direction-setting full texts,
  voraus official baseline, RoAD independent review, AURSAD data audit.
- Exploration and confirmation are separated; the final test opens only after
  the candidate, inputs, hyperparameters, thresholds and gates are frozen.

## Amendment rule

Any change to this protocol, `configs/paper_reset_v2.yaml`, or
`src/certo_fdi_reset_v2/decision.py` after the freeze commit must be its own
commit whose message restates the old value, the new value, and the reason.
Results may never motivate silently editing the gates.
