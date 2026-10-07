from pathlib import Path
from fractions import Fraction
import json
import hashlib
import sys
import importlib.util

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "work/r1_extract/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919"

text = (ROOT / "references/audit_20261007/dialogue_body.md").read_text(encoding="utf-8")
brief = text.split("STAGE D2-a — Readout-regime selection and certified first-success horizons (ω = 40 fixed)", 1)[1].split('<a id="message-104">', 1)[0]
(ROOT / "work/d2a_original_brief.md").write_text(brief, encoding="utf-8")
print(brief)
manifest = json.loads((R / "MANIFEST_SHA256.json").read_text(encoding="utf-8"))
print("MANIFEST_TYPE", type(manifest).__name__, list(manifest)[:5])
for name in ["PROTOCOL.json", "MULTIBLOCK_PROTOCOL.json", "audit/SEGMENT_COMPONENT_RETURN.json"]:
    data = json.loads((R / name).read_text())
    keys = ["h", "delta", "fault_slope", "fixed_parameters", "scope", "minimum_postarrival_steps_before_next_move"]
    print(name, json.dumps({k:data[k] for k in keys if k in data}, ensure_ascii=False))
for path in R.rglob("*robot_input.json"):
    data = json.loads(path.read_text())
    print("ROBOT", str(path.relative_to(R)), json.dumps(data, ensure_ascii=False))
    break
for path in R.rglob("*POINT_READOUT_CERTIFICATE.json"):
    data = json.loads(path.read_text())
    print("POINT", str(path.relative_to(R)), json.dumps(data, ensure_ascii=False)[:3000])
    break
