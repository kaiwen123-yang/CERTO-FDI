"""Resumable frozen-candidate certification with retained failure rows.

The CSV always contains all 400 declared rows. --max-H stages computation,
leaving later rows explicitly NOT_RUN. Identical physical experiments may reuse
one separately verified witness; no candidate is deleted or optimized away.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import collections
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/"work"
PROTOCOL_SHA=hashlib.sha256((WORK/"d2a_PROTOCOL_v1.json").read_bytes()).hexdigest()
assert PROTOCOL_SHA==(WORK/"d2a_PROTOCOL_v1.sha256").read_text().strip()

def read(path):return json.loads(path.read_text(encoding="utf-8"))

def read_direction_record(row):
    path=ROOT/row["direction_record_path"]
    payload=path.read_bytes()
    assert hashlib.sha256(payload).hexdigest()==row["direction_record_sha256"], "Frozen preflight direction record changed"
    record=json.loads(payload)
    assert record["protocol_sha256"]==PROTOCOL_SHA
    return record

def atomic(path,text):
    temporary=path.with_name(path.name+".next")
    temporary.write_bytes(text.encode("utf-8"))
    deadline=time.monotonic()+20
    while True:
        try:
            os.replace(temporary,path)
            break
        except PermissionError as error:
            if os.name!="nt" or getattr(error,"winerror",None) not in (5,32,33) or time.monotonic()>=deadline:raise
            time.sleep(.05)

def semantic(record):
    item=record["calendar"]
    return {"protocol_sha256":record["protocol_sha256"],"T_fast_steps":item["T_fast_steps"],
            "moves":item["moves"],"observations":item["observations"],"readout":record["readout"],
            "direction":record["direction"]}

def key(record):
    return hashlib.sha256(json.dumps(semantic(record),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()

def name_for(row):
    suffix=f"_S{row['stage_endpoint']}" if row.get("stage_endpoint") not in (None,"") else ""
    return f"h{row['H_post_slots']}_{row['family']}{suffix}_{row['readout']}"

def verified_receipt(out,result,case_hash):
    covariance=out/"audit"/(result["case"]+"_DIRECTION_CERTIFICATE.json")
    for receipt_path in (out/"STDLIB_VERIFICATION_RECEIPT.json",out/"DERIVED_VERIFICATION_RECEIPT.json"):
        try:
            receipt=read(receipt_path)
            assert result["protocol_sha256"]==PROTOCOL_SHA==receipt["protocol_sha256"]
            assert receipt["status"] in ("PASS_STDLIB_NEW_CASE_VERIFIER","PASS_STDLIB_DERIVED_REBINDING")
            assert receipt["case_result_sha256"]==case_hash
            if receipt["status"]=="PASS_STDLIB_DERIVED_REBINDING":
                assert receipt["uniform_variance_payload_unchanged"] and not receipt["big_adjoint_recursions_reexecuted"]
                prior_receipt_bytes=(ROOT/receipt["prior_full_stdlib_receipt_path"]).read_bytes()
                prior_case_bytes=(ROOT/receipt["prior_case_result_path"]).read_bytes()
                assert hashlib.sha256(prior_receipt_bytes).hexdigest()==receipt["prior_full_stdlib_receipt_sha256"]
                assert hashlib.sha256(prior_case_bytes).hexdigest()==receipt["prior_case_result_sha256"]
                assert json.loads(prior_receipt_bytes)["case_result_sha256"]==hashlib.sha256(prior_case_bytes).hexdigest()
                assert hashlib.sha256(covariance.read_bytes()).hexdigest()==receipt["uniform_variance_payload_sha256"]
            return receipt_path,receipt
        except (FileNotFoundError,AssertionError,KeyError,json.JSONDecodeError):continue
    return None

def existing(record):
    out=WORK/("d2a_cert_"+name_for(record["calendar"]|{"readout":record["readout"]}))
    try:
        import d2a_cert_case as core
        result=read(out/"CASE_RESULT.json")
        candidate={"calendar":result["calendar"],"readout":result["readout"],
                   "direction":read(out/"DIRECTION.json"),"protocol_sha256":result["protocol_sha256"]}
        assert semantic(candidate)==semantic(record)
        assert read(out/"ACTUAL_PROTOCOL.json")==core.actual_protocol(record["calendar"],record["readout"],
                  {k:([F(x) for x in v] if k in ("physical",) else v) for k,v in record["direction"].items()})
        covariance=out/"audit"/(result["case"]+"_DIRECTION_CERTIFICATE.json")
        assert read(covariance)==result["uniform_variance"]
        assert (out/"audit"/(result["case"]+"_ADJOINT_JET.json.gz")).exists()
        canonical_status,canonical_failures=core.target_classification(result["uniform_variance"],result["protected_risk"])
        assert result.get("arithmetic_risk_target_status",result["status"])==canonical_status
        assert result["failure_classification"]==canonical_failures
        if result.get("shared_mean_review_status")=="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN":
            current=core.review_binding(record["calendar"])
            assert result["independent_mean_math_review"]==current
        case_hash=hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest()
    except (FileNotFoundError,AssertionError,KeyError,json.JSONDecodeError,ValueError,TypeError):return None
    # A stale derived annotation must not hide a later valid full verifier.
    return (out,result) if verified_receipt(out,result,case_hash) else None

def apply_result(row,out,result,reused):
    co,mean,risk=result["uniform_variance"],result["uniform_mean"],result["protected_risk"]
    import d2a_cert_case as core
    canonical_status,canonical_failures=core.target_classification(co,risk)
    assert result.get("arithmetic_risk_target_status",result["status"])==canonical_status
    assert result["failure_classification"]==canonical_failures
    row.update({"uniform_variance_status":"SEPARATE_STDLIB_VERIFIED", "uniform_mean_status":"COMPUTED_WITH_INHERITED_TUBES_AND_NEW_SUPPORT_ALGEBRA",
                "risk_status":result.get("arithmetic_risk_target_status",result["status"]) if result.get("shared_mean_review_status")=="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN" else "PENDING_SHARED_MEAN_REVIEW",
                "arithmetic_risk_target_status":result.get("arithmetic_risk_target_status",result["status"]),
                "mathematical_review_status":result.get("shared_mean_review_status","PENDING_SHARED_MEAN_REVIEW"),
                "mean_review_report_sha256":result.get("independent_mean_math_review",{}).get("report_sha256","NA"),
                "mean_review_scope":"frozen template; H<=600; actual f<=0.045; no wide f<=0.75 mirror claim",
                "failure_classification":";".join(result["failure_classification"]),
                "Vminus":co["variance_lower"],"Vplus":co["variance_upper"],"variance_ratio_upper":co["variance_ratio_upper"],
                "mu0_upper":mean["mean_H0_upper"],"mu1_lower":mean["mean_H1_lower"],
                "b0":mean["error_H0"],"b1":mean["error_H1"],"dynamic_loss_per_side":mean["mean_dynamic_loss_per_hypothesis"],
                "threshold":risk["threshold"],"gap":risk["gap_lower"],"standardized_gap":risk["standardized_gap_lower"],
                "false_alarm_upper":risk["false_alarm_upper"],"protected_power_lower":risk["power_lower"],
                "event_budget_per_hypothesis":risk["event_failure_per_hypothesis"],
                "certificate_reference":str(out.relative_to(ROOT)),
                "exact_experiment_identity_reuse":reused,
                "first_success_or_optimum_claimed":False})
    case_hash=hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest()
    row["case_result_sha256"]=case_hash
    selected_receipt=verified_receipt(out,result,case_hash)
    assert selected_receipt is not None, "No valid receipt for applied result"
    path,receipt=selected_receipt
    row["current_receipt_path"]=str(path.relative_to(ROOT))
    row["current_receipt_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    artifacts=receipt.get("artifact_sha256")
    binding_path=out/"EVIDENCE_ARTIFACT_HASHES.json"
    if artifacts is None and binding_path.exists():
        binding=read(binding_path)
        receipt_binding={"path":path.name,"sha256":row["current_receipt_sha256"]}
        if binding.get("case_result_sha256")==case_hash and binding.get("protocol_sha256")==PROTOCOL_SHA and receipt_binding in binding.get("verified_receipts",[]):
            artifacts=binding["artifact_sha256"]
            row["evidence_hash_binding_path"]=str(binding_path.relative_to(ROOT))
            row["evidence_hash_binding_sha256"]=hashlib.sha256(binding_path.read_bytes()).hexdigest()
    if artifacts:
        for name,entry in artifacts.items():
            if name.endswith("_ADJOINT_JET.json.gz"):row["witness_sha256"]=entry["sha256"]
            elif name.endswith("_DIRECTION_CERTIFICATE.json"):row["covariance_certificate_sha256"]=entry["sha256"]
        row["evidence_hash_binding_status"]="BOUND_AT_VERIFICATION_OR_HASH_ONLY_RECEIPT"
    else:row["evidence_hash_binding_status"]="NOT_YET_HASH_BOUND"

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--max-H",type=int,default=600)
    parser.add_argument("--limit-new-cases",type=int)
    parser.add_argument("--inventory-only",action="store_true")
    parser.add_argument("--reserve-disk-gib",type=float,default=25.0)
    args=parser.parse_args();start=time.perf_counter()
    records=[]
    with (WORK/"d2a_cert_direction_preflight.csv").open(encoding="utf-8",newline="") as stream:
        for row in csv.DictReader(stream):
            record=read_direction_record(row)
            row["H_post_slots"]=int(row["H_post_slots"])
            row["stage_endpoint"]=int(row["stage_endpoint"]) if row["stage_endpoint"] else None
            for k in ("Vminus","Vplus","variance_ratio_upper","mu0_upper","mu1_lower","b0","b1","threshold","gap","standardized_gap","false_alarm_upper","protected_power_lower","event_budget_per_hypothesis"):
                row[k]="NA"
            row["uniform_mean_status"]="NOT_RUN";row["uniform_variance_status"]="NOT_RUN";row["risk_status"]="NOT_RUN"
            records.append((row,record))
    unique=collections.defaultdict(set);zero=collections.Counter()
    for row,record in records:
        if record["direction"] is None:zero[row["H_post_slots"]]+=1
        else:unique[row["H_post_slots"]].add(key(record))
    weighted_slots=sum((H+4)*len(v) for H,v in unique.items())
    estimate={"unique_nonzero_cases":sum(map(len,unique.values())),"total_fast_steps_unique":weighted_slots*250,
              "generation_hours_from_129s_H120":129*weighted_slots/124/3600,
              "generation_plus_verification_hours_planning_range":[160*weighted_slots/124/3600,200*weighted_slots/124/3600],
              "jet_bytes_linear_estimate_from_H120":60500000*weighted_slots/124,
              "jet_bytes_with_50_percent_headroom":1.5*60500000*weighted_slots/124,
              "free_disk_bytes_at_start":shutil.disk_usage(WORK).free,"disk_reserve_bytes":int(args.reserve_disk_gib*2**30),
              "calibration":"Actual H120 gzip jets average60190348 bytes/point60740809 bytes; actual generation129.47s/125.31s. Times scale estimates, not ETA guarantees."}
    atomic(WORK/"d2a_cert_resource_estimate.json",json.dumps(estimate,indent=2)+"\n")
    print("INVENTORY",json.dumps({"rows":len(records),"unique_nonzero_by_H":{k:len(v) for k,v in unique.items()},"zeros_by_H":dict(zero),"resource_estimate":estimate}),flush=True)
    if args.inventory_only:return
    cache={}
    for row,record in records:
        if record["direction"] is None:continue
        found=existing(record)
        if found:cache[key(record)]=(record,*found)
    def save(phase,current=None,**extra):
        fields=list(dict.fromkeys(k for row,record in records for k in row))
        stream=io.StringIO(newline="")
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(row for row,record in records)
        atomic(WORK/"d2a_cert_partial_table.csv",stream.getvalue())
        counts=collections.Counter(row["risk_status"] for row,record in records)
        checkpoint={"protocol_sha256":PROTOCOL_SHA,"phase":phase,"current_case":current,
                    "max_H_this_run":args.max_H,"rows_total":len(records),"status_counts":dict(counts),
                    "elapsed_wall_seconds":time.perf_counter()-start,"full_arithmetic_table_completed":not counts.get("NOT_RUN") and not counts.get("CERTIFICATION_EXECUTION_FAILED"),
                    "full_risk_table_completed":False,
                    "next_resume_command":"python -B -X utf8 work/d2a_cert_batch.py", "mathematical_review_status":read(WORK/"d2a_cert_mean_review_binding.json").get("status","PENDING_SHARED_MEAN_REVIEW") if (WORK/"d2a_cert_mean_review_binding.json").exists() else "PENDING_SHARED_MEAN_REVIEW",
                    "mathematical_review_scope":"fixed template; H<=600; actual f<=0.045; inherited conditions",
                    "interruption_history":interruptions,
                    "execution_failures":failures,**extra}
        atomic(WORK/"d2a_cert_batch_checkpoint.json",json.dumps(checkpoint,indent=2)+"\n")
    previous_checkpoint=read(WORK/"d2a_cert_batch_checkpoint.json") if (WORK/"d2a_cert_batch_checkpoint.json").exists() else {}
    new=0;failures=list(previous_checkpoint.get("execution_failures",[]));interruptions=list(previous_checkpoint.get("interruption_history",[]));save("STARTED")
    for row,record in records:
        name=name_for(row)
        if record["direction"] is None:
            row["risk_status"]="ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE"
            row["failure_classification"]="ZERO_DIRECTION"
            row["randomized_constant_control_size_and_power"]="1/2000"
            row["full_experiment_zero_information_claimed"]=False
            save("ROW_COMPLETED",name)
            continue
        fingerprint=key(record)
        if fingerprint in cache:
            previous,out,result=cache[fingerprint]
            assert semantic(previous)==semantic(record)
            apply_result(row,out,result,name_for(previous["calendar"]|{"readout":previous["readout"]})!=name)
            save("ROW_REUSED_VERIFIED_IDENTITY",name)
            continue
        if row["H_post_slots"]>args.max_H or (args.limit_new_cases is not None and new>=args.limit_new_cases):continue
        free=shutil.disk_usage(WORK).free
        next_estimate=60500000*record["calendar"]["T_fast_steps"]/31000
        required=int(args.reserve_disk_gib*2**30+max(2*2**30,3*next_estimate))
        if free<required:
            save("DISK_GUARD_CHECKPOINTED",name,free_disk_bytes=free,required_disk_bytes=required,new_cases_started=new)
            print("DISK_GUARD_CHECKPOINTED",free,required,flush=True)
            return
        out=WORK/("d2a_cert_"+name)
        out.mkdir(exist_ok=True)
        command=[sys.executable,"-B","-X","utf8",str(WORK/"d2a_cert_case.py"),"--H",str(row["H_post_slots"]),"--family",row["family"],"--readout",row["readout"]]
        if row["stage_endpoint"] is not None:command.extend(["--stage-endpoint",str(row["stage_endpoint"])])
        verifier=[sys.executable,"-S","-B","-X","utf8",str(WORK/"d2a_cert_verify.py"),"--case-dir",str(out)]
        case_id=("D2A_"+name).upper()
        # Reuse completed scientific payload after a wrapper failure. A fully
        # generated case only needs the fixed verifier, not fresh NumPy jets.
        have_generated=all((out/file).exists() for file in ("CASE_RESULT.json","ACTUAL_PROTOCOL.json","DIRECTION.json","PROJECTION_CERTIFICATE.json")) and (out/"audit"/(case_id+"_DIRECTION_CERTIFICATE.json")).exists() and (out/"audit"/(case_id+"_ADJOINT_JET.json.gz")).exists()
        have_witness=(out/"audit"/(case_id+"_ADJOINT_JET.json.gz")).exists()
        if have_generated:
            stages=[("stdlib_verify",verifier)]
        elif have_witness:
            stages=[("derive_from_saved_witness",command+["--derive-from-witness"]),("stdlib_verify",verifier)]
        else:stages=[("generate",command),("stdlib_verify",verifier)]
        save("GENERATING_CASE",name,active_command=command,new_cases_started=new+1)
        print("RUN",name,flush=True);new+=1
        success=True
        for label,cmd in stages:
            legacy=out/(label+"_batch_stdout.log")
            if legacy.exists():
                legacy_bytes=legacy.read_bytes();history=out/(label+"_prior_"+hashlib.sha256(legacy_bytes).hexdigest()+".log")
                if not history.exists():history.write_bytes(legacy_bytes)
            attempt=out/(label+"_attempt_"+str(time.time_ns())+".log")
            with attempt.open("x",encoding="utf-8") as log:
                child=subprocess.Popen(cmd,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8")
                for line in child.stdout:
                    log.write(line);log.flush()
                    if line.startswith(("PHASE","RESULT","HEARTBEAT","Traceback")):print(name,line.rstrip(),flush=True)
                code=child.wait()
            atomic(legacy,attempt.read_text(encoding="utf-8"))
            if code:
                row["risk_status"]="CERTIFICATION_EXECUTION_FAILED";row["failure_classification"]=label+"_EXIT_"+str(code)
                failures.append({"case":name,"stage":label,"exit_code":code});success=False;break
        if success:
            found=existing(record);assert found is not None
            out,result=found;cache[fingerprint]=(record,out,result);apply_result(row,out,result,False)
        save("ROW_COMPLETED" if success else "ROW_FAILED_RETAINED",name,new_cases_started=new)
    save("BOUNDED_PREFIX_COMPLETE" if args.max_H<600 else "RUN_COMPLETE",new_cases_started=new,execution_failures=failures)
    print(json.dumps(read(WORK/"d2a_cert_batch_checkpoint.json")),flush=True)

if __name__=="__main__":
    lock=WORK/"d2a_cert_batch.lock"
    try:
        descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("An existing batch lock must be inspected before starting another large runner: "+str(lock))
    os.write(descriptor,json.dumps({"pid":os.getpid(),"protocol_sha256":PROTOCOL_SHA,"command":sys.argv}).encode("utf-8"))
    os.close(descriptor)
    original_stdout=sys.stdout
    class Tee:
        def __init__(self,stream,log):self.stream,self.log=stream,log
        def write(self,text):
            self.log.write(text);self.log.flush()
            try:return self.stream.write(text)
            except BrokenPipeError:return len(text)
        def flush(self):
            self.log.flush()
            try:self.stream.flush()
            except BrokenPipeError:pass
    try:
        with (WORK/"d2a_cert_batch_stdout.log").open("a",encoding="utf-8") as logfile:
            sys.stdout=Tee(original_stdout,logfile)
            main()
    finally:
        sys.stdout=original_stdout
        lock.unlink(missing_ok=True)
