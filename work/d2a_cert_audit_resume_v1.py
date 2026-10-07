"""Isolated resume control: stub child launcher, no process or jets generated."""
from pathlib import Path
import contextlib
import csv
import io
import json
import sys
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"work"))
import d2a_cert_batch as batch
FIX=ROOT/"work/d2a_cert_audit_resume_fixture_v1"
(FIX/"work/d2a_cert_preflight").mkdir(parents=True,exist_ok=True)
with (ROOT/"work/d2a_cert_direction_preflight.csv").open(encoding="utf-8",newline="") as stream:
    reader=csv.DictReader(stream)
    row=next(r for r in reader if r["H_post_slots"]=="80" and r["family"]=="fixed40" and r["readout"]=="point_last_fast_read")
path=Path(row["direction_record_path"])
(FIX/path).write_bytes((ROOT/path).read_bytes())
with (FIX/"work/d2a_cert_direction_preflight.csv").open("w",encoding="utf-8",newline="") as stream:
    writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)
out=FIX/"work/d2a_cert_h80_fixed40_point_last_fast_read"
(out/"audit").mkdir(parents=True,exist_ok=True)
jet=out/"audit/D2A_H80_FIXED40_POINT_LAST_FAST_READ_ADJOINT_JET.json.gz"
jet.write_bytes(b"audit small sentinel; not a scientific witness")
log=out/"generate_batch_stdout.log"
log.write_text("historical generation failure evidence\n",encoding="utf-8")
(FIX/"work/d2a_cert_batch_checkpoint.json").write_text(json.dumps({"execution_failures":[{"case":"old_failure_marker"}]}),encoding="utf-8")
calls=[]
class NoChild:
    def __init__(self,command,**kwargs):
        calls.append(command)
        self.stdout=iter(["audit stub exits1; no child process started\n"])
    def wait(self):return 1
batch.ROOT=FIX;batch.WORK=FIX/"work"
with patch.object(batch.subprocess,"Popen",NoChild),patch.object(sys,"argv",["audit-batch","--max-H","80","--limit-new-cases","1","--reserve-disk-gib","0"]),contextlib.redirect_stdout(io.StringIO()):
    batch.main()
checkpoint=json.loads((FIX/"work/d2a_cert_batch_checkpoint.json").read_text(encoding="utf-8"))
result={"no_child_process_started":True,"new_generation_command_selected_despite_existing_jet":bool(calls) and "--verify-only" not in calls[0],"old_per_case_log_overwritten":"historical generation failure evidence" not in log.read_text(encoding="utf-8"),"prior_checkpoint_failure_not_retained":not any(x.get("case")=="old_failure_marker" for x in checkpoint.get("execution_failures",[])),"failed_only_table_marked_arithmetic_complete":checkpoint["status_counts"]=={"CERTIFICATION_EXECUTION_FAILED":1} and checkpoint["full_arithmetic_table_completed"] is True,"stub_did_not_modify_existing_jet":jet.read_bytes()==b"audit small sentinel; not a scientific witness","commands":calls}
(ROOT/"work/d2a_cert_audit_resume_v1_results.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
