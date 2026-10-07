"""Preserve stopped-run evidence and prepare a checked, minimal resume."""
from datetime import datetime, timezone
import argparse
import ctypes
from ctypes import wintypes
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import d2a_cert_batch as batch

ROOT=batch.ROOT.resolve();WORK=ROOT/"work"
OLD_SCIENCE_PID=59248;OLD_PUBLISHER_PID=63968


def alive(pid):
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
    finally:kernel.CloseHandle(handle)


def within(path):
    resolved=path.resolve()
    assert resolved.is_relative_to(ROOT),str(resolved)
    return resolved


def digest(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--old-science-pid",type=int,default=OLD_SCIENCE_PID)
    parser.add_argument("--old-publisher-pid",type=int,default=OLD_PUBLISHER_PID)
    parser.add_argument("--allow-missing-locks",action="store_true")
    parser.add_argument("--cause",default="EXTERNAL_FORCED_TERMINATION_NO_EXIT_CODE")
    args=parser.parse_args();old_science=args.old_science_pid;old_publisher=args.old_publisher_pid
    assert not alive(old_science) and not alive(old_publisher)
    for name,expected in (("d2a_cert_batch.lock",{"pid":old_science,"protocol_sha256":batch.PROTOCOL_SHA}),
                          ("d2a_cert_live_publisher.lock",{"pid":old_publisher,"watch_pid":old_science})):
        path=within(WORK/name)
        if path.exists():
            actual=batch.read(path)
            assert all(actual.get(key)==value for key,value in expected.items())
        else:assert args.allow_missing_locks
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive=within(WORK/("d2a_cert_recovery_"+stamp));archive.mkdir(exist_ok=False)
    preserved=[]
    names=list(("d2a_cert_batch.lock","d2a_cert_live_publisher.lock","d2a_cert_batch_checkpoint.json",
                 "d2a_cert_live_publisher_checkpoint.json","d2a_cert_checkpoint.json","d2a_cert_partial_table.csv",
                 "d2a_cert_review_bound_table.csv","d2a_cert_review_bound_table_receipt.json",
                 "d2a_cert_batch_stdout.log","d2a_cert_live_publisher.log","d2a_cert_owner_session.json",
                 "d2a_cert_detached_launch_receipt.json","d2a_cert_detached_recovery_preparation.json"))
    names+= [path.name for path in WORK.glob("d2a_cert_detached_*") if path.is_file() and path.name not in names]
    for name in names:
        source=within(WORK/name)
        if source.exists():
            dest=within(archive/name);shutil.copy2(source,dest)
            assert digest(source)==digest(dest)
            preserved.append({"source":str(source.relative_to(ROOT)),"archive":str(dest.relative_to(ROOT)),"sha256":digest(dest),"bytes":dest.stat().st_size})
    checkpoint=batch.read(WORK/"d2a_cert_batch_checkpoint.json")
    current=checkpoint["current_case"]
    case_out=within(WORK/("d2a_cert_"+current));case_id=("D2A_"+current).upper()
    witness=within(case_out/"audit"/(case_id+"_ADJOINT_JET.json.gz"))
    witness_state={"path":str(witness.relative_to(ROOT)),"exists":witness.exists()}
    if witness.exists():
        witness_state.update(sha256=digest(witness),compressed_bytes=witness.stat().st_size)
        try:
            size=0
            with gzip.open(witness,"rb") as stream:
                while chunk:=stream.read(2**20):size+=len(chunk)
            witness_state.update(gzip_crc_eof_pass=True,uncompressed_bytes=size,recovery_action="DERIVE_FROM_SAVED_WITNESS_THEN_STDLIB_VERIFY")
        except (EOFError,OSError) as error:
            interrupted=within(witness.with_name("INTERRUPTED_"+witness_state["sha256"]+"_"+witness.name))
            assert not interrupted.exists()
            witness.rename(interrupted)
            assert digest(interrupted)==witness_state["sha256"]
            witness_state.update(gzip_crc_eof_pass=False,error=type(error).__name__+": "+str(error),
                                 preserved_interrupted_path=str(interrupted.relative_to(ROOT)),
                                 recovery_action="ONLY_INTERRUPTED_CASE_REGENERATES_WITNESS;PARTIAL_BYTES_RETAINED")
    else:witness_state["recovery_action"]="ONLY_INTERRUPTED_CASE_GENERATES_MISSING_WITNESS"
    failures=list(checkpoint.get("execution_failures",[]))
    preflight={batch.name_for(row):row for row in csv.DictReader((WORK/"d2a_cert_direction_preflight.csv").open(encoding="utf-8",newline=""))}
    with (WORK/"d2a_cert_partial_table.csv").open(encoding="utf-8",newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("risk_status")!="CERTIFICATION_EXECUTION_FAILED":continue
            name=batch.name_for(row);found=batch.existing(batch.read_direction_record(preflight[name]))
            entry={"case":name,"stage":"stdlib_verify","exit_code":1,"legacy_failure":row.get("failure_classification"),"preserved_from_old_raw_table":True,
                   "resolved_before_detached_resume":found is not None}
            if found:
                out,result=found;case_hash=digest(out/"CASE_RESULT.json");path,receipt=batch.verified_receipt(out,result,case_hash)
                entry.update(current_receipt_path=str(path.relative_to(ROOT)),current_receipt_sha256=digest(path))
            if not any(item.get("case")==name for item in failures):failures.append(entry)
    interruption={"case":current,"phase":checkpoint["phase"],"observed_utc":datetime.now(timezone.utc).isoformat(),
                  "old_supervisor_pid":old_science,"old_publisher_pid":old_publisher,
                  "exit_code":"UNAVAILABLE; PROCESS_HANDLE_NOT_RETAINED", "observed_shape":args.cause,
                  "agent_final_cleanup_cause":"CONSISTENT_WITH_OBSERVATIONS_BUT_NOT_DIRECTLY_PROVEN" if args.cause.startswith("EXTERNAL") else "NOT_ASSERTED_FOR_THIS_ATTEMPT", "witness":witness_state}
    checkpoint["execution_failures"]=failures
    checkpoint["interruption_history"]=list(checkpoint.get("interruption_history",[]))+[interruption]
    batch.atomic(WORK/"d2a_cert_batch_checkpoint.json",json.dumps(checkpoint,indent=2)+"\n")
    receipt={"status":"PREPARED_STOPPED_RUN_RECOVERY","workspace":str(ROOT),"protocol_sha256":batch.PROTOCOL_SHA,
             "old_pids_confirmed_dead":True,"old_science_pid":old_science,"old_publisher_pid":old_publisher,"allow_missing_locks":args.allow_missing_locks,
             "archive_directory":str(archive),"preserved":preserved,"interruption":interruption,
             "execution_failure_history":failures,"large_recursions_reexecuted":False,
             "stale_locks_removed":False,"new_processes_started":False}
    batch.atomic(archive/"RECOVERY_PREPARATION_RECEIPT.json",json.dumps(receipt,indent=2)+"\n")
    batch.atomic(WORK/"d2a_cert_detached_recovery_preparation.json",json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"status":receipt["status"],"archive_directory":str(archive),"witness":witness_state,"execution_failure_history":failures}),flush=True)


if __name__=="__main__":main()
