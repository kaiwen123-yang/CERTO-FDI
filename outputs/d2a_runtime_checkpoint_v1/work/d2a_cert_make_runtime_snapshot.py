"""Create a non-overwriting, hash-verified small-runtime checkpoint."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys

ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/"outputs/d2a_runtime_checkpoint_v1"
STAGE=ROOT/"outputs/d2a_runtime_checkpoint_v1.next"
assert not DEST.exists() and not STAGE.exists(), "A v1 checkpoint must never be overwritten"
STAGE.mkdir()
sources=[
    "work/d2a_core.py","work/d2a_extract_r1.py","work/d2a_freeze.py","work/d2a_discovery.py","work/d2a_smoke.py",
    "work/d2a_cert_case.py","work/d2a_cert_verify.py","work/d2a_cert_batch.py","work/d2a_cert_preflight.py",
    "work/d2a_cert_accept_mean_review.py","work/d2a_cert_rebind_derived.py","work/d2a_cert_sync_review_table.py",
    "work/d2a_cert_bind_artifact_hashes.py","work/d2a_cert_verify_artifact_bindings.py",
    "work/d2a_cert_publish_live.py","work/d2a_cert_partial_first_success.py",
    "work/d2a_cert_prepare_detached_recovery.py","work/d2a_cert_resume_detached.ps1","work/d2a_cert_launch_via_wmi.ps1",
    "work/d2a_cert_audit_fixture_v1.py","work/d2a_cert_audit_fixture_v2.py","work/d2a_cert_audit_fixture_v3.py",
    "work/d2a_cert_atomic_retry_fixture.py","work/d2a_cert_make_runtime_snapshot.py",
    "work/d2a_PROTOCOL_v1.json","work/d2a_PROTOCOL_v1.sha256","work/d2a_cert_mean_review_binding.json",
    "work/d2a_cert_direction_preflight.csv","work/d2a_cert_preflight_summary.json","work/d2a_extraction_receipt.json",
    "work/d2a_smoke_results.json","work/d2a_calendar_inventory.csv","work/d2a_cert_audit_fixture_v3_results.json",
    "work/d2a_cert_atomic_retry_fixture_results.json","work/d2a_cert_runner_audit_v1.md",
    "outputs/d2a_protocol_v1.md","outputs/d2a_source_map_v1.md","outputs/d2a_mean_risk_review_v1.md",
    "outputs/d2a_certificate_progress_v1.md","outputs/d2a_recovery_index_v1.md","outputs/d2a_detached_recovery_v1.md",
    "outputs/d2a_partial_first_success_v1.py","outputs/d2a_partial_first_success_v1.md","outputs/d2a_partial_first_success_v1.json",
    "outputs/d2a_runner_finite_audit_v1.md","outputs/d2a_runner_finite_audit_v1.json",
]
sources += [str(path.relative_to(ROOT)).replace(os.sep,"/") for path in sorted((ROOT/"work/d2a_cert_preflight").glob("*.json"))]
for relative in sources:
    source=ROOT/relative;target=STAGE/relative
    assert source.resolve().is_relative_to(ROOT.resolve()) and not source.is_symlink()
    payload=source.read_bytes()
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
    assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(payload).digest(), "Source changed during snapshot: "+relative

readme="""# D2-a runtime checkpoint v1

This is an immutable small-source checkpoint for local Git preservation, not a complete D2-a certificate release. No large adjoint gzip, CASE directories, current locks, or runtime PID files are included. It preserves the tested physical protocol, exact direction records, wrapper/runner/verifier/rebinding/content-hash code, detached launcher/publisher, and finite regression evidence.

## Verify before restore

Run `python -S -B outputs/d2a_runtime_checkpoint_v1/verify_manifest.py` from the original project, or run the same script by absolute path. It verifies manifest SHA, every file SHA/byte count, and the exact file set, without modifying the snapshot. Files have the Windows read-only attribute. Do not edit v1 or overwrite it; future changes require a new version.

## Safe bootstrap from the original input

1. Restore the checkpoint's `work/` and `outputs/` subtrees into a clean project tree while preserving relative paths. Do not overwrite the active workspace or its witness/history files. The scientific Python entrypoints infer their project root from their restored location. This checkpoint targets Windows; preflight CSV paths retain Windows separators. The detached PowerShell launcher deliberately permits only `C:\\Users\\ykw\\Documents\\ChatGPT\\CEO-FDI`; restore at that path, or explicitly review and change only its workspace safety guard before use at another location.
2. Supply `inputs/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip`. Its required SHA256 is `f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b`. The ZIP is not included in this checkpoint and must remain unchanged.
3. With `work/r1_extract/` absent, run `python -B -X utf8 work/d2a_extract_r1.py`. It checks the input hash, validates all resolved member paths and casefold duplicates before content writes, rejects traversal/absolute paths/symlinks, reads members through CRC verification, and confirms the ZIP hash unchanged. It refuses to replace an existing extraction. The expected extraction has 463 files. Reuse an existing extraction only after checking its source/hash receipts; do not delete it automatically.
4. Use the byte-frozen `work/d2a_PROTOCOL_v1.json` and `.sha256` supplied here. Protocol SHA is `0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6`. Do not rerun `d2a_freeze.py` or change the physical model to chase results. All 400 preflight direction records are included with CSV byte hashes; they can be checked without changing live preflight files. `d2a_cert_preflight.py` is preserved for independent regeneration in a separate fresh tree.
5. The tested generation/preflight environment is Python 3.12.10, NumPy 2.4.5, SciPy 1.17.1 on Windows. Independent `d2a_cert_verify.py`, derived rebinding, and artifact byte verification run with `python -S` and do not load NumPy/SciPy. The exact review report and binding are included; mean-function/report/protocol gates must match. Acceptance remains limited to the fixed template, H<=600, actual f<=0.045, and inherited conditions.
6. `python -B -X utf8 work/d2a_cert_batch.py --inventory-only` checks the frozen inventory without case generation. The included tiny audit fixtures and real Windows atomic-sharing regression are finite engineering checks, not new science or substitutes for full-table certificates.

