"""Read-only checkpoint integrity verification using only the standard library."""
from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
manifest_path=root/"MANIFEST_SHA256.json"
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==(root/"MANIFEST_SHA256.sha256").read_text().strip()
manifest=json.loads(manifest_path.read_bytes())
exclude={"MANIFEST_SHA256.json","MANIFEST_SHA256.sha256"}
actual={str(p.relative_to(root)).replace("\\","/") for p in root.rglob("*") if p.is_file() and p.name not in exclude}
assert actual==set(manifest["files"]),"File set differs from manifest"
for relative,expected in manifest["files"].items():
    path=(root/relative).resolve()
    assert path.is_relative_to(root) and not path.is_symlink()
    payload=path.read_bytes()
    assert len(payload)==expected["bytes"] and hashlib.sha256(payload).hexdigest()==expected["sha256"],relative
print(json.dumps({"status":"PASS_READ_ONLY_RUNTIME_SNAPSHOT","files":len(actual),"total_bytes":sum(v["bytes"] for v in manifest["files"].values())}))
