"""Independent bounded IO/coverage review; never invokes science or recipe main."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import stat
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from d2a_archive_witness_view_v1 import ZipWitnessView, FilesystemWitnessView
import d2a_archive_coverage_gate_v1 as gate
import d2a_archive_coverage_gate_fixtures_v1 as data_fixture

AREA = ROOT / 'work' / ('archive_bridge_independent_review_' + uuid.uuid4().hex[:8])
AREA.mkdir(exist_ok=False)
tests = []
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    tests.append({'name': name, 'pass': True})

def reject(name, callback, text=None):
    try:
        callback()
    except (ValueError, KeyError, OSError, IndexError, zipfile.BadZipFile) as exc:
        check(name, text is None or text in str(exc))
    else:
        raise AssertionError(name + ': accepted')

def archive(name, manifest, members, extra=None):
    target = AREA / (name + '.zip')
    raw = (json.dumps(manifest, sort_keys=True) + '\n').encode()
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as z:
        for path, body in members.items():
            z.writestr(path, body)
        if extra:
            for entry, body in extra:
                z.writestr(entry, body)
        z.writestr('MANIFEST.json', raw)
        z.writestr('MANIFEST.sha256', sha(raw) + '  MANIFEST.json\n')
    return target, sha(raw)

case = 'work/d2a_cert_h40_review_average250'
witness = case + '/audit/D2A_H40_REVIEW_AVERAGE250_ADJOINT_JET.json.gz'
body = b'independent tiny fixture body; no scientific arithmetic'
manifest = {'files': [{'path': witness, 'bytes': len(body), 'sha256': sha(body)}]}
good, manifest_sha = archive('presence_good', manifest, {witness: body})
original_read = zipfile.ZipFile.read
opened = []
def guarded_read(self, name, *args, **kwargs):
    if str(name).endswith('.gz'):
        opened.append(str(name))
        raise AssertionError('presence backend opened witness body')
    return original_read(self, name, *args, **kwargs)
zipfile.ZipFile.read = guarded_read
try:
    view = ZipWitnessView(good, manifest_sha)
    check('actual member, manifest binding and exact uncompressed size accepted',
          view.available(witness, sha(body), len(body)))
    check('Windows query separators normalize without changing archive namespace',
          view.available(witness.replace('/', '\\'), sha(body), len(body)))
    check('presence view never reads witness body', not opened)
finally:
    zipfile.ZipFile.read = original_read
check('presence scope declines payload hash and scientific arithmetic',
      view.scope_info()['witness_payload_bytes_read'] == 0 and
      not view.scope_info()['witness_payload_hash_verified'] and
      not view.scope_info()['scientific_arithmetic_verified'])
missing, bound = archive('missing_member', manifest, {})
check('manifest entry cannot create an absent actual ZIP member',
      not ZipWitnessView(missing, bound).available(witness, sha(body), len(body)))
unmapped, bound = archive('missing_mapping', {'files': []}, {witness: body})
check('real member without manifest entry is unavailable',
      not ZipWitnessView(unmapped, bound).available(witness, sha(body), len(body)))
reject('independent manifest SHA mismatch rejects', lambda: ZipWitnessView(good, '0' * 64), 'MANIFEST_SHA')
reject('receipt SHA disagreement rejects', lambda: view.available(witness, 'f' * 64, len(body)), 'SHA_MAPPING')
reject('receipt size disagreement rejects', lambda: view.available(witness, sha(body), len(body) + 1), 'SIZE_MISMATCH')
wrong_size, bound = archive('central_size_wrong', manifest, {witness: body + b'!'})
reject('actual central-directory size mismatch rejects',
       lambda: ZipWitnessView(wrong_size, bound).available(witness, sha(body), len(body)), 'SIZE_MISMATCH')
for name, namespace in [('traversal', '../escape'), ('device', 'work/CON.json'),
                        ('trailing_dot', 'work/name.'), ('drive', 'C:/escape')]:
    bad, bound = archive(name, manifest, {witness: body}, [(namespace, b'x')])
    reject('unsafe ZIP namespace rejects: ' + name, lambda p=bad, h=bound: ZipWitnessView(p, h), 'NAMESPACE')
duplicate, bound = archive('casefold_duplicate', manifest, {witness: body}, [(witness.upper(), body)])
reject('casefold duplicate rejects', lambda: ZipWitnessView(duplicate, bound), 'CASEFOLD')
link = zipfile.ZipInfo('work/link')
link.create_system = 3
link.external_attr = (stat.S_IFLNK | 0o777) << 16
linked, bound = archive('symlink', manifest, {witness: body}, [(link, b'target')])
reject('symlink central member rejects', lambda: ZipWitnessView(linked, bound), 'SYMLINK')
reject('unsafe witness query rejects', lambda: view.available('../x', sha(body), len(body)), 'NAMESPACE')

spec = importlib.util.spec_from_file_location('review_frozen_recipe', ROOT / 'outputs/package_full_d2a_release_v2.py')
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)
corrupt_body = bytes([body[0] ^ 1]) + body[1:]
corrupt, bound = archive('same_size_body_corruption', manifest, {witness: corrupt_body})
check('same-size corruption is intentionally accepted only for presence',
      ZipWitnessView(corrupt, bound).available(witness, sha(body), len(body)))
with zipfile.ZipFile(corrupt) as z:
    reject('separate full payload extractor rejects same-size corruption',
           lambda: recipe.extract_members(z, manifest['files'], AREA / 'hash_rejection', set()), 'PAYLOAD_HASH_MISMATCH')
fs_root = AREA / 'filesystem'
(fs_root / 'work').mkdir(parents=True)
(fs_root / 'work/one').write_bytes(b'tiny')
filesystem = FilesystemWitnessView(fs_root)
check('filesystem default retains original contained is_file semantics',
      filesystem.available('work/one', 'invalid ignored binding', -1) and
      not filesystem.available('work/absent', 'invalid ignored binding', -1))
reject('filesystem containment remains enforced', lambda: filesystem.available('../outside'), 'OUTSIDE')

m, payload, science = data_fixture.make_data()
original = copy.deepcopy(m)
check('complete synthetic 400 logical rows / 3 science rows / 2 cases passes inventory',
      gate.validate_manifest_inventory(m)['science_rows'] == 3 and len(m['cases']) == 2)
omitted = copy.deepcopy(m)
omitted['cases'].pop(next(iter(omitted['cases'])))
reject('science omitted from canonical set fails before extraction',
       lambda: gate.validate_manifest_inventory(omitted), 'CANONICAL_CASE_SET_NOT_EXACT')
orphan = copy.deepcopy(m)
orphan['files'].append({'path': 'work/d2a_cert_h80_orphan_average250/audit/D2A_H80_ORPHAN_AVERAGE250_ADJOINT_JET.json.gz',
                        'sha256': 'a' * 64, 'bytes': 1})
reject('current-case witness cannot fall into shared hash-only payloads',
       lambda: gate.validate_manifest_inventory(orphan), 'ORPHAN_CURRENT_CASE_WITNESS')
coverage_zip, bound = archive('coverage_actual_zip', m, payload)
metadata_root = AREA / 'immutable_metadata'
with zipfile.ZipFile(coverage_zip) as z:
    selected, verified = recipe.extract_immutable_metadata_view(z, m['files'], metadata_root)
check('immutable metadata derives from actual ZIP bytes and excludes witness files',
      not any(path.endswith('.gz') for path in verified) and not list(metadata_root.rglob('*.gz')))
binding = gate.validate_immutable_metadata(m, metadata_root)
check('actual CSV/direction/CASE bytes bind complete logical inventory',
      binding['logical_rows'] == 400 and binding['canonical_cases'] == 2 and binding['witness_payload_bytes_read'] == 0)
forged = copy.deepcopy(m)
first = next(iter(forged['cases']))
canonical = forged['cases'].pop(first)
forged['cases']['e' * 64] = canonical
for mapping in forged['row_mappings']:
    if mapping['identity'] == first:
        mapping['identity'] = mapping['canonical_case'] = 'e' * 64
reject('coherent manifest-only forged identity fails actual metadata binding',
       lambda: gate.validate_immutable_metadata(forged, metadata_root), 'MAPPING_ACTUAL_CSV_DIRECTION_BINDING')
replay_root = AREA / 'isolated_replay'
replay_root.mkdir()
(replay_root / 'STDLIB_VERIFICATION_RECEIPT.json').write_text('{"fixture":true}\n', encoding='utf-8')
temporary_witness = replay_root / 'fixture_witness.gz'
temporary_witness.write_bytes(b'tiny disposable fixture')
temporary_witness.unlink()
recipe.check_immutable_metadata_view(selected, metadata_root)
check('separate replay write/removal does not alter immutable archive metadata',
      gate.validate_immutable_metadata(m, metadata_root)['logical_rows'] == 400)
records = [{'identity': key, 'case': c['case_id'], 'directory': c['directory'],
            'status': 'PASS_FULL_INDEPENDENT_CASE_VERIFIER', 'fresh_receipt_sha256': 'b' * 64}
           for key, c in m['cases'].items()]
check('complete synthetic receipt set passes coverage only',
      gate.record_case_replays(m, records)['fresh_canonical_case_replays'] == 2)
reject('missing fresh replay fails coverage despite all metadata present',
       lambda: gate.record_case_replays(m, records[:-1]), 'FRESH_REPLAY_SET_NOT_EXACT')
reject('duplicated replay cannot replace missing canonical identity',
       lambda: gate.record_case_replays(m, [records[0], records[0]]), 'FRESH_REPLAY_SET_NOT_EXACT')
wrong = copy.deepcopy(records)
wrong[0]['directory'] = records[1]['directory']
reject('fresh replay directory must bind its canonical identity',
       lambda: gate.record_case_replays(m, wrong), 'FRESH_REPLAY_CASE_BINDING')
check('pure coverage gates do not mutate supplied manifest', m == original)

result = {'status': 'PASS_INDEPENDENT_BOUNDED_ARCHIVE_IO_AND_COVERAGE_REVIEW',
          'tests': tests, 'test_count': len(tests), 'failed': 0, 'fixture_root': str(AREA),
          'actual_coverage_zip_bytes': coverage_zip.stat().st_size,
          'fixture_payload_is_science': False, 'science_or_R1_executed': False,
          'real_large_witness_bytes_read': 0, 'live_science_files_modified': False,
          'frozen_author_outputs_modified': False, 'scientific_ready': False,
          'synthetic_receipts_are_actual_scientific_replays': False,
          'source_sha256': {name: sha((ROOT / 'outputs' / name).read_bytes())
                            for name in ['d2a_archive_witness_view_v1.py', 'd2a_full_grid_acceptance_v2.py',
                                         'd2a_archive_coverage_gate_v1.py', 'package_full_d2a_release_v2.py']}}
(AREA / 'independent_review_fixture_receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': result['status'], 'checks': len(tests), 'failed': 0,
                  'receipt': str(AREA / 'independent_review_fixture_receipt.json'),
                  'science_executed': False, 'author_outputs_modified': False}))
