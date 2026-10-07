"""Hash completed evidence files without reexecuting scientific recursions."""
from pathlib import Path
import hashlib
import json
import d2a_cert_case as core

results=[]
for out in sorted((core.ROOT/"work").glob("d2a_cert_h*")):
    if not (out/"CASE_RESULT.json").exists():continue
    result=core.read_json(out/"CASE_RESULT.json")
    case_hash=hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest()
    usable=[]
    for name in ("STDLIB_VERIFICATION_RECEIPT.json","DERIVED_VERIFICATION_RECEIPT.json"):
        path=out/name
        if not path.exists():continue
        receipt=core.read_json(path)
        if receipt.get("case_result_sha256")==case_hash:usable.append((path,receipt))
    if not usable:continue
    artifacts=core.artifact_hashes(out,result["case"])
    for path,receipt in usable:
        if receipt.get("artifact_sha256") is not None:
            assert receipt["artifact_sha256"]==artifacts, "Artifact bytes differ from verified receipt: "+result["case"]
    sidecar=out/"EVIDENCE_ARTIFACT_HASHES.json"
    if sidecar.exists():
        prior=core.read_json(sidecar)
        if prior.get("case_result_sha256")==case_hash:
            assert prior["artifact_sha256"]==artifacts, "Artifact bytes differ from prior sidecar: "+result["case"]
    record={"case":result["case"],"case_result_sha256":case_hash,"protocol_sha256":core.PROTOCOL_SHA,
            "artifact_sha256":artifacts,"verified_receipts":[{"path":str(path.relative_to(out)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()} for path,receipt in usable],
            "purpose":"content integrity binding only; previous scientific checks inherited unchanged",
            "large_recursions_reexecuted":False}
    core.atomic_text(sidecar,json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    results.append({"case":result["case"],"binding_sha256":hashlib.sha256(sidecar.read_bytes()).hexdigest()})
core.atomic_text(core.ROOT/"work/d2a_cert_artifact_binding_receipt.json",json.dumps({"cases":results,"large_recursions_reexecuted":False},indent=2)+"\n")
print("BOUND_COMPLETED_EVIDENCE_HASHES",len(results),flush=True)
