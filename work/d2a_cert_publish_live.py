"""Keep review-bound views current beside the existing serial science runner.

No case generation, scientific verification, witness reads, or worker control.
The only child commands are the small-JSON merge and partial-H* view scripts.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/"work"
LOCK=WORK/"d2a_cert_live_publisher.lock"


def atomic(path,payload):
    next_path=path.with_name(path.name+".next")
    next_path.write_bytes((json.dumps(payload,indent=2)+"\n").encode("utf-8"))
    deadline=time.monotonic()+20
    while True:
        try:
            os.replace(next_path,path)
            break
        except PermissionError as error:
            if os.name!="nt" or getattr(error,"winerror",None) not in (5,32,33) or time.monotonic()>=deadline:raise
            time.sleep(.05)


def alive(pid):
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        status=wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(status))) and status.value==259
    finally:kernel.CloseHandle(handle)


def fingerprint():
    paths=[WORK/"d2a_cert_mean_review_binding.json",ROOT/"outputs/d2a_mean_risk_review_v1.md",
           WORK/"d2a_cert_batch_checkpoint.json"]
    for out in WORK.glob("d2a_cert_h*"):
        if out.is_dir():
            paths.extend(out/name for name in ("STDLIB_VERIFICATION_RECEIPT.json","DERIVED_VERIFICATION_RECEIPT.json"))
    return tuple((str(path),path.stat().st_mtime_ns,path.stat().st_size) for path in sorted(paths) if path.exists())


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--watch-pid",type=int,required=True)
    parser.add_argument("--interval-seconds",type=float,default=45)
    parser.add_argument("--science-session",type=int)
    args=parser.parse_args()
    lock=json.loads((WORK/"d2a_cert_batch.lock").read_text(encoding="utf-8"))
    assert lock["pid"]==args.watch_pid and alive(args.watch_pid)
    descriptor=os.open(LOCK,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(descriptor,json.dumps({"pid":os.getpid(),"watch_pid":args.watch_pid}).encode("utf-8"));os.close(descriptor)
    previous=None;rounds=0;failures=[]
    try:
        with (WORK/"d2a_cert_live_publisher.log").open("a",encoding="utf-8") as logfile:
            while True:
                active=alive(args.watch_pid)
                current=fingerprint()
                if current!=previous or not active:
                    round_errors=[]
                    for script in (WORK/"d2a_cert_sync_review_table.py",ROOT/"outputs/d2a_partial_first_success_v1.py"):
                        command=[sys.executable,"-B","-X","utf8",str(script)]
                        child=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8")
                        if child.returncode:
                            round_errors.append({"script":str(script.relative_to(ROOT)),"exit_code":child.returncode,"output":child.stdout+child.stderr})
                            break
                    rounds+=1
                    if round_errors:failures.append({"round":rounds,"errors":round_errors})
                    receipt_path=WORK/"d2a_cert_review_bound_table_receipt.json"
                    receipt=json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
                    snapshot={"publisher_pid":os.getpid(),"science_supervisor_pid":args.watch_pid,
                              "owner_agent":"/root/d2a_recovery","unified_science_session":args.science_session,
                              "science_session_scope":"owner_agent_only" if args.science_session else "detached_os_process; no_unified_exec_session",
                              "snapshot_utc":datetime.now(timezone.utc).isoformat(),
                              "supervisor_os_alive":active,"round":rounds,"status_counts":receipt.get("status_counts",{}),
                              "authoritative_table_sha256":receipt.get("table_sha256"),
                              "complete_full_table":receipt.get("complete_full_table",False),
                              "round_errors":round_errors,"failure_history":failures,
                              "case_generation_or_scientific_verification_started":False,
                              "status":"LIVE_METADATA_REFRESH" if active else "SUPERVISOR_STOPPED_FINAL_VIEW_REFRESHED"}
                    atomic(WORK/"d2a_cert_live_publisher_checkpoint.json",snapshot)
                    line=json.dumps(snapshot,ensure_ascii=False)
                    logfile.write(line+"\n");logfile.flush();print(line,flush=True)
                    previous=current
                if not active:break
                time.sleep(args.interval_seconds)
    finally:LOCK.unlink(missing_ok=True)


if __name__=="__main__":main()
