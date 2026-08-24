# Paper Reset V2 — Port Provenance

What V2 inherits, from where, and under which trust label. Nothing in this
round is re-derived from scratch when a verified V1 artifact exists; nothing
inherited is upgraded in trust without re-verification.

## Inherited from PR #8 (`stage/paper-reset-literature-public-benchmarks`, head `bf8c70a`)

| Artifact | Location | Trust label |
|---|---|---|
| Dedup discovery library (5470 rows) | `/mnt/g/CERTO-FDI/01_frozen_sources/literature_reset/metadata/L1_discovery/` | VERIFIED_INVENTORY (counts re-checked 2026-08-24) |
| 10 full-text PDFs + page-marked text | `/mnt/g/CERTO-FDI/01_frozen_sources/literature_reset/open_fulltexts/` | VERIFIED_BY_FULLTEXT (cards re-usable; matrix rows re-audited before reuse) |
| 10 method cards + evidence matrix + NN matrix | `/mnt/g/CERTO-FDI/02_research_docs/paper_reset/literature/` | CANDIDATE_EVIDENCE (labels re-checked against V2 schema before counting toward the 100) |
| Dataset feasibility/license/schema/applicability matrices (6 datasets) | `<run_v1>/d0/` | VERIFIED_FROM_DATA_BYTES |
| voraus Track A official CPU env + smoke | `~/research/CERTO-FDI-BASELINES/voraus-ad-dataset` (conda `voraus_exact`) | EXACT_OFFICIAL_CPU (smoke only) |
| voraus Track B GPU port + parity smoke | `~/research/CERTO-FDI-BASELINES/voraus-ad-dataset-gpu` | FAITHFUL_OFFICIAL (10-epoch smoke; NOT final) |
| VARADE code audit (11 findings) | `<run_v1>/b0/road_varade/varade_code_audit.json` | POLICY_BASELINE audit, VERIFIED |
| RoAD frozen repo + dataset | `/mnt/g/CERTO-FDI/01_frozen_sources/public_baseline_repos/roaddataset` @ `8d33669…` | FROZEN_SOURCE |
| Decision code v1 semantics | `src/certo_fdi_reset/decision.py` (v1.0.0) | Superseded for V2 by `certo_fdi_reset_v2.decision` v2.0.0; v1 file untouched |

`<run_v1>` = `/mnt/g/CERTO-FDI/04_runs/paper_reset_public_benchmarks/run_20260818T124611Z_paper_reset`.

## Explicitly NOT inherited

- The two ChatGPT sandbox result ZIPs (`ROAD_SANDBOX_FULL_BENCHMARK_20260820`,
  `ROAD_SANDBOX_EXTENDED_AUDIT_20260821`): absent from this host; their claims
  enter only as quoted text inside the V2 contract, labeled
  `EXTERNAL_UNVERIFIED_CLAIM`, and each load-bearing one is re-derived locally
  in Phase B-RoAD.
- Any "OPEN"/"FIRST"/"T-RO-able" judgment from stage-0/early reports
  (contract §1.5): all such statements re-enter as candidates with one of
  VERIFIED_BY_FULLTEXT / SUPPORTED_BY_METADATA_ONLY / SECONDARY_SOURCE_ONLY /
  CONTRADICTED / OUTDATED / FULLTEXT_UNAVAILABLE.
- The internal MuJoCo 590-episode results: historical negative record only.

## Code reuse rule

`src/certo_fdi_reset_v2/` may import from `certo_fdi_reset` (V1 audit code)
where behaviour is unchanged and the import is recorded here; it never imports
`certo_fdi` (internal simulation stack). New V2 behaviour lives in V2 modules.
