"""Read-only verification of downloaded release assets; stdlib only.
Use: python -S -B publication/verify_assets.py <download_directory>
Omitted assets are reported as not downloaded, never passed.
"""
from pathlib import Path
import hashlib,json,sys
manifest=json.loads(Path(__file__).with_name('RELEASE_ASSET_MANIFEST.json').read_text(encoding='utf-8'))
directory=Path(sys.argv[1]).resolve()
results=[]
for item in manifest['assets']:
    p=directory/item['name']
    if not p.is_file():
        results.append({'name':item['name'],'status':'NOT_DOWNLOADED'})
        continue
    with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    ok=p.stat().st_size==item['bytes'] and actual==item['sha256']
    results.append({'name':item['name'],'status':'PASS_BYTES_SHA256' if ok else 'FAIL_BYTES_SHA256','sha256':actual})
print(json.dumps({'scope':'Asset bytes only, not scientific arithmetic or full400 acceptance.','results':results},indent=2))
raise SystemExit(1 if any(r['status'].startswith('FAIL') for r in results) else 0)
