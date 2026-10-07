"""Meaningful cache negative controls without touching verified case files."""
from pathlib import Path
import json
import shutil
import d2a_cert_batch as batch

ROOT=batch.ROOT
record=json.loads((ROOT/"work/d2a_cert_preflight/h120_terminal_balanced_average250.json").read_text(encoding="utf-8"))
name="d2a_cert_h120_terminal_balanced_average250"
source=ROOT/"work"/name
fixture=ROOT/"work/d2a_cert_resume_probe_fixture"
destination=fixture/name
destination.mkdir(parents=True,exist_ok=True)
for filename in ("CASE_RESULT.json","DIRECTION.json","STDLIB_VERIFICATION_RECEIPT.json"):
    shutil.copyfile(source/filename,destination/filename)
batch.WORK=fixture
assert batch.existing(record) is not None
original=(destination/"CASE_RESULT.json").read_bytes()
tampered=json.loads(original)
tampered["protected_risk"]["power_lower"]="9/10"
(destination/"CASE_RESULT.json").write_text(json.dumps(tampered),encoding="utf-8")
assert batch.existing(record) is None
(destination/"CASE_RESULT.json").write_bytes(original)
direction=json.loads((destination/"DIRECTION.json").read_text(encoding="utf-8"))
direction["physical"][0]="1/1000"
(destination/"DIRECTION.json").write_text(json.dumps(direction),encoding="utf-8")
assert batch.existing(record) is None
shutil.copyfile(source/"DIRECTION.json",destination/"DIRECTION.json")
receipt=json.loads((destination/"STDLIB_VERIFICATION_RECEIPT.json").read_text(encoding="utf-8"))
receipt["protocol_sha256"]="0"*64
(destination/"STDLIB_VERIFICATION_RECEIPT.json").write_text(json.dumps(receipt),encoding="utf-8")
assert batch.existing(record) is None
shutil.copyfile(source/"STDLIB_VERIFICATION_RECEIPT.json",destination/"STDLIB_VERIFICATION_RECEIPT.json")
assert batch.existing(record) is not None
print("PASS_RESUME_IDENTITY_AND_THREE_NEGATIVE_CONTROLS")
