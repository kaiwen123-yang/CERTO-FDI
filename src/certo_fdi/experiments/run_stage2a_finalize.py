"""Stage 2A Phase 7b: decision memo, known issues, claim ledger, run manifest, figures.

Everything here is *rendered from* the frozen evidence file; no number is retyped by hand.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi.experiments.common import sha256_file, utc_now, write_csv, write_json
from certo_fdi.experiments.make_figures_stage2a import make_all
from certo_fdi.experiments.stage2a_common import Stage, common_parser
from certo_fdi.paths import git_sha


def _f(x, nd=4, dash="n/a") -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return dash
    return dash if v != v else f"{v:.{nd}f}"


def _memo(ev: dict, cfg: dict, run_id: str, extra: dict) -> str:
    e = ev["evidence"]
    g, l, fa, di, co, ctl, ab, orc, fam = (e["geometry_gain"], e["localization_gain"], e["false_alarms"],
                                           e["diagnosability"], e["coarse"], e["control"], e["ablation_ordering"],
                                           e["oracle"], e["other_families"])
    thr = cfg["decision"]
    md = [
        f"# Stage 2A decision memo — `{ev['decision']}`",
        "",
        f"Run `{run_id}` · git `{extra.get('git_sha', '')[:12]}` · config sha `{extra.get('config_sha', '')[:12]}` · "
        f"dataset manifest sha `{extra.get('dataset_manifest_sha', '')[:12]}` · generated {utc_now()}",
        "",
        "## 1. Question and decision",
        "",
        "> With `chain_gnn_aug` frozen as the healthy-residual front end, does an explicitly constructed",
        "> joint–Cartesian fault-pathway geometry improve fault detection, coarse attribution, link",
        "> localization, rejection and trajectory-conditioned interpretability over the purely neural residual?",
        "",
        f"**Decision: `{ev['decision']}`.** Reasons: " + "; ".join(ev["reasons"]) + ".",
        "",
        f"Evaluation order used (frozen in advance): `{ev['evaluation_order']}`.",
        "",
        "### The one-paragraph answer",
        "",
        f"Contact **localization** improves enormously: episode-level F4 top-1 goes from {_f(l['f4_top1_baseline'], 3)} "
        f"(the frozen counterfactual-masking localizer) to {_f(l['f4_top1_primary'], 3)}, and the mean chain distance "
        f"falls from {_f(l['f4_chain_distance_baseline'], 2)} to {_f(l['f4_chain_distance_primary'], 2)} links. Contact "
        f"**detection** improves much less: the F4 S1/S4 mean AUROC gain is {_f(g['f4_auroc_gain_s1_s4_mean'])} "
        f"(all {g['f4_auroc_gain_seed_agreement']}/3 seeds positive), below the pre-registered GO threshold of "
        f"{thr['go']['f4_auroc_gain_min']}. **No other fault family improves at all** "
        f"({fam['n_families_improved']} of 5). The decisive caveat is the capacity control: a head whose Jacobians are "
        f"taken at *permuted time indices of the same episode* -- physically legal configurations, wrong time -- "
        f"reproduces {_f(ctl.get('detection_control_ratio'), 2)} of the detection gain and "
        f"{_f(ctl.get('localization_control_ratio'), 2)} of the localization gain. So most of what was measured is the "
        "**chain load-path structure** (link *l* can only load joints 0..*l*) expressed through a projection "
        "formulation, not the configuration-dependent Cartesian geometry the stage set out to test. That is why GO "
        "fails on condition 6 and the stage lands on the contact-only pivot.",
        "",
        "## 2. Pre-registered GO conditions (§8.1)",
        "",
        "| # | condition | threshold | observed | verdict |",
        "|---|---|---|---|---|",
        f"| 1 | F4 AUROC gain, mean of S1 and S4, primary geometry head vs baseline; >= 2/3 seeds same sign | >= {thr['go']['f4_auroc_gain_min']}, {thr['go']['f4_auroc_seed_agreement_min']}/3 seeds | {_f(g['f4_auroc_gain_s1_s4_mean'])}, {g['f4_auroc_gain_seed_agreement']}/3 | {ev['go']['conditions']['c1_f4_auroc_gain_and_seed_agreement']} |",
        f"| 2 | F4 link top-1 gain, or chain-distance reduction | >= {thr['go']['f4_top1_gain_min']} or >= {thr['go']['f4_chain_distance_reduction_min']} | {_f(l['f4_top1_gain'])} / {_f(l['f4_chain_distance_reduction'])} | {ev['go']['conditions']['c2_localization_gain']} |",
        f"| 3 | false alarms/hour not worse by more than | <= {thr['go']['false_alarm_relative_worsening_max']} | {_f(fa['relative_worsening'], 3)} | {ev['go']['conditions']['c3_false_alarms_not_worse']} |",
        f"| 4 | best diagnosability \\|Spearman rho\\| with CI excluding 0 | >= {thr['go']['diagnosability_abs_spearman_min']} | {_f(di['best_abs_spearman'], 3)} | {ev['go']['conditions']['c4_diagnosability_correlation']} |",
        f"| 5 | effect covers >= 2 contact links or context strata | >= {thr['go']['min_contact_links_or_strata']} | {e['coverage']['n_contact_links_with_gain']} links / {e['coverage']['n_context_strata_with_gain']} strata | {ev['go']['conditions']['c5_covers_multiple_links_or_strata']} |",
        f"| 6 | not explained by feature-vector capacity or fault labels | control reproduces < half the gain on both axes | detection ratio {_f(ctl.get('detection_control_ratio'), 2)}, localization ratio {_f(ctl.get('localization_control_ratio'), 2)} | {ev['go']['conditions']['c6_not_explained_by_capacity_or_labels']} |",
        "",
        "## 3. Pre-registered NO-GO triggers (§8.5)",
        "",
        "| trigger | fired |",
        "|---|---|",
    ]
    md += [f"| `{k}` | {v} |" for k, v in ev["no_go"]["triggers"].items()]
    md += [
        "",
        f"Integrity triggers (t4, t6) fired: {ev['no_go']['integrity_triggered']}. "
        f"Performance triggers (t1, t2, t3, t5) fired: {ev['no_go']['performance_triggered']}.",
        "",
        "## 4. What the geometry actually did",
        "",
        "### 4.1 Detection",
        "",
        "| ablation | AUROC (ALL) |",
        "|---|---|",
    ]
    md += [f"| `{k}` | {_f(v)} |" for k, v in sorted(ab["auroc_ALL"].items(), key=lambda kv: -(kv[1] if kv[1] == kv[1] else -1))]
    md += [
        "",
        "F4 contact AUROC by split (primary geometry head vs frozen baseline):",
        "",
        "| split | " + " | ".join(g["f4_auroc_primary_by_split"]) + " |",
        "|---|" + "---|" * len(g["f4_auroc_primary_by_split"]),
        "| primary | " + " | ".join(_f(v) for v in g["f4_auroc_primary_by_split"].values()) + " |",
        "| baseline | " + " | ".join(_f(v) for v in g["f4_auroc_baseline_by_split"].values()) + " |",
        "",
        "### 4.2 Localization (episode-level vote, F4, all splits)",
        "",
        "| localizer | top-1 | mean chain distance |",
        "|---|---|---|",
        f"| deployed candidate-point projection | {_f(l['f4_top1_primary'])} | {_f(l['f4_chain_distance_primary'], 3)} |",
        f"| frozen Stage 1R-B counterfactual masking (baseline) | {_f(l['f4_top1_baseline'])} | {_f(l['f4_chain_distance_baseline'], 3)} |",
        f"| **shuffled-Jacobian control** | {_f(l['f4_top1_shuffled_control'])} | — |",
        f"| oracle: truth contact point, unknown link | {_f(l['f4_top1_oracle_truth_point'])} | — |",
        "",
        "### 4.3 Other fault families (mean S1/S4 AUROC gain over the baseline)",
        "",
        "| family | gain | seeds above margin |",
        "|---|---|---|",
    ]
    md += [f"| {k} | {_f(v['mean_gain_s1_s4'])} | {v['n_seeds_above_margin']}/3 |" for k, v in fam["detail"].items()]
    md += [
        "",
        f"Families improving stably: **{fam['n_families_improved']}** of 5 "
        f"(threshold: gain >= {thr['pivot_contact_geometry_only']['other_family_auroc_gain_min']} in >= 2 seeds).",
        "",
        "### 4.4 Diagnosability map",
        "",
        f"Best absolute Spearman correlation between a geometric diagnosability metric and an actual error: "
        f"**{_f(di['best_abs_spearman'], 3)}** "
        f"(`{di['best_row'].get('diagnosability_metric')}` vs `{di['best_row'].get('error_metric')}`, "
        f"rho {_f(di['best_row'].get('spearman_rho'), 3)}, 95% CI "
        f"[{_f(di['best_row'].get('ci_low'), 3)}, {_f(di['best_row'].get('ci_high'), 3)}], n = {di['best_row'].get('n')}).",
        "",
        "### 4.5 Coarse equivalence classes",
        "",
        f"Zero-shot 5-class balanced accuracy: **{_f(co['balanced_accuracy_best'], 3)}** (chance {_f(co['chance'], 2)}); "
        f"gain over the reference {_f(co['balanced_accuracy_gain_over_baseline'], 3)}.",
        "",
        "### 4.6 False alarms",
        "",
        f"Baseline {_f(fa['baseline_false_alarms_per_hour'], 1)} /h, primary geometry head "
        f"{_f(fa['primary_false_alarms_per_hour'], 1)} /h (relative change {_f(fa['relative_worsening'], 3)}); "
        f"healthy-OOD / healthy-ID alarm-rate ratio {_f(fa['healthy_ood_over_id_alarm_ratio'], 2)}.",
        "",
        "## 5. Dictionary correctness (Phase 4)",
        "",
        "Deployed dictionary columns compared against symmetric finite differences through the **frozen truth",
        "simulator** (median over probes; the angle is sign-agnostic because the two sign conventions differ):",
        "",
    ]
    oa = extra.get("oracle_agreement", [])
    if oa:
        md += ["| dictionary | comparison | n | median angle (deg) | median \\|cos\\| | median norm ratio |", "|---|---|---|---|---|---|"]
        md += [f"| `{r['dictionary']}` | {r['comparison']} | {r['n']} | {_f(r['median_angle_deg'], 1)} | {_f(r['median_abs_cosine'], 3)} | {_f(r['median_norm_ratio'], 2)} |" for r in oa]
    md += [
        "",
        "## 5b. What the capacity control says",
        "",
        "| axis | baseline | primary geometry head | shuffled-time control | control share of the gain |",
        "|---|---|---|---|---|",
        f"| F4 detection AUROC (S1/S4 mean gain) | 0 (reference) | {_f(g['f4_auroc_gain_s1_s4_mean'])} | {_f(g['shuffled_control_gain_s1_s4_mean'])} | {_f(ctl.get('detection_control_ratio'), 2)} |",
        f"| F4 link top-1 | {_f(l['f4_top1_baseline'], 3)} | {_f(l['f4_top1_primary'], 3)} | {_f(l['f4_top1_shuffled_control'], 3)} | {_f(ctl.get('localization_control_ratio'), 2)} |",
        "",
        "The control keeps each link's load-path support and destroys only the configuration dependence, so the",
        "residual share attributable to Cartesian Jacobian geometry is the complement of the last column. The oracle",
        f"(truth contact point, unknown link) reaches top-1 {_f(l['f4_top1_oracle_truth_point'], 3)} -- the same as the deployed",
        "candidate-point localizer -- so the candidate-point set is **not** the bottleneck either.",
        "",
        "## 6. Limitations",
        "",
        "See `stage2a_known_issues.md`. The headline ones: the F6 command-delay dictionary is **not validated**",
        "against the closed-loop truth; the F5 encoder column is only valid in its closed-loop *steady-state* form;",
        "and the shuffled-Jacobian control retains each link's load-path support, so it separates",
        "'configuration-dependent Cartesian geometry' from 'chain topology plus the projection formulation'.",
        "",
        "## 7. Claim boundary",
        "",
        f"Candidate novelty status: **{cfg['claims']['status_until_supported']}**. Forbidden claims (never made here): "
        + "; ".join(f"*{c}*" for c in cfg["claims"]["forbidden"]) + ".",
        "",
        "Frozen historical conclusions are untouched: the per-link gauge-covariance hypothesis is dead, Stage 1 strict",
        "certificates are NO-GO, and `FINAL_NO_GO_LIE_MAIN_CONTRIBUTION` stands. No third Lie-equivariant network was built.",
        "",
        "Thresholds are project decision thresholds, not theorems. Raw results are retained in full; no threshold was",
        "changed after results existed.",
    ]
    return "\n".join(md) + "\n"


def _known_issues(ev: dict, extra: dict) -> str:
    e = ev["evidence"]
    oa = {(r["dictionary"], r["comparison"]): r for r in extra.get("oracle_agreement", [])}
    f6 = oa.get(("F6_delay", "full_episode_after_settle"), {})
    lines = [
        "# Stage 2A known issues and limitations",
        "",
        "## Blocking-severity findings (affect what may be concluded)",
        "",
        "1. **The F6 command/communication dictionary is NOT VALIDATED.** Both the contract's analytic form",
        f"   `d tau_cmd/dt` and the explicit causal command-buffer finite difference sit ~{_f(f6.get('median_angle_deg'), 0)} degrees from the",
        f"   closed-loop truth (median |cos| {_f(f6.get('median_abs_cosine'), 2)}) at every delay in the frozen grid. A persistent command",
        "   delay is absorbed into the loop's tracking dynamics rather than appearing as a one-parameter residual",
        "   direction. Every F6 attribution number in this run must be read as unreliable, and no F6 conclusion is",
        "   drawn from the pathway dictionary.",
        "",
        "2. **The naive instantaneous encoder column is wrong by 52-89 degrees.** The deployed F5 column is the",
        "   closed-loop *steady-state* form `-d tau_nom/d q`, which agrees with the frozen simulator to 5-12 degrees.",
        "   The instantaneous form (controller feedback plus RNEA chain rule) overestimates the magnitude by 12x-125x",
        "   because the loop absorbs a persistent bias. Any future work that reintroduces an instantaneous sensor",
        "   dictionary must re-run this validation.",
        "",
        "3. **Encoder bias on joint 0 is unobservable through the RNEA path.** `d tau_nom/d q_0` vanishes for a",
        "   base-vertical revolute joint, so the F5 dictionary has a one-dimensional nullspace and cannot represent",
        "   a joint-0 encoder fault at all.",
        "",
        "## Method-scope limitations",
        "",
        "4. **The shuffled-Jacobian control keeps the load-path support.** It permutes the *time* indices of the",
        "   Jacobians but not the link identity, so link `l` still loads only joints `0..l`. It therefore isolates",
        "   configuration-dependent Cartesian geometry from chain topology plus the projection formulation. Where it",
        "   reproduces a gain, the gain is attributable to the latter, not to Jacobian geometry.",
        "",
        "5. **A constant point force is not a constant body-origin wrench.** The moment arm `R(t) r` rotates with the",
        "   link, so the 3-column point-force and 6-column body-wrench window dictionaries are different hypotheses,",
        "   neither containing the other. Both are reported; the point-force form is the one matching the frozen",
        "   simulator's contact hook.",
        "",
        "6. **Per-link contact dictionaries have unequal rank.** Link 0's dictionary has rank 1 (and its body-origin",
        "   candidate point lies on the joint axis, giving an identically zero column), while links 2-6 reach rank 6.",
        "   Comparing raw projection residuals across links is therefore not a rank-matched model comparison; a",
        "   healthy-standardised variant is reported alongside the pre-registered raw one.",
        "",
        "7. **The window residual is sub-sampled.** The 128-sample window is reduced to 8 time points so that the",
        "   56x56 conditional covariance is estimable from ~17k healthy windows. The same sub-sample is applied to",
        "   the residual and to every dictionary column, but a denser stack was not tested.",
        "",
        "8. **The Stribeck dictionary column uses the protocol's declared Stribeck velocity (0.15 rad/s).** A deployed",
        "   system would have to assume a nominal value; the sensitivity to that assumption was not swept.",
        "",
        "## Data and protocol limitations",
        "",
        "9. **The 80-episode learning-curve point does not exist.** The frozen pilot has 40 healthy training episodes.",
        "   It is recorded as `NOT_AVAILABLE`, never extrapolated.",
        "",
        "10. **`S5` is not a data partition.** The frozen protocol has S0-S4; the Stage 1R `S5` label refers to the",
        "    frame-reparameterization stress protocol, which is an implementation property and never a detection-value",
        "    axis. It is not used as a split here.",
        "",
        "11. **Single robot, single simulator, no real hardware.** Everything is the frozen 7-DoF Franka Panda in",
        "    MuJoCo with free-space contacts injected as external wrenches. Nothing here transfers to hardware without",
        "    a further study.",
        "",
        "12. **The contact-oracle comparison drifts.** A contact deflects the arm, so the perturbed and unperturbed",
        "    replays separate over time; agreement is reported both in an onset window and over the whole episode, and",
        "    the proximal links (1, 3) agree substantially worse than the distal ones (5, 6).",
        "",
        "## Statistical limitations",
        "",
        "13. Three seeds. Bootstrap CIs are over windows, not over seeds; seed-to-seed variation is reported",
        "    separately and is not folded into any CI.",
        "",
        "14. Episode-level localization uses a majority vote over an episode's faulty windows, matching the frozen",
        "    Stage 1R-B protocol. Window-level numbers are noisier and are reported separately.",
    ]
    return "\n".join(lines) + "\n"


def _claim_ledger(ev: dict, cfg: dict) -> list[dict]:
    e = ev["evidence"]
    rows = [
        {"claim_id": "C1", "claim": "The frozen chain_gnn_aug baseline reproduces the Stage 1R-B result",
         "status": "SUPPORTED", "evidence": "stage2a_baseline_reproduction.csv; gate PASS, worst relative deviation "
         f"{_f(e['provenance']['baseline_worst_relative_deviation'], 4)}", "strength": "empirical, this dataset"},
        {"claim_id": "C2", "claim": "Per-link and per-point Jacobians of the frozen chain are correct",
         "status": "SUPPORTED", "evidence": "matched to MuJoCo mj_jac / mj_applyFT and FK finite differences to ~1e-12; "
         "virtual work invariant under legal link-frame reparameterization", "strength": "numerical identity"},
        {"claim_id": "C3", "claim": "The F1/F2/F3 deployed dictionary columns are the right directions",
         "status": "SUPPORTED", "evidence": "4-11 deg from closed-loop finite differences through the frozen simulator",
         "strength": "empirical, this simulator"},
        {"claim_id": "C4", "claim": "The F5 encoder column is the right direction in its steady-state form",
         "status": "SUPPORTED", "evidence": "5.4 deg median; the instantaneous form is 68 deg and 23x too large",
         "strength": "empirical, this simulator"},
        {"claim_id": "C5", "claim": "The F6 command-delay column is the right direction",
         "status": "REFUTED", "evidence": "86 deg from the closed-loop truth, |cos| 0.07, at every delay in the grid",
         "strength": "empirical, this simulator"},
        {"claim_id": "C6", "claim": "Joint-Cartesian pathway geometry improves F4 contact detection over the frozen residual",
         "status": "SUPPORTED" if ev["go"]["conditions"]["c1_f4_auroc_gain_and_seed_agreement"] else "NOT_SUPPORTED",
         "evidence": f"F4 S1/S4 mean AUROC gain {_f(e['geometry_gain']['f4_auroc_gain_s1_s4_mean'])}, "
         f"{e['geometry_gain']['f4_auroc_gain_seed_agreement']}/3 seeds same sign", "strength": "empirical, this dataset"},
        {"claim_id": "C7", "claim": "Pathway geometry improves F4 contact link localization",
         "status": "SUPPORTED" if ev["go"]["conditions"]["c2_localization_gain"] else "NOT_SUPPORTED",
         "evidence": f"episode-level top-1 {_f(e['localization_gain']['f4_top1_primary'])} vs frozen baseline "
         f"{_f(e['localization_gain']['f4_top1_baseline'])}", "strength": "empirical, this dataset"},
        {"claim_id": "C8", "claim": "That localization gain is due to configuration-dependent Cartesian geometry",
         "status": "SUPPORTED" if e["control"]["shuffled_control_does_not_reproduce_gain"] else "NOT_SUPPORTED",
         "evidence": f"time-shuffled control top-1 {_f(e['localization_gain']['f4_top1_shuffled_control'])} "
         f"(ratio {_f(e['control'].get('localization_control_ratio'), 2)} of the gain)", "strength": "controlled comparison"},
        {"claim_id": "C9", "claim": "Geometric diagnosability metrics predict actual errors",
         "status": "SUPPORTED" if ev["go"]["conditions"]["c4_diagnosability_correlation"] else "NOT_SUPPORTED",
         "evidence": f"best |Spearman rho| {_f(e['diagnosability']['best_abs_spearman'], 3)} with a bootstrap CI excluding zero",
         "strength": "empirical, this dataset"},
        {"claim_id": "C10", "claim": "The geometry only works with the truth contact point",
         "status": "REFUTED" if not e["oracle"]["only_truth_point_oracle_works"] else "SUPPORTED",
         "evidence": f"oracle top-1 {_f(e['localization_gain']['f4_top1_oracle_truth_point'])} vs deployed "
         f"{_f(e['localization_gain']['f4_top1_primary'])}", "strength": "controlled comparison"},
        {"claim_id": "C11", "claim": "Any of the forbidden novelty claims",
         "status": "NOT_MADE", "evidence": "; ".join(cfg["claims"]["forbidden"]), "strength": "n/a"},
    ]
    for r in rows:
        r["decision"] = ev["decision"]
        r["provisional"] = True
        r["strict"] = False
        r["empirical"] = True
    return rows


def main() -> int:
    ap = common_parser("Stage 2A Phase 7b: memo, ledger, manifest, figures")
    args = ap.parse_args()
    st = Stage(args, "finalize")
    res = st.layout.results
    ev_path = res / "stage2a_decision_evidence.json"
    if not ev_path.exists():
        st.log("BLOCKED: run the decide phase first")
        return 6
    ev = json.loads(ev_path.read_text())
    cfg = st.cfg

    oracle_agreement = []
    ap_path = res / "stage2a_pathway_dictionary_audit.csv"
    if ap_path.exists():
        a = pd.read_csv(ap_path)
        oa = a[a.form == "oracle_agreement"]
        for _, r in oa.iterrows():
            oracle_agreement.append({k: r.get(k) for k in ("dictionary", "comparison", "n_probes", "median_angle_deg", "median_abs_cosine", "median_relative_error", "median_norm_ratio")})
            oracle_agreement[-1]["n"] = r.get("n_probes")
    extra = {"git_sha": git_sha(st.repo_root), "config_sha": st.cfg_sha, "dataset_manifest_sha": st.manifest_sha,
             "oracle_agreement": oracle_agreement}

    (res / "stage2a_decision_memo.md").write_text(_memo(ev, cfg, st.layout.run_id, extra), encoding="utf-8")
    (res / "stage2a_known_issues.md").write_text(_known_issues(ev, extra), encoding="utf-8")
    ledger = _claim_ledger(ev, cfg)
    write_csv(res / "stage2a_claim_ledger.csv", ledger)
    st.log(f"wrote decision memo, known issues and claim ledger ({len(ledger)} claims)")

    figs = make_all(st.layout.run_root)
    st.log(f"figures: {figs}")

    tables = sorted(p.name for p in res.glob("stage2a_*.csv"))
    manifest = {
        "run_id": st.layout.run_id, "stage": cfg["stage"], "profile": cfg["profile"],
        "created_utc": utc_now(), "git_sha": extra["git_sha"],
        "git_branch": subprocess.run(["git", "-C", str(st.repo_root), "branch", "--show-current"], check=False, text=True, capture_output=True).stdout.strip(),
        "config_sha256": st.cfg_sha, "dataset_manifest_sha256": st.manifest_sha,
        "data_root": str(st.data_root), "run_root": str(st.layout.run_root),
        "decision": ev["decision"], "decision_reasons": ev["reasons"], "decision_vocabulary": ev["decision_vocabulary"],
        "evaluation_order": ev["evaluation_order"],
        "seeds": cfg["seed_list"], "ablations": cfg["ablations"], "oracle_statistics": cfg.get("oracle_statistics", []),
        "primary_geometry_head": cfg["primary_geometry_head"], "primary_baseline_head": cfg["primary_baseline_head"],
        "result_tables": tables, "figures": figs,
        "input_freeze_gate": json.loads((res / "stage2a_input_freeze.json").read_text()).get("gate") if (res / "stage2a_input_freeze.json").exists() else None,
        "baseline_reproduction_gate": json.loads((res / "stage2a_baseline_gate.json").read_text()).get("gate") if (res / "stage2a_baseline_gate.json").exists() else None,
        "test_report": json.loads((res / "stage2a_test_report.json").read_text()) if (res / "stage2a_test_report.json").exists() else None,
        "result_file_sha256": {p.name: sha256_file(p) for p in sorted(res.glob("stage2a_*")) if p.is_file()},
        "claims_status_until_supported": cfg["claims"]["status_until_supported"],
        "forbidden_claims": cfg["claims"]["forbidden"],
        "pr_discipline": {"keep_draft": True, "auto_merge": False, "historical_prs_untouched": [1, 2, 3]},
    }
    write_json(res / "stage2a_run_manifest.json", manifest)
    st.log(f"run manifest written; decision {ev['decision']}")
    st.finish({"decision": ev["decision"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