## Evidence still required from work

To resume already computed rows without regeneration, retain each source `work/d2a_cert_h*/` directory: ACTUAL_PROTOCOL, exact projection and direction JSON, audit covariance certificate, full ADJOINT_JET gzip, CASE_RESULT, SUMMARY, full/DERIVED standard-library receipts, EVIDENCE_ARTIFACT_HASHES sidecars, and all referenced PRIOR_CASE/PRIOR_RECEIPT/rebinding-transaction history. Duplicate members retain table rows and refer to byte-identical scientific designs. These science directories and large jets are deliberately excluded. Source ZIP/inherited proof archive, full case receipts, and saved witnesses are all required; code alone cannot reproduce a claimed PASS.

Also retain `work/d2a_cert_recovery_*/`, INTERRUPTED gzip bytes, execution/interruption histories, and attempt stdout/stderr logs. This snapshot contains review and finite-test evidence, but the live tables/partial-H* data remain incomplete snapshots. Do not use copied historical PID values or stale `alive` flags to restart a process. Confirm actual OS death and matching protocol/lock owners before recovery. Prepare with `d2a_cert_prepare_detached_recovery.py` using actual stopped PIDs/cause, then invoke `d2a_cert_launch_via_wmi.ps1`; it uses an independent WMI broker and `Start-Process -WindowStyle Hidden`, separate new stdout/stderr attempts, and no unified-exec session. The publisher refreshes small metadata only; the serial science runner is unique.

After completion, independently recheck current receipt metadata and artifact bytes with `python -S -B -X utf8 work/d2a_cert_verify_artifact_bindings.py --all-completed`, then strictly merge the table and H* views. Full release still requires all declared rows/classifications, closed predecessor/current members, and a clean unpacked release acceptance. This code checkpoint is not that release.
"""
(STAGE/"README.md").write_bytes(readme.encode("utf-8"))
verify='''"""Read-only checkpoint integrity verification using only the standard library."""
from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
manifest_path=root/"MANIFEST_SHA256.json"
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==(root/"MANIFEST_SHA256.sha256").read_text().strip()
manifest=json.loads(manifest_path.read_bytes())
exclude={"MANIFEST_SHA256.json","MANIFEST_SHA256.sha256"}
actual={str(p.relative_to(root)).replace("\\\\","/") for p in root.rglob("*") if p.is_file() and p.name not in exclude}
assert actual==set(manifest["files"]),"File set differs from manifest"
for relative,expected in manifest["files"].items():
    path=(root/relative).resolve()
    assert path.is_relative_to(root) and not path.is_symlink()
    payload=path.read_bytes()
    assert len(payload)==expected["bytes"] and hashlib.sha256(payload).hexdigest()==expected["sha256"],relative
print(json.dumps({"status":"PASS_READ_ONLY_RUNTIME_SNAPSHOT","files":len(actual),"total_bytes":sum(v["bytes"] for v in manifest["files"].values())}))
'''
(STAGE/"verify_manifest.py").write_bytes(verify.encode("utf-8"))
metadata={"snapshot_utc":datetime.now(timezone.utc).isoformat(),"workspace_source":str(ROOT),
          "source_archive_sha256":"f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b",
          "protocol_sha256":"0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6",
          "scope":"small source/protocol/preflight/review/regression checkpoint; no large witness or final risk release",
          "tested_environment":{"python":"3.12.10","numpy":"2.4.5","scipy":"1.17.1","os":"Windows"},
          "source_files":sources,"large_jets_included":False,"active_work_modified":False}
(STAGE/"SNAPSHOT_METADATA.json").write_bytes((json.dumps(metadata,indent=2)+"\n").encode("utf-8"))
files={}
for path in sorted(STAGE.rglob("*")):
    if path.is_file():
        payload=path.read_bytes();files[str(path.relative_to(STAGE)).replace(os.sep,"/")]={"sha256":hashlib.sha256(payload).hexdigest(),"bytes":len(payload)}
manifest={"files":files,"total_bytes":sum(item["bytes"] for item in files.values()),"large_jets_included":False}
payload=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode("utf-8")
(STAGE/"MANIFEST_SHA256.json").write_bytes(payload)
(STAGE/"MANIFEST_SHA256.sha256").write_bytes((hashlib.sha256(payload).hexdigest()+"\n").encode("ascii"))
STAGE.rename(DEST)
for path in DEST.rglob("*"):
    if path.is_file():path.chmod(stat.S_IREAD)
print(json.dumps({"snapshot":str(DEST),"files":len(files),"bytes":manifest["total_bytes"],"manifest_sha256":hashlib.sha256(payload).hexdigest(),"read_only":True,"large_jets_included":False}),flush=True)
