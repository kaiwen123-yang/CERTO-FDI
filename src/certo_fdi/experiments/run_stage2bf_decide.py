"""Stage 2B-F Phase 6: integrity terminal, evidence delta, and the frozen scientific decision.

The scientific decision is not made here. The historical Stage 2B decision evidence is deep-copied,
exactly one Boolean is changed -- the reproduction-gate flag that Stage 2B-R showed had fired for
the wrong reason -- every difference is enumerated and checked against the delta policy, and then
the ORIGINAL frozen ``decision_stage2b.decide`` is imported and called on it.

If any forbidden field moved, or any integrity gate failed, the decision is not called at all.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from certo_fdi.experiments.common import load_config, write_json
from certo_fdi.stage2bf import estimator_identity as EI
from certo_fdi.stage2bf.decision_stage2bf import (
    PASS_STATE,
    combined_terminal,
    evidence_delta,
    integrity_state,
    run_scientific_decision,
    sha256_file,
)

#: historical artifacts whose bytes must be unchanged by this stage
HISTORICAL = {
    "stage2a": ["results/stage2a_localization_metrics.csv", "results/stage2a_decision_evidence.json",
                "p5_ablations/scores_seed260815.npz", "p5_ablations/scores_seed260816.npz",
                "p5_ablations/scores_seed260817.npz"],
    "stage2b": ["results/stage2b_decision_evidence.json", "results/stage2b_decision_memo.md",
                "results/stage2b_contact_reproduction_gate.json", "results/stage2b_reproduction_gate.json",
                "results/stage2b_localizer_selection.json", "results/stage2b_loadpath_controls.csv",
                "results/stage2b_input_freeze.json",
                "p1_loadpath/controls_seed260815.npz", "p1_loadpath/controls_seed260816.npz",
                "p1_loadpath/controls_seed260817.npz"],
    "stage2br": ["results/stage2br_reproduction_gate.json", "results/stage2br_execution_summary.md"],
}
#: the one field Stage 2B-F is allowed to move, plus the descriptive fields that carry the reason
ALLOWED_DELTA_PREFIXES = ("integrity.baseline_reproduction_outside_tolerance",
                          "reproduction_gate", "contact_reproduction",
                          "stage2bf_provenance", "evidence.integrity.baseline_reproduction_outside_tolerance")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 2B-F phase 6")
    ap.add_argument("--config", required=True)
    ap.add_argument("--stage2b-config", required=True)
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()

    fcfg = yaml.safe_load(Path(args.config).read_text())
    cfg, cfg_sha = load_config(args.stage2b_config)
    repo = Path(args.repo_root).resolve()
    root = Path(args.run_root)
    res = root / "results"
    res.mkdir(parents=True, exist_ok=True)
    log: list[str] = []

    def say(m: str) -> None:
        line = f"[{utc_now()}] {m}"
        print(line, flush=True)
        log.append(line)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "logs" / "stage2bf_decide.log").write_text("\n".join(log) + "\n", encoding="utf-8")

    say("Stage 2B-F Phase 6 start")
    roots = {"stage2a": Path(fcfg["paths"]["stage2a_run_root"]),
             "stage2b": Path(fcfg["paths"]["stage2b_run_root"]),
             "stage2br": Path(fcfg["paths"]["stage2br_run_root"])}

    # ---------------------------------------------------------------- historical byte-preservation
    prov = json.loads((res / "stage2bf_input_provenance.json").read_text())
    baseline = prov.get("historical_artifact_sha256", {})
    hist_rows, unchanged = [], True
    for stage, rels in HISTORICAL.items():
        for rel in rels:
            p = roots[stage] / rel
            now = sha256_file(p) if p.is_file() else "ABSENT"
            was = baseline.get(f"{stage}/{rel}")
            same = (was is None) or (was == now)
            unchanged &= same and now != "ABSENT"
            hist_rows.append({"stage": stage, "path": rel, "sha256_now": now,
                              "sha256_at_phase0": was or "(not recorded)",
                              "unchanged": bool(same), "present": now != "ABSENT"})
    say(f"historical artifacts: {sum(1 for r in hist_rows if r['present'])}/{len(hist_rows)} present, "
        f"all unchanged since Phase 0: {unchanged}")
    with (res / "stage2bf_historical_artifact_preservation.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(hist_rows[0].keys()))
        w.writeheader()
        w.writerows(hist_rows)

    # ---------------------------------------------------------------- integrity
    gates = json.loads((res / "stage2bf_reproduction_gates.json").read_text())
    sel = json.loads((res / "stage2bf_f4cal_selection_reproduction.json").read_text())
    decision_src = repo / "src" / "certo_fdi" / "stage2b" / "decision_stage2b.py"
    decision_sha = sha256_file(decision_src)

    ev = {
        "input_provenance_ok": bool(prov.get("input_provenance_ok")),
        "base_head_matches": bool(prov.get("base_head_matches")),
        "scientific_code_identical": bool(prov.get("scientific_code_identical")),
        "decision_code_identical": bool(prov.get("decision_code_identical")),
        "reference_score_precision_ok": bool(prov.get("reference_score_precision_ok")),
        "ridge_reproduction_ok": bool(gates["phase2_stage2a_ridge"]["all_pass"]),
        "svd_reproduction_ok": bool(gates["phase3_stage2b_svd"]["all_pass"]
                                    and sel["reproduction_gate"]["all_pass"]),
        "historical_artifacts_unchanged": bool(unchanged),
    }
    integ = integrity_state(ev, fcfg)
    say(f"INTEGRITY: {integ['integrity_state']}  ({integ['reason']})")

    # ---------------------------------------------------------------- evidence delta
    hist_ev_path = roots["stage2b"] / "results" / "stage2b_decision_evidence.json"
    historical = json.loads(hist_ev_path.read_text())
    new = copy.deepcopy(historical)
    delta_applied = []
    if integ["integrity_state"] == PASS_STATE:
        # exactly one Boolean: the reproduction gate that Stage 2B-R showed had fired for the
        # wrong reason. Nothing numeric is touched.
        new["evidence"]["integrity"]["baseline_reproduction_outside_tolerance"] = False
        new["reproduction_gate"] = {"encoder": "PASS", "contact_localizer": "PASS"}
        # the historical diagnosis is KEPT verbatim and the resolution is added beside it. Replacing
        # the record would drop the very evidence that explains why the gate had fired, which is the
        # opposite of what an audit trail is for.
        new["contact_reproduction"] = {**historical["contact_reproduction"], "gate": "PASS",
                                       "historical_gate": historical["contact_reproduction"]["gate"]}
        new["contact_reproduction"]["stage2bf_resolution"] = {
            "resolved_by": "stage2b_f_estimator_harmonization",
            "reason": ("the Stage 2A reference and the Stage 2B observation were different "
                       "estimators, not one estimator reproduced badly; both pipelines reproduce "
                       "exactly under their own names"),
            "stage2a_estimator": EI.RIDGE_CANONICAL,
            "stage2b_estimator": EI.SVD_CANONICAL,
            "stage2a_ridge_scores_bit_identical": True,
            "stage2b_svd_scores_bit_identical": True}
        delta_applied = ["evidence.integrity.baseline_reproduction_outside_tolerance: true -> false",
                         "reproduction_gate.contact_localizer: FAIL -> PASS",
                         "contact_reproduction.gate: FAIL -> PASS (historical diagnosis preserved "
                         "verbatim; historical_gate and stage2bf_resolution added)"]

    delta = evidence_delta(historical, new, ALLOWED_DELTA_PREFIXES)
    say(f"evidence delta: {delta['n_changes']} changed field(s), "
        f"{len(delta['allowed'])} allowed, {len(delta['violations'])} violation(s)")
    for v in delta["violations"][:10]:
        say(f"  VIOLATION {v['path']}: {v['historical']!r} -> {v['stage2bf']!r}")
    write_json(res / "stage2bf_evidence_delta.json", {
        "generated_utc": utc_now(),
        "historical_source": str(hist_ev_path),
        "historical_sha256": sha256_file(hist_ev_path),
        "allowed_prefixes": list(ALLOWED_DELTA_PREFIXES),
        "applied": delta_applied, **delta,
        "historical_stage2b_decision": historical["decision"],
        "note": ("the historical evidence is deep-copied; only the reproduction-gate Boolean is "
                 "changed. No detection, localization, selective, load-path, sequential or "
                 "healthy-expansion metric, and no threshold, is touched."),
    })
    if not delta["clean"]:
        integ = {**integ, "integrity_state": "BLOCKED_HISTORICAL_ARTIFACT_MUTATION",
                 "reason": "the evidence delta changed a forbidden field",
                 "scientific_decision_permitted": False}
        say("BLOCKED: forbidden field changed in the evidence delta")

    # ---------------------------------------------------------------- frozen scientific decision
    sci = run_scientific_decision(integ, new["evidence"], cfg["decision"])
    decision = sci["stage2bf_scientific_decision"]
    say(f"SCIENTIFIC: {decision} "
        f"({'frozen decision_stage2b.decide called' if sci['decision_function_called'] else 'not run'})")
    if sci["decision_function_called"]:
        for r in sci["result"].get("reasons", []):
            say(f"  reason: {r}")
        for k, v in sci["result"].get("go", {}).get("conditions", {}).items():
            say(f"  go condition {k}: {'PASS' if v else 'FAIL'}")

    out = {
        "generated_utc": utc_now(), "run_id": root.name,
        "stage2bf_integrity_decision": integ["integrity_state"],
        "stage2bf_scientific_decision": decision,
        "stage2bf_combined_terminal": combined_terminal(integ["integrity_state"], decision),
        "historical_stage2b_decision": historical["decision"],
        "historical_stage2b_decision_unchanged": True,
        "integrity": integ,
        "decision_function": {
            "module": "certo_fdi.stage2b.decision_stage2b", "name": "decide",
            "file": str(decision_src.relative_to(repo)), "file_sha256": decision_sha,
            "config_sha256": cfg_sha, "manual_override": False},
        "evidence_delta_clean": delta["clean"],
        "gates": {"stage2a_ridge": gates["phase2_stage2a_ridge"]["all_pass"],
                  "stage2b_svd": gates["phase3_stage2b_svd"]["all_pass"],
                  "f4cal_selection": sel["reproduction_gate"]["all_pass"],
                  "historical_artifacts_unchanged": unchanged},
        "scientific_result": sci.get("result"),
    }
    EI.assert_no_legacy_names({k: v for k, v in out.items() if k != "scientific_result"})
    write_json(res / "stage2bf_integrity_decision.json", {k: v for k, v in out.items()
                                                          if k != "scientific_result"})
    if sci["decision_function_called"]:
        write_json(res / "stage2bf_scientific_decision_evidence.json", {
            "generated_utc": utc_now(),
            "stage2bf_scientific_decision": decision,
            "produced_by": "certo_fdi.stage2b.decision_stage2b.decide (frozen, imported)",
            "decision_function_sha256": decision_sha, "config_sha256": cfg_sha,
            "historical_stage2b_decision": historical["decision"],
            # `evidence_used` is a verbatim deep copy of the historical Stage 2B evidence with one
            # Boolean changed. It therefore still carries Stage 2B's historical score names, and it
            # MUST: rewriting them would be a change to the decision function's input and would show
            # up as an evidence-delta violation. The quotation is labelled instead.
            "quoted_historical_evidence_retains_historical_names": True,
            "legacy_name_mapping": dict(EI.LEGACY_NAME_MAPPING),
            "canonical_names": {"stage2a": EI.RIDGE_CANONICAL, "stage2b": EI.SVD_CANONICAL},
            "evidence_used": new["evidence"], "result": sci["result"]})
    say(f"COMBINED: {out['stage2bf_combined_terminal']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
