"""Read-only audit of completed small JSON receipts; never reads jets."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/"work"
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
checkpoint = read(WORK/"d2a_cert_batch_checkpoint.json")
active = "d2a_cert_"+str(checkpoint.get("current_case"))
binding = read(WORK/"d2a_cert_mean_review_binding.json")
checks = []
for out in sorted(WORK.glob("d2a_cert_h*")):
    if out.name == active or not (out/"CASE_RESULT.json").exists(): continue
    candidates = [out/"DERIVED_VERIFICATION_RECEIPT.json",out/"STDLIB_VERIFICATION_RECEIPT.json"]
    receipt_path = next((p for p in candidates if p.exists()),None)
    if receipt_path is None: continue
    case_bytes = (out/"CASE_RESULT.json").read_bytes()
    case = json.loads(case_bytes)
    receipt = read(receipt_path)
    failures = []
    if receipt["case_result_sha256"] != hashlib.sha256(case_bytes).hexdigest(): failures.append("CASE_RECEIPT_HASH")
    if receipt["protocol_sha256"] != case["protocol_sha256"]: failures.append("PROTOCOL_RECEIPT_CASE")
    review = case.get("independent_mean_math_review",{})
    if review.get("report_sha256") != binding["report_sha256"]: failures.append("REVIEW_REPORT_VERSION")
    if review.get("mean_function_after_scope_binding_sha256") != binding["mean_function_after_scope_binding_sha256"]: failures.append("MEAN_FUNCTION_VERSION")
    if case["calendar"]["H_post_slots"] > 600 or F(review.get("actual_case_fault_max","1")) > F(9,200): failures.append("FROZEN_SCOPE")
    covariance_path=out/"audit"/(case["case"]+"_DIRECTION_CERTIFICATE.json")
    if not covariance_path.exists() or read(covariance_path) != case["uniform_variance"]: failures.append("COVARIANCE_PAYLOAD")
    if receipt["status"] == "PASS_STDLIB_DERIVED_REBINDING":
        prior_case_path=ROOT/receipt["prior_case_result_path"]
        prior_receipt_path=ROOT/receipt["prior_full_stdlib_receipt_path"]
        prior_case=read(prior_case_path)
        prior_receipt=read(prior_receipt_path)
        if sha(prior_case_path) != receipt["prior_case_result_sha256"]: failures.append("PRIOR_CASE_HASH")
        if sha(prior_receipt_path) != receipt["prior_full_stdlib_receipt_sha256"]: failures.append("PRIOR_RECEIPT_HASH")
        if prior_receipt["status"] != "PASS_STDLIB_NEW_CASE_VERIFIER" or prior_receipt["case_result_sha256"] != sha(prior_case_path): failures.append("PRIOR_CHAIN_BINDING")
        if prior_case["uniform_variance"] != case["uniform_variance"]: failures.append("PRIOR_VARIANCE_UNCHANGED")
        if sha(covariance_path) != receipt["uniform_variance_payload_sha256"]: failures.append("COVARIANCE_HASH")
    expected_failure=[]
    if F(case["uniform_variance"]["variance_ratio_upper"]) > F(101,100): expected_failure.append("VARIANCE_RATIO_TARGET_NOT_MET")
    if not case["protected_risk"]["target_pass"]: expected_failure.append("RISK_TARGET_NOT_MET")
    expected_status="CERTIFIED_TARGET_PASS" if not expected_failure else "VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET"
    if case.get("arithmetic_risk_target_status") != expected_status or case["failure_classification"] != expected_failure: failures.append("TARGET_LABEL_CONSISTENCY")
    if (out/"CASE_RESULT.json").read_bytes() != case_bytes: failures.append("CHANGED_DURING_SNAPSHOT")
    checks.append({"case":out.name,"receipt":receipt_path.name,"failures":failures})
result={"active_case_skipped":active,"completed_cases_checked":len(checks),"full_receipts":sum(x["receipt"]=="STDLIB_VERIFICATION_RECEIPT.json" for x in checks),"derived_receipts":sum(x["receipt"]=="DERIVED_VERIFICATION_RECEIPT.json" for x in checks),"failed_cases":[x for x in checks if x["failures"]],"checks":checks,"large_witness_read_or_recursion_executed":False,"live_process_modified":False}
(WORK/"d2a_cert_audit_live_snapshot_v1_results.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k != "checks"},ensure_ascii=False,indent=2))
