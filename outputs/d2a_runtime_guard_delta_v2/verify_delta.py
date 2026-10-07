from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
manifest=root/"MANIFEST.json"
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==(root/"MANIFEST.sha256").read_text().strip()
m=json.loads(manifest.read_text(encoding="utf-8"))
for entry in m["files"]:
    p=(root/entry["path"]).resolve()
    p.relative_to(root.resolve())
    assert p.is_file() and p.stat().st_size==entry["bytes"]
    assert hashlib.sha256(p.read_bytes()).hexdigest()==entry["sha256"]
print(json.dumps({"status":"PASS_SMALL_METADATA_DELTA_HASHES","files":len(m["files"]),"science_replayed":False}))
