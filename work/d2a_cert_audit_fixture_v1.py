"""Small isolated audit controls. Never executes proposal or large recursion.

Production evidence is read only. Every mutation is inside audit_fixture_v1.
The full verifier's expensive certify call is stubbed with its saved payload;
all projection/direction/mean/event/risk and wrapper code still execute.
"""
from pathlib import Path
from fractions import Fraction as F
import contextlib
import copy
import hashlib
import importlib
import inspect
import io
import json
import shutil
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "work"))
import d2a_cert_batch as batch
import d2a_cert_case as core
import d2a_cert_verify as verify
import d2a_cert_rebind_derived as derived

FIX = ROOT / "work/d2a_cert_audit_fixture_v1"
FIX.mkdir(exist_ok=True)
results = {}
snapshots = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"work").glob("d2a_cert*.py")}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")

def fixture(name, case_name):
    root = FIX/name
    (root/"work").mkdir(parents=True, exist_ok=True)
    (root/"outputs").mkdir(exist_ok=True)
    for rel in ["work/d2a_cert_mean_review_binding.json", "outputs/d2a_mean_risk_review_v1.md"]:
        shutil.copyfile(ROOT/rel, root/rel)
    src = ROOT/"work"/case_name
    out = root/"work"/case_name
    (out/"audit").mkdir(parents=True, exist_ok=True)
    for p in src.glob("*.json"):
        shutil.copyfile(p, out/p.name)
    for p in (src/"audit").glob("*.json"):
        shutil.copyfile(p, out/"audit"/p.name)
    batch.ROOT = core.ROOT = root
    batch.WORK = root/"work"
    item = read(out/"CASE_RESULT.json")
    record = {"calendar":item["calendar"], "readout":item["readout"],
              "direction":read(out/"DIRECTION.json"), "protocol_sha256":item["protocol_sha256"]}
    return root, out, record

def fast_full_verifier(out):
    covariance = copy.deepcopy(read(out/"CASE_RESULT.json")["uniform_variance"])
    for k in ["variance_lower", "variance_upper"]:
        covariance[k] = F(covariance[k])
    class SavedPayload:
        def certify(self, verify):
            assert verify is True
            return covariance
    with patch.object(core, "bind_actual", return_value=SavedPayload()), \
         patch.object(sys, "argv", ["audit-verifier", "--case-dir", str(out)]), \
         contextlib.redirect_stdout(io.StringIO()):
        verify.main()
    return read(out/"STDLIB_VERIFICATION_RECEIPT.json")

# The bound function hash currently agrees with the source snapshot.
root, out, record = fixture("binding_hash", "d2a_cert_h80_fixed40_point_last_fast_read")
binding = read(root/"work/d2a_cert_mean_review_binding.json")
actual_hash = hashlib.sha256(inspect.getsource(core.mean_certificate).encode("utf-8")).hexdigest()
results["baseline_mean_function_hash_matches"] = actual_hash == binding["mean_function_after_scope_binding_sha256"]
binding["mean_function_after_scope_binding_sha256"] = "0"*64
write(root/"work/d2a_cert_mean_review_binding.json", binding)
results["wrong_mean_function_hash_still_accepted"] = core.review_binding(record["calendar"])["status"] == "ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN"
bad_item = copy.deepcopy(record["calendar"])
bad_item["H_post_slots"] = 601
try:
    core.review_binding(bad_item)
except AssertionError:
    results["H601_scope_rejected"] = True
else:
    results["H601_scope_rejected"] = False

# Direct cache read does not require the protocol/covariance/witness files.
root, out, record = fixture("missing_artifacts", "d2a_cert_h80_fixed40_point_last_fast_read")
for p in [out/"ACTUAL_PROTOCOL.json", *list((out/"audit").glob("*DIRECTION_CERTIFICATE.json"))]:
    p.unlink()
