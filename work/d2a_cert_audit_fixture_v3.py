"""Patch re-audit in isolated fixtures: never launches workers or reads real jets."""
from pathlib import Path
from fractions import Fraction as F
import contextlib
import copy
import csv
import hashlib
import inspect
import io
import json
import sys
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"work"))
import d2a_cert_case as core
import d2a_cert_batch as batch
import d2a_cert_verify as verify
import d2a_cert_rebind_derived as derived
FIX=ROOT/"work/d2a_cert_audit_fixture_v3"
FIX.mkdir(exist_ok=True)
checks={}
def read(path):return json.loads(path.read_text(encoding="utf-8"))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
def fixture(name,case_name="d2a_cert_h80_fixed40_point_last_fast_read"):
    root=FIX/name
    (root/"work").mkdir(parents=True,exist_ok=True)
    (root/"outputs").mkdir(exist_ok=True)
    for rel in ["work/d2a_cert_mean_review_binding.json","outputs/d2a_mean_risk_review_v1.md"]:
        (root/rel).write_bytes((ROOT/rel).read_bytes())
    src=ROOT/"work"/case_name;out=root/"work"/case_name
    (out/"audit").mkdir(parents=True,exist_ok=True)
    for p in [*src.glob("*.json"),*(src/"audit").glob("*.json")]:
        relative=p.relative_to(src)
        (out/relative).write_bytes(p.read_bytes())
    result=read(out/"CASE_RESULT.json")
    # A tiny dummy sentinel satisfies the cache existence check. Never scientific jets.
    (out/"audit"/(result["case"]+"_ADJOINT_JET.json.gz")).write_bytes(b"audit sentinel only")
    batch.ROOT=core.ROOT=root;batch.WORK=root/"work"
    record={"calendar":result["calendar"],"readout":result["readout"],"direction":read(out/"DIRECTION.json"),"protocol_sha256":result["protocol_sha256"]}
    return root,out,record
def rejected(call):
    try:call()
    except (AssertionError,FileNotFoundError):return True
    return False
def fast_full_verifier(out):
    covariance=copy.deepcopy(read(out/"CASE_RESULT.json")["uniform_variance"])
    for k in ["variance_lower","variance_upper"]:covariance[k]=F(covariance[k])
    class SavedPayload:
        def certify(self,verify):
            assert verify is True
            return covariance
    with patch.object(core,"bind_actual",return_value=SavedPayload()),patch.object(sys,"argv",["audit","--case-dir",str(out)]),contextlib.redirect_stdout(io.StringIO()):
        verify.main()
    return read(out/"STDLIB_VERIFICATION_RECEIPT.json")

root,out,record=fixture("binding")
checks["valid_baseline_cache_accepted"]=batch.existing(record) is not None
binding=read(root/"work/d2a_cert_mean_review_binding.json")
checks["baseline_mean_hash_matches"]=hashlib.sha256(inspect.getsource(core.mean_certificate).encode()).hexdigest()==binding["mean_function_after_scope_binding_sha256"]
binding["mean_function_after_scope_binding_sha256"]="0"*64
write(root/"work/d2a_cert_mean_review_binding.json",binding)
checks["wrong_mean_hash_rejected"]=rejected(lambda:core.review_binding(record["calendar"]))
checks["wrong_mean_hash_cache_rejected"]=batch.existing(record) is None

root,out,record=fixture("metadata")
for name in ["ACTUAL_PROTOCOL.json","DIRECTION.json"]:
    p=out/name;data=p.read_bytes();p.unlink()
    checks["missing_"+name+"_rejected"]=batch.existing(record) is None
    p.write_bytes(data)
covariance=out/"audit"/(read(out/"CASE_RESULT.json")["case"]+"_DIRECTION_CERTIFICATE.json")
data=covariance.read_bytes();covariance.unlink()
checks["missing_covariance_rejected"]=batch.existing(record) is None
covariance.write_bytes(data)
(root/"outputs/d2a_mean_risk_review_v1.md").write_text("stale report",encoding="utf-8")
checks["stale_report_cache_rejected"]=batch.existing(record) is None

