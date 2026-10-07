"""Record review-pending metadata without changing verified arithmetic payload.

The old verification digest is retained. Only status metadata is annotated; all
mean, variance, event, direction, and risk arithmetic is byte-equivalent as JSON
values. No new verifier success is invented.
"""
from pathlib import Path
import hashlib
import json
import os

ROOT=Path(__file__).resolve().parent.parent
def atomic(path,document):
    temporary=path.with_name(path.name+".next")
    temporary.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temporary,path)

for out in sorted((ROOT/"work").glob("d2a_cert_h120_*")):
    path=out/"CASE_RESULT.json"
    if not path.exists():continue
    old=json.loads(path.read_text(encoding="utf-8"))
    if old["status"]=="PENDING_SHARED_MEAN_REVIEW":continue
    original_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    updated={**old,"status":"PENDING_SHARED_MEAN_REVIEW",
             "arithmetic_risk_target_status":old["status"],
             "shared_mean_review_status":"PENDING_SHARED_MEAN_REVIEW"}
    recovered={k:v for k,v in updated.items() if k not in ("arithmetic_risk_target_status","shared_mean_review_status")}
    recovered["status"]=updated["arithmetic_risk_target_status"]
    assert recovered==old
    atomic(path,updated)
    summary_path=out/"SUMMARY.json"
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(status="PENDING_SHARED_MEAN_REVIEW",arithmetic_risk_target_status=old["status"])
    atomic(summary_path,summary)
    receipt_path=out/"STDLIB_VERIFICATION_RECEIPT.json"
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["case_result_sha256"]==original_hash
        receipt.update(verified_case_result_sha256_before_review_annotation=original_hash,
                       case_result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       review_annotation_only=True,
                       arithmetic_payload_changed=False,
                       mathematical_mean_support_review_status="PENDING_SHARED_MEAN_REVIEW")
        atomic(receipt_path,receipt)
    print(out.name,"PENDING_SHARED_MEAN_REVIEW",flush=True)
