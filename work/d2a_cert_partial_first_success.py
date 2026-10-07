"""Metadata-only partial-grid report with fail-closed frozen400 guards.
--dry-run reads one CSV byte snapshot and prints only; no live output writes.
Requires work/d2a_metadata_guard.py in final recovery/release recipes.
"""
from pathlib import Path
import argparse, json, os, sys, time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"work"))
from d2a_metadata_guard import build_report, MetadataCoverageError

def atomic(path,text):
    temporary=path.with_name(path.name+".next")
    temporary.write_bytes(text.encode("utf-8"));deadline=time.monotonic()+20
    while True:
        try:os.replace(temporary,path);break
        except PermissionError as error:
            if os.name!="nt" or getattr(error,"winerror",None) not in (5,32,33) or time.monotonic()>=deadline:raise
            time.sleep(.05)

def main():
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");a=p.parse_args()
    try:
        protocol_bytes=(ROOT/"work/d2a_PROTOCOL_v1.json").read_bytes()
        csv_bytes=(ROOT/"work/d2a_cert_review_bound_table.csv").read_bytes()
        result=build_report(csv_bytes,protocol_bytes)
    except (MetadataCoverageError,KeyError,ValueError,OSError) as error:
        print(json.dumps({"status":"FAIL_CLOSED_METADATA_GUARD","full_table_complete":False,
                          "metadata_written":False,"error":str(error)},indent=2),flush=True)
        return 3
    if not a.dry_run:
        payload=json.dumps(result,indent=2)+"\n"
        atomic(ROOT/"work/d2a_cert_partial_first_success.json",payload)
        atomic(ROOT/"outputs/d2a_partial_first_success_v1.json",payload)
    print(json.dumps({"full_table_complete":result["full_D2a_table_complete"],
                      "review_bound_table_sha256":result["review_bound_table_sha256"],
                      "metadata_guard":result["metadata_guard"],"rows":result["rows"],
                      "dry_run":a.dry_run,"metadata_written":not a.dry_run,
                      "pairs":[{k:x.get(k) for k in ("readout","family","first_success_H","physical_endpoint_seconds",
                                  "family_selection_at_H_complete","selected_stage_endpoint")} for x in result["pairs"]]},
                     indent=2),flush=True)
    return 0
if __name__=="__main__":raise SystemExit(main())
