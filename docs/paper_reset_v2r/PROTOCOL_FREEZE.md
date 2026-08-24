# Paper Reset V2-R — Protocol Freeze (2026-08-24)

One contract: `contracts/paper_reset_v2r/01_MASTER_PROMPT.md` (zip sha256
`a0a27bf9…7109`, inner SHA256SUMS verified). Frozen BEFORE any ME-AD/AURSAD
V2-R result exists.

## Verified state at freeze (§20 report)
- Host: Ubuntu 22.04.5 WSL2, kernel 6.6.87.2; py3.10.12; torch 2.13.0+cu130;
  24 threads / RTX 5080 16GB / 23GB RAM.
- /mnt/g drvfs mounted, writable; 143 GiB free (red line 50); WSL root 781 GiB.
- Base repo clean; PR #9 OPEN/Draft, head `e8ca639…` == contract expectation;
  PR #1–#9 protected (no merge/force-push/history edits).
- V2 Full package found at `06_review_exchange/to_review/full/`, SHA256 ==
  expected `7cb14c…b73f`; treated as FROZEN historical evidence.
- Datasets on G: voraus (1.1G parquet), AURSAD.h5 (6.0G), RoAD repo (frozen
  commit 8d33669), UR5e (2.5G), PyScrew s03, SARCOS. ME-AD: downloading to
  `03_data/public/me_ad/source_v1/ME-AD.zip` (Zenodo 20817531, 10.79 GB,
  official md5 c74dedb9…, CC-BY-SA-4.0; metadata JSON saved).
- Literature: 94 V2 cards + 10 inherited V1 cards + 16 dossiers on G.
- RUN_ID `run_20260824T084349Z_paper_reset_v2r`; run root
  `/mnt/g/CERTO-FDI/04_runs/paper_reset_v2r/<RUN_ID>/`.

## Frozen decisions
1. Three-axis decision code `certo_fdi_reset_v2r/decision.py` v2.1.0 mirrors
   03_DECISION_RULES.yaml exactly (tested); combined state never masks axes;
   PR #9 historical state immutable.
2. Matrix-truth rules: completeness flags computed from actual rows;
   deterministic models = 1 fit + cycle-bootstrap CI; stochastic = 3 seeds;
   `seed_count` explicit; NOT_APPLICABLE ≠ NOT_RUN; the V2 phrase
   "8 models × 3 seeds × 3 datasets" is retired unless literally true.
3. ME-AD: cycle is the sample unit; forbidden inputs (cycle index, fault
   stage, split id, labels); official 7 tasks are primary; onset =
   `benchmark_onset` terminology; RUL only with official labels; first-pass
   selective extraction only (README/Tasks/Pandas/scripts).
4. Blind all-joint residual is the primary physics-residual score; joint-3 is
   diagnostic-only; permuted-joint and context-permuted controls mandatory.
5. AURSAD dual protocol: FAITHFUL_NATIVE_POLICY (exact split known
   unrecoverable from V2 audit) vs honest grouped healthy-only; inflation
   effect sizes with cycle/operation-level CIs; "missing workpiece IDs" is
   reported as "random splits cannot demonstrate new-workpiece
   generalization", never as proven same-workpiece leakage.
6. V2 claim repairs in scope (§1.5 items 1–10) are closure work, not history
   rewriting: PR #9 artifacts stay untouched; corrections live in V2-R docs.

## Prohibitions (§2) restated
No third LiGRA; no gauge-breaking revival; no new Jacobian/pathway nets; no
590-episode MuJoCo tuning; no final-test tuning; no silent URDF/inertia
fabrication; no cycle-index/fault-label/split-ID inputs; no "physical onset"
claims; no RUL claims without labels; no point adjustment as main metric; no
overlapping-window bootstrap; PR #9 immutable; no merge; no force-push; end
with a terminal state.
