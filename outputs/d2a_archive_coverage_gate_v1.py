"""Pure archive inventory/immutable-small-metadata/replay coverage gates.

No science imports, witness body reads, subprocesses or filesystem writes.
"""
from pathlib import Path, PurePosixPath
from collections import defaultdict
import csv
import hashlib
import io
import json
import re
from d2a_archive_witness_view_v1 import archive_relative

PROTOCOL_SHA='0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6'
SCIENCE={'CERTIFIED_TARGET_PASS','VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET'}
ZERO='ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE'
FAILURES={'CERTIFICATION_EXECUTION_FAILED','PHYSICAL_CONTRACT_FAILED','PROJECTION_CERTIFICATE_FAILED',
          'MEAN_CERTIFICATE_MISSING_OR_FAILED','VARIANCE_CERTIFICATE_MISSING_OR_FAILED','DIRECTION_OR_CONTRACT_FAILURE'}
CLOSED=SCIENCE|{ZERO}|FAILURES
CASE=re.compile(r'^work/d2a_cert_h[0-9]+_[A-Za-z0-9_]+$')
HEX=re.compile(r'^[0-9a-f]{64}$')
TABLE='work/d2a_cert_review_bound_table.csv'

def rel(value):return archive_relative(str(value).replace('\\','/'))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def semantic(record):
    c=record['calendar']
    return {'protocol_sha256':record['protocol_sha256'],'T_fast_steps':c['T_fast_steps'],
            'moves':c['moves'],'observations':c['observations'],
            'readout':record['readout'],'direction':record['direction']}
