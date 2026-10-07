"""Finite adversarial tests for new metadata guards, never preflight/science."""
from pathlib import Path
import copy, csv, hashlib, io, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"work"))
from d2a_metadata_guard import (build_report,expected_keys,apply_physical_guard,
    apply_preflight_failure,PhysicalContractError,MetadataCoverageError)
proto=(ROOT/"work/d2a_PROTOCOL_v1.json").read_bytes();p=json.loads(proto)
fields=("H_post_slots","family","stage_endpoint","readout","risk_status",
        "protected_power_lower","false_alarm_upper","certificate_reference")
rows=[dict(zip(fields,(h,f,"" if s is None else str(s),r,
                       "ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE","","","")))
      for h,f,s,r in expected_keys(p)]
for r in rows:
    if r["H_post_slots"]==100 and r["family"]=="switch_then_stay" and r["readout"]=="average250" and r["stage_endpoint"] in ("80","100"):
        r.update(risk_status="CERTIFIED_TARGET_PASS",protected_power_lower="19/20",
                 false_alarm_upper="1/2000",certificate_reference="fixture://same-bound-alias")
def payload(rs):
    out=io.StringIO(newline="");w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(rs)
    return out.getvalue().encode()
tests=[]
def test(name,value):tests.append({"name":name,"pass":bool(value)})
def rejects(rs):
    try:build_report(payload(rs),proto);return False
    except MetadataCoverageError:return True
valid=build_report(payload(rows),proto)
sel=next(x for x in valid["pairs"] if x["family"]=="switch_then_stay" and x["readout"]=="average250")
test("400 aliases remain logical rows",valid["rows"]==400 and len(rows)==400)
test("exact max power/minS tie retained",sel["first_success_H"]==100 and sel["selected_stage_endpoint"]=="80" and sel["selected_power_lower"]=="19/20")
test("captured bytes rows/hash same snapshot",valid["review_bound_table_sha256"]==hashlib.sha256(payload(rows)).hexdigest())
test("deleted predecessor rejected",rejects([r for r in rows if not (r["H_post_slots"]==80 and r["family"]=="switch_then_stay" and r["readout"]=="average250")]))
test("same count duplicate hides no missing key",rejects(rows[1:]+[rows[-1].copy()]))
test("stage alias may not be dropped",rejects([r for r in rows if not (r["H_post_slots"]==40 and r["family"]=="switch_then_stay" and r["stage_endpoint"]=="20" and r["readout"]=="average250")]))
test("unexpected S0 rejected",rejects(rows+[dict(rows[0],family="switch_then_stay",stage_endpoint="0")]))
pending=copy.deepcopy(rows)
pending[0]["risk_status"]="NOT_RUN"
test("pending is not complete",build_report(payload(pending),proto)["full_D2a_table_complete"] is False)
badpower=copy.deepcopy(rows)
next(r for r in badpower if r["risk_status"]=="CERTIFIED_TARGET_PASS")["protected_power_lower"]="NA"
test("missing certified power rejected, not zero",rejects(badpower))
short=payload(rows).decode().splitlines()
index=next(i for i,x in enumerate(short) if x.startswith("100,switch_then_stay,80,average250,CERTIFIED_TARGET_PASS"))
short[index]=",".join(short[index].split(",")[:5])
try:build_report(("\n".join(short)+"\n").encode(),proto);rejected=False
except MetadataCoverageError:rejected=True
test("short CSV row with None power fails closed",rejected)
base=json.loads((ROOT/"work/d2a_cert_preflight/h40_terminal_balanced_average250.json").read_text())["calendar"]
row={"physical_rule_status":"NOT_CHECKED","direction_status":"NOT_RUN","risk_status":"NOT_RUN"}
apply_physical_guard(row,base)
test("valid inherited clock gets physical pass",row["physical_rule_status"]=="PASS_INHERITED_RULE_INSTANCE_CHECK")
def fail_item(item):
    r={"physical_rule_status":"NOT_CHECKED","direction_status":"NOT_RUN","risk_status":"NOT_RUN"}
    try:apply_physical_guard(r,item);return r,None
    except PhysicalContractError as e:apply_preflight_failure(r,e,"physical");return r,e
invalid=copy.deepcopy(base);invalid["validation_errors"]=["GAP_NOT_K_SLOTS"]
r,error=fail_item(invalid)
test("explicit contract failure cannot retain physical pass",error is not None and r["physical_rule_status"]=="PHYSICAL_CONTRACT_FAILED" and r["risk_status"]=="PHYSICAL_CONTRACT_FAILED")
clock=copy.deepcopy(base);clock["moves"][0][0]=1500;clock["moves"][0][1]=3000
r,error=fail_item(clock)
test("1750 clock guards even spoofed valid flag",error is not None and r["risk_status"]=="PHYSICAL_CONTRACT_FAILED")
r={"physical_rule_status":"PASS_INHERITED_RULE_INSTANCE_CHECK"};apply_preflight_failure(r,ValueError("projection fixture"),"projection")
test("projection failure separate from physical",r["physical_rule_status"]=="PASS_INHERITED_RULE_INSTANCE_CHECK" and r["risk_status"]=="PROJECTION_CERTIFICATE_FAILED")
r={"physical_rule_status":"PASS_INHERITED_RULE_INSTANCE_CHECK"};apply_preflight_failure(r,OSError("metadata fixture"),"metadata")
test("metadata failure does not falsify physical or projection",r["physical_rule_status"]=="PASS_INHERITED_RULE_INSTANCE_CHECK" and r["risk_status"]=="CERTIFICATION_EXECUTION_FAILED")
print(json.dumps({"status":"PASS_TINY_METADATA_GUARD_FIXTURES" if all(x["pass"] for x in tests) else "FAIL_TINY_METADATA_GUARD_FIXTURES",
                  "tests":tests,"preflight_executed":False,"science_executed":False,"files_written":False},indent=2))
if not all(x["pass"] for x in tests):raise SystemExit(3)
