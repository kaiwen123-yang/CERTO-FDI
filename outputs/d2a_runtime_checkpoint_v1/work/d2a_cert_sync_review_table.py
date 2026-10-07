"""Read-only reconciliation of the live raw table with bound case receipts.

The old already-running supervisor may retain conservative pending annotations
from startup. A separate review-bound table is authoritative for current receipt
bindings; it never edits the worker's table or scientific payload.
"""
import csv
import io
import json
import hashlib
from pathlib import Path
import d2a_cert_batch as batch

ROOT=batch.ROOT
rows=[]
with (ROOT/"work/d2a_cert_direction_preflight.csv").open(encoding="utf-8",newline="") as stream:
    for row in csv.DictReader(stream):
        row["H_post_slots"]=int(row["H_post_slots"])
        row["stage_endpoint"]=int(row["stage_endpoint"]) if row["stage_endpoint"] else None
        row["risk_status"]="NOT_RUN"
        if row["direction_status"]=="ZERO_OR_ROUNDED_DEGENERATE_DIRECTION":
            row.update(risk_status="ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE",failure_classification="ZERO_DIRECTION")
        rows.append(row)
cache={}
for row in rows:
    record=batch.read_direction_record(row)
    if record["direction"] is None:continue
    found=batch.existing(record)
    if found:cache[batch.key(record)]=(record,*found)
for row in rows:
    record=batch.read_direction_record(row)
    if record["direction"] is None:continue
    identity=batch.key(record)
    if identity in cache:
        source,out,result=cache[identity]
        assert batch.semantic(source)==batch.semantic(record)
        reused=batch.name_for(row)!=batch.name_for(source["calendar"]|{"readout":source["readout"]})
        batch.apply_result(row,out,result,reused)
raw_path=ROOT/"work/d2a_cert_partial_table.csv"
raw_failures={}
historical_failures={}
if raw_path.exists():
    with raw_path.open(encoding="utf-8",newline="") as stream:
        for raw in csv.DictReader(stream):
            if raw.get("risk_status")=="CERTIFICATION_EXECUTION_FAILED":
                raw_failures[batch.name_for(raw)]=raw
history_path=ROOT/"work/d2a_cert_batch_checkpoint.json"
if history_path.exists():
    for entry in batch.read(history_path).get("execution_failures",[]):
        historical_failures[entry["case"]]=entry
for row in rows:
    raw=raw_failures.get(batch.name_for(row))
    historical=historical_failures.get(batch.name_for(row))
    if historical:
        row["historical_execution_failure_retained"]=historical.get("legacy_failure",historical.get("stage",""))
        row["historical_execution_failure_resolved"]=historical.get("resolved_before_detached_resume",row["risk_status"]!="NOT_RUN")
    if raw:
        row["historical_execution_failure_retained"]=raw.get("failure_classification","")
        if row["risk_status"]=="NOT_RUN":
            row["risk_status"]="CERTIFICATION_EXECUTION_FAILED"
            row["failure_classification"]=raw.get("failure_classification","")
fields=list(dict.fromkeys(k for row in rows for k in row))
buffer=io.StringIO(newline="");writer=csv.DictWriter(buffer,fieldnames=fields)
writer.writeheader();writer.writerows(rows)
batch.atomic(ROOT/"work/d2a_cert_review_bound_table.csv",buffer.getvalue())
counts={}
for row in rows:counts[row["risk_status"]]=counts.get(row["risk_status"],0)+1
summary={"status_counts":counts,"rows":len(rows),"protocol_sha256":batch.PROTOCOL_SHA,
         "binding_report":batch.read(ROOT/"work/d2a_cert_mean_review_binding.json"),
         "raw_live_worker_table_modified":False,
         "raw_historical_execution_failure_rows":len(raw_failures),
         "checkpoint_historical_execution_failure_rows":len(historical_failures),
         "complete_full_table":all(row["risk_status"] in {"CERTIFIED_TARGET_PASS","VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET","ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE"} for row in rows)}
summary["table_sha256"]=hashlib.sha256((ROOT/"work/d2a_cert_review_bound_table.csv").read_bytes()).hexdigest()
batch.atomic(ROOT/"work/d2a_cert_review_bound_table_receipt.json",json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary),flush=True)
