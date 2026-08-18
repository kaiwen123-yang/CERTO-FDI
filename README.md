# CERTO-FDI

**Current round: Paper Reset — systematic full-text literature audit and public benchmark reproduction.**

## Current round (this branch)

`stage/paper-reset-literature-public-benchmarks` is a clean cut from `main`. It is not a
new-algorithm stage. Its only jobs are a systematic full-text literature audit, a
licence/schema audit of public robot-anomaly datasets, faithful reproduction of those
datasets' native baselines plus a unified universal baseline matrix, a fair external
check of the existing candidate on public data, and one paper-level decision.

New networks, new Jacobian/pathway modules, strict certificates, simulation fault
injection, and real-robot experiments are all **forbidden** this round
(`contracts/paper_reset/03_SCOPE_AND_CLAIM_FREEZE.md`).

| Item | Location |
|---|---|
| Frozen governing contracts | `contracts/paper_reset/` |
| Protocol freeze record | `docs/paper_reset/PROTOCOL_FREEZE.md` |
| Code-port ledger from PR #1–#7 | `docs/paper_reset/PORT_PROVENANCE.md` |
| Frozen decision code | `src/certo_fdi_reset/decision.py` |
| Stage config | `configs/paper_reset.yaml` |

Phase 0 bootstrap (verifies the persist root, builds its tree, writes the run manifest):

```bash
python -m certo_fdi_reset.freeze --config configs/paper_reset.yaml
```

Draft PRs #1–#7 are historical. They stay Draft, unmerged, and their heads are never
moved or rewritten.

## Historical status (Stage 1)

- Stage 1 project decision: **PIVOT** (frozen at Stage 0 round 3; re-evaluated at end of Stage 1).
- **No non-empty detection / isolation / identification certificate has been established yet.**
- This repository contains *active code only*. It must **not** be interpreted as a completed
  T-RO-ready method, nor cited as evidence that any certificate is non-empty.
- Entry into 7-DoF, neural-network training, public-dataset training, or real-manipulator
  fault injection is **forbidden** until the pre-registered Stage 1 gate produces `GO`.

## What lives where

| Content | Location |
|---|---|
| Active code, tests, configs, CI | this repository (Linux-local working tree) |
| Research documents, claim ledgers, decisions | `G:/CERTO-FDI/02_research_docs/` (not committed) |
| Raw/interim/processed data, run outputs | `G:/CERTO-FDI/03_data/`, `G:/CERTO-FDI/04_runs/` |
| Thin/Full review packages | `G:/CERTO-FDI/06_review_exchange/` |
| Frozen input archives (untrusted) | `G:/CERTO-FDI/01_frozen_sources/` |

Experiment outputs are always written to an external `CERTO_RUN_ROOT` (see
`configs/paths.example.env`); the repository hygiene check rejects committed results.

## Stage 1 scientific question

For a fixed-base 2R serial arm in an explicit closed loop (arm + sensor + controller +
actuator + generalized-momentum observer), using trajectory-window fault operators, a
physical healthy basis and a bounded healthy tube: after deducting closed-loop
linearization error, healthy-set error and stochastic noise scale, do computable,
strictly non-empty, repeatable detection / isolation / local-identification certificates
exist?

## License

**License decision pending.** No open-source license has been chosen; all rights reserved
until the owner decides otherwise.
