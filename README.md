# CERTO-FDI

**Stage 1: closed-loop 2R falsification of certificate-based fault detection, isolation, and local identification.**

## Scientific status

- Current project decision: **PIVOT** (frozen at Stage 0 round 3; re-evaluated at end of Stage 1).
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