def identity(record):
    return sha(json.dumps(semantic(record),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8'))
def row_key(row):
    return (int(row['H_post_slots']),row['family'],int(row['stage_endpoint']) if row['stage_endpoint'] else None,row['readout'])
def expected_keys():
    keys=set()
    for h in [40,60,80,100,120,160,200,240,300,400,500,600]:
        for readout in ['average250','point_last_fast_read']:
            keys.update((h,f,None,readout) for f in ['stay','fixed20','fixed40','fixed76','terminal_balanced'])
            keys.update((h,'switch_then_stay',s,readout) for s in range(20,h+1,20))
    return keys

def validate_manifest_inventory(m):
    """Must run before shared extraction: manifest cannot omit a science case."""
    if m.get('protocol_sha256')!=PROTOCOL_SHA:raise ValueError('COVERAGE_PROTOCOL_MISMATCH')
    rows=m['row_mappings'];cases=m['cases'];files={}
    if len(rows)!=400 or {r['row'] for r in rows}!=set(range(400)) or any(type(r['row']) is not int for r in rows):
        raise ValueError('COVERAGE_ROW_INDEX_NOT_EXACT_0_TO_399')
    keys=[];science=defaultdict(list)
    for r in rows:
        k=r['key']
        if (not isinstance(k,list) or len(k)!=4 or type(k[0]) is not int
                or (k[2] is not None and type(k[2]) is not int)):
            raise ValueError('COVERAGE_MALFORMED_ROW_KEY')
        keys.append(tuple(k))
        if r['status'] not in CLOSED or not HEX.fullmatch(str(r['identity'])):
            raise ValueError('COVERAGE_UNCLOSED_OR_BAD_IDENTITY')
        if r['status'] in SCIENCE:
            if r['canonical_case']!=r['identity']:raise ValueError('COVERAGE_SCIENCE_CANONICAL_IDENTITY_MISMATCH')
            science[r['identity']].append(r['row'])
        elif r['canonical_case'] is not None:raise ValueError('COVERAGE_NONSCIENCE_HAS_CANONICAL_CASE')
    if len(set(keys))!=400 or set(keys)!=expected_keys():raise ValueError('COVERAGE_LOGICAL_KEY_INVENTORY_NOT_EXACT')
    if set(cases)!=set(science):raise ValueError('COVERAGE_CANONICAL_CASE_SET_NOT_EXACT')
    folded=set()
    for item in m['files']:
        n=archive_relative(item['path'])
        if n.casefold() in folded:raise ValueError('COVERAGE_DUPLICATE_FILE')
        folded.add(n.casefold());files[n]=item
        if not HEX.fullmatch(str(item['sha256'])) or type(item['bytes']) is not int or item['bytes']<0:
            raise ValueError('COVERAGE_MALFORMED_FILE_BINDING')
    if TABLE not in files or files[TABLE]['sha256']!=m['table_sha256']:
        raise ValueError('COVERAGE_MANIFEST_TABLE_BINDING')
    directories=set()
    for key,c in cases.items():
        d=archive_relative(c['directory'])
        if not CASE.fullmatch(d) or d.casefold() in directories:raise ValueError('COVERAGE_BAD_OR_DUPLICATE_CASE_DIRECTORY')
        directories.add(d.casefold())
        name=('D2A_'+PurePosixPath(d).name[len('d2a_cert_'):]).upper()
        if c['case_id']!=name:raise ValueError('COVERAGE_CASE_DIRECTORY_NAME_BINDING')
        if len(c['rows'])!=len(set(c['rows'])) or any(type(i) is not int for i in c['rows']) or set(c['rows'])!=set(science[key]):
            raise ValueError('COVERAGE_CASE_ROW_SET_NOT_EXACT')
        required=['CASE_RESULT.json','SUMMARY.json','ACTUAL_PROTOCOL.json','PROJECTION_CERTIFICATE.json','DIRECTION.json',
                  'audit/'+name+'_DIRECTION_CERTIFICATE.json','audit/'+name+'_ADJOINT_JET.json.gz']
        if any(d+'/'+n not in files for n in required):raise ValueError('COVERAGE_CANONICAL_PAYLOAD_MISSING')
        for n,b in c['artifact_hashes'].items():
            item=files.get(d+'/'+rel(n))
            if item is None or item['sha256']!=b['sha256'] or item['bytes']!=b['bytes']:
                raise ValueError('COVERAGE_CASE_ARTIFACT_MANIFEST_BINDING')
    # Historical recovery namespaces remain historical payloads. A current
    # case witness cannot silently become a shared, hash-only scientific case.
    for n in files:
        parts=PurePosixPath(n).parts
        if len(parts)>=3 and CASE.fullmatch('/'.join(parts[:2])) and n.endswith('_ADJOINT_JET.json.gz'):
            if '/'.join(parts[:2]).casefold() not in directories:
                raise ValueError('COVERAGE_ORPHAN_CURRENT_CASE_WITNESS')
    for r in rows:
        if rel(r['direction_record']) not in files:raise ValueError('COVERAGE_DIRECTION_MEMBER_MISSING')
    return {'status':'PASS_MANIFEST_REPLAY_INVENTORY','logical_rows':400,
            'science_rows':sum(map(len,science.values())),'canonical_cases':len(cases),'files':files}

def validate_immutable_metadata(m,root):
    inventory=validate_manifest_inventory(m);files=inventory['files'];root=Path(root).resolve();total=0
    def read(n):
        nonlocal total
        n=rel(n);p=(root/Path(*PurePosixPath(n).parts)).resolve()
        if not p.is_relative_to(root):raise ValueError('COVERAGE_OUTSIDE_IMMUTABLE_METADATA_ROOT')
        cap=16*1024**2 if n==TABLE else 2*1024**2
        if p.stat().st_size>cap:raise ValueError('COVERAGE_SMALL_METADATA_CAP')
        raw=p.read_bytes();total+=len(raw)
        if total>256*1024**2:raise ValueError('COVERAGE_TOTAL_SMALL_METADATA_CAP')
        if len(raw)!=files[n]['bytes'] or sha(raw)!=files[n]['sha256']:
            raise ValueError('COVERAGE_ACTUAL_ZIP_SMALL_METADATA_HASH')
        return raw
    table=read(TABLE)
    if sha(table)!=m['table_sha256']:raise ValueError('COVERAGE_ACTUAL_TABLE_HASH')
    actual=list(csv.DictReader(io.StringIO(table.decode('utf-8-sig'))))
    if len(actual)!=400 or len({row_key(r) for r in actual})!=400 or {row_key(r) for r in actual}!=expected_keys():
        raise ValueError('COVERAGE_ACTUAL_CSV_KEY_INVENTORY')
    mappings={r['row']:r for r in m['row_mappings']};records={}
    for number,row in enumerate(actual):
        a=mappings[number];n=rel(row['direction_record_path']);raw=read(n);record=json.loads(raw)
        if (tuple(a['key'])!=row_key(row) or a['status']!=row['risk_status'] or rel(a['direction_record'])!=n
                or sha(raw)!=row['direction_record_sha256'] or identity(record)!=a['identity']
                or record['protocol_sha256']!=PROTOCOL_SHA):
            raise ValueError('COVERAGE_MAPPING_ACTUAL_CSV_DIRECTION_BINDING')
        c=record['calendar']
        if (c['H_post_slots'],c['family'],c['stage_endpoint'],record['readout'])!=row_key(row):
            raise ValueError('COVERAGE_DIRECTION_LOGICAL_ROW_BINDING')
        if row['risk_status'] in SCIENCE:
            canonical=m['cases'][a['identity']];d=canonical['directory']
            if rel(row['certificate_reference'])!=d:raise ValueError('COVERAGE_CSV_CANONICAL_DIRECTORY_BINDING')
            result_raw=read(d+'/CASE_RESULT.json');result=json.loads(result_raw)
            direction=json.loads(read(d+'/DIRECTION.json'))
            candidate={k:result[k] for k in ['protocol_sha256','calendar','readout']};candidate['direction']=direction
            if sha(result_raw)!=row['case_result_sha256'] or result['case']!=canonical['case_id'] or identity(candidate)!=a['identity']:
                raise ValueError('COVERAGE_CANONICAL_CASE_ACTUAL_IDENTITY_BINDING')
        records[number]=record
    return {'status':'PASS_MANIFEST_ACTUAL_IMMUTABLE_CSV_DIRECTION_CASE_BINDING',
            'logical_rows':400,'science_rows':inventory['science_rows'],'canonical_cases':inventory['canonical_cases'],
            'small_metadata_bytes_read':total,'witness_payload_bytes_read':0}

def record_case_replays(m,results):
    inventory=validate_manifest_inventory(m)
    if len(results)!=len(m['cases']) or len({r['identity'] for r in results})!=len(results) or {r['identity'] for r in results}!=set(m['cases']):
        raise ValueError('COVERAGE_FRESH_REPLAY_SET_NOT_EXACT')
    for r in results:
        c=m['cases'][r['identity']]
        if (r['case']!=c['case_id'] or r['directory']!=c['directory']
                or r['status']!='PASS_FULL_INDEPENDENT_CASE_VERIFIER' or not HEX.fullmatch(str(r['fresh_receipt_sha256']))):
            raise ValueError('COVERAGE_FRESH_REPLAY_CASE_BINDING')
    return {'status':'PASS_COMPLETE_CANONICAL_REPLAY_COVERAGE','logical_rows':400,
            'science_rows':inventory['science_rows'],'required_canonical_cases':len(m['cases']),
            'fresh_canonical_case_replays':len(results)}
