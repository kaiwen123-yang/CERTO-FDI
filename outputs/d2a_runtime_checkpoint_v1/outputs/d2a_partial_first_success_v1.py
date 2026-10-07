"""Report only first grid successes whose required predecessors are complete."""
from pathlib import Path
from fractions import Fraction as F
import csv
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"work"))
import d2a_cert_batch as batch
from d2a_core import GRID

ROOT=batch.ROOT
with (ROOT/"work/d2a_cert_review_bound_table.csv").open(encoding="utf-8",newline="") as stream:
    rows=list(csv.DictReader(stream))
known={"CERTIFIED_TARGET_PASS","VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET","ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE"}
answers=[]
for readout in ("average250","point_last_fast_read"):
    for family in ("stay","fixed20","fixed40","fixed76","terminal_balanced","switch_then_stay"):
        group=[r for r in rows if r["readout"]==readout and r["family"]==family]
        predecessors_complete=True;answer={"readout":readout,"family":family,"first_success_H":None,
                                           "all_grid_complete":all(r["risk_status"] in known for r in group)}
        for H in GRID:
            current=[r for r in group if int(r["H_post_slots"])==H]
            completed=all(r["risk_status"] in known for r in current)
            passing=[r for r in current if r["risk_status"]=="CERTIFIED_TARGET_PASS"]
            if passing and predecessors_complete and completed:
                answer.update(first_success_H=H,physical_endpoint_seconds=str(F(H+4,4)),
                              predecessor_grid_rows_complete=True,family_selection_at_H_complete=completed)
                if completed:
                    selected=sorted(passing,key=lambda r:(-F(r["protected_power_lower"]),int(r["stage_endpoint"] or 0)))[0]
                    answer["selected_stage_endpoint"]=selected["stage_endpoint"] or None
                    answer["selected_certificate"]=selected["certificate_reference"]
                    answer["selected_power_lower"]=selected["protected_power_lower"]
                    answer["selected_false_alarm_upper"]=selected["false_alarm_upper"]
                    answer["selected_evidence_binding"]={key:selected.get(key,"NA") for key in (
                        "direction_record_sha256","case_result_sha256","current_receipt_path",
                        "current_receipt_sha256","witness_sha256","covariance_certificate_sha256",
                        "evidence_hash_binding_status","evidence_hash_binding_path","evidence_hash_binding_sha256",
                        "mean_review_report_sha256","mean_review_scope")}
                    answer["previous_H"]=GRID[GRID.index(H)-1] if GRID.index(H) else None
                break
            predecessors_complete &= completed
        answers.append(answer)
result={"protocol_sha256":batch.PROTOCOL_SHA,"scope":"declared finite grid/procedure; fixed fault template; inherited conditions; no minimax/continuous/sequential optimality",
        "review_bound_table_sha256":hashlib.sha256((ROOT/"work/d2a_cert_review_bound_table.csv").read_bytes()).hexdigest(),
        "full_D2a_table_complete":all(r["risk_status"] in known for r in rows),"pairs":answers}
batch.atomic(ROOT/"work/d2a_cert_partial_first_success.json",json.dumps(result,indent=2)+"\n")
batch.atomic(ROOT/"outputs/d2a_partial_first_success_v1.json",json.dumps(result,indent=2)+"\n")
print(json.dumps({"full_table_complete":result["full_D2a_table_complete"],
                  "pairs":[{k:answer.get(k) for k in ("readout","family","first_success_H","physical_endpoint_seconds","family_selection_at_H_complete","selected_stage_endpoint")} for answer in answers]},indent=2),flush=True)
