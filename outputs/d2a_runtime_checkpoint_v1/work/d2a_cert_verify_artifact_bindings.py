"""Check current completed-case bytes against receipt hashes; no math rerun."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import d2a_cert_batch as batch
import d2a_cert_case as core


def check(out, result):
    case_hash=hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest()
    selected=batch.verified_receipt(out,result,case_hash)
    assert selected is not None
    path,receipt=selected
    receipt_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    expected=receipt.get("artifact_sha256")
    source=str(path.relative_to(batch.ROOT))
    if expected is None:
        sidecar=out/"EVIDENCE_ARTIFACT_HASHES.json"
        binding=batch.read(sidecar)
        assert binding["case_result_sha256"]==case_hash
        assert binding["protocol_sha256"]==batch.PROTOCOL_SHA
        assert {"path":path.name,"sha256":receipt_hash} in binding["verified_receipts"]
        expected=binding["artifact_sha256"]
        source=str(sidecar.relative_to(batch.ROOT))
    actual=core.artifact_hashes(out,result["case"])
    assert actual==expected, "Artifact bytes differ from bound hashes"
    return {"case":result["case"],"case_result_sha256":case_hash,
            "current_receipt_path":str(path.relative_to(batch.ROOT)),
            "current_receipt_sha256":receipt_hash,"hash_binding_source":source,
            "artifact_sha256":actual,"status":"PASS_CURRENT_ARTIFACT_BYTE_BINDING"}


def main():
    parser=argparse.ArgumentParser()
    selection=parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all-completed",action="store_true")
    selection.add_argument("--case-dir",type=Path)
    args=parser.parse_args()
    requested=args.case_dir.resolve() if args.case_dir else None
    seen=set();results=[];failures=[];requested_found=False
    with (batch.WORK/"d2a_cert_direction_preflight.csv").open(encoding="utf-8",newline="") as stream:
        for row in csv.DictReader(stream):
            record=batch.read_direction_record(row)
            if record["direction"] is None:continue
            own_out=batch.WORK/("d2a_cert_"+batch.name_for(row))
            if requested is not None and own_out.resolve()!=requested:continue
            found=batch.existing(record)
            if not found:
                if any((own_out/name).exists() for name in ("STDLIB_VERIFICATION_RECEIPT.json","DERIVED_VERIFICATION_RECEIPT.json")):
                    failures.append({"case_dir":str(own_out.relative_to(batch.ROOT)),"error":"PUBLISHED_RECEIPT_METADATA_NOT_CURRENTLY_ACCEPTED"})
                continue
            out,result=found
            requested_found=True
            if out in seen:continue
            seen.add(out)
            try:results.append(check(out,result))
            except (AssertionError,FileNotFoundError,KeyError,ValueError) as error:
                failures.append({"case":result["case"],"error":type(error).__name__,"message":str(error)})
    if requested is not None and not requested_found:
        failures.append({"case_dir":str(requested),"error":"NO_CURRENT_VERIFIED_CASE"})
    payload={"protocol_sha256":batch.PROTOCOL_SHA,"completed_cases_checked":len(results),
             "status":"PASS_CURRENT_COMPLETED_ARTIFACT_BINDINGS" if not failures else "FAIL_ARTIFACT_BINDING",
             "cases":results,"failures":failures,"large_recursions_reexecuted":False,
             "scope":"Current byte integrity and existing receipt metadata only; not full-table completion or new arithmetic proof"}
    batch.atomic(batch.WORK/"d2a_cert_artifact_integrity_receipt.json",json.dumps(payload,indent=2)+"\n")
    print(json.dumps({key:payload[key] for key in ("status","completed_cases_checked","failures","large_recursions_reexecuted")}),flush=True)
    return bool(failures)


if __name__=="__main__":sys.exit(main())