results["direct_cache_accepts_missing_protocol_and_covariance_artifacts"] = batch.existing(record) is not None
results["fixture_has_no_jets"] = not list(FIX.rglob("*.gz"))
(root/"outputs/d2a_mean_risk_review_v1.md").write_text("invalidated report\n", encoding="utf-8")
results["direct_cache_accepts_stale_report_hash"] = batch.existing(record) is not None
original_case = (out/"CASE_RESULT.json").read_bytes()
(out/"CASE_RESULT.json").write_bytes(original_case+b" ")
results["case_byte_change_rejected"] = batch.existing(record) is None
(out/"CASE_RESULT.json").write_bytes(original_case)
direction = read(out/"DIRECTION.json")
direction["iterations"] += 1
write(out/"DIRECTION.json", direction)
results["direction_change_rejected"] = batch.existing(record) is None

# False successful target labels pass the wrapper verifier.
root, out, record = fixture("false_target_label", "d2a_cert_h80_fixed40_point_last_fast_read")
case = read(out/"CASE_RESULT.json")
assert case["protected_risk"]["target_pass"] is False
case.update(status="CERTIFIED_TARGET_PASS", arithmetic_risk_target_status="CERTIFIED_TARGET_PASS", failure_classification=[])
write(out/"CASE_RESULT.json", case)
receipt = fast_full_verifier(out)
results["false_target_label_full_wrapper_accepted"] = receipt["status"] == "PASS_STDLIB_NEW_CASE_VERIFIER" and receipt["scientific_target_status"] == "CERTIFIED_TARGET_PASS"
row = {}
batch.apply_result(row, out, read(out/"CASE_RESULT.json"), False)
results["false_target_label_table_claims_pass"] = row["risk_status"] == "CERTIFIED_TARGET_PASS"

# A stale derived receipt shadows a fresh full verifier receipt.
root, out, record = fixture("stale_derived", "d2a_cert_h120_terminal_balanced_average250")
case = read(out/"CASE_RESULT.json")
case["elapsed_wall_seconds"] += 1
write(out/"CASE_RESULT.json", case)
receipt = fast_full_verifier(out)
current_sha = hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest()
results["fresh_full_receipt_is_bound"] = receipt["case_result_sha256"] == current_sha
results["stale_derived_shadows_fresh_full_receipt"] = batch.existing(record) is None

# Rebinding crash: CASE commits, final derived receipt does not.
root, out, record = fixture("rebind_crash", "d2a_cert_h120_terminal_balanced_average250")
old_receipt = read(out/"DERIVED_VERIFICATION_RECEIPT.json")
(out/"CASE_RESULT.json").write_bytes((root/old_receipt["prior_case_result_path"]).read_bytes())
(out/"STDLIB_VERIFICATION_RECEIPT.json").write_bytes((root/old_receipt["prior_full_stdlib_receipt_path"]).read_bytes())
(out/"DERIVED_VERIFICATION_RECEIPT.json").unlink()
real_atomic = core.atomic_text
def crash_before_receipt(path, text):
    if path.name == "DERIVED_VERIFICATION_RECEIPT.json":
        raise OSError("audit injected crash before derived receipt commit")
    return real_atomic(path, text)
try:
    with patch.object(core, "atomic_text", side_effect=crash_before_receipt):
        derived.rebind(out)
except OSError as exc:
    assert "audit injected" in str(exc)
results["crash_leaves_accepted_case_without_usable_receipt"] = read(out/"CASE_RESULT.json")["shared_mean_review_status"] == "ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN" and batch.existing(record) is None
try:
    derived.rebind(out)
except AssertionError:
    results["rebind_retry_cannot_resume_after_case_commit"] = True
else:
    results["rebind_retry_cannot_resume_after_case_commit"] = False

results["source_script_sha256"] = snapshots
results["production_scripts_or_certificates_modified"] = False
results["large_recursion_or_proposal_executed"] = False
write(ROOT/"work/d2a_cert_audit_fixture_v1_results.json", results)
print(json.dumps(results, ensure_ascii=False, indent=2))
