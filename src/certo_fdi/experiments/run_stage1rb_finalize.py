"""Stage 1R-B finalization: claims ledger, known-issues document, run manifest, figures, reference
copy on the storage root, decision docs, and validated Thin/Full review packages."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from certo_fdi.experiments.common import utc_now, write_csv, write_json
from certo_fdi.experiments.stage1rb_common import Stage, common_parser
from certo_fdi.paths import git_sha


def claims_ledger(ev: dict, basis: dict, M: dict, base_row: dict) -> list[dict]:
    ax = ev.get("axes", {})
    won = ev.get("axes_won", [])
    dec = ev.get("decision")
    rows = []

    def add(claim, status, evidence, strict=""):
        rows.append({**base_row, "claim": claim, "status": status, "evidence": evidence, "strict_claim": strict, "provisional": False})

    fired = basis.get("rules_fired", [])
    add("LiGRA-v1 fixed 12-column basis is capacity-limited (span too small)", "REJECTED" if basis.get("verdict") else "UNKNOWN", f"pointwise rank <= 6 (complete wrench span except root link); oracle at matched edf {basis.get('rules', {}).get('rule1_oracle_test_rmse_gap', {}).get('secondary_matched_edf', {})}", "capacity")
    add("LiGRA-v1 fixed 12-column basis is redundant / ill-posed for coefficient regression", "SUPPORTED" if "rule3_gram_condition" in fired or "rule4_stable_exact_redundancy" in fired else "NOT_SUPPORTED", f"verdict {basis.get('verdict')}; rules fired {fired}", "conditioning")
    add("shared temporal chain structure has value", "SUPPORTED-EMPIRICAL" if (ev.get("structure_effectiveness", {}) or {}).get("chain_structure_clearly_effective") else "NOT_ESTABLISHED", json.dumps(ev.get("structure_effectiveness", {})), "")
    add("exact covariance automatically improves detection", "FALSELY FRAMED (kept)", "covariance is a correctness/implementation property; frame drift is never a value axis", "")
    add("typed-equivariant full-information model (LiGRA-v2) has value over chain_gnn_aug", "SUPPORTED" if dec == "RESEARCH_GO_LIE_MAIN_CONTRIBUTION" else ("PARTIAL" if won else "NOT_SUPPORTED"), f"axes won {won}; decision {dec}", "four_axes")
    add("chain_gnn_aug is the strongest matched baseline", "VERIFIED-PILOT / used as judge", "matched inputs (52 raw fields), 63,047 params vs 65,454", "")
    add("internal message energy localizes physical faults", "NOT ESTABLISHED (not used)", "counterfactual masking and joint-residual pattern only; message energy never primary", "")
    add("counterfactual link contribution is usable for operational localization", "CANDIDATE" if (ax.get("axis3_localization", {}) or {}).get("candidate_top1") is not None else "UNKNOWN", json.dumps({k: v for k, v in (ax.get("axis3_localization", {}) or {}).items() if k in ("candidate_top1", "baseline_top1", "candidate_chain_distance", "baseline_chain_distance", "pass")}), "")
    add("LiGRA-v2 wins >= 3/4 axes -> main contribution", "MET" if dec == "RESEARCH_GO_LIE_MAIN_CONTRIBUTION" else "NOT MET", f"{len(won)}/4", "preregistered")
    add("LiGRA-v2 parity with frame stability -> implementation guarantee", "APPLIES" if dec == "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE" else "DOES NOT APPLY", json.dumps(ev.get("parity_conditions", {})), "")
    add("continue a third equivariant architecture after a fair failure", "PROHIBITED", "this round is the last architecture-family arbitration", "")
    add("LiGRA-v1 pilot NO_GO_LIE_MAIN_CONTRIBUTION (PR #2)", "UNCHANGED", "historical result kept; reported as NO_GO_CURRENT_LIGRA_V1 + <new decision>", "")
    return rows


def known_issues_md(st: Stage, ev: dict, basis: dict, M: dict, tun: dict, r0: dict) -> str:
    prov = st.provenance
    lines = [f"# Known issues and limitations — Stage 1R-B ({st.layout.run_id})", "",
             "## Data / provenance",
             "- Reused the frozen Stage 1R pilot data (590 episodes; 40 healthy training episodes, 12 healthy validation, 188 test episodes). Nothing was regenerated.",
             f"- The pilot `episode_index.csv` SHA256 column is stale by construction (pre-`r_gmo`, see STAGE1RB_PROTOCOL.md); content was verified (schema/finiteness of all 590 files, `tau_nominal` and `r_gmo` re-derived on a stratified sample) and a post-GMO manifest (sha `{st.manifest_sha}`) is cited by every result table. Provenance gate: {prov.get('gate')}.",
             "- The pilot healthy sample is small (40 training episodes at fraction 1.0, 10 at fraction 0.25); seed variance is reported per seed everywhere and no claim rests on a single seed or family.",
             "",
             "## Phase A audit",
             f"- Verdict {basis.get('verdict')} (rules fired: {basis.get('rules_fired')}). The 12 columns span at most a rank-6 wrench space per link (root link rank 4), so the coefficient Gram is exactly singular everywhere: rule 3 (condition number) fires by construction, and rule 1/2 comparisons at each oracle's own regularization partly reflect the free oracle's larger effective degrees of freedom; matched-edf comparisons are reported alongside and must be read together with the literal rules.",
             "- The oracle ceilings are per-window in-sample fits with fixed Tikhonov + temporal-smoothness penalties selected on healthy validation windows by held-out-timestep error; the zero-regularization limit is exact (rank(M_t) = 7) and is reported as an upper bound only.",
             "- Oracle B covers the inertial truth-vs-nominal mismatch only; the joint-space friction mismatch is not a link wrench (NOT_AVAILABLE).",
             "",
             "## Models / training",
             f"- Parameter counts: chain_gnn_aug {M.get('chain_gnn_aug', {}).get('n_params')} vs ligra_v2_typed {M.get('ligra_v2_typed', {}).get('n_params')} (within +-10 %). The chain GNN input set was extended to the contract's matched field list (adds F and I A over PR #2), so its numbers are not identical to PR #2's chain_gnn_aug.",
             f"- Tuning: 8 configurations per primary model, healthy validation RMSE only; selected {json.dumps({k: v.get('tag') for k, v in tun.items() if k in ('chain_gnn_aug', 'ligra_v2_typed')})}. Diagnostics reuse the PR #2 schedule (OneCycle, lr 2e-3).",
             "- Early stopping (min 15 epochs, patience 10, max 40) is identical for every model; the typed model is ~2-3x slower per epoch than the chain GNN (two GRU passes + typed scans).",
             "- LiGRA-v2's typed recurrence uses invariant sigmoid gates and unbounded linear mixing coefficients (as LiGRA-v1); no coefficient clipping was applied.",
             "- The typed encoder's invariants (pairings, Grams through I / I^-1) are GL(6)-invariant, i.e. the gates cannot use the Lie-bracket structure explicitly; brackets enter only through the analytic front end (A, F_body). This is a documented modelling choice within the contract's allowed operations, not a bug.",
             "",
             "## Anomaly heads / evaluation",
             "- Primary head: residual-only conditional Gaussian fitted on healthy validation windows (LOO-selected among 6 candidates; threshold = 0.995 LOO quantile) — identical for every model. The secondary 'representation' head is reported but never decisive.",
             "- Localization: counterfactual link masking (primary, unified) ranks links by |NLL(mask j) - NLL(full)|; the joint-residual pattern decoders of PR #2 are reported as secondary. Neither reads internal message energy.",
             f"- `qdd_true` results are an oracle diagnostic (same checkpoints, truth acceleration input); every decision number uses `qdd_est`. R0 gate: {r0.get('decision')}.",
             "- Frame drift of chain_gnn_aug is reported for completeness; it is an implementation property and never a value axis.",
             "- Window-level AUROCs are moderate for all models on this plant-mismatch design; F2 friction stays near chance for every detector (as in PR #2).",
             "",
             "## Decision reading",
             f"- Reported decision: **{ev.get('decision_reported')}** (reasons: {'; '.join(ev.get('reasons', []))}). It judges LiGRA-v2-Typed as a main contribution only; it does not reject manipulator FDI with structured residuals and it does not touch the PR #2 result.",
             "- Gap resolution of the decision rules (partial gains below the 3/4 bar) was frozen in `decision_stage1rb.py` before any Stage 1R-B training result existed (see git history).",
             ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = common_parser("Stage 1R-B finalize (ledger, known issues, manifest, figures, reference copy, packages)")
    ap.add_argument("--kickoff-dir", default="/mnt/g/CERTO-FDI/01_frozen_sources/extracted/CERTO_FDI_STAGE1RB_EQUIVARIANT_CAPACITY_KICKOFF_20260815_6793482a")
    ap.add_argument("--skip-packages", action="store_true")
    ap.add_argument("--milestone", default="AUDIT")
    args = ap.parse_args(argv)
    st = Stage(args, "finalize")
    res = st.layout.results
    load = lambda n: json.loads((res / n).read_text()) if (res / n).exists() else {}
    ev, basis, M, tun, r0 = load("stage1rb_decision_evidence.json"), load("stage1rb_basis_audit_evidence.json"), load("stage1rb_metrics_summary.json"), load("stage1rb_tuning_selection.json"), load("stage1rb_r0_gate.json")
    base = st.base_row()
    write_csv(res / "stage1rb_claim_ledger.csv", claims_ledger(ev, basis, M, base))
    (res / "stage1rb_known_issues.md").write_text(known_issues_md(st, ev, basis, M, tun, r0), encoding="utf-8")
    manifest = {"run_id": st.layout.run_id, "git_sha": git_sha(st.repo_root), "config_sha256": st.cfg_sha, "dataset_manifest_sha256": st.manifest_sha, "timestamp_utc": utc_now(), "profile": st.cfg.get("profile"), "data_root": str(st.data_root), "decision": ev.get("decision"), "decision_reported": ev.get("decision_reported"), "basis_audit_verdict": basis.get("verdict"), "r0_gate": r0.get("decision"), "tuning_selection": {k: v.get("tag") for k, v in tun.items()}, "models": {k: {"n_params": v.get("n_params"), "n_final_runs": v.get("n_final_runs")} for k, v in M.items()}, "result_files": sorted(p.name for p in res.iterdir()), "frozen_inputs": st.cfg["frozen_inputs"]}
    write_json(res / "stage1rb_run_manifest.json", manifest)
    from certo_fdi.experiments.make_figures_stage1rb import make_all

    made = make_all(st.layout.run_root)
    st.log(f"figures: {made}")
    # reference copy + decision docs on the storage root
    storage = Path(args.storage_root)
    ref = storage / "05_reference_results" / "stage1r_b" / st.layout.run_id
    for sub in ("results", "figures", "provenance"):
        if (st.layout.run_root / sub).exists():
            shutil.copytree(st.layout.run_root / sub, ref / sub, dirs_exist_ok=True)
    (ref / "README.md").write_text(f"# Stage 1R-B reference results — {st.layout.run_id}\n\nDecision: {ev.get('decision_reported')}\nBasis audit: {basis.get('verdict')}\nGit: {manifest['git_sha']}\nRun root: {st.layout.run_root}\n", encoding="utf-8")
    docs = storage / "02_research_docs" / "stage1r_b" / "decisions"
    docs.mkdir(parents=True, exist_ok=True)
    for name in ("stage1rb_decision_memo.md", "stage1rb_basis_audit_memo.md", "stage1rb_known_issues.md", "stage1rb_decision_evidence.json"):
        if (res / name).exists():
            shutil.copyfile(res / name, docs / f"{st.layout.run_id}_{name}")
    st.log(f"reference copy at {ref}; decision docs at {docs}")
    if not args.skip_packages:
        from certo_fdi.packaging.build_review_package_stage1rb import build_packages

        results = build_packages(st.layout.run_root, st.repo_root, args.milestone, args.kickoff_dir)
        st.log("review packages: " + json.dumps([{k: r[k] for k in ("archive", "sha256", "size_bytes", "validation_status")} for r in results]))
    st.finish({"decision": ev.get("decision")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
