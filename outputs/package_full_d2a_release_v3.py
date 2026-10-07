"""Read-only full-D2-a plan/preflight; guarded future scientific ZIP/replay recipe.

Never imports the live runner or touches its locks. --plan/--preflight perform
small metadata checks and stat inventories only. Big hashes, R1 bootstrap and
science replay exist exclusively in explicit frozen --build/--verify-archive.
"""
from pathlib import Path, PurePosixPath
from fractions import Fraction as F
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import io
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
import zipfile
from d2a_archive_witness_view_v1 import ZipWitnessView
from d2a_native_owned_case_cleanup_v1 import cleanup_owned_case
from d2a_archive_coverage_gate_v1 import validate_manifest_inventory,validate_immutable_metadata,record_case_replays
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_SHA = '0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6'
R1_PATH = 'inputs/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip'
R1_SHA = 'f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b'
TABLE_PATH = 'work/d2a_cert_review_bound_table.csv'
HGRID = [40,60,80,100,120,160,200,240,300,400,500,600]
READOUTS = ['average250','point_last_fast_read']
SCIENCE = {'CERTIFIED_TARGET_PASS','VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET'}
ZERO = 'ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE'
EXEC_FAIL = 'CERTIFICATION_EXECUTION_FAILED'
FAILURES = {EXEC_FAIL,'PHYSICAL_CONTRACT_FAILED','PROJECTION_CERTIFICATE_FAILED',
            'MEAN_CERTIFICATE_MISSING_OR_FAILED','VARIANCE_CERTIFICATE_MISSING_OR_FAILED','DIRECTION_OR_CONTRACT_FAILURE'}
CLOSED = SCIENCE | {ZERO} | FAILURES
RESERVE = 25 * 2**30
SMALL_METADATA_CAP = 2 * 1024**2
TABLE_METADATA_CAP = 16 * 1024**2
TOTAL_SMALL_METADATA_CAP = 256 * 1024**2
SHARED = '''work/d2a_core.py
work/d2a_cert_case.py
work/d2a_cert_verify.py
work/d2a_cert_batch.py
work/d2a_cert_preflight.py
work/d2a_cert_rebind_derived.py
work/d2a_cert_bind_artifact_hashes.py
work/d2a_cert_verify_artifact_bindings.py
work/d2a_cert_sync_review_table.py
work/d2a_cert_partial_first_success.py
work/d2a_extract_r1.py
work/d2a_PROTOCOL_v1.json
work/d2a_PROTOCOL_v1.sha256
work/d2a_cert_direction_preflight.csv
work/d2a_cert_review_bound_table.csv
work/d2a_cert_review_bound_table_receipt.json
work/d2a_cert_mean_review_binding.json
work/d2a_metadata_guard.py
outputs/full_d2a_release_metadata_guard_v1.py
outputs/d2a_full_grid_acceptance_v1.py
outputs/d2a_full_grid_acceptance_v2.py
outputs/d2a_archive_witness_view_v1.py
outputs/d2a_native_owned_case_cleanup_v1.py
outputs/d2a_archive_coverage_gate_v1.py
outputs/d2a_metadata_guard_fix_v1.md
outputs/d2a_metadata_guard_fix_v1.json
work/d2a_cert_batch_checkpoint.json
work/d2a_original_brief.md
outputs/d2a_protocol_v1.md
outputs/d2a_source_map_v1.md
outputs/d2a_mean_risk_review_v1.md
references/audit_20261007/post_move_point_bound.md
references/audit_20261007/post_move_point_support.py
references/audit_20261007/post_move_point_support.json
references/audit_20261007/r1_verification.md
references/audit_20261007/r1_verification_receipt.json
references/audit_20261007/next_proofs.tex
outputs/package_full_d2a_release_v1.py
outputs/package_full_d2a_release_v2.py
outputs/package_full_d2a_release_v3.py'''.splitlines()

def relative(value):
    value = str(value).replace('\\','/')
    pure = PurePosixPath(value)
    if pure.is_absolute() or '..' in pure.parts or ':' in value or not pure.parts:
        raise ValueError('Unsafe relative path: '+value)
    return pure.as_posix()

def path(value, root=ROOT):
    p = root / Path(*PurePosixPath(relative(value)).parts)
    p.resolve().relative_to(root.resolve())
    if p.is_symlink():raise ValueError('Symlink not allowed: '+str(p))
    return p

def digest_bytes(data):return hashlib.sha256(data).hexdigest()

def small(value, root=ROOT):
    p = path(value,root)
    cap=TABLE_METADATA_CAP if relative(value)==TABLE_PATH else SMALL_METADATA_CAP
    if p.stat().st_size>cap:raise ValueError('Small-metadata cap exceeded: '+str(p))
    raw=p.read_bytes()
    if len(raw)>cap:raise ValueError('Small-metadata cap exceeded while reading: '+str(p))
    return raw

def document(value, root=ROOT):return json.loads(small(value,root))