root,out,record=fixture("false_status")
case=read(out/"CASE_RESULT.json");assert case["protected_risk"]["target_pass"] is False
case.update(status="CERTIFIED_TARGET_PASS",arithmetic_risk_target_status="CERTIFIED_TARGET_PASS",failure_classification=[])
write(out/"CASE_RESULT.json",case)
checks["false_target_full_wrapper_rejected"]=rejected(lambda:fast_full_verifier(out))
checks["false_target_apply_rejected"]=rejected(lambda:batch.apply_result({},out,case,False))
checks["false_target_cache_rejected"]=batch.existing(record) is None

root,out,record=fixture("stale_derived","d2a_cert_h120_terminal_balanced_average250")
case=read(out/"CASE_RESULT.json");case["elapsed_wall_seconds"]+=1;write(out/"CASE_RESULT.json",case)
receipt=fast_full_verifier(out)
checks["full_receipt_bound_after_wrapper"]=receipt["case_result_sha256"]==hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest()
checks["stale_derived_does_not_shadow_full"]=batch.existing(record) is not None

root,out,record=fixture("rebind_crash","d2a_cert_h120_terminal_balanced_average250")
prior=read(out/"DERIVED_VERIFICATION_RECEIPT.json")
(out/"CASE_RESULT.json").write_bytes((root/prior["prior_case_result_path"]).read_bytes())
(out/"STDLIB_VERIFICATION_RECEIPT.json").write_bytes((root/prior["prior_full_stdlib_receipt_path"]).read_bytes())
(out/"DERIVED_VERIFICATION_RECEIPT.json").unlink()
transaction=out/"DERIVED_REBINDING_TRANSACTION.json"
transaction.unlink(missing_ok=True)
real_atomic=core.atomic_text
def injected_crash(path,text):
    if path.name=="DERIVED_VERIFICATION_RECEIPT.json":raise OSError("audit crash before derived receipt")
    return real_atomic(path,text)
try:
    with patch.object(core,"atomic_text",side_effect=injected_crash):derived.rebind(out)
except OSError as exc:assert "audit crash" in str(exc)
checks["crash_transaction_prepared"]=read(transaction)["state"]=="PREPARED"
checks["crash_no_false_usable_receipt"]=batch.existing(record) is None
try:
    derived.rebind(out)
except AssertionError:
    checks["crash_retry_committed"]=False
    plan=read(transaction)
    checks["crash_current_sha256"]=hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest()
    checks["crash_proposed_sha256"]=plan["proposed_case_result_sha256"]
    checks["crash_lf_normalized_sha256"]=hashlib.sha256((out/"CASE_RESULT.json").read_text(encoding="utf-8").encode("utf-8")).hexdigest()
else:
    checks["crash_retry_committed"]=read(transaction)["state"]=="COMMITTED"
checks["crash_retry_cache_accepted"]=batch.existing(record) is not None

def seed_inventory(root):
    with (ROOT/"work/d2a_cert_direction_preflight.csv").open(encoding="utf-8",newline="") as stream:
        row=next(r for r in csv.DictReader(stream) if r["H_post_slots"]=="80" and r["family"]=="fixed40" and r["readout"]=="point_last_fast_read")
    path=Path(row["direction_record_path"]);(root/path).parent.mkdir(parents=True,exist_ok=True);(root/path).write_bytes((ROOT/path).read_bytes())
    with (root/"work/d2a_cert_direction_preflight.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    write(root/"work/d2a_cert_batch_checkpoint.json",{"execution_failures":[{"case":"old_failure_marker"}]})
def run_stub(root,callback=None,free_disk=None):
    calls=[]
    class NoChild:
        def __init__(self,cmd,**kwargs):
            calls.append(cmd)
            if callback:callback(cmd)
            self.stdout=iter(["audit stub exit1; no actual child\n"])
        def wait(self):return 1
    batch.ROOT=core.ROOT=root;batch.WORK=root/"work"
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(batch.subprocess,"Popen",NoChild))
        stack.enter_context(patch.object(sys,"argv",["audit-batch","--max-H","80","--limit-new-cases","1","--reserve-disk-gib","0"]))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        if free_disk is not None:
            class Disk:
                free=free_disk
            stack.enter_context(patch.object(batch.shutil,"disk_usage",return_value=Disk()))
        batch.main()
    return calls,read(root/"work/d2a_cert_batch_checkpoint.json")

