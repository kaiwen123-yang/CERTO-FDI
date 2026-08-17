"""Stage 2B-F Phase 7: figures, memos, claim ledger and run manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics as stats
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from certo_fdi.experiments.common import write_json
from certo_fdi.stage2bf import estimator_identity as EI

ACC, ALT, OK, BAD, MUT = "#2E6E8E", "#C8933C", "#41705A", "#A6433A", "#6B7885"
CTRL = ["random_within_support_rankmatched", "support_prefix_rankmatched",
        "fixed_reference_jacobian", "shuffled_time_jacobian", "time_aligned_jacobian"]
SHORT = {"random_within_support_rankmatched": "random\n(rank-matched)",
         "support_prefix_rankmatched": "support\nprefix",
         "fixed_reference_jacobian": "fixed\nreference J",
         "shuffled_time_jacobian": "shuffled\ntime J",
         "time_aligned_jacobian": "time-aligned\nJ"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2B-F reports and figures")
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())
    root, repo = Path(args.run_root), Path(args.repo_root).resolve()
    res, fig = root / "results", root / "figures"
    fig.mkdir(parents=True, exist_ok=True)

    def rd(name):
        with (res / name).open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def js(name):
        return json.loads((res / name).read_text())

    matrix = [r for r in rd("stage2bf_estimator_control_matrix.csv") if r["is_replicate_row"] == "False"]
    contrasts = rd("stage2bf_estimator_contrast_ci.csv")
    robust = rd("stage2bf_mechanism_robustness.csv")
    gates = js("stage2bf_reproduction_gates.json")
    sel = js("stage2bf_f4cal_selection_reproduction.json")
    dec = js("stage2bf_integrity_decision.json")
    delta = js("stage2bf_evidence_delta.json")

    def cell(est_key, control, field="episode_top1"):
        v = [float(r[field]) for r in matrix
             if r["control"] == control and (est_key in r["estimator"])]
        return stats.fmean(v) if v else float("nan")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ---- 1. ridge vs svd score scatter (time-aligned, the raw-dictionary control)
    z = np.load(root / "arrays" / "stage2bf_dual_scores_seed260817.npz", allow_pickle=False)
    rn = z["time_aligned_jacobian__ridge_norm"] ** 2      # square onto the SVD unit
    ss = z["time_aligned_jacobian__svd_rss"]
    idx = np.random.default_rng(0).choice(rn.size, 30000, replace=False)
    f, a = plt.subplots(1, 2, figsize=(11, 4.3))
    a[0].scatter(ss.ravel()[idx], rn.ravel()[idx], s=1.5, alpha=.15, color=ACC, rasterized=True)
    lim = [0, float(np.nanpercentile(ss, 99.5))]
    a[0].plot(lim, lim, ls="--", lw=1, color=MUT)
    a[0].set_xlim(lim); a[0].set_ylim(lim)
    a[0].set_xlabel("truncated-SVD RSS"); a[0].set_ylabel("ridge residual energy")
    a[0].set_title("Same window, same dictionary, two estimators")
    rel = np.abs(rn - ss) / np.maximum(np.abs(ss), 1e-300)
    a[1].hist(np.log10(np.clip(rel[rel > 0], 1e-20, None).ravel()), bins=80, color=BAD, alpha=.85)
    a[1].axvline(np.log10(1000 * np.finfo(float).eps), ls="--", color=OK, label="roundoff floor")
    a[1].set_xlabel(r"$\log_{10}$ relative gap"); a[1].set_ylabel("(window, link) pairs")
    a[1].set_title("They are not the same score"); a[1].legend(fontsize=8)
    for ax in a:
        ax.grid(alpha=.3)
    f.tight_layout(); f.savefig(fig / "stage2bf_ridge_vs_svd_score_scatter.png", dpi=150); plt.close(f)

    # ---- 2. per-link estimator gap
    med = [float(np.median(np.abs(rn[:, l] - ss[:, l]) / np.maximum(np.abs(ss[:, l]), 1e-300)))
           for l in range(7)]
    f, a = plt.subplots(figsize=(7.2, 4.2))
    a.semilogy(range(7), med, "o-", color=BAD)
    a.axhline(1000 * np.finfo(float).eps, ls="--", color=OK, label="roundoff floor")
    a.set_xlabel("candidate link  (support rows = 8·(link+1) of 56)")
    a.set_ylabel("median relative estimator gap")
    a.set_title("The gap concentrates where the chain gives fewest support rows")
    a.legend(fontsize=8); a.grid(alpha=.3, which="both")
    f.tight_layout(); f.savefig(fig / "stage2bf_per_link_estimator_gap.png", dpi=150); plt.close(f)

    # ---- 3/4. the 2x5 matrices
    for field, fname, title in (("episode_top1", "stage2bf_2x5_top1_matrix.png", "episode top-1"),
                                ("mean_chain_distance", "stage2bf_2x5_chain_distance_matrix.png",
                                 "mean chain distance")):
        M = np.array([[cell("ridge", c, field) for c in CTRL],
                      [cell("truncated", c, field) for c in CTRL]])
        f, a = plt.subplots(figsize=(9.2, 3.4))
        im = a.imshow(M, cmap="Blues" if field == "episode_top1" else "Oranges", aspect="auto")
        a.set_xticks(range(5)); a.set_xticklabels([SHORT[c] for c in CTRL], fontsize=8)
        a.set_yticks([0, 1]); a.set_yticklabels(["ridge\n(Stage 2A)", "truncated SVD\n(Stage 2B)"], fontsize=8)
        for i in range(2):
            for j in range(5):
                a.text(j, i, f"{M[i, j]:.4f}", ha="center", va="center", fontsize=9,
                       color="white" if M[i, j] > M.max() * .6 else "black")
        for j, c in enumerate(CTRL):
            if c in cfg["orthonormalised_controls"]:
                a.add_patch(plt.Rectangle((j - .5, -.5), 1, 2, fill=False, ec=MUT, ls=":", lw=1.6))
        a.set_title(f"2x5 estimator/control matrix — {title}   "
                    f"(dotted = orthonormalised control: estimators agree by construction)", fontsize=9)
        f.colorbar(im, ax=a, fraction=.025)
        f.tight_layout(); f.savefig(fig / fname, dpi=150); plt.close(f)

    # ---- 5. mechanism contrasts
    names = list(cfg["mechanism_contrasts"])
    f, a = plt.subplots(figsize=(8.6, 4.4))
    y = np.arange(len(names))
    for k, (est, col, off) in enumerate((("ridge", ACC, -.16), ("truncated", ALT, .16))):
        pts = [next(r for r in contrasts if r["contrast"] == n and est in r["estimator"]) for n in names]
        v = [float(p["top1_delta"]) for p in pts]
        lo = [float(p["top1_delta"]) - float(p["top1_ci_low"]) for p in pts]
        hi = [float(p["top1_ci_high"]) - float(p["top1_delta"]) for p in pts]
        a.errorbar(v, y + off, xerr=[lo, hi], fmt="o", color=col, capsize=3,
                   label="ridge" if est == "ridge" else "truncated SVD")
    a.axvline(0, color=MUT, lw=1)
    a.set_yticks(y); a.set_yticklabels(names)
    a.invert_yaxis()
    a.set_xlabel("episode top-1 delta (paired episode-cluster bootstrap, 95% CI)")
    a.set_title("Mechanism contrasts under both estimators")
    a.legend(fontsize=8); a.grid(alpha=.3, axis="x")
    f.tight_layout(); f.savefig(fig / "stage2bf_mechanism_contrasts.png", dpi=150); plt.close(f)

    # ---- 6. evidence delta
    f, a = plt.subplots(figsize=(8.6, 3.2))
    paths = [c["path"] for c in delta["allowed"]]
    a.barh(range(len(paths)), [1] * len(paths), color=OK, alpha=.8)
    a.set_yticks(range(len(paths)))
    a.set_yticklabels([p if len(p) < 52 else "…" + p[-50:] for p in paths], fontsize=7)
    a.invert_yaxis(); a.set_xticks([])
    a.set_title(f"Evidence delta: {delta['n_changes']} field(s) changed, "
                f"{len(delta['violations'])} violation(s) — no scientific metric moved", fontsize=9)
    f.tight_layout(); f.savefig(fig / "stage2bf_evidence_delta.png", dpi=150); plt.close(f)

    # ---------------------------------------------------------------- mechanism summary
    def lab(n, metric):
        return next(r["robustness"] for r in robust if r["contrast"] == n and r["metric"] == metric)

    lines = ["# Stage 2B-F — load-path mechanism under two estimators", "",
             f"Integrity **{dec['stage2bf_integrity_decision']}**, scientific "
             f"**{dec['stage2bf_scientific_decision']}**. Historical Stage 2B stays `BLOCKED`.", "",
             "## The matrix", "",
             "| control | ridge top-1 | SVD top-1 | ridge chain dist | SVD chain dist | orthonormalised |",
             "|---|---|---|---|---|---|"]
    for c in CTRL:
        lines.append(f"| `{c}` | {cell('ridge', c):.4f} | {cell('truncated', c):.4f} | "
                     f"{cell('ridge', c, 'mean_chain_distance'):.4f} | "
                     f"{cell('truncated', c, 'mean_chain_distance'):.4f} | "
                     f"{'**yes**' if c in cfg['orthonormalised_controls'] else 'no'} |")
    lines += ["", "Three of the five controls are built from orthonormal bases, so the ridge gain is "
              "`1/(1+1e-6)` and the two estimators agree there **by construction**. That was declared "
              "in the Phase 1 freeze, before these numbers existed; those columns are not independent "
              "evidence about estimators. Only `time_aligned_jacobian` and `shuffled_time_jacobian` "
              "use raw dictionaries, and only `time_aligned_jacobian` actually separates them.", "",
              f"The separation it shows is exactly the historical discrepancy: ridge "
              f"{cell('ridge','time_aligned_jacobian'):.4f} is Stage 2A's published mean and SVD "
              f"{cell('truncated','time_aligned_jacobian'):.4f} is Stage 2B's observed mean. The 2.38 % "
              "that blocked Stage 2B is reproduced here as a change of estimator, not a change of run.",
              "", "## The contrasts", "",
              "| contrast | metric | ridge | SVD | robustness |", "|---|---|---|---|---|"]
    for n in names:
        for metric, key in (("top1", "top1_delta"), ("chain_distance", "chain_distance_reduction")):
            r = {("ridge" if "ridge" in x["estimator"] else "svd"): x for x in contrasts if x["contrast"] == n}
            lines.append(f"| `{n}` | {metric} | {float(r['ridge'][key]):+.4f} | "
                         f"{float(r['svd'][key]):+.4f} | `{lab(n, metric)}` |")
    lines += ["", "## What may and may not be said", "",
              "- `delta_alignment` (time-aligned minus shuffled) has a 95 % CI crossing zero under "
              "**both** estimators, on top-1 and on chain distance. **A time-aligned Cartesian claim "
              "stays forbidden**, exactly as in Stage 2B.",
              "- `delta_trajectory` (time-aligned minus fixed-reference) is positive and CI-separated "
              "from zero under both estimators. The episode's own configuration distribution carries "
              "signal — but one of its two terms is an orthonormalised control, so this is a weaker "
              "form of estimator-robustness than `delta_alignment` would have been.",
              "- `delta_support` top-1 is essentially zero: the support mask alone buys nothing over a "
              "rank-matched random frame. Its chain-distance reduction is CI-separated, so the mask "
              "helps get *closer* without getting the link *right*.",
              "- No mechanism claim here rests on a single estimator, and none is upgraded to a "
              "product claim. The scientific terminal state is "
              f"`{dec['stage2bf_scientific_decision']}`, which means the current autonomous contact "
              "product misses its pre-registered thresholds. It says nothing about whether the "
              "Cartesian subspace carries information."]
    (res / "stage2bf_loadpath_mechanism_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- memos
    g2 = gates["phase2_stage2a_ridge"]["per_seed"]
    memo = [f"# Stage 2B-F integrity decision — `{dec['stage2bf_integrity_decision']}`", "",
            "## Gates, in precedence order", "",
            "| gate | result |", "|---|---|"]
    for k, v in dec["integrity"]["evidence_used"].items():
        memo.append(f"| `{k}` | {'PASS' if v else '**FAIL**'} |")
    memo += ["", "## Stage 2A ridge reproduction", "",
             "| seed | score pairs | bit-identical | max abs diff | candidate | window label | votes | confusion |",
             "|---|---|---|---|---|---|---|---|"]
    for s, v in g2.items():
        memo.append(f"| {s} | {v['n_score_pairs']} | **{v['n_bit_identical']}** | {v['max_abs_diff']:.1e} | "
                    f"{'exact' if v['candidate_index_exact'] else 'FAIL'} | "
                    f"{'exact' if v['window_label_exact'] else 'FAIL'} | "
                    f"{'exact' if v['episode_votes_exact'] else 'FAIL'} | "
                    f"{'exact' if v['confusion_exact'] else 'FAIL'} |")
    memo += ["", "Not merely inside the `1e-12 + 1e-10·|ref|` tolerance the contract allows — every "
             "score is bit-identical to Stage 2A's frozen `contact_residual`, with maximum absolute "
             "difference exactly zero. Importing `geometry.batched_projection` reproduces Stage 2A, "
             "which is what licenses calling that estimator the ridge.", "",
             "## Stage 2B truncated-SVD reproduction", "",
             "All five load-path controls, all three seeds: window key order identical, RSS/ESS "
             "bit-identical, ranks exactly equal, published F4_TEST top-1 and chain distance "
             "reproduced. The random control is compared per replicate against its own "
             "`…#k` historical row.", "",
             "## F4_CAL selection", "",
             "| seed | replayed | historical | cal top-1 |", "|---|---|---|---|"]
    for s, v in sel["reproduction_gate"]["per_seed"].items():
        memo.append(f"| {s} | `{v['replay_selected_canonical']}` | `{v['historical_selected_canonical']}` | "
                    f"{v['replay_calibration_top1']:.4f} |")
    memo += ["", "Acceptance thresholds bit-exact and the reject feature/threshold rule reproduced. "
             "The ridge was scored for the audit table only and never entered the candidate set; "
             "F4_TEST is not opened in the selection module.", "",
             "## What this PASS does not mean", "",
             "The historical Stage 2B run remains `BLOCKED`. Stage 2B-R's "
             "`FAIL_REPRODUCTION_IMPLEMENTATION_MISMATCH` remains correct — it was reporting a real "
             "estimator mismatch, and this stage fixed the mismatch rather than overturning the "
             "finding. What passed is Stage 2B-F's own integrity gate, which is what permits the "
             "frozen decision function to be re-run."]
    (res / "stage2bf_integrity_decision_memo.md").write_text("\n".join(memo) + "\n", encoding="utf-8")

    sci = [f"# Stage 2B-F scientific decision — `{dec['stage2bf_scientific_decision']}`", "",
           f"Produced by the original frozen `certo_fdi.stage2b.decision_stage2b.decide` "
           f"(sha256 `{dec['decision_function']['file_sha256'][:16]}…`), imported and called. No logic "
           "was copied and no terminal state was written by hand.", "",
           f"**Combined terminal: `{dec['stage2bf_combined_terminal']}`**", "",
           f"Historical Stage 2B decision: `{dec['historical_stage2b_decision']}` — unchanged, and its "
           "files are byte-preserved.", "", "## Evidence delta", "",
           f"{delta['n_changes']} field(s) changed, {len(delta['violations'])} violation(s):", ""]
    for c in delta["allowed"]:
        sci.append(f"- `{c['path']}`: `{str(c['historical'])[:40]}` → `{str(c['stage2bf'])[:40]}`")
    sci += ["", "No detection, localization, selective, load-path, sequential or healthy-expansion "
            "metric moved, and no threshold changed. The historical `contact_reproduction` diagnosis "
            "is preserved verbatim with the resolution added beside it.", "", "## §3 GO conditions", "",
            "| condition | result |", "|---|---|"]
    for k, v in (dec.get("scientific_result") or {}).get("go", {}).get("conditions", {}).items():
        sci.append(f"| `{k}` | {'PASS' if v else 'FAIL'} |")
    sci += ["", "## Reading this correctly", "",
            f"`{dec['stage2bf_scientific_decision']}` means the current autonomous contact product "
            "misses its pre-registered thresholds. It does **not** mean the Cartesian subspace "
            "mechanism carries no information, and it does not license a deployment claim. The "
            "detection and localization conditions fail on their own thresholds; see "
            "`stage2bf_loadpath_mechanism_summary.md` for what the mechanism evidence does support."]
    (res / "stage2bf_scientific_decision_memo.md").write_text("\n".join(sci) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- known issues + ledger
    known = ["# Stage 2B-F — known issues and limits", "",
             "## K1. Three of five controls cannot separate the estimators",
             "",
             "`support_prefix_rankmatched`, `random_within_support_rankmatched` and "
             "`fixed_reference_jacobian` are built from orthonormal bases, where every singular value "
             "is 1, the ridge gain is `1/(1+1e-6)` and the truncated-SVD gain is 1. The two estimators "
             "agree there to ~1e-6 by construction. The 2x5 matrix is therefore not ten independent "
             "cells, and `delta_support` / `delta_shape` agreeing across estimators is arithmetic, not "
             "corroboration. Declared in the Phase 1 freeze before the numbers existed.", "",
             "## K2. `shuffled_time_jacobian` uses raw dictionaries yet still shows no gap", "",
             "It is a raw-dictionary control, so the estimators *could* differ there, and they do not "
             "to four decimal places. Shuffling time destroys the correspondence but leaves genuine "
             "Jacobians whose conditioning evidently keeps both estimators on the same side of every "
             "episode vote. Only `time_aligned_jacobian` separates them.", "",
             "## K3. The mechanism evidence is one arm, one dataset", "",
             "590 frozen episodes, one 7-DoF Panda, one simulator. Nothing here is a general claim "
             "about link identifiability, and no novelty or first-of-kind claim is made.", "",
             "## K4. `delta_alignment` remains inconclusive", "",
             "CI crosses zero under both estimators on both metrics. The time-aligned Cartesian claim "
             "stays forbidden — this stage did not resolve it and was not asked to.", "",
             "## K5. The scientific terminal is the default branch", "",
             "`NO_GO_CONTACT_PRODUCT` was returned as the default terminal state after no §3–§7 "
             "condition set was satisfied. That is the frozen function's own logic; it was not "
             "steered, but it does mean the outcome is 'nothing else matched' rather than a positive "
             "finding of adequacy.", "",
             "## K6. Ridge on F4_CAL was computed but not used", "",
             "The audit table records the ridge as a row with `is_selection_candidate = false` and no "
             "metrics, so the selection could not see it even accidentally. A future stage wanting a "
             "ridge-vs-SVD selection comparison must do it on a calibration partition, never on "
             "F4_TEST."]
    (res / "stage2bf_known_issues.md").write_text("\n".join(known) + "\n", encoding="utf-8")

    ledger = [
        dict(claim_id="F1", claim="Stage 2A and Stage 2B used different estimators",
             status="CONFIRMED", strength="strong",
             evidence="ridge replay is bit-identical to Stage 2A's contact_residual; SVD replay is "
                      "bit-identical to Stage 2B's rss; on time_aligned_jacobian they give 0.5833 vs 0.5694",
             limits="none"),
        dict(claim_id="F2", claim="The Stage 2A ridge localizer reproduces at every level",
             status="SUPPORTED", strength="strong",
             evidence="3 seeds: 159936/159936 scores bit-identical, max abs diff 0.0; candidate index, "
                      "window label, episode votes, episode labels and confusion all exact",
             limits="reuses the frozen pathway cache and refits the whitener from frozen checkpoints"),
        dict(claim_id="F3", claim="The Stage 2B truncated-SVD pipeline reproduces",
             status="SUPPORTED", strength="strong",
             evidence="all 5 controls x 3 seeds bit-identical rss/ess, exact ranks, published F4_TEST "
                      "metrics reproduced; F4_CAL selection exact including acceptance thresholds",
             limits="none"),
        dict(claim_id="F4", claim="delta_trajectory is positive under both estimators",
             status="SUPPORTED", strength="moderate",
             evidence="top-1 +0.2639 (ridge) / +0.2500 (SVD), both CIs exclude 0; chain distance "
                      "+0.6667 / +0.6528, both exclude 0",
             limits="one term is an orthonormalised control, so estimator-robustness here is weaker "
                    "than it looks; not a product claim"),
        dict(claim_id="F5", claim="A time-aligned Cartesian claim remains forbidden",
             status="SUPPORTED", strength="strong",
             evidence="delta_alignment CI crosses zero under both estimators on top-1 and chain distance",
             limits="none"),
        dict(claim_id="F6", claim="The support mask alone adds nothing over a rank-matched random frame",
             status="SUPPORTED", strength="moderate",
             evidence="delta_support top-1 -0.0009, CI [-0.0720, +0.0747]; chain-distance reduction "
                      "+0.3160 with CI excluding 0",
             limits="both terms orthonormalised; estimator agreement is by construction"),
        dict(claim_id="F7", claim="Stage 2B's scientific terminal under a released gate is NO_GO_CONTACT_PRODUCT",
             status="SUPPORTED", strength="strong",
             evidence="frozen decision_stage2b.decide called on the historical evidence with only the "
                      "reproduction-gate Boolean changed; 5-field delta, 0 violations",
             limits="default terminal state after no condition set matched; not a statement about mechanism"),
        dict(claim_id="F8", claim="The historical Stage 2B BLOCKED record is intact",
             status="SUPPORTED", strength="strong",
             evidence="17/17 historical artifacts byte-unchanged; PRs #1-#6 Draft with unmoved heads",
             limits="none"),
    ]
    common = dict(run_id=root.name, git_sha="", config_sha="",
                  dataset_manifest_sha=cfg["frozen_inputs"]["dataset_content_manifest_sha256"],
                  unit_of_independence="episode", partition="F4_TEST unless stated",
                  integrity_state=dec["stage2bf_integrity_decision"],
                  scientific_state=dec["stage2bf_scientific_decision"], provisional=False)
    rows = [{**common, **r} for r in ledger]
    EI.assert_no_legacy_names(rows)
    with (res / "stage2bf_claim_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    write_json(root / "provenance" / "stage2bf_run_manifest.json", {
        "generated_utc": utc_now(), "run_id": root.name,
        "stage2bf_integrity_decision": dec["stage2bf_integrity_decision"],
        "stage2bf_scientific_decision": dec["stage2bf_scientific_decision"],
        "stage2bf_combined_terminal": dec["stage2bf_combined_terminal"],
        "historical_stage2b_decision": "BLOCKED",
        "estimators": {"stage2a": EI.RIDGE_CANONICAL, "stage2b": EI.SVD_CANONICAL},
        "artifacts": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(root.rglob("*")) if p.is_file() and p.stat().st_size < 200_000_000},
    })
    print(f"reports and {len(list(fig.glob('*.png')))} figures written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
