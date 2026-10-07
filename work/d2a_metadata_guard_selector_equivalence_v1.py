"""Actual single-snapshot old/new selector comparison; no live writes/science."""
from pathlib import Path
import ast,csv,hashlib,io,json,sys
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"work"))
from d2a_metadata_guard import build_report
old=ROOT/"outputs/d2a_runtime_checkpoint_v1/work/d2a_cert_partial_first_success.py"
source=old.read_text(encoding="utf-8")
assert hashlib.sha256(old.read_bytes()).hexdigest()=="7c83403d97418d38e290762d6b6141fe21b4916c8465e706f64b9eafbce03bdc"
pb=(ROOT/"work/d2a_PROTOCOL_v1.json").read_bytes();p=json.loads(pb)
captured=(ROOT/"work/d2a_cert_review_bound_table.csv").read_bytes()
rows=list(csv.DictReader(io.StringIO(captured.decode("utf-8-sig"))))
nodes=[]
for n in ast.parse(source).body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ("known","answers") for t in n.targets):nodes.append(n)
    if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=="readout":nodes.append(n)
assert len(nodes)==3
env={"rows":rows,"GRID":p["H_post_slots"],"F":F}
exec(compile(ast.Module(body=nodes,type_ignores=[]),"only_old_pure_selector","exec"),env)
new=build_report(captured,pb)
assert new["pairs"]==env["answers"]
print(json.dumps({"status":"PASS_ACTUAL_SINGLE_SNAPSHOT_OLD_NUMERIC_PAYLOAD_PRESERVED",
                 "csv_sha256":hashlib.sha256(captured).hexdigest(),"rows":len(rows),
                 "pairs_and_selected_numeric_strings_exactly_equal":True,"science_imports":False,
                 "old_script_main_or_atomic_executed":False,"live_output_written":False},indent=2))