root,out,record=fixture("resume_complete")
seed_inventory(root)
for name in ["STDLIB_VERIFICATION_RECEIPT.json","DERIVED_VERIFICATION_RECEIPT.json"]:(out/name).unlink(missing_ok=True)
legacy=out/"stdlib_verify_batch_stdout.log";legacy.write_text("historical failure evidence\n",encoding="utf-8")
jet=out/"audit"/(read(out/"CASE_RESULT.json")["case"]+"_ADJOINT_JET.json.gz");jet_bytes=jet.read_bytes()
calls,checkpoint=run_stub(root)
checks["complete_payload_resume_verifier_only"]=len(calls)==1 and any("d2a_cert_verify.py" in x for x in calls[0]) and "-S" in calls[0]
checks["historical_log_archived"]=any("historical failure evidence" in p.read_text(encoding="utf-8") for p in out.glob("stdlib_verify_prior_*.log"))
checks["attempt_log_exists"]=bool(list(out.glob("stdlib_verify_attempt_*.log")))
checks["failure_history_retained_on_normal_finish"]=any(x["case"]=="old_failure_marker" for x in checkpoint["execution_failures"])
checks["failed_table_not_arithmetic_complete"]=checkpoint["full_arithmetic_table_completed"] is False
checks["sentinel_jet_unchanged"]=jet.read_bytes()==jet_bytes

root,out,record=fixture("resume_witness_only")
seed_inventory(root)
saved_covariance=copy.deepcopy(read(out/"CASE_RESULT.json")["uniform_variance"])
for name in ["CASE_RESULT.json","STDLIB_VERIFICATION_RECEIPT.json","DERIVED_VERIFICATION_RECEIPT.json"]:(out/name).unlink(missing_ok=True)
for p in (out/"audit").glob("*DIRECTION_CERTIFICATE.json"):p.unlink()
calls,checkpoint=run_stub(root)
checks["witness_only_resume_selects_derive_from_witness"]=len(calls)==1 and "--derive-from-witness" in calls[0]
# Exercise the real case branch with a tiny adapter. No proposal, covariance
# calculation, production gzip, or degree-8 recursion is executed.
flags=[]
for key in ("variance_lower","variance_upper","variance_ratio_upper"):saved_covariance[key]=F(saved_covariance[key])
class SavedWitness:
    def proposal(self):raise AssertionError("must not regenerate saved witness")
    def certify(self,verify):flags.append(verify);assert verify is False;return saved_covariance
with patch.object(core,"bind_actual",return_value=SavedWitness()),patch.object(sys,"argv",["audit","--H","80","--family","fixed40","--readout","point_last_fast_read","--derive-from-witness"]),contextlib.redirect_stdout(io.StringIO()):
    core.main()
checks["witness_only_derives_without_covariance_reference"]=flags==[False]

root,out,record=fixture("history_disk_guard")
seed_inventory(root)
for name in ["STDLIB_VERIFICATION_RECEIPT.json","DERIVED_VERIFICATION_RECEIPT.json"]:(out/name).unlink(missing_ok=True)
calls,checkpoint=run_stub(root,free_disk=0)
checks["disk_guard_starts_no_child"]=not calls
checks["failure_history_retained_on_disk_guard"]=any(x.get("case")=="old_failure_marker" for x in checkpoint.get("execution_failures",[]))

root,out,record=fixture("history_interrupted")
seed_inventory(root)
for name in ["STDLIB_VERIFICATION_RECEIPT.json","DERIVED_VERIFICATION_RECEIPT.json"]:(out/name).unlink(missing_ok=True)
def interrupted(cmd):raise RuntimeError("audit injected launcher interruption")
try:run_stub(root,callback=interrupted)
except RuntimeError as exc:assert "audit injected" in str(exc)
checkpoint=read(root/"work/d2a_cert_batch_checkpoint.json")
checks["failure_history_retained_before_child"]=any(x.get("case")=="old_failure_marker" for x in checkpoint.get("execution_failures",[]))
result={"checks":checks,"failing_boolean_checks":[k for k,v in checks.items() if v is False],"production_jets_read":False,"large_recursions_executed":False,"worker_processes_launched":0,"source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/"work"/n for n in ["d2a_cert_batch.py","d2a_cert_case.py","d2a_cert_verify.py","d2a_cert_rebind_derived.py"]]}}
write(ROOT/"work/d2a_cert_audit_fixture_v3_results.json",result)
print(json.dumps(result,ensure_ascii=False,indent=2))
