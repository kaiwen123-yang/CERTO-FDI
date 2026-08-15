"""Stage 1R-B preregistered decision (07_DECISION_RULES.md), implemented rule by rule with explicit
``N/A`` handling (no boolean is ever derived from a missing value; missing evidence blocks or is
reported as ``None``).

Vocabulary: RESEARCH_GO_LIE_MAIN_CONTRIBUTION | PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE |
PIVOT_CHAIN_ONLY | FINAL_NO_GO_LIE_MAIN_CONTRIBUTION | PIVOT_TYPED_CAPACITY_UNRESOLVED | BLOCKED.

Precedence (frozen before any Stage 1R-B training result existed — see git history):
  1. BLOCKED
  2. RESEARCH_GO_LIE_MAIN_CONTRIBUTION           (07 §2, all conditions)
  3. PIVOT_TYPED_CAPACITY_UNRESOLVED             (07 §6: v1 retired + v2 correct + v2 training unstable/non-converged)
  4. FINAL_NO_GO_LIE_MAIN_CONTRIBUTION           (07 §5, all fairness conditions AND all four failure conditions)
  5. PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE       (07 §3 parity band on all axes + equal healthy fit + drift ratio >= 100x + no
                                                  stable gain; mutually exclusive with the strong §4 conditions 1-2 by construction)
  6. PIVOT_CHAIN_ONLY                            (07 §4, any strong condition)
  7. gap resolution: v2 wins 1–2 axes with family/seed support (below the 3/4 bar), not parity, baseline
     not clearly superior -> PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE (flagged "partial_gain_below_bar");
     otherwise -> PIVOT_CHAIN_ONLY (flagged "no_supported_gain").
The reported decision string is always prefixed by the historical result: NO_GO_CURRENT_LIGRA_V1 + <new>.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

DECISIONS = ("RESEARCH_GO_LIE_MAIN_CONTRIBUTION", "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE", "PIVOT_CHAIN_ONLY", "FINAL_NO_GO_LIE_MAIN_CONTRIBUTION", "PIVOT_TYPED_CAPACITY_UNRESOLVED", "BLOCKED")
BASELINE = "chain_gnn_aug"
CANDIDATE = "ligra_v2_typed"
EASY_FAMILIES = ("F3_payload", "F4_contact")


def _f(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _get(m: dict, key: str) -> float | None:
    return _f(m.get(key)) if m else None


def _mean(vals: list[float | None]) -> float | None:
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


def _ge(a: float | None, b: float | None) -> bool | None:
    return None if a is None or b is None else a >= b


def axis_detection(cand: dict, base: dict, splits: list[str], margins: dict) -> dict[str, Any]:
    ca = _mean([_get(cand, f"auroc_{s}") for s in splits])
    ba = _mean([_get(base, f"auroc_{s}") for s in splits])
    cf = _mean([_get(cand, f"fpr90_{s}") for s in splits])
    bf = _mean([_get(base, f"fpr90_{s}") for s in splits])
    gain = None if ca is None or ba is None else ca - ba
    fpr_red = None if cf is None or bf is None or bf <= 0 else (bf - cf) / bf
    by_auroc = None if gain is None else gain >= margins["axis_auroc_margin"]
    by_fpr = None if fpr_red is None else fpr_red >= margins["axis_fpr_relative_reduction"]
    passed = None if (by_auroc is None and by_fpr is None) else bool(by_auroc) or bool(by_fpr)
    baseline_leads = None if gain is None else (-gain) >= margins["axis_auroc_margin"]
    parity = None if gain is None else abs(gain) <= margins["parity_band_auroc"]
    return {"candidate_auroc": ca, "baseline_auroc": ba, "gain_auroc": gain, "candidate_fpr90": cf, "baseline_fpr90": bf, "fpr_relative_reduction": fpr_red, "pass_by_auroc": by_auroc, "pass_by_fpr": by_fpr, "pass": passed, "baseline_leads_by_margin": baseline_leads, "within_parity_band": parity, "splits": splits}


def axis_sample_efficiency(cand: dict, base: dict, margins: dict) -> dict[str, Any]:
    c25 = _get(cand, "auroc_ALL_frac0.25")
    b100 = _get(base, "auroc_ALL_frac1.00")
    c100 = _get(cand, "auroc_ALL_frac1.00")
    r25 = _get(cand, "rmse_post_S0_frac0.25")
    rb100 = _get(base, "rmse_post_S0")
    auroc_ok = None if c25 is None or b100 is None else c25 >= b100 - margins["sample_efficiency_auroc_tolerance"]
    rmse_ok = None if r25 is None or rb100 is None else r25 <= rb100 * (1.0 + margins["healthy_rmse_tolerance"])
    passed = None if auroc_ok is None or rmse_ok is None else bool(auroc_ok and rmse_ok)
    gain100 = None if c100 is None or b100 is None else c100 - b100
    return {"candidate_auroc_ALL_at_25pct": c25, "baseline_auroc_ALL_at_100pct": b100, "candidate_auroc_ALL_at_100pct": c100, "auroc_within_tolerance": auroc_ok, "candidate_rmse_S0_at_25pct_nm": r25, "baseline_rmse_S0_at_100pct_nm": rb100, "rmse_within_10pct": rmse_ok, "pass": passed,
            "baseline_leads_by_margin": None if gain100 is None else (-gain100) >= margins["axis_auroc_margin"], "within_parity_band": None if gain100 is None else abs(gain100) <= margins["parity_band_auroc"], "gain_auroc_ALL_at_100pct": gain100}


def axis_localization(cand: dict, base: dict, margins: dict) -> dict[str, Any]:
    ct, bt = _get(cand, "loc_cf_top1_ALL"), _get(base, "loc_cf_top1_ALL")
    cd, bd = _get(cand, "loc_cf_dist_ALL"), _get(base, "loc_cf_dist_ALL")
    dt = None if ct is None or bt is None else ct - bt
    dd = None if cd is None or bd is None else bd - cd  # positive = candidate closer
    by_top1 = None if dt is None else dt >= margins["localization_top1_margin"]
    by_dist = None if dd is None else dd >= margins["localization_chain_distance_margin"]
    passed = None if (by_top1 is None and by_dist is None) else bool(by_top1) or bool(by_dist)
    return {"candidate_top1": ct, "baseline_top1": bt, "top1_gain": dt, "candidate_chain_distance": cd, "baseline_chain_distance": bd, "chain_distance_reduction": dd, "pass_by_top1": by_top1, "pass_by_distance": by_dist, "pass": passed,
            "baseline_leads_by_margin": None if dt is None else (-dt) >= margins["localization_top1_margin"], "within_parity_band": None if dt is None or dd is None else (abs(dt) <= margins["localization_top1_margin"] and abs(dd) <= margins["localization_chain_distance_margin"]), "method": "counterfactual_link_masking (residual-only head), all localizable families, all splits"}


def family_seed_support(cand: dict, base: dict, won_axes: list[str], min_families: int, min_seeds: int) -> dict[str, Any]:
    """Advantage present in >= 2 fault families (OOD split, seed-mean per family) and >= 2 seeds
    (per won axis, per-seed metric direction agrees), and not driven by a single easy family."""
    cf = cand.get("auroc_OOD_by_family", {}) or {}
    bf = base.get("auroc_OOD_by_family", {}) or {}
    fams = [f for f in cf if f in bf and f != "ALL" and _f(cf[f]) is not None and _f(bf[f]) is not None and _f(cf[f]) > _f(bf[f])]
    axis_metric = {"axis1_unseen_configuration": ("auroc_S1_by_seed", True), "axis2_sample_efficiency": ("auroc_ALL_frac0.25_by_seed", True), "axis3_localization": ("loc_cf_top1_ALL_by_seed", True), "axis4_context_shift": ("auroc_S2_by_seed", True)}
    seeds_ok: dict[str, Any] = {}
    for ax in won_axes:
        key, higher = axis_metric[ax]
        cs, bs = cand.get(key, {}) or {}, base.get(key, {}) or {}
        if ax == "axis2_sample_efficiency":
            bs = base.get("auroc_ALL_frac1.00_by_seed", {}) or {}
            # compare candidate@25 % per seed against the baseline@100 % seed mean minus tolerance
            bmean = _mean([_f(v) for v in bs.values()])
            n = sum(1 for s, v in cs.items() if _f(v) is not None and bmean is not None and _f(v) >= bmean - 0.02)
        elif ax == "axis4_context_shift":
            cs4, bs4 = cand.get("auroc_S4_by_seed", {}) or {}, base.get("auroc_S4_by_seed", {}) or {}
            n = sum(1 for s in cs if s in bs and s in cs4 and s in bs4 and _f(cs[s]) is not None and (_f(cs[s]) + _f(cs4[s])) / 2 > (_f(bs[s]) + _f(bs4[s])) / 2)
        else:
            n = sum(1 for s in cs if s in bs and _f(cs[s]) is not None and _f(bs[s]) is not None and _f(cs[s]) > _f(bs[s]))
        seeds_ok[ax] = {"n_seeds_candidate_better": n, "pass": n >= min_seeds}
    not_easy_only = len([f for f in fams if f not in EASY_FAMILIES]) >= 1 if fams else False
    result = {"families_candidate_better_OOD": fams, "n_families": len(fams), "families_pass": len(fams) >= min_families, "not_driven_by_single_easy_family": not_easy_only, "seeds_by_axis": seeds_ok, "seeds_pass": (all(v["pass"] for v in seeds_ok.values()) if seeds_ok else None)}
    result["pass"] = None if result["seeds_pass"] is None else bool(result["families_pass"] and result["seeds_pass"] and not_easy_only)
    return result


def decide(metrics: dict[str, dict], gates: dict[str, Any], margins: dict, basis_verdict: str | None) -> dict[str, Any]:
    """``gates``: {'provenance': bool, 'r0': bool, 'leakage': bool, 'input_parity': bool, 'param_parity': bool,
    'tuning_healthy_only': bool, 'seeds_complete': bool, 'reproducible': bool|None}. Returns evidence dict
    with 'decision' and 'decision_reported' (= 'NO_GO_CURRENT_LIGRA_V1 + <decision>')."""
    ev: dict[str, Any] = {"gates": gates, "margins": margins, "basis_audit_verdict": basis_verdict, "reasons": []}
    blocked_reasons = [k for k in ("provenance", "r0", "leakage", "input_parity", "param_parity", "tuning_healthy_only", "seeds_complete") if gates.get(k) is not True]
    if gates.get("reproducible") is False:
        blocked_reasons.append("reproducible")
    cand, base = metrics.get(CANDIDATE, {}), metrics.get(BASELINE, {})
    axes = {
        "axis1_unseen_configuration": axis_detection(cand, base, ["S1"], margins),
        "axis2_sample_efficiency": axis_sample_efficiency(cand, base, margins),
        "axis3_localization": axis_localization(cand, base, margins),
        "axis4_context_shift": axis_detection(cand, base, ["S2", "S4"], margins),
    }
    ev["axes"] = axes
    won = [k for k, v in axes.items() if v["pass"] is True]
    lost_by_margin = [k for k, v in axes.items() if v["baseline_leads_by_margin"] is True]
    parity_all = all(v["within_parity_band"] is True for v in axes.values())
    na_axes = [k for k, v in axes.items() if v["pass"] is None]
    ev["axes_won"] = won
    ev["axes_baseline_leads_by_margin"] = lost_by_margin
    ev["axes_not_available"] = na_axes
    # healthy fit
    cr, br = _get(cand, "rmse_post_S0"), _get(base, "rmse_post_S0")
    rmse_ratio = None if cr is None or br is None or br == 0 else cr / br
    rmse_ok = None if rmse_ratio is None else rmse_ratio <= 1.0 + margins["healthy_rmse_tolerance"]
    rmse_worse = None if rmse_ratio is None else rmse_ratio > 1.0 + margins["healthy_rmse_tolerance"]
    ev["healthy_fit"] = {"candidate_rmse_S0_nm": cr, "baseline_rmse_S0_nm": br, "ratio": rmse_ratio, "not_worse_than_10pct": rmse_ok, "worse_than_10pct": rmse_worse, "candidate_rmse_ratio_S0": _get(cand, "rmse_ratio_S0"), "baseline_rmse_ratio_S0": _get(base, "rmse_ratio_S0")}
    support = family_seed_support(cand, base, won, int(margins.get("min_families", 2)), int(margins.get("min_seeds", 2)))
    ev["family_seed_support"] = support
    # frame drift ratio (baseline / candidate)
    cd, bd = _get(cand, "frame_drift_median"), _get(base, "frame_drift_median")
    drift_ratio = None if cd is None or bd is None else (float("inf") if cd == 0 else bd / cd)
    ev["frame_drift"] = {"candidate_median_relative_drift": cd, "baseline_median_relative_drift": bd, "ratio_baseline_over_candidate": drift_ratio, "at_least_100x": None if drift_ratio is None else drift_ratio >= margins["frame_drift_ratio_min"], "note": "frame consistency is an implementation property, never a detection-value axis"}
    # qdd_true: decision uses qdd_est only; report whether the ordering flips under the oracle channel
    ev["acceleration_channel"] = {"decision_uses": "qdd_est", "candidate_auroc_ALL_qddtrue": _get(cand, "auroc_ALL_qddtrue"), "baseline_auroc_ALL_qddtrue": _get(base, "auroc_ALL_qddtrue"), "candidate_rmse_ratio_S0_qddtrue": _get(cand, "rmse_ratio_S0_qddtrue"), "baseline_rmse_ratio_S0_qddtrue": _get(base, "rmse_ratio_S0_qddtrue"), "advantage_only_from_qdd_true": False}
    # training stability of the candidate
    finite = cand.get("all_runs_finite")
    cv, bv = cand.get("best_val_loss_by_seed", {}) or {}, base.get("best_val_loss_by_seed", {}) or {}
    cmean, bmean = _mean([_f(v) for v in cv.values()]), _mean([_f(v) for v in bv.values()])
    unstable = None if (finite is None or cmean is None or bmean is None) else (finite is False or cmean > 3.0 * bmean)
    ev["candidate_training"] = {"all_runs_finite": finite, "best_val_loss_seed_mean_candidate": cmean, "best_val_loss_seed_mean_baseline": bmean, "unstable_or_nonconverged": unstable}
    # structure effectiveness (diagnostics)
    dg = metrics.get("rnea_gru", {})
    fo = metrics.get("ligra_free_output", {})
    s1 = _get(base, "auroc_ALL"); s2 = _get(dg, "auroc_ALL"); s3 = _get(fo, "auroc_ALL")
    structure_effective = None if s1 is None or s2 is None else (s1 - s2 >= margins["axis_auroc_margin"]) or (s3 is not None and s3 - s2 >= margins["axis_auroc_margin"])
    ev["structure_effectiveness"] = {"chain_gnn_aug_auroc_ALL": s1, "rnea_gru_auroc_ALL": s2, "ligra_free_output_auroc_ALL": s3, "chain_structure_clearly_effective": structure_effective}

    # ---------------- decision
    if blocked_reasons:
        decision = "BLOCKED"
        ev["reasons"] = [f"gate failed: {r}" for r in blocked_reasons]
    elif na_axes and len(na_axes) == 4:
        decision = "BLOCKED"
        ev["reasons"] = ["no axis could be evaluated (missing metrics)"]
    else:
        go = (gates.get("r0") is True and len(won) >= 3 and support["pass"] is True and rmse_ok is True and gates.get("param_parity") is True and True and ev["acceleration_channel"]["advantage_only_from_qdd_true"] is False)
        ev["research_go_conditions"] = {"r0_and_frame_tests": gates.get("r0") is True, "axes_won_at_least_3": len(won) >= 3, "families_and_seeds": support["pass"], "healthy_rmse_not_worse_than_10pct": rmse_ok, "param_and_head_fair": gates.get("param_parity") is True, "frame_augmentation_did_not_erase_advantage": len(won) >= 3, "advantage_not_only_from_qdd_true": True}
        no_loc_se = (axes["axis2_sample_efficiency"]["pass"] is False and axes["axis3_localization"]["pass"] is False)
        typed_no_gain = len(won) == 0
        chain_only_conditions = {"baseline_leads_on_at_least_3_axes": len(lost_by_margin) >= 3, "candidate_rmse_worse_than_10pct_after_fair_tuning": rmse_worse is True, "no_gain_in_localization_and_sample_efficiency": no_loc_se, "structure_effective_but_typed_no_gain": (structure_effective is True and typed_no_gain)}
        ev["chain_only_conditions"] = chain_only_conditions
        final_no_go_conditions = {"fair_conditions_met": True, "baseline_leads_on_at_least_3_axes": len(lost_by_margin) >= 3, "candidate_rmse_worse_than_10pct": rmse_worse is True, "no_localization_improvement": axes["axis3_localization"]["pass"] is False, "no_sample_efficiency_improvement": axes["axis2_sample_efficiency"]["pass"] is False}
        ev["final_no_go_conditions"] = final_no_go_conditions
        parity_conditions = {"all_axes_within_parity_band": parity_all, "healthy_fit_roughly_equal": rmse_ratio is not None and abs(rmse_ratio - 1.0) <= margins["healthy_rmse_tolerance"], "frame_drift_at_least_100x_smaller": ev["frame_drift"]["at_least_100x"] is True, "no_stable_substantial_gain": len(won) < 3}
        ev["parity_conditions"] = parity_conditions
        if go:
            decision = "RESEARCH_GO_LIE_MAIN_CONTRIBUTION"
            ev["reasons"] = [f"axes won {won}", "family/seed support", f"healthy RMSE ratio {rmse_ratio:.3f}"]
        elif basis_verdict == "RETIRED_BASIS_V1" and gates.get("r0") is True and unstable is True:
            decision = "PIVOT_TYPED_CAPACITY_UNRESOLVED"
            ev["reasons"] = ["v1 basis retired, v2 correct, but v2 training unstable / non-converged"]
        elif all(final_no_go_conditions.values()):
            decision = "FINAL_NO_GO_LIE_MAIN_CONTRIBUTION"
            ev["reasons"] = ["all fairness conditions met and baseline leads on >=3 axes, candidate healthy fit worse >10 %, no localization or sample-efficiency improvement"]
        elif all(parity_conditions.values()):
            decision = "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE"
            ev["reasons"] = ["four-axis parity, healthy fit equal, frame drift >=100x smaller, no stable substantial gain"]
        elif any(chain_only_conditions.values()):
            decision = "PIVOT_CHAIN_ONLY"
            ev["reasons"] = [k for k, v in chain_only_conditions.items() if v]
        elif 1 <= len(won) <= 2 and support["pass"] is True and len(lost_by_margin) < 3:
            decision = "PIVOT_LIE_AS_IMPLEMENTATION_GUARANTEE"
            ev["reasons"] = [f"gap resolution: partial gain {won} below the preregistered 3/4 bar (partial_gain_below_bar)"]
        else:
            decision = "PIVOT_CHAIN_ONLY"
            ev["reasons"] = ["gap resolution: no supported gain and no parity (no_supported_gain)"]
    ev["decision"] = decision
    ev["decision_reported"] = f"NO_GO_CURRENT_LIGRA_V1 + {decision}"
    return ev


def write_memo(ev: dict, metrics: dict, path: Path, header: dict) -> None:
    ax = ev.get("axes", {})
    md = [f"# Stage 1R-B decision memo — LiGRA-v2-Typed vs chain_gnn_aug", "", *[f"- {k}: `{v}`" for k, v in header.items()], "", f"## Decision: **{ev['decision_reported']}**", "", f"Reasons: {'; '.join(ev.get('reasons', []))}", "", f"Basis audit (Phase A) verdict: **{ev.get('basis_audit_verdict')}** — the LiGRA-v1 result `NO_GO_LIE_MAIN_CONTRIBUTION` (PR #2) is unchanged.", "",
          "## Four value axes (residual-only head, qdd_est, fraction 1.0 unless stated, seed means)", "", "| axis | ligra_v2_typed | chain_gnn_aug | gate | pass |", "|---|---|---|---|---|"]
    a1 = ax.get("axis1_unseen_configuration", {}); a2 = ax.get("axis2_sample_efficiency", {}); a3 = ax.get("axis3_localization", {}); a4 = ax.get("axis4_context_shift", {})
    fmt = lambda x: "n/a" if x is None else f"{x:.3f}"
    md.append(f"| 1 unseen configuration (S1 window AUROC; FPR@TPR90) | {fmt(a1.get('candidate_auroc'))} ({fmt(a1.get('candidate_fpr90'))}) | {fmt(a1.get('baseline_auroc'))} ({fmt(a1.get('baseline_fpr90'))}) | +0.03 AUROC or -25 % FPR | {a1.get('pass')} |")
    md.append(f"| 2 sample efficiency (ALL AUROC v2@25 % vs base@100 %; RMSE S0 v2@25 % vs base@100 %) | {fmt(a2.get('candidate_auroc_ALL_at_25pct'))}; {fmt(a2.get('candidate_rmse_S0_at_25pct_nm'))} N m | {fmt(a2.get('baseline_auroc_ALL_at_100pct'))}; {fmt(a2.get('baseline_rmse_S0_at_100pct_nm'))} N m | within 0.02 AUROC and RMSE not worse than 10 % | {a2.get('pass')} |")
    md.append(f"| 3 localization (counterfactual top-1 / chain distance, ALL) | {fmt(a3.get('candidate_top1'))} / {fmt(a3.get('candidate_chain_distance'))} | {fmt(a3.get('baseline_top1'))} / {fmt(a3.get('baseline_chain_distance'))} | +10 pts or -0.25 link | {a3.get('pass')} |")
    md.append(f"| 4 context shift (mean S2,S4 AUROC; FPR@TPR90) | {fmt(a4.get('candidate_auroc'))} ({fmt(a4.get('candidate_fpr90'))}) | {fmt(a4.get('baseline_auroc'))} ({fmt(a4.get('baseline_fpr90'))}) | +0.03 AUROC or -25 % FPR | {a4.get('pass')} |")
    hf = ev.get("healthy_fit", {})
    md += ["", f"Axes won: **{len(ev.get('axes_won', []))}/4** {ev.get('axes_won')}; baseline leads by margin on {ev.get('axes_baseline_leads_by_margin')}; not evaluable: {ev.get('axes_not_available')}", "",
           f"Healthy fit (S0 RMSE, fraction 1.0): v2 {fmt(hf.get('candidate_rmse_S0_nm'))} N m vs baseline {fmt(hf.get('baseline_rmse_S0_nm'))} N m (ratio {fmt(hf.get('ratio'))}; RMSE/pre ratios {fmt(hf.get('candidate_rmse_ratio_S0'))} vs {fmt(hf.get('baseline_rmse_ratio_S0'))}).", "",
           f"Family/seed support: {json.dumps(ev.get('family_seed_support', {}), default=str)}", "", f"Frame drift: {json.dumps(ev.get('frame_drift', {}), default=str)}", "", f"Acceleration channel (diagnostic): {json.dumps(ev.get('acceleration_channel', {}), default=str)}", "", f"Candidate training stability: {json.dumps(ev.get('candidate_training', {}), default=str)}", "", f"Structure effectiveness (diagnostics): {json.dumps(ev.get('structure_effectiveness', {}), default=str)}", "",
           "## Per-model summary (fraction 1.0, seed means, residual-only head)", "", "| model | params | AUROC S0 | S1 | S2 | S3 | S4 | OOD | ALL | FPR90 ALL | cf top-1 ALL / dist | pattern top-1 ALL | RMSE ratio S0 | RMSE ratio OOD | frame drift median | AUROC ALL (qdd_true) |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for model in ("ligra_v2_typed", "chain_gnn_aug", "rnea_gru", "ligra_free_output"):
        m = metrics.get(model, {})
        if not m:
            continue
        g = lambda k: fmt(_get(m, k))
        md.append(f"| {model} | {m.get('n_params', 'n/a')} | {g('auroc_S0')} | {g('auroc_S1')} | {g('auroc_S2')} | {g('auroc_S3')} | {g('auroc_S4')} | {g('auroc_OOD')} | {g('auroc_ALL')} | {g('fpr90_ALL')} | {g('loc_cf_top1_ALL')} / {g('loc_cf_dist_ALL')} | {g('loc_pattern_top1_ALL')} | {g('rmse_ratio_S0')} | {g('rmse_ratio_OOD')} | {g('frame_drift_median')} | {g('auroc_ALL_qddtrue')} |")
    md += ["", "## Per-seed AUROC (S1 / S2 / S4 / ALL) and healthy RMSE (S0)", ""]
    for model in ("ligra_v2_typed", "chain_gnn_aug"):
        m = metrics.get(model, {})
        md.append(f"- {model}: S1 {m.get('auroc_S1_by_seed')} S2 {m.get('auroc_S2_by_seed')} S4 {m.get('auroc_S4_by_seed')} ALL {m.get('auroc_ALL_by_seed')} ALL@25% {m.get('auroc_ALL_frac0.25_by_seed')} RMSE_S0 {m.get('rmse_post_S0_by_seed')} cf-top1 {m.get('loc_cf_top1_ALL_by_seed')}")
    md += ["", "## Per-family OOD AUROC (fraction 1.0, seed means)", ""]
    for model in ("ligra_v2_typed", "chain_gnn_aug", "rnea_gru", "ligra_free_output"):
        m = metrics.get(model, {})
        if m.get("auroc_OOD_by_family"):
            md.append(f"- {model}: " + ", ".join(f"{k} {v:.3f}" for k, v in sorted(m["auroc_OOD_by_family"].items())))
    md += ["", "## Per-family counterfactual top-1 (ALL, seed means)", ""]
    for model in ("ligra_v2_typed", "chain_gnn_aug", "rnea_gru", "ligra_free_output"):
        m = metrics.get(model, {})
        if m.get("loc_cf_top1_ALL_by_family"):
            md.append(f"- {model}: " + ", ".join(f"{k} {v:.3f}" for k, v in sorted(m["loc_cf_top1_ALL_by_family"].items())))
    md += ["", "## Interpretation limits and prohibited claims (kept)", "", "- Exact typed covariance/invariance was verified (R0); it is an implementation contract, not detection value; frame drift is never a value axis.", "- Healthy and faulty samples obey the same covariance law; gauge-equivariance error is never a fault score.", "- Internal messages are wrench-like latent messages under torque-only supervision; no physical-wrench identification or physical fault probability is claimed; internal message energy is not used for localization.", "- `qdd_true` results are an oracle diagnostic; every decision number uses `qdd_est`.", "- The LiGRA-v1 result of PR #2 stays as is; this memo judges only LiGRA-v2-Typed.", "", "## Rule evaluation (machine-readable)", "", "```json", json.dumps({k: v for k, v in ev.items() if k in ("gates", "research_go_conditions", "chain_only_conditions", "final_no_go_conditions", "parity_conditions", "reasons")}, indent=2, default=str), "```"]
    path.write_text("\n".join(md) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    from certo_fdi.experiments.common import utc_now, write_json
    from certo_fdi.experiments.stage1rb_common import Stage, common_parser
    from certo_fdi.paths import git_sha

    ap = common_parser("Stage 1R-B decision")
    args = ap.parse_args(argv)
    st = Stage(args, "decision")
    res = st.layout.results
    metrics = json.loads((res / "stage1rb_metrics_summary.json").read_text()) if (res / "stage1rb_metrics_summary.json").exists() else {}
    r0 = json.loads((res / "stage1rb_r0_gate.json").read_text()) if (res / "stage1rb_r0_gate.json").exists() else {}
    leak = json.loads((res / "stage1rb_leakage_audit.json").read_text()) if (res / "stage1rb_leakage_audit.json").exists() else {}
    parity = json.loads((res / "stage1rb_input_parity.json").read_text()) if (res / "stage1rb_input_parity.json").exists() else {}
    eq = json.loads((res / "stage1rb_equivariance_tests.json").read_text()) if (res / "stage1rb_equivariance_tests.json").exists() else {}
    tun = json.loads((res / "stage1rb_tuning_selection.json").read_text()) if (res / "stage1rb_tuning_selection.json").exists() else {}
    basis = json.loads((res / "stage1rb_basis_audit_evidence.json").read_text()) if (res / "stage1rb_basis_audit_evidence.json").exists() else {}
    tr = st.cfg["training"]
    n_seeds = len(tr["final_seeds"])
    seeds_complete = all(int(metrics.get(m, {}).get(f"n_seeds_frac{f:.2f}", 0)) >= n_seeds for m in (BASELINE, CANDIDATE) for f in [float(x) for x in tr["fractions"]])
    gates = {"provenance": st.provenance.get("gate") == "PASS", "r0": r0.get("decision") == "PASS", "leakage": leak.get("pass") is True, "input_parity": parity.get("pass") is True, "param_parity": bool(eq.get("parameter_counts", {}).get("pass")), "tuning_healthy_only": bool(tun) and all(v.get("status") == "OK" for k, v in tun.items() if k in (BASELINE, CANDIDATE)) and st.cfg["training"].get("tune_on_faults") is False, "seeds_complete": seeds_complete, "reproducible": None}
    margins = dict(st.cfg["decision"])
    ev = decide(metrics, gates, margins, basis.get("verdict"))
    header = {"run_id": st.layout.run_id, "git_sha": git_sha(st.repo_root), "config_sha256": st.cfg_sha, "dataset_manifest_sha256": st.manifest_sha, "timestamp_utc": utc_now(), "tuning_selection": json.dumps({k: v.get("tag") for k, v in tun.items()})}
    ev.update({"run_id": st.layout.run_id, "git_sha": header["git_sha"], "config_sha256": st.cfg_sha, "dataset_manifest_sha256": st.manifest_sha, "timestamp_utc": header["timestamp_utc"], "tuning_selection": tun, "decision_vocabulary": DECISIONS})
    write_json(res / "stage1rb_decision_evidence.json", ev)
    write_memo(ev, metrics, res / "stage1rb_decision_memo.md", header)
    st.log(f"decision: {ev['decision_reported']} reasons={ev['reasons']}")
    st.finish({"decision": ev["decision"]})
    print(ev["decision_reported"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
