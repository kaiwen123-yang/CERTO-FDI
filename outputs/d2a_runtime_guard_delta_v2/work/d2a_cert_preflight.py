"""Exact projected-direction preflight of all frozen D2-a candidates.

This is not the full uniform risk table. It retains zeros and proposal failures,
and binds every nonzero direction to an exact KKT certificate and protocol hash.
"""
from pathlib import Path
import csv
import hashlib
import json
import time
import traceback
import d2a_cert_case as core
from d2a_core import all_members
from d2a_metadata_guard import apply_physical_guard, apply_preflight_failure

def main():
    start=time.perf_counter()
    destination=core.ROOT/"work/d2a_cert_preflight"
    destination.mkdir(exist_ok=True)
    rows=[];members=list(all_members())
    for item in members:
        H,family,S=item["H_post_slots"],item["family"],item["stage_endpoint"]
        suffix=f"_S{S}" if S is not None else ""
        for readout in core.PROTOCOL["readouts"]:
            name=f"h{H}_{family}{suffix}_{readout}"
            row={"H_post_slots":H,"elapsed_seconds":item["elapsed_seconds"],"family":family,
                 "stage_endpoint":S,"readout":readout,"transfers":len(item["moves"]),
                 "completed_symmetric_blocks":item["completed_symmetric_blocks"],
                 "physical_rule_status":"NOT_CHECKED",
                 "direction_status":"NOT_RUN","uniform_variance_status":"NOT_RUN",
                 "uniform_mean_status":"NOT_RUN","risk_status":"NOT_RUN"}
            stage="physical"
            try:
                apply_physical_guard(row,item)
                stage="projection"
                direction,projection=core.design(item,readout)
                stage="metadata"
                record={"protocol_sha256":core.PROTOCOL_SHA,"calendar":item,"readout":readout,
                        "projection":projection,"direction":direction,
                        "status":"NONZERO_EXACT_KKT_DIRECTION" if direction is not None else "ZERO_OR_ROUNDED_DEGENERATE_DIRECTION"}
                payload=(json.dumps(core.serial(record),ensure_ascii=False,indent=2)+"\n").encode("utf-8")
                path=destination/f"{name}.json";path.write_bytes(payload)
                row["direction_status"]=record["status"]
                row["direction_record_sha256"]=hashlib.sha256(payload).hexdigest()
                row["direction_record_path"]=str(path.relative_to(core.ROOT))
                if direction is None:row["risk_status"]="ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE"
                else:row["raw_zero_moment"]=direction["exact_zero_moment_preserved"]
                prior=core.ROOT/f"work/d2a_cert_{name}"/"SUMMARY.json"
                if prior.exists():
                    summary=core.read_json(prior)
                    row["uniform_variance_status"]="GENERATED"
                    row["uniform_mean_status"]="GENERATED"
                    row["risk_status"]=summary["status"]
            except Exception as error:
                apply_preflight_failure(row,error,stage)
                (destination/f"{name}_FAILED.json").write_text(json.dumps({"row":row,"traceback":traceback.format_exc()},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            rows.append(row)
        print("PREFLIGHT",H,family,S,"rows",len(rows),flush=True)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (core.ROOT/"work/d2a_cert_direction_preflight.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    counts={}
    for row in rows:counts[row["direction_status"]]=counts.get(row["direction_status"],0)+1
    result={"protocol_sha256":core.PROTOCOL_SHA,"candidate_rows":len(rows),"counts":counts,
            "nonzero_moment_directions":sum(row.get("raw_zero_moment") is False for row in rows),
            "elapsed_wall_seconds":time.perf_counter()-start,
            "full_uniform_risk_scan_completed":False,
            "next_required":"Generate and independently verify actual-direction degree8/Abel plus uniform mean/event/risk for each nonzero candidate; retain failures."}
    (core.ROOT/"work/d2a_cert_preflight_summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result),flush=True)

if __name__=="__main__":main()
