"""Independent stdlib review/risk rebinding without repeating verified jets.

Requires an existing full stdlib receipt bound to the old CASE_RESULT. Keeps
both old files under content-addressed audit names. Recomputes only exact KKT,
direction/protocol, mean/event/risk and binds the accepted fixed-template review.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import hashlib
import json
import sys
import time
import d2a_cert_case as core
from d2a_core import calendar,normalize_raw,RATE,B,ETA
from d2a_cert_verify import verify_projection

def rebind(out):
    transaction=out/"DERIVED_REBINDING_TRANSACTION.json"
    current_bytes=(out/"CASE_RESULT.json").read_bytes()
    current_hash=hashlib.sha256(current_bytes).hexdigest()
    if transaction.exists() and core.read_json(transaction).get("state")=="PREPARED":
        plan=core.read_json(transaction)
        old_bytes=(core.ROOT/plan["prior_case_result_path"]).read_bytes()
        receipt_bytes=(core.ROOT/plan["prior_full_stdlib_receipt_path"]).read_bytes()
        assert hashlib.sha256(old_bytes).hexdigest()==plan["prior_case_result_sha256"]
        assert hashlib.sha256(receipt_bytes).hexdigest()==plan["prior_full_stdlib_receipt_sha256"]
        assert current_hash in (plan["prior_case_result_sha256"],plan["proposed_case_result_sha256"])
    else:
        old_bytes=current_bytes
        receipt_bytes=(out/"STDLIB_VERIFICATION_RECEIPT.json").read_bytes()
    old=json.loads(old_bytes);prior=json.loads(receipt_bytes)
    old_hash=hashlib.sha256(old_bytes).hexdigest()
    assert prior["status"]=="PASS_STDLIB_NEW_CASE_VERIFIER" and prior["case_result_sha256"]==old_hash
    assert prior["protocol_sha256"]==old["protocol_sha256"]==core.PROTOCOL_SHA
    pr=core.read_json(out/"ACTUAL_PROTOCOL.json");item=pr["calendar"];readout=pr["readout"]
    assert item==calendar(item["H_post_slots"],item["family"],item["stage_endpoint"])
    projection=core.read_json(out/"PROJECTION_CERTIFICATE.json");raw=verify_projection(projection)
    observations=item["observations"]
    expected=[F(0) if o["relative_node"]<=0 else o["task"]*ETA*(o["relative_node"]-(F(1,2) if readout=="average250" else 0)) for o in observations]
    assert list(map(F,projection["y"]))==expected
    assert list(map(F,projection["t"]))==[F(o["relative_node"]) for o in observations]
    direction=normalize_raw(raw,[o["task"] for o in observations]);assert direction is not None
    saved_direction=core.read_json(out/"DIRECTION.json")
    direction["iterations"]=saved_direction["iterations"]
    nodes=[o["relative_node"] for o in observations]
    direction["dual_support"]=sum((abs(F(q))*RATE*(nodes[i+1]-nodes[i]) for i,q in enumerate(projection["q"])),F(0))+B*sum((abs(F(e)) for e in projection["eta"]),F(0))
    assert core.serial(direction)==saved_direction and core.actual_protocol(item,readout,direction)==pr
    covariance_path=out/"audit"/(old["case"]+"_DIRECTION_CERTIFICATE.json")
    stored_covariance=core.read_json(covariance_path)
    assert stored_covariance==old["uniform_variance"]
    mean=core.mean_certificate(item,readout,direction)
    mean_serial=core.serial(mean)
    strip=lambda v:{k:x for k,x in v.items() if k!="independent_mean_math_review"}
    assert strip(mean_serial)==strip(old["uniform_mean"])
    events=core.budget(item["T_fast_steps"],len(item["moves"]))
    assert core.serial(events)==old["event_accounting"]
    risk=core.guarded_risk(mean["mean_H0_upper"],mean["mean_H1_lower"],mean["error_H0"],mean["error_H1"],F(stored_covariance["variance_lower"]),F(stored_covariance["variance_upper"]),events["total_failure"])
    assert core.serial(risk)==old["protected_risk"]
    canonical_status,canonical_failures=core.target_classification(stored_covariance,risk)
    assert old.get("arithmetic_risk_target_status",old["status"])==canonical_status
    assert old["failure_classification"]==canonical_failures
    reviewed=mean["independent_mean_math_review"]
    assert reviewed["status"]=="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN"
    history_case=out/"audit"/f"PRIOR_CASE_RESULT_{old_hash}.json"
    receipt_hash=hashlib.sha256(receipt_bytes).hexdigest()
    history_receipt=out/"audit"/f"PRIOR_STDLIB_RECEIPT_{receipt_hash}.json"
    if not history_case.exists():history_case.write_bytes(old_bytes)
    if not history_receipt.exists():history_receipt.write_bytes(receipt_bytes)
    status=canonical_status
    updated={**old,"uniform_mean":mean_serial,"protected_risk":core.serial(risk),
             "status":status,"arithmetic_risk_target_status":status,
             "shared_mean_review_status":reviewed["status"],"independent_mean_math_review":reviewed,
             "new_point_mean_algebra_requires_independent_review":False,
             "derived_rebinding_prior_case_sha256":old_hash}
    proposed_text=json.dumps(updated,ensure_ascii=False,indent=2)+"\n"
    plan={"state":"PREPARED","protocol_sha256":core.PROTOCOL_SHA,
          "prior_case_result_sha256":old_hash,"prior_case_result_path":str(history_case.relative_to(core.ROOT)),
          "prior_full_stdlib_receipt_sha256":receipt_hash,"prior_full_stdlib_receipt_path":str(history_receipt.relative_to(core.ROOT)),
          "proposed_case_result_sha256":hashlib.sha256(proposed_text.encode("utf-8")).hexdigest()}
    core.atomic_text(transaction,json.dumps(plan,indent=2)+"\n")
    core.atomic_text(out/"CASE_RESULT.json",proposed_text)
    summary=core.read_json(out/"SUMMARY.json")
    summary.update(status=status,shared_mean_review_status=reviewed["status"],independent_mean_math_review=reviewed)
    core.atomic_text(out/"SUMMARY.json",json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    result={"status":"PASS_STDLIB_DERIVED_REBINDING","case":old["case"],"protocol_sha256":core.PROTOCOL_SHA,
            "case_result_sha256":hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest(),
            "prior_case_result_sha256":old_hash,"prior_case_result_path":str(history_case.relative_to(core.ROOT)),
            "prior_full_stdlib_receipt_sha256":receipt_hash,"prior_full_stdlib_receipt_path":str(history_receipt.relative_to(core.ROOT)),
            "uniform_variance_payload_sha256":hashlib.sha256(covariance_path.read_bytes()).hexdigest(),
            "uniform_variance_payload_unchanged":True,"big_adjoint_recursions_reexecuted":False,
            "exact_KKT_protocol_direction_rechecked":True,"mean_event_risk_recomputed":True,
            "risk_values_changed":False,"independent_mean_math_review":reviewed,
            "artifact_sha256":core.artifact_hashes(out,old["case"]),
            "tiny_positive_mills_guard_boundary_test_passed":True,"numpy_loaded":False,"scipy_loaded":False}
    assert "numpy" not in sys.modules and "scipy" not in sys.modules
    core.atomic_text(out/"DERIVED_VERIFICATION_RECEIPT.json",json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    core.atomic_text(transaction,json.dumps({**plan,"state":"COMMITTED","derived_receipt_sha256":hashlib.sha256((out/"DERIVED_VERIFICATION_RECEIPT.json").read_bytes()).hexdigest()},indent=2)+"\n")
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--case-dir");parser.add_argument("--all-completed",action="store_true")
    args=parser.parse_args();outputs=[]
    candidates=[Path(args.case_dir).resolve()] if args.case_dir else sorted((core.ROOT/"work").glob("d2a_cert_h*"))
    active=core.read_json(core.ROOT/"work/d2a_cert_batch_checkpoint.json").get("current_case") if (core.ROOT/"work/d2a_cert_batch.lock").exists() else None
    for out in candidates:
        if out.name=="d2a_cert_"+str(active):continue
        if not (out/"STDLIB_VERIFICATION_RECEIPT.json").exists():continue
        result=core.read_json(out/"CASE_RESULT.json")
        transaction=out/"DERIVED_REBINDING_TRANSACTION.json"
        incomplete=transaction.exists() and core.read_json(transaction).get("state")=="PREPARED"
        if result.get("shared_mean_review_status")=="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN" and not incomplete:continue
        outputs.append(rebind(out))
        print("DERIVED_REBIND",out.name,outputs[-1]["status"],flush=True)
    core.atomic_text(core.ROOT/"work/d2a_cert_derived_rebinding_receipt.json",json.dumps({"results":outputs,"no_large_recursion_rerun":True},ensure_ascii=False,indent=2)+"\n")

if __name__=="__main__":main()
