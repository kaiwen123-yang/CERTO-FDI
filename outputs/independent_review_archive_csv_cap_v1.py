"""Independent synthetic CSV IO cap check; no science or live sources read."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import io
import json
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
import d2a_archive_coverage_gate_v1 as gate
from d2a_archive_coverage_gate_fixtures_v1 import make_data
spec = importlib.util.spec_from_file_location('independent_cap_recipe', ROOT / 'outputs/package_full_d2a_release_v2.py')
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)
AREA = ROOT / 'work' / ('archive_cap_independent_review_' + uuid.uuid4().hex[:8])
AREA.mkdir(exist_ok=False)
tests = []
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def check(name, condition):
    if not condition:
        raise AssertionError(name)
    tests.append({'name': name, 'pass': True})
def reject(name, call, text):
    try:
        call()
    except ValueError as exc:
        check(name, text in str(exc))
    else:
        raise AssertionError(name + ': accepted')
def item(path, size):
    return {'path': path, 'bytes': size, 'sha256': 'a' * 64}

m, payload, science = make_data()
rows = list(csv.DictReader(io.StringIO(payload[gate.TABLE].decode())))
for row in rows:
    row['independent_fixture_padding'] = 'P' * 7000
buffer = io.StringIO(newline='')
writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
writer.writeheader()
writer.writerows(rows)
table = buffer.getvalue().encode()
payload[gate.TABLE] = table
m['table_sha256'] = sha(table)
m['files'] = [{**entry, 'bytes': len(table), 'sha256': sha(table)} if entry['path'] == gate.TABLE else entry
              for entry in m['files']]
check('actual synthetic table exceeds 2MiB and stays within exact TABLE cap',
      recipe.SMALL_METADATA_CAP < len(table) <= recipe.TABLE_METADATA_CAP)
archive = AREA / 'actual_synthetic_table.zip'
manifest = (json.dumps(m, sort_keys=True) + '\n').encode()
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
    for name, body in payload.items():
        z.writestr(name, body)
    z.writestr('MANIFEST.json', manifest)
    z.writestr('MANIFEST.sha256', sha(manifest) + '  MANIFEST.json\n')
metadata_root = AREA / 'actual_zip_metadata'
with zipfile.ZipFile(archive) as z:
    selected, verified = recipe.extract_immutable_metadata_view(z, m['files'], metadata_root)
check('actual ZIP TABLE >2MiB is selected, extracted and hash checked',
      gate.TABLE in verified and (metadata_root / gate.TABLE).read_bytes() == table)
check('snapshot small permits only exact TABLE for this larger size', recipe.small(gate.TABLE, metadata_root) == table)
check('coverage accepts actual larger TABLE and binds all synthetic rows',
      gate.validate_immutable_metadata(m, metadata_root)['logical_rows'] == 400)
check('no dummy witness enters metadata view', not list(metadata_root.rglob('*.gz')))
boundary = item(gate.TABLE, 16 * 1024**2)
check('selector accepts exact TABLE 16MiB boundary', recipe.immutable_metadata_items([boundary]) == [boundary])
oversized = item(gate.TABLE, 16 * 1024**2 + 1)
reject('required TABLE 16MiB+1 is explicit rejection',
       lambda: recipe.immutable_metadata_items([oversized]), 'REQUIRED_TABLE_METADATA_CAP_EXCEEDED')
partial_root = AREA / 'must_remain_absent'
with zipfile.ZipFile(archive) as z:
    reject('oversized TABLE rejects before creating any view',
           lambda: recipe.extract_immutable_metadata_view(z, [oversized], partial_root), 'REQUIRED_TABLE_METADATA_CAP_EXCEEDED')
check('oversized TABLE leaves no partial metadata root', not partial_root.exists())
other = item('outputs/other.csv', 2 * 1024**2 + 1)
check('other CSV gets no TABLE exception', recipe.immutable_metadata_items([other]) == [])
exact_other = item('outputs/other.json', 2 * 1024**2)
check('ordinary exact 2MiB boundary remains accepted', recipe.immutable_metadata_items([exact_other]) == [exact_other])
too_many = [item('outputs/item_' + str(number) + '.json', 2 * 1024**2) for number in range(129)]
reject('total original small view above 256MiB rejects',
       lambda: recipe.immutable_metadata_items(too_many), 'TOTAL_IMMUTABLE_SMALL_METADATA_CAP_EXCEEDED')
result = {'status': 'PASS_INDEPENDENT_BOUNDED_ACTUAL_ZIP_CSV_CAP_REVIEW',
          'test_count': len(tests), 'failed': 0, 'tests': tests,
          'actual_zip_bytes': archive.stat().st_size, 'synthetic_table_bytes': len(table),
          'fixture_root': str(AREA), 'science_or_R1_executed': False,
          'real_large_witness_bytes_read': 0, 'frozen_author_outputs_modified': False,
          'scientific_ready': False, 'recipe_sha256': sha((ROOT / 'outputs/package_full_d2a_release_v2.py').read_bytes())}
receipt = AREA / 'independent_review_fixture_receipt.json'
receipt.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': result['status'], 'checks': len(tests), 'failed': 0,
                  'receipt': str(receipt), 'science_executed': False}))
