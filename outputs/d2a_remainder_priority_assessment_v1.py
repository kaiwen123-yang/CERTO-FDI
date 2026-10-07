"""Exact finite metadata assessment; stdlib only, stdout only, no science import.

Run: python -S -B -X utf8 outputs/d2a_remainder_priority_assessment_v1.py
The JSON stdout is the formal companion receipt. No source/live output is written.
"""
from pathlib import Path
from fractions import Fraction as F
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
FIGURE = "outputs/d2a_readout_figure_data_v1.json"
FIGURE_SHA = "8022e863c9b74179f01c3452e0028ab489aa84b7111823b8bd811aab2a816e97"
PROTOCOL_SHA = "0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6"
H_GRID = [40, 60, 80, 100, 120, 160, 200]


def read_small(relative, expected_sha=None):
    p = ROOT / relative
    assert p.resolve().is_relative_to(ROOT.resolve())
    assert p.suffix == ".json" and p.stat().st_size <= 2_000_000
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None:
        assert sha == expected_sha, (relative, sha, expected_sha)
    return json.loads(raw), sha


def stringify(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: stringify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [stringify(v) for v in value]
    return value


def assess():
    figure, sha = read_small(FIGURE, FIGURE_SHA)
    protocol, psha = read_small("work/d2a_PROTOCOL_v1.json", PROTOCOL_SHA)
    assert figure["protocol_sha256"] == psha
    assert figure["H_post_slots"] == H_GRID
    assert len(figure["rows"]) == 14 and figure["complete_subset"]
    assert not figure["full_400_table_claimed_complete"]
    expected = {(str(h), r) for h in H_GRID
                for r in ("average250", "point_last_fast_read")}
    assert {(r["H_post_slots"], r["readout"]) for r in figure["rows"]} == expected
    assert len({(r["H_post_slots"], r["readout"]) for r in figure["rows"]}) == 14

    # Taylor remainders: at n>=5, successive e^1 terms have ratio <=1/6;
    # at n>=3, successive e^(1/2) terms have ratio <=1/8.
    e1_upper = F(65, 24) + F(1, 120) / (1 - F(1, 6))
    ehalf_upper = F(13, 8) + F(1, 48) / (1 - F(1, 8))
    assert e1_upper < F(11, 4)
    assert ehalf_upper < F(5, 3)
    e45_upper = F(11, 4) ** 4 * F(5, 3)
    assert e45_upper < 100
    # pi<4 => sqrt(2*pi)<3. Mills lower bound yields the strict statements
    # Q(1)>1/(2*3*(5/3))=1/10 and Q(3)>3/(10*3*100)=1/1000.
    assert F(1, 2) / (3 * F(5, 3)) == F(1, 10)
    assert F(3, 10) / (3 * 100) == F(1, 1000)

    results = []
    evidence = []
    for row in figure["rows"]:
        h, readout = int(row["H_post_slots"]), row["readout"]
        result = {"H_post_slots": h, "elapsed_seconds": row["elapsed_seconds"],
                  "readout": readout, "existing_status": row["risk_status"]}
        if not row["certificate_reference"]:
            assert h == 40 and row["risk_status"] == "ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE"
            assert not row["Vminus"] and not row["mu1_lower"]
            result.update({"assessment_status": "ZERO_DIRECTION_NO_RISK_BUDGET_ASSESSMENT",
                           "actual_power_zero_asserted": False})
            results.append(result)
            continue
        case_path = str(Path(row["certificate_reference"]) / "CASE_RESULT.json")
        case, case_sha = read_small(case_path, row["case_result_sha256"])
        receipt, receipt_sha = read_small(row["current_receipt_path"], row["current_receipt_sha256"])
        assert case["protocol_sha256"] == PROTOCOL_SHA
        assert case["shared_mean_review_status"] == "ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN"
        m, v, risk = case["uniform_mean"], case["uniform_variance"], case["protected_risk"]
        assert m["two_hypothesis_budgets_paid"]
        assert not m["point_uses_average_cancellation"]
        assert v["no_memory_truncation"] and v["no_covariance_reset"]
        assert not v["cross_task_independence_assumed"]
        fields = {"mu0_upper": m["mean_H0_upper"], "mu1_lower": m["mean_H1_lower"],
                  "dynamic_loss_per_side": m["mean_dynamic_loss_per_hypothesis"],
                  "b0": m["error_H0"], "b1": m["error_H1"],
                  "Vminus": v["variance_lower"], "Vplus": v["variance_upper"],
                  "event_budget_per_hypothesis": risk["event_failure_per_hypothesis"],
                  "protected_power_lower": risk["power_lower"],
                  "false_alarm_upper": risk["false_alarm_upper"]}
        assert all(F(row[key]) == F(value) for key, value in fields.items())
        assert F(risk["threshold_z"]) == F(25, 8)
        m0, m1 = F(fields["mu0_upper"]), F(fields["mu1_lower"])
        dyn, vlo, vhi = F(fields["dynamic_loss_per_side"]), F(fields["Vminus"]), F(fields["Vplus"])
        assert dyn >= 0 and 0 < vlo <= vhi
        a = m1 - m0
        u = a + 2 * dyn
        rounding_residual = u - (F(m["fault_signal_for_exact_sampled_times"]) -
                                  2 * F(m["health_support_per_hypothesis"]))
        assert 0 <= rounding_residual <= F(1, 5 * 10 ** 21)
        result.update({"assessment_status": "EXACT_METADATA_BUDGETS_EVALUATED",
                       "exact_source_fields": fields,
                       "mean_signal": m["fault_signal_for_exact_sampled_times"],
                       "health_support_per_side": m["health_support_per_hypothesis"],
                       "rounding_residual_vs_signal_minus_two_health": rounding_residual,
                       "budget_A_separation": a,
                       "budget_B_separation": u,
                       "existing_target_pass": bool(risk["target_pass"]),
                       "existing_PFA_below_001": F(risk["false_alarm_upper"]) < F(1, 1000),
                       "case_path": case_path, "case_sha256": case_sha,
                       "receipt_path": row["current_receipt_path"], "receipt_sha256": receipt_sha})
        if readout == "point_last_fast_read":
            assert u >= 0 and a <= u
            assert F(18110, 10**6) < vlo < F(18111, 10**6)
            assert u * u < 16 * vlo
            # A much stronger exact finite-subgrid margin:
            assert 5 * u * u < vlo
            assert u * u < F(625, 64) * vhi
            result.update({"budget_A_fails_existing_90pct_interface": True,
                           "budget_B_fails_existing_90pct_interface": True,
                           "U_squared_less_than_16Vminus": True,
                           "five_U_squared_less_than_Vminus": True,
                           "optimistic_U_squared_over_16Vminus": u*u/(16*vlo),
                           "strict_obstruction_margin_16Vminus_minus_U_squared": 16*vlo-u*u,
                           "best_budget_still_negative_gap_at_existing_z_25over8": True,
                           "actual_power_upper_bound_claimed": False})
        results.append(result)
        evidence.append({"case": case_path, "case_sha256": case_sha,
                         "receipt": row["current_receipt_path"], "receipt_sha256": receipt_sha})

    points = [r for r in results if r["readout"] == "point_last_fast_read" and r["H_post_slots"] != 40]
    assert len(points) == 6
    averages = [r["H_post_slots"] for r in results
                if r["readout"] == "average250" and r.get("existing_target_pass")]
    assert averages == [100, 120, 160, 200]
    source_hashes = {}
    function_hashes = {}
    for rel in ["work/d2a_cert_case.py", "work/d2a_core.py",
                "work/r1_extract/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919/src/risk_and_control.py",
                "outputs/d2a_three_block_example_review_v1.md", "outputs/d2a_mean_risk_review_v1.md"]:
        raw = (ROOT / rel).read_bytes()
        assert len(raw) < 2_000_000
        source_hashes[rel] = hashlib.sha256(raw).hexdigest()
        if rel == "work/d2a_cert_case.py":
            text = raw.decode("utf-8")
            for node in ast.parse(text).body:
                if isinstance(node, ast.FunctionDef) and node.name in ("guarded_risk", "mean_certificate"):
                    function_hashes[node.name] = hashlib.sha256(
                        ast.get_source_segment(text, node).encode("utf-8")).hexdigest()
    return stringify({
        "assessment_date": "2026-10-07",
        "status": "EXACT_FINITE_SUBGRID_WITHIN_INTERFACE_PRIORITY_ASSESSMENT_PASS",
        "figure_data_path": FIGURE, "figure_sha256": sha,
        "figure_snapshot_utc": figure["snapshot_utc"],
        "source_table_at_frozen_snapshot": figure["source"],
        "source_table_sha256_at_frozen_snapshot": figure["source_sha256"],
        "source_live_table_reread": False,
        "protocol_path": "work/d2a_PROTOCOL_v1.json", "protocol_sha256": psha,
        "source_hashes": source_hashes, "function_AST_source_segment_hashes": function_hashes,
        "new_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tail_proof_support": {"e_upper_taylor": e1_upper, "ehalf_upper_taylor": ehalf_upper,
                               "e45_upper_rational": e45_upper, "pi_less_than_4": True,
                               "Q1_strictly_greater_01": True,
                               "Q3_strictly_greater_0001": True,
                               "necessary_envelope_separation": "U>4*sqrt(Vminus)"},
        "budgets": {"A": "b0=b1=events=0; keep both dynamic mean losses; separation=mu1_lower-mu0_upper",
                    "B": "Additionally remove recorded dynamic mean losses on both hypotheses; U=A+2*dynamic_loss_per_side"},
        "rows": results, "metadata_bindings": evidence,
        "nondegenerate_point_rows": 6, "point_obstructions": 6,
        "zero_direction_rows_kept_unassessed": 2,
        "average_existing_certified_H": averages,
        "decision": "Do not open a new P6/D1.b/6R branch solely to shrink remainder budgets and rescue these fixed point rows. Existing average H160 three-block deterministic certificate remains adequate for the representative finite example.",
        "scope": "Frozen terminal H<=200 Figure2 subgrid, same directions/means/Gaussian comparator variances/history and risk interface. Not actual-power upper bounds, point non-detectability or all-statistic/global-calendar lower bounds.",
        "not_done": ["No science or matrix replay", "No modern numeric quantile library or fitting",
                     "No source/protocol/physical parameter changes", "No live writes",
                     "No full400 or future-row extrapolation", "No principal paper theorem added"]})


if __name__ == "__main__":
    print(json.dumps(assess(), ensure_ascii=False, indent=2))