def stream_hash(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def semantic(record):
    c = record['calendar']
    return {'protocol_sha256':record['protocol_sha256'],'T_fast_steps':c['T_fast_steps'],
            'moves':c['moves'],'observations':c['observations'],
            'readout':record['readout'],'direction':record['direction']}

def experiment_key(record):
    return digest_bytes(json.dumps(semantic(record),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8'))

def row_key(row):
    return (int(row['H_post_slots']),row['family'],int(row['stage_endpoint']) if row['stage_endpoint'] else None,row['readout'])

def expected_keys():
    values = set()
    for h in HGRID:
        for readout in READOUTS:
            for family in ['stay','fixed20','fixed40','fixed76','terminal_balanced']:
                values.add((h,family,None,readout))
            values.update((h,'switch_then_stay',s,readout) for s in range(20,h+1,20))
    return values

def collect_tree(folder):
    folder = path(folder)
    return [p.relative_to(ROOT).as_posix() for p in sorted(folder.rglob('*')) if p.is_file()]

def snapshot():
    raw = small(TABLE_PATH)
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    errors, mappings, cases, identities, files = [], [], {}, {}, set(SHARED)
    counts = Counter(r['risk_status'] for r in rows)
    if len(rows)!=400 or {row_key(r) for r in rows}!=expected_keys():errors.append('400_ROW_INVENTORY_NOT_EXACT')
    if digest_bytes(small('work/d2a_PROTOCOL_v1.json'))!=PROTOCOL_SHA:errors.append('FROZEN_PROTOCOL_CHANGED')
    guard_spec=importlib.util.spec_from_file_location('d2a_release_metadata_guard',path('work/d2a_metadata_guard.py'))
    guard=importlib.util.module_from_spec(guard_spec);guard_spec.loader.exec_module(guard)
    guard_report=guard.build_report(raw,small('work/d2a_PROTOCOL_v1.json'))
    for number,row in enumerate(rows):
        try:
            rec_path = relative(row['direction_record_path'])
            payload = small(rec_path)
            if digest_bytes(payload)!=row['direction_record_sha256']:raise ValueError('direction hash mismatch')
            record = json.loads(payload)
            if record['protocol_sha256']!=PROTOCOL_SHA:raise ValueError('direction protocol mismatch')
            if row['risk_status'] not in FAILURES:guard.validate_physical_item(record['calendar'])
            identity = experiment_key(record)
            files.add(rec_path)
            info = {'row':number,'key':list(row_key(row)),'identity':identity,'status':row['risk_status'],
                    'direction_record':rec_path,'canonical_case':None}
            if F(row['elapsed_seconds'])!=F(int(row['H_post_slots'])+4,4):raise ValueError('physical time mismatch')
            if row['risk_status']==ZERO:
                if record['direction'] is not None:raise ValueError('nonzero direction labelled ZERO')
                if row.get('protected_power_lower') or row.get('Vplus'):raise ValueError('ZERO row populated with numeric risk')
            elif row['risk_status'] in SCIENCE:
                case_dir = relative(row['certificate_reference'])
                if not re.fullmatch(r'work/d2a_cert_h\d+_[A-Za-z0-9_]+',case_dir):raise ValueError('case namespace invalid')
                result_raw = small(case_dir+'/CASE_RESULT.json')
                result = json.loads(result_raw)
                cand = {'calendar':result['calendar'],'readout':result['readout'],
                        'protocol_sha256':result['protocol_sha256'],'direction':document(case_dir+'/DIRECTION.json')}
                if semantic(cand)!=semantic(record):raise ValueError('alias is not exact experiment identity')
                if digest_bytes(result_raw)!=row['case_result_sha256']:raise ValueError('current CASE_RESULT binding mismatch')
                receipt_path = relative(row['current_receipt_path'])
                receipt_raw = small(receipt_path)
                receipt = json.loads(receipt_raw)
                if digest_bytes(receipt_raw)!=row['current_receipt_sha256']:raise ValueError('current receipt hash mismatch')
                if receipt['case_result_sha256']!=row['case_result_sha256'] or receipt['protocol_sha256']!=PROTOCOL_SHA:raise ValueError('receipt IDs mismatch')
                review = receipt['independent_mean_math_review']
                if review['status']!='ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN' or review['report_sha256']!=row['mean_review_report_sha256']:raise ValueError('mean scope not accepted')
                if digest_bytes(small('outputs/d2a_mean_risk_review_v1.md'))!=review['report_sha256']:raise ValueError('mean report bytes not bound')
                if review.get('general_wide_f_0_75_mirror_coverage_claimed'):raise ValueError('wide fault scope imported')
                if F(review['actual_case_fault_max'])>F(9,200):raise ValueError('fixed fault template scope exceeded')
                for column,key in [('Vplus','variance_upper'),('Vminus','variance_lower'),('variance_ratio_upper','variance_ratio_upper')]:
                    if F(row[column])!=F(result['uniform_variance'][key]):raise ValueError('table/covariance value mismatch '+column)
                for column,key in [('false_alarm_upper','false_alarm_upper'),('protected_power_lower','power_lower'),('gap','gap_lower'),('threshold','threshold')]:
                    if F(row[column])!=F(result['protected_risk'][key]):raise ValueError('table/risk value mismatch '+column)
                if receipt['status']=='PASS_STDLIB_DERIVED_REBINDING':
                    for pkey,hkey in [('prior_case_result_path','prior_case_result_sha256'),('prior_full_stdlib_receipt_path','prior_full_stdlib_receipt_sha256')]:
                        prior=relative(receipt[pkey]);files.add(prior)
                        if digest_bytes(small(prior))!=receipt[hkey]:raise ValueError('prior derived chain bytes mismatch')
                artifact = receipt.get('artifact_sha256')
                if artifact is None:
                    binding = document(relative(row['evidence_hash_binding_path']))
                    if binding['case_result_sha256']!=row['case_result_sha256']:raise ValueError('artifact binding CASE mismatch')
                    if not any(x['sha256']==row['current_receipt_sha256'] for x in binding['verified_receipts']):raise ValueError('artifact binding receipt mismatch')
                    artifact = binding['artifact_sha256']
                case_id = result['case']
                required = ['CASE_RESULT.json','SUMMARY.json','ACTUAL_PROTOCOL.json','PROJECTION_CERTIFICATE.json','DIRECTION.json',
                            'audit/'+case_id+'_DIRECTION_CERTIFICATE.json','audit/'+case_id+'_ADJOINT_JET.json.gz']
                for name in required:
                    if not path(case_dir+'/'+name).is_file():raise ValueError('missing science payload '+name)
                if document(case_dir+'/audit/'+case_id+'_DIRECTION_CERTIFICATE.json')!=result['uniform_variance']:raise ValueError('CASE/covariance certificate mismatch')
                for name,item in artifact.items():
                    p = path(case_dir+'/'+relative(name))
                    if not p.is_file() or p.stat().st_size!=item['bytes']:raise ValueError('artifact missing/size mismatch '+name)
                files.update(collect_tree(case_dir))
                info['canonical_case'] = identity
                identities.setdefault(identity,case_dir)
                if identities[identity]!=case_dir:raise ValueError('same identity has inconsistent canonical directories')
                cases.setdefault(identity,{'case_id':case_id,'directory':case_dir,'rows':[],'artifact_hashes':artifact})['rows'].append(number)
            elif row['risk_status'] in FAILURES:
                if not row['failure_classification']:raise ValueError('execution failure lacks classification')
                own = 'work/d2a_cert_h'+row['H_post_slots']+'_'+row['family']
                if row['stage_endpoint']:own += '_S'+row['stage_endpoint']
                own += '_'+row['readout']
                if path(own).is_dir():files.update(collect_tree(own))
                info['failure_classification'] = row['failure_classification']
            mappings.append(info)
        except (KeyError,ValueError,FileNotFoundError,json.JSONDecodeError) as exc:
            errors.append({'row':number,'key':list(row_key(row)),'error':str(exc),'live_snapshot_may_race':True})
    for p in ROOT.joinpath('work').glob('d2a_cert_recovery_*'):
        if p.is_dir():files.update(collect_tree(p.relative_to(ROOT).as_posix()))
    for name in ['d2a_cert_batch_stdout.log','d2a_cert_detached_recovery_preparation.json',
                 'd2a_cert_derived_rebinding_receipt.json','d2a_cert_artifact_binding_receipt.json']:
        if path('work/'+name).is_file():files.add('work/'+name)
    for rel in list(files):
        if not path(rel).is_file():errors.append('MISSING_REQUIRED_SHARED_FILE '+rel)
    sizes = {rel:path(rel).stat().st_size for rel in files if path(rel).is_file()}
    jet_sizes = [n for rel,n in sizes.items() if rel.endswith('_ADJOINT_JET.json.gz')]
    return {'checked_utc':datetime.now(timezone.utc).isoformat(),'table_sha256':digest_bytes(raw),'rows':rows,
            'row_mappings':mappings,'cases':cases,'files':sorted(files),'file_sizes':sizes,
            'status_counts':dict(counts),'errors':errors,'classified_400':len(rows)==400 and not any(r['risk_status'] not in CLOSED for r in rows),
            'scientific_ready':False,'not_run_rows':counts.get('NOT_RUN',0),
            'observed_unique_science_cases':len(cases),'observed_witness_bytes':sum(jet_sizes),'observed_max_witness_bytes':max(jet_sizes,default=0),
            'metadata_guard_source_sha256':digest_bytes(small('work/d2a_metadata_guard.py')),
            'metadata_guard_full400_done':guard_report['full_D2a_table_complete'],
            'metadata_only_check':True,'large_witness_hashes_checked':False,'science_replayed':False}

def summary(s):
    total = sum(s['file_sizes'].values()) + path(R1_PATH).stat().st_size
    peak = max((sum(s['file_sizes'].get(p,0) for p in s['files'] if p.startswith(c['directory']+'/')) for c in s['cases'].values()),default=0)
    return {k:s[k] for k in ['checked_utc','table_sha256','status_counts','classified_400','not_run_rows','observed_unique_science_cases','observed_witness_bytes','observed_max_witness_bytes']} | {
        'preflight_status':'CLASSIFICATION_COMPLETE_REQUIRES_FROZEN_ZIP_AND_SCIENCE_REPLAY' if s['classified_400'] and not s['errors'] else 'NOT_READY_INCOMPLETE_OR_UNBOUND',
        'scientific_ready':False,'metadata_error_count':len(s['errors']),'metadata_error_examples':s['errors'][:3],
        'observed_payload_bytes_including_R1':total,'observed_max_case_scratch_bytes':peak,
        'free_disk_bytes':shutil.disk_usage(ROOT).free,'reserve_bytes':RESERVE,
        'shared_R1_zip_bytes':path(R1_PATH).stat().st_size,'shared_R1_unpacked_bytes':139638206,
        'plan':'Direct stored-gzip ZIP build; actual-ZIP fresh case-by-case -S verification; cleanup only successful owned scratch case.',
        'metadata_only_stage_V2_is_full_science_package':False,'build_allowed_before_full400':False}

def checked_go(freeze_path,s):
    if not s['classified_400'] or s['errors']:raise ValueError('BUILD_REJECTED_FULL400_INCOMPLETE_OR_UNBOUND')
    freeze = json.loads(Path(freeze_path).read_text(encoding='utf-8'))
    if freeze.get('authorization')!='ROOT_FULL_D2A_FREEZE_GO' or not freeze.get('sources_stopped_and_snapshots_frozen') or not freeze.get('os_process_quiescence_confirmed'):
        raise ValueError('FROZEN_SOURCE_AND_OS_QUIESCENCE_GO_REQUIRED')
    if freeze['table_sha256']!=s['table_sha256'] or freeze['protocol_sha256']!=PROTOCOL_SHA:raise ValueError('FREEZE_BINDING_MISMATCH')
    if any(s['status_counts'].get(x) for x in FAILURES) and not freeze.get('allow_failure_inclusive_archive'):raise ValueError('CLASSIFIED_FAILURES_REQUIRE_EXPLICIT_FAILURE_INCLUSIVE_SCOPE')
    quiescence(freeze)
    return freeze

def quiescence(freeze):
    if not freeze.get('sources_stopped_and_snapshots_frozen') or not freeze.get('os_process_quiescence_confirmed'):
        raise ValueError('QUIESCENT_FROZEN_SOURCE_REQUIRED')
    pids=[int(p) for p in freeze.get('science_owner_pids',[])]
    if os.name=='nt':
        if not pids or any(p<=0 for p in pids):raise ValueError('WINDOWS_OWNER_PIDS_REQUIRED_FOR_ACTUAL_CIM_QUIESCENCE_CHECK')
        code='$d2releasePids=@('+','.join(map(str,pids))+'); @(Get-CimInstance Win32_Process | Where-Object { $d2releasePids -contains $_.ProcessId } | Select-Object -ExpandProperty ProcessId) | ConvertTo-Json -Compress'
        check=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        if check.returncode:raise ValueError('ACTUAL_CIM_QUIESCENCE_CHECK_FAILED')
        if json.loads(check.stdout.strip() or '[]'):raise ValueError('SCIENCE_OR_PUBLISHER_OWNER_PID_STILL_EXISTS')

def build(args,s):
    freeze = checked_go(args.freeze,s)
    target = Path(args.archive or ROOT/'outputs/CERTO_FDI_D2A_FULL_RELEASE_V3.zip').resolve()
    target.relative_to((ROOT/'outputs').resolve())
    if target.exists():raise ValueError('Never overwrite an existing release archive')
    files = set(s['files']) | {R1_PATH}
    publication=freeze.get('publication_artifacts')
    if not publication or not publication.get('revision'):raise ValueError('EXPLICIT_FINAL_PAPER_VERSION_AND_BINDINGS_REQUIRED')
    publication_items=[publication[k] for k in ['source','pdf','compile_layout_json','compile_layout_md']]+publication.get('reviews',[])+publication.get('figures',[])
    for item in publication_items:
        rel=relative(item['path'])
        if not rel.startswith(('outputs/','references/')):raise ValueError('Publication path outside allowed roots')
        files.add(rel)
    layout=document(publication['compile_layout_json']['path'])
    if layout['source_sha256']!=publication['source']['sha256'] or layout['pdf_sha256']!=publication['pdf']['sha256']:
        raise ValueError('CURRENT_PUBLICATION_SOURCE_PDF_LAYOUT_BINDING_MISMATCH')
    for rel in freeze.get('frozen_document_paths',[]):
        rel = relative(rel)
        if not rel.startswith(('outputs/','references/')):raise ValueError('Document path outside allowed roots')
        if rel.endswith('.pdf') and not rel.startswith('outputs/'):raise ValueError('No literature full-text PDF bundling')
        files.add(rel)
    bytes_needed = sum(path(p).stat().st_size for p in files)
    max_case = summary(s)['observed_max_case_scratch_bytes']
    required_free = bytes_needed + max_case + 254624535 + RESERVE + 2*2**30
    if shutil.disk_usage(ROOT).free < required_free:raise ValueError('DISK_BUDGET_REJECTED_WITH_RESERVE_AND_MAX_CASE_SCRATCH')
    temporary = target.with_suffix(target.suffix+'.building')
    if temporary.exists():raise ValueError('Preserve existing partial archive for inspection')
    items = []
    expected = {R1_PATH:R1_SHA}
    expected.update({relative(i['path']):i['sha256'] for i in publication_items})
    for case in s['cases'].values():
        expected.update({case['directory']+'/'+relative(n):v['sha256'] for n,v in case['artifact_hashes'].items()})
    with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
        for rel in sorted(files):
            p = path(rel)
            if p.is_symlink():raise ValueError('Symlink not allowed')
            h = hashlib.sha256();count=0
            # Large witness gzip and original ZIP are stored without recompression.
            with p.open('rb') as source, archive.open(rel,'w',force_zip64=True) as dest:
                while True:
                    block = source.read(2**20)
                    if not block:break
                    h.update(block);count+=len(block);dest.write(block)
            if count!=p.stat().st_size:raise ValueError('File changed during streaming copy')
            value = h.hexdigest()
            if rel in expected and value!=expected[rel]:raise ValueError('Frozen scientific payload hash mismatch '+rel)
            items.append({'path':rel,'bytes':count,'sha256':value})
        manifest = {'schema':'full-d2a-scientific-release-v1','protocol_sha256':PROTOCOL_SHA,'table_sha256':s['table_sha256'],
                    'row_mappings':s['row_mappings'],'cases':s['cases'],'files':items,'freeze':freeze,
                    'status':'BUILT_REQUIRES_ACTUAL_ZIP_OFFLINE_SCIENTIFIC_VERIFICATION','scientific_ready':False,
                    'closed_execution_failure_rows':s['status_counts'].get(EXEC_FAIL,0),
                    'unresolved_classified_failure_rows':sum(s['status_counts'].get(x,0) for x in FAILURES),
                    'R1_bootstrap':{'path':R1_PATH,'sha256':R1_SHA,'expected_source_files':463},
                    'environment':{'independent_verifier':'64-bit Python>=3.11, -S -B -X utf8; stdlib only',
                                   'tested_generation':'Python3.12.10 NumPy2.4.5 SciPy1.17.1 Windows; not used by default verifier'},
                    'scope':'All400 classifications and every canonical scientific witness; aliases by exact identity only.'}
        raw = (json.dumps(manifest,indent=2)+'\n').encode('utf-8')
        archive.writestr('MANIFEST.json',raw)
        archive.writestr('MANIFEST.sha256',digest_bytes(raw)+'  MANIFEST.json\n')
    if target.exists():raise ValueError('Target appeared during build; preserve partial archive')
    os.rename(temporary,target)
    os.chmod(target,stat.S_IREAD)
    print(json.dumps({'status':manifest['status'],'archive':str(target),'sha256':stream_hash(target),'manifest_sha256':digest_bytes(raw),'files':len(items)+2,'scientific_ready':False}))

def extract_members(archive,items,scratch,verified):
    for item in items:
        dest = path(item['path'],scratch)
        dest.parent.mkdir(parents=True,exist_ok=True)
        h=hashlib.sha256();count=0
        with archive.open(item['path']) as source,dest.open('xb') as output:
            while True:
                block=source.read(2**20)
                if not block:break
                h.update(block);count+=len(block);output.write(block)
        if count!=item['bytes'] or h.hexdigest()!=item['sha256']:raise ValueError('ACTUAL_ZIP_PAYLOAD_HASH_MISMATCH '+item['path'])
        verified.add(item['path'])

def run_logged(command,cwd,base):
    base.parent.mkdir(parents=True,exist_ok=True)
    with base.with_suffix('.stdout.log').open('x',encoding='utf-8') as stdout,base.with_suffix('.stderr.log').open('x',encoding='utf-8') as stderr:
        result=subprocess.run(command,cwd=cwd,stdout=stdout,stderr=stderr)
    if result.returncode:raise RuntimeError('OFFLINE_VERIFIER_FAILED '+str(base)+' exit='+str(result.returncode))

def immutable_metadata_items(items):
    """Only original small archive bytes; no R1, PDFs or witness placeholders."""
    suffixes={'.py','.json','.md','.csv','.sha256'}
    selected=[]
    for item in items:
        if item['path']==TABLE_PATH:
            if item['bytes']>TABLE_METADATA_CAP:raise ValueError('REQUIRED_TABLE_METADATA_CAP_EXCEEDED')
            selected.append(item)
        elif PurePosixPath(item['path']).suffix in suffixes and item['bytes']<=SMALL_METADATA_CAP:
            selected.append(item)
    if sum(i['bytes'] for i in selected)>TOTAL_SMALL_METADATA_CAP:
        raise ValueError('TOTAL_IMMUTABLE_SMALL_METADATA_CAP_EXCEEDED')
    return selected

def extract_immutable_metadata_view(archive,items,metadata_root):
    if metadata_root.exists():raise ValueError('New immutable metadata root required')
    selected=immutable_metadata_items(items);verified=set()
    metadata_root.mkdir(exist_ok=False)
    extract_members(archive,selected,metadata_root,verified)
    for item in selected:os.chmod(path(item['path'],metadata_root),stat.S_IREAD)
    return selected,verified

def check_immutable_metadata_view(items,metadata_root):
    for item in items:
        p=path(item['path'],metadata_root)
        if p.stat().st_size!=item['bytes'] or stream_hash(p)!=item['sha256']:
            raise ValueError('ORIGINAL_ARCHIVED_SMALL_METADATA_CHANGED '+item['path'])

def metadata_gate(scratch,metadata_root,archive_path,manifest_sha,logs,tag):
    base=logs/tag
    run_logged([sys.executable,'-S','-B','-X','utf8',
                str(scratch/'outputs/d2a_full_grid_acceptance_v2.py'),
                '--root',str(metadata_root),'--witness-archive',str(archive_path),
                '--archive-manifest-sha256',manifest_sha],metadata_root,base)
    report=json.loads(base.with_suffix('.stdout.log').read_text(encoding='utf-8'))
    if not report.get('full_grid_accepted') or report.get('status')!='PASS_FULL_GRID_METADATA':
        raise ValueError('ACTUAL_ARCHIVE_FULL_GRID_METADATA_GATE_NOT_ACCEPTED')
    return {k:report[k] for k in ['status','exit_code','full_grid_accepted',
                                 'small_metadata_bytes_read','large_witness_bytes_read',
                                 'witness_availability']}

def cleanup_case(case_path,scratch):
    return cleanup_owned_case(case_path,scratch)

def verify_archive(args):
    if not args.freeze:raise ValueError('Explicit quiescent-source GO required before full replay')
    owner=json.loads(Path(args.freeze).read_text(encoding='utf-8'))
    if owner.get('authorization')!='ROOT_FULL_D2A_FREEZE_GO' or not owner.get('os_process_quiescence_confirmed'):
        raise ValueError('NO_FULL_REPLAY_WHILE_SCIENCE_OR_PUBLISHER_LIVE')
    quiescence(owner)
    archive_path=Path(args.archive).resolve()
    # Caller binds the actual manifest emitted by --build, rather than trusting
    # an unbound archive self-assertion. This index never certifies big bytes.
    view=ZipWitnessView(archive_path,args.archive_manifest_sha256)
    scratch=ROOT/'work'/('fd2v3_'+uuid.uuid4().hex[:8]);scratch.mkdir(exist_ok=False)
    metadata_root=scratch/'immutable_metadata_view'
    logs=ROOT/'outputs'/('full_d2a_offline_validation_'+uuid.uuid4().hex[:8]);logs.mkdir(exist_ok=False)
    verified=set();case_results=[]
    with zipfile.ZipFile(archive_path) as archive:
        raw=archive.read('MANIFEST.json')
        if digest_bytes(raw)!=archive.read('MANIFEST.sha256').decode('ascii').split()[0]:raise ValueError('MANIFEST_HASH_MISMATCH')
        m=json.loads(raw)
        names=archive.namelist()
        if len(names)!=len(set(n.casefold() for n in names)):raise ValueError('Duplicate/casefold archive member')
        if set(names)!={i['path'] for i in m['files']}|{'MANIFEST.json','MANIFEST.sha256'}:raise ValueError('Unexpected/missing archive members')
        for info in archive.infolist():
            relative(info.filename)
            if stat.S_ISLNK(info.external_attr>>16):raise ValueError('Symlink archive member')
        if len(m['row_mappings'])!=400 or m['protocol_sha256']!=PROTOCOL_SHA:raise ValueError('Not complete frozen protocol inventory')
        if m['table_sha256']!=owner['table_sha256']:raise ValueError('Archive differs from frozen table')
        if digest_bytes(raw)!=view.manifest_sha256:raise ValueError('Actual manifest changed after index')
        manifest_coverage=validate_manifest_inventory(m)
        dirs={c['directory'] for c in m['cases'].values()}
        shared=[i for i in m['files'] if not any(i['path'].startswith(d+'/') for d in dirs)]
        metadata_items,metadata_verified=extract_immutable_metadata_view(archive,m['files'],metadata_root)
        actual_metadata_coverage=validate_immutable_metadata(m,metadata_root)
        extract_members(archive,shared,scratch,verified)
        original_metadata_gate=metadata_gate(scratch,metadata_root,archive_path,view.manifest_sha256,logs,'original_archive_metadata_before_replay')
        run_logged([sys.executable,'-S','-B','-X','utf8',str(scratch/'work/d2a_extract_r1.py')],scratch,logs/'R1_bootstrap')
        (scratch/'MANIFEST.json').write_bytes(raw)
        run_logged([sys.executable,'-S','-B','-X','utf8',str(scratch/'outputs/package_full_d2a_release_v3.py'),'--offline-small-check'],scratch,logs/'directions_and_alias_inventory')
        for key,c in sorted(m['cases'].items()):
            subset=[i for i in m['files'] if i['path'].startswith(c['directory']+'/')]
            extract_members(archive,subset,scratch,verified)
            case_dir=path(c['directory'],scratch)
            run_logged([sys.executable,'-S','-B','-X','utf8',str(scratch/'outputs/package_full_d2a_release_v3.py'),'--offline-case-check',key],scratch,logs/(c['case_id']+'_alias_scope'))
            run_logged([sys.executable,'-S','-B','-X','utf8',str(scratch/'work/d2a_cert_verify.py'),'--case-dir',str(case_dir)],scratch,logs/(c['case_id']+'_full_stdlib'))
            receipt=case_dir/'STDLIB_VERIFICATION_RECEIPT.json'
            target=logs/(c['case_id']+'_fresh_science_receipt.json')
            target.write_bytes(receipt.read_bytes())
            case_results.append({'identity':key,'case':c['case_id'],'directory':c['directory'],'fresh_receipt':str(target),'fresh_receipt_sha256':stream_hash(target),'status':'PASS_FULL_INDEPENDENT_CASE_VERIFIER'})
            cleanup_case(case_dir,scratch)
        if verified!={i['path'] for i in m['files']}:raise ValueError('Not every actual ZIP payload hash verified')
        check_immutable_metadata_view(metadata_items,metadata_root)
        final_metadata_gate=metadata_gate(scratch,metadata_root,archive_path,view.manifest_sha256,logs,'original_archive_metadata_after_case_cleanup')
        replay_coverage=record_case_replays(m,case_results)
    failed=m.get('unresolved_classified_failure_rows',0)
    result={'status':'PASS_ALL_CANONICAL_SCIENTIFIC_REPLAYS' if not failed else 'FAILURE_INCLUSIVE_CLASSIFICATION_ARCHIVE_VERIFIED_WITH_UNREPLAYED_CLASSIFIED_FAILURES',
            'classified_rows':400,'unique_cases_replayed':len(case_results),'files_hashed_from_actual_ZIP':len(verified),
            'execution_failure_rows':failed,'scientific_ready':not failed,'archive_sha256':stream_hash(archive_path),
            'actual_archive_full_grid_metadata_gate_completed':True,
            'archive_manifest_sha256':view.manifest_sha256,
            'immutable_metadata_view':str(metadata_root),'original_small_metadata_hashes_verified':len(metadata_verified),
            'metadata_before_replay':original_metadata_gate,'metadata_after_case_cleanup':final_metadata_gate,
            'witness_presence_scope':view.scope_info(),
            'manifest_replay_inventory':{k:v for k,v in manifest_coverage.items() if k!='files'},
            'manifest_actual_metadata_binding':actual_metadata_coverage,'complete_case_replay_coverage':replay_coverage,
            'case_results':case_results,'scratch_root':str(scratch),'log_root':str(logs),
            'original_science_modified':False,'full_workspace_unpacked':False,'hardware_operated':False}
    identity=archive_path.stat()
    result['archive_file_identity']={'path':str(archive_path),'bytes':identity.st_size,'mtime_ns':identity.st_mtime_ns,'device':identity.st_dev,'inode':identity.st_ino}
    (logs/'RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='case_results'}))

def projection_raw(doc):
    y,t,z,q,eta=[list(map(F,doc[k])) for k in ['y','t','z','q','eta']]
    box,rate=F(doc['B']),F(doc['R']);n=len(y)
    for i in range(n):
        if abs(z[i])>box or eta[i]*(z[i]-(box if eta[i]>0 else -box))!=0:raise ValueError('Exact box KKT failure')
        if z[i]-y[i]+(q[i-1] if i else 0)-(q[i] if i<n-1 else 0)+eta[i]!=0:raise ValueError('Exact stationarity failure')
    for i in range(n-1):
        b=rate*(t[i+1]-t[i]);v=z[i+1]-z[i]
        if abs(v)>b or q[i]*v!=abs(q[i])*b:raise ValueError('Exact edge KKT failure')
    v=[a-b for a,b in zip(y,z)]
    if sum((a*a for a in v),F(0))/2!=F(doc['objective']):raise ValueError('Squared objective mismatch')
    return v

def offline_small_check(case_key=None):
    m=document('MANIFEST.json')
    sys.path.insert(0,str(ROOT/'work'))
    from d2a_core import calendar,normalize_raw,B,RATE,ETA
    records={}
    for row in m['row_mappings']:
        rec=document(row['direction_record']);records[row['row']]=rec
        c=rec['calendar']
        if c!=calendar(c['H_post_slots'],c['family'],c['stage_endpoint']):raise ValueError('Frozen calendar instance differs')
        if experiment_key(rec)!=row['identity']:raise ValueError('Exact identity differs')
        if case_key is not None:continue
        projection=rec.get('projection_certificate',rec.get('projection'))
        if projection is None:raise ValueError('Direction record lacks exact projection certificate')
        if F(projection['B'])!=B or F(projection['R'])!=RATE:raise ValueError('Projection box/rate differs from frozen source')
        obs=c['observations']
        expected=[F(0) if o['relative_node']<=0 else o['task']*ETA*(o['relative_node']-(F(1,2) if rec['readout']=='average250' else 0)) for o in obs]
        if list(map(F,projection['y']))!=expected or list(map(F,projection['t']))!=[F(o['relative_node']) for o in obs]:raise ValueError('Projection target/time differs')
        raw=projection_raw(projection)
        physical=normalize_raw(raw,[o['task'] for o in c['observations']])
        if (physical is None)!=(rec['direction'] is None):raise ValueError('ZERO classification does not replay')
    if case_key is not None:
        case=m['cases'][case_key];result=document(case['directory']+'/CASE_RESULT.json')
        candidate={'calendar':result['calendar'],'readout':result['readout'],'protocol_sha256':result['protocol_sha256'],
                   'direction':document(case['directory']+'/DIRECTION.json')}
        for index in case['rows']:
            if semantic(candidate)!=semantic(records[index]):raise ValueError('Aliased row is not exact canonical experiment')
    print(json.dumps({'status':'PASS_EXACT_SMALL_DIRECTION_OR_ALIAS_REPLAY','rows':len(records),'case_key':case_key,'large_science_replayed':False}))

def hardlink_delivery(args):
    source=Path(args.archive).resolve();destination=Path(args.link_destination).resolve()
    receipt=json.loads(Path(args.validated_receipt).read_text(encoding='utf-8'))
    if not receipt.get('scientific_ready') or receipt.get('status')!='PASS_ALL_CANONICAL_SCIENTIFIC_REPLAYS':raise ValueError('NO_FULL_SCIENCE_DELIVERY_BEFORE_ACTUAL_ZIP_REPLAY_ACCEPTANCE')
    if source.drive.casefold()!=destination.drive.casefold():raise ValueError('HARDLINK_REQUIRES_SAME_VOLUME_NO_OTHER_DRIVE_COPY')
    actual=source.stat();known=receipt['archive_file_identity']
    if (str(source),actual.st_size,actual.st_mtime_ns,actual.st_dev,actual.st_ino)!=(known['path'],known['bytes'],known['mtime_ns'],known['device'],known['inode']):raise ValueError('Validated archive file identity changed')
    if destination.exists() or not destination.parent.is_dir():raise ValueError('Hardlink destination exists or parent absent')
    if os.name=='nt' and not (source.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY):raise ValueError('Set validated ZIP immutable before delivery link')
    os.link(source,destination)
    if not os.path.samefile(source,destination):raise ValueError('Delivery is not the same file identity')
    print(json.dumps({'status':'SAME_VOLUME_IMMUTABLE_ARCHIVE_HARDLINK','source':str(source),'destination':str(destination),'physical_second_zip_copy':False}))

def main():
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--plan',action='store_true');modes.add_argument('--preflight',action='store_true')
    modes.add_argument('--build',action='store_true');modes.add_argument('--verify-archive',action='store_true')
    modes.add_argument('--offline-small-check',action='store_true');modes.add_argument('--offline-case-check')
    modes.add_argument('--link-delivery',action='store_true')
    parser.add_argument('--freeze');parser.add_argument('--archive');parser.add_argument('--report')
    parser.add_argument('--archive-manifest-sha256')
    parser.add_argument('--link-destination');parser.add_argument('--validated-receipt')
    args=parser.parse_args()
    try:
        if args.link_delivery:hardlink_delivery(args);return 0
        if args.offline_small_check or args.offline_case_check:
            offline_small_check(args.offline_case_check);return 0
        if args.verify_archive:verify_archive(args);return 0
        s=snapshot()
        if args.build:
            build(args,s);return 0
        result=summary(s)
        if args.report:
            target=Path(args.report).resolve();target.relative_to((ROOT/'outputs').resolve())
            target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2))
        return 2 if args.preflight and (not s['classified_400'] or s['errors']) else 0
    except (ValueError,RuntimeError,FileNotFoundError,KeyError,OSError,subprocess.CalledProcessError) as exc:
        print(json.dumps({'status':'FAIL_CLOSED_NO_SCIENTIFIC_READY','reason':str(exc),'scientific_ready':False}));return 2

if __name__=='__main__':raise SystemExit(main())
