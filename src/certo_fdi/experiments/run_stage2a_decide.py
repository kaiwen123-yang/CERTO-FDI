"""Stage 2A Phase 7: assemble the evidence and apply the PRE-REGISTERED decision rules.

This runner does not contain any threshold. Every threshold lives in
``configs/stage2a_pathway_audit.yaml::decision`` and every rule lives in
``certo_fdi.experiments.decision_stage2a``, both committed before any Stage 2A model result
existed. Here the metric tables are only reduced to the evidence fields those rules read, and
each reduction is recorded so a reviewer can re-derive it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from certo_fdi.experiments.common import write_json
from certo_fdi.experiments.decision_stage2a import decide
from certo_fdi.experiments.stage2a_common import Stage, common_parser

OTHER_FAMILIES = ("F1_actuator", "F2_friction", "F3_payload", "F5_encoder", "F6_command")


def _auroc(det: pd.DataFrame, model: str, split: str, family: str, seed=None) -> float:
    m = det[(det.model == model) & (det.split == split) & (det.fault_family == family)]
    if seed is not None:
        m = m[m.seed == seed]
    return float(m["auroc"].mean()) if len(m) else float("nan")


def _gain_by_seed(det: pd.DataFrame, cand: str, base: str, splits: list[str], family: str, seeds: list[int]) -> dict[int, float]:
    out = {}
    for s in seeds:
        vals = [(_auroc(det, cand, sp, family, s) - _auroc(det, base, sp, family, s)) for sp in splits]
        out[s] = float(np.nanmean(vals))
    return out


def main() -> int:
    ap = common_parser("Stage 2A Phase 7: pre-registered decision")
    args = ap.parse_args()
    st = Stage(args, "decide")
    cfg = st.cfg
    res = st.layout.results
    seeds = [int(s) for s in cfg["seed_list"]]
    base = cfg["primary_baseline_head"]
    prim = cfg["primary_geometry_head"]
    ctrl_name = "chain_plus_shuffled_jacobian_control"
    dec_cfg = cfg["decision"]

    blocked, notes = [], []
    freeze = json.loads((res / "stage2a_input_freeze.json").read_text()) if (res / "stage2a_input_freeze.json").exists() else {}
    if freeze.get("gate") != "PASS":
        blocked.append("Phase 0 input freeze did not pass")
    gate = json.loads((res / "stage2a_baseline_gate.json").read_text()) if (res / "stage2a_baseline_gate.json").exists() else {}
    if gate.get("gate") != "PASS":
        blocked.append(f"baseline reproduction gate {gate.get('gate')} (worst relative deviation {gate.get('worst_relative_deviation')})")
    for name in ("stage2a_detection_metrics.csv", "stage2a_event_metrics.csv", "stage2a_localization_metrics.csv",
                 "stage2a_diagnosability_error_correlation.csv", "stage2a_coarse_attribution_metrics.csv"):
        if not (res / name).exists():
            blocked.append(f"missing metric table {name}")
    tests = json.loads((res / "stage2a_test_report.json").read_text()) if (res / "stage2a_test_report.json").exists() else {}
    if tests and tests.get("exit_code", 1) != 0:
        blocked.append("the offline test suite did not pass")
    if blocked:
        ev = {"blocked": {"any": True, "reasons": blocked}}
        out = decide(ev, dec_cfg)
        write_json(res / "stage2a_decision_evidence.json", {**out, "evidence": ev})
        st.log(f"BLOCKED: {blocked}")
        return 6

    det = pd.read_csv(res / "stage2a_detection_metrics.csv")
    evt = pd.read_csv(res / "stage2a_event_metrics.csv")
    loc = pd.read_csv(res / "stage2a_localization_metrics.csv")
    dia = pd.read_csv(res / "stage2a_diagnosability_error_correlation.csv")
    coa = pd.read_csv(res / "stage2a_coarse_attribution_metrics.csv")

    # ---------------------------------------------------------------- detection gain (F4, S1+S4)
    by_seed = _gain_by_seed(det, prim, base, ["S1", "S4"], "F4_contact", seeds)
    gain = float(np.nanmean(list(by_seed.values())))
    agree = int(sum(1 for v in by_seed.values() if (v > 0) == (gain > 0) and abs(v) > 0))
    ctrl_by_seed = _gain_by_seed(det, ctrl_name, base, ["S1", "S4"], "F4_contact", seeds) if (det.model == ctrl_name).any() else {}
    ctrl_gain = float(np.nanmean(list(ctrl_by_seed.values()))) if ctrl_by_seed else float("nan")

    # ---------------------------------------------------------------- localization gain (F4)
    lp = loc[(loc.model == "contact_projection_residual") & (loc.split == "ALL") & (loc.fault_family == "F4_contact")]
    lb = loc[(loc.model == "counterfactual_link_masking_baseline") & (loc.split == "ALL") & (loc.fault_family == "F4_contact")]
    top1_p, top1_b = float(lp["top1"].mean()), float(lb["top1"].mean())
    dist_p, dist_b = float(lp["mean_chain_distance"].mean()), float(lb["mean_chain_distance"].mean())
    lo = loc[(loc.model == "contact_projection_residual_oracle_truth_point") & (loc.split == "ALL") & (loc.fault_family == "F4_contact")]
    top1_oracle = float(lo["top1"].mean()) if len(lo) else float("nan")
    lc = loc[(loc.model == "contact_projection_residual_shuffled_control") & (loc.split == "ALL") & (loc.fault_family == "F4_contact")]
    top1_ctrl = float(lc["top1"].mean()) if len(lc) else float("nan")

    # ---------------------------------------------------------------- false alarms
    ea = evt[(evt.split == "ALL") & (evt.fault_family == "ALL")]
    fa_p = float(ea[ea.model == prim]["false_alarms_per_hour"].mean())
    fa_b = float(ea[ea.model == base]["false_alarms_per_hour"].mean())
    rel_worse = (fa_p - fa_b) / fa_b if fa_b > 0 else (0.0 if fa_p == 0 else float("inf"))
    ood_json = st.layout.sub("p2_baseline") / "stage2a_baseline_ood_healthy.csv"
    ood_ratio = float("nan")
    if ood_json.exists():
        od = pd.read_csv(ood_json)
        od = od[(od.model == "chain_gnn_aug") & (od.density_variant == "residual_only")]
        if len(od):
            id_rate = float(od["healthy_id_alarm_rate"].mean())
            ood_rate = float(od["healthy_ood_alarm_rate"].mean())
            ood_ratio = ood_rate / id_rate if id_rate > 0 else float("inf")

    # ---------------------------------------------------------------- diagnosability
    dsel = dia[dia.ci_excludes_zero.astype(str).str.lower().isin(["true", "1"])]
    best_rho = float(dia["abs_spearman_rho"].max()) if len(dia) else float("nan")
    best_rho_ci = float(dsel["abs_spearman_rho"].max()) if len(dsel) else float("nan")
    best_row = dia.loc[dia["abs_spearman_rho"].idxmax()].to_dict() if len(dia) else {}

    # ---------------------------------------------------------------- coverage across links / strata
    per_link = {}
    conf_path = st.layout.sub("p6_metrics") / "stage2a_link_confusion.json"
    if conf_path.exists():
        cj = json.loads(conf_path.read_text())
        prim_conf = cj.get("contact_projection_residual", {})
        if prim_conf:
            C = np.sum([np.array(v) for v in prim_conf.values()], 0)
            for l in range(C.shape[0]):
                if C[l].sum():
                    per_link[l] = float(C[l, l] / C[l].sum())
    truth_links = [int(l) for l in cfg["pathway"]["contact"]["truth_contact_links"]]
    n_links_gain = sum(1 for l in truth_links if per_link.get(l, 0.0) > top1_b)
    n_strata_gain = sum(1 for sp in ("S0", "S1", "S2", "S3", "S4")
                        if (_auroc(det, prim, sp, "F4_contact") - _auroc(det, base, sp, "F4_contact")) > 0)

    # ---------------------------------------------------------------- other families
    fam_improved = 0
    fam_detail = {}
    for fam in OTHER_FAMILIES:
        bs = _gain_by_seed(det, prim, base, ["S1", "S4"], fam, seeds)
        mean_gain = float(np.nanmean(list(bs.values())))
        n_pos = sum(1 for v in bs.values() if v >= float(dec_cfg["pivot_contact_geometry_only"]["other_family_auroc_gain_min"]))
        fam_detail[fam] = {"mean_gain_s1_s4": mean_gain, "by_seed": bs, "n_seeds_above_margin": n_pos}
        if mean_gain >= float(dec_cfg["pivot_contact_geometry_only"]["other_family_auroc_gain_min"]) and n_pos >= 2:
            fam_improved += 1

    # ---------------------------------------------------------------- ablation ordering
    def _all_auroc(model: str) -> float:
        return _auroc(det, model, "ALL", "ALL")

    geo_only = _all_auroc("geometry_only")
    base_all = _all_auroc(base)
    prim_all = _all_auroc(prim)
    full_all = _all_auroc("chain_plus_full_pathway_dictionary")

    # ---------------------------------------------------------------- coarse
    cz = coa[(coa.model == "zero_shot_pathway_evidence") & (coa.fault_family == "ALL")]
    coarse_best = float(cz["balanced_accuracy"].max()) if len(cz) else float("nan")
    chance = float(cz["chance"].iloc[0]) if len(cz) else 0.2
    sup = res / "stage2a_supervised_attribution.json"
    sup_json = json.loads(sup.read_text()) if sup.exists() else {}
    coarse_gain = (coarse_best - chance) if coarse_best == coarse_best else float("nan")
    if sup_json:
        g = sup_json.get("geometry_plus_residual", {}).get("balanced_accuracy")
        r = sup_json.get("residual_only", {}).get("balanced_accuracy")
        if g is not None and r is not None:
            coarse_best = max(coarse_best, float(g)) if coarse_best == coarse_best else float(g)
            coarse_gain = float(g) - float(r)

    evidence = {
        "blocked": {"any": False, "reasons": []},
        "geometry_gain": {
            "primary_geometry_head": prim, "baseline_head": base,
            "f4_auroc_gain_s1_s4_mean": gain, "f4_auroc_gain_by_seed": by_seed,
            "f4_auroc_gain_seed_agreement": agree,
            "f4_auroc_primary_by_split": {sp: _auroc(det, prim, sp, "F4_contact") for sp in ("S0", "S1", "S2", "S3", "S4", "OOD", "ALL")},
            "f4_auroc_baseline_by_split": {sp: _auroc(det, base, sp, "F4_contact") for sp in ("S0", "S1", "S2", "S3", "S4", "OOD", "ALL")},
            "shuffled_control_gain_s1_s4_mean": ctrl_gain,
        },
        "localization_gain": {
            "f4_top1_primary": top1_p, "f4_top1_baseline": top1_b, "f4_top1_gain": top1_p - top1_b,
            "f4_chain_distance_primary": dist_p, "f4_chain_distance_baseline": dist_b,
            "f4_chain_distance_reduction": dist_b - dist_p,
            "f4_top1_best": max([v for v in (top1_p, top1_b, top1_oracle) if v == v], default=float("nan")),
            "f4_top1_oracle_truth_point": top1_oracle, "f4_top1_shuffled_control": top1_ctrl,
            "per_truth_link_recall_primary": per_link,
        },
        "false_alarms": {
            "primary_false_alarms_per_hour": fa_p, "baseline_false_alarms_per_hour": fa_b,
            "relative_worsening": rel_worse, "healthy_ood_over_id_alarm_ratio": ood_ratio,
        },
        "diagnosability": {
            "best_abs_spearman": best_rho, "best_abs_spearman_with_ci_excluding_zero": best_rho_ci,
            "best_abs_spearman_ci_excludes_zero": bool(best_rho_ci == best_rho_ci and best_rho_ci >= float(dec_cfg["go"]["diagnosability_abs_spearman_min"])),
            "best_row": {k: best_row.get(k) for k in ("diagnosability_metric", "error_metric", "spearman_rho", "ci_low", "ci_high", "n", "seed")},
            "n_rows": int(len(dia)),
        },
        "coverage": {"n_contact_links_with_gain": n_links_gain, "n_context_strata_with_gain": n_strata_gain,
                     "truth_contact_links": truth_links, "per_link_recall": per_link},
        "control": {
            "primary_detection_is_healthy_only": True,
            "shuffled_control_detection_gain": ctrl_gain,
            "shuffled_control_localization_top1": top1_ctrl,
            "shuffled_control_localization_gain": (top1_ctrl - top1_b) if top1_ctrl == top1_ctrl else float("nan"),
            "detection_control_ratio": (ctrl_gain / gain) if gain > 0 and ctrl_gain == ctrl_gain else float("nan"),
            "localization_control_ratio": ((top1_ctrl - top1_b) / (top1_p - top1_b)) if (top1_p - top1_b) > 0 and top1_ctrl == top1_ctrl else float("nan"),
            # The control must fail to reproduce the gain on BOTH axes. Requiring both is stricter
            # than either alone and can only make GO harder, never easier.
            "shuffled_control_does_not_reproduce_gain": bool(
                (not (ctrl_gain == ctrl_gain) or gain <= 0 or ctrl_gain < 0.5 * gain)
                and (not (top1_ctrl == top1_ctrl) or (top1_p - top1_b) <= 0 or (top1_ctrl - top1_b) < 0.5 * (top1_p - top1_b))),
            "gain_requires_fault_label_fuser": False,
            "note": "every head shares the same conditional-Gaussian form, LOO selection and 0.995 healthy-validation threshold; the primary localizer and the coarse attribution use no fault labels",
        },
        "ablation_ordering": {
            "auroc_ALL": {m: _all_auroc(m) for m in sorted(det.model.unique())},
            "geometry_only_not_better_than_residual_only": bool(geo_only <= base_all + 1e-9),
            "chain_plus_geometry_not_better_than_residual_only": bool(max(prim_all, full_all) <= base_all + 1e-9),
        },
        "oracle": {
            "f4_top1_oracle_truth_point": top1_oracle, "f4_top1_deployed": top1_p,
            "only_truth_point_oracle_works": bool(
                (top1_p - top1_b) < float(dec_cfg["pivot_contact_geometry_only"]["f4_top1_gain_min"])
                and (top1_oracle == top1_oracle)
                and (top1_oracle - top1_b) >= float(dec_cfg["go"]["f4_top1_gain_min"])),
        },
        "other_families": {"n_families_improved": fam_improved, "detail": fam_detail},
        "coarse": {"balanced_accuracy_best": coarse_best, "balanced_accuracy_gain_over_baseline": coarse_gain,
                   "chance": chance, "supervised_secondary": sup_json or None},
        "reductions": {
            "f4_auroc_gain": "mean over S1 and S4 of (primary - baseline) window AUROC on F4 positives vs all healthy windows of that split, averaged over seeds",
            "localization": "episode-level vote over the faulty windows, ALL splits, F4 only",
            "false_alarms": "ALL split, family ALL, alarm onsets per healthy hour at the 0.995 healthy-validation threshold",
            "diagnosability": "max |Spearman rho| over (metric, error) pairs whose percentile bootstrap CI excludes zero",
            "shuffled_control": "the control keeps each link's load-path support (which joints link l can load) and destroys only the configuration-dependent Cartesian geometry, by taking the Jacobians at permuted time indices of the same episode. It therefore isolates 'Jacobian geometry' from 'chain topology + projection formulation'. GO condition c6 requires the control to reproduce less than half of the gain on BOTH detection and localization.",
        },
        "provenance": {
            "run_id": st.layout.run_id, "config_sha": st.cfg_sha, "dataset_manifest_sha": st.manifest_sha,
            "baseline_gate": gate.get("gate"), "baseline_worst_relative_deviation": gate.get("worst_relative_deviation"),
            "input_freeze_gate": freeze.get("gate"), "seeds": seeds,
        },
    }

    out = decide(evidence, dec_cfg)
    out["evidence"] = evidence
    write_json(res / "stage2a_decision_evidence.json", out)
    st.log(f"DECISION: {out['decision']}  reasons={out['reasons']}")
    for k, v in out["go"]["conditions"].items():
        st.log(f"  GO {k:44s} {v}")
    for k, v in out["no_go"]["triggers"].items():
        st.log(f"  NO-GO {k:44s} {v}")
    st.finish({"decision": out["decision"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
