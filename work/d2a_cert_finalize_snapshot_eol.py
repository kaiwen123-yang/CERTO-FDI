"""Seal byte-preserving Git attributes before the first checkpoint commit."""
import hashlib
import json
from pathlib import Path
import stat
root=Path(__file__).resolve().parent.parent
snapshot=root/"outputs/d2a_runtime_checkpoint_v1"
manifest_path=snapshot/"MANIFEST_SHA256.json";hash_path=snapshot/"MANIFEST_SHA256.sha256"
prior_bytes=manifest_path.read_bytes();prior=json.loads(prior_bytes)
prior_hash=hashlib.sha256(prior_bytes).hexdigest()
assert prior_hash==hash_path.read_text().strip()
for relative,expected in prior["files"].items():
    payload=(snapshot/relative).read_bytes()
    assert len(payload)==expected["bytes"] and hashlib.sha256(payload).hexdigest()==expected["sha256"]
attributes=snapshot/".gitattributes"
assert not attributes.exists()
payload=b"* -text\n";attributes.write_bytes(payload)
prior["files"][".gitattributes"]={"sha256":hashlib.sha256(payload).hexdigest(),"bytes":len(payload)}
prior["total_bytes"]+=len(payload)
payload=(json.dumps(prior,indent=2,sort_keys=True)+"\n").encode("utf-8")
new_hash=hashlib.sha256(payload).hexdigest()
for path in (manifest_path,hash_path):path.chmod(stat.S_IREAD|stat.S_IWRITE)
manifest_path.write_bytes(payload);hash_path.write_bytes((new_hash+"\n").encode("ascii"))
for path in (manifest_path,hash_path,attributes):path.chmod(stat.S_IREAD)
receipt={"reason":"core.autocrlf=true; seal Git -text before initial commit to preserve bytes",
         "prior_preseal_manifest_sha256":prior_hash,"sealed_manifest_sha256":new_hash,
         "existing_scientific_runtime_source_bytes_changed":False,"files":len(prior["files"]),"bytes":prior["total_bytes"]}
(root/"work/d2a_cert_snapshot_eol_finalize_receipt.json").write_bytes((json.dumps(receipt,indent=2)+"\n").encode("utf-8"))
print(json.dumps(receipt),flush=True)
