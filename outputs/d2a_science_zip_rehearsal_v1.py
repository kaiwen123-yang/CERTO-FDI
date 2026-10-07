"""Scoped actual-ZIP/fresh-R1/full-stdlib H160 pair rehearsal, never full400.

Default --precheck reads only small source/case metadata, stat and gzip footer.
--execute is an explicit scoped rehearsal; it never calls the full-release GO
gate, edits it, fakes400 rows or writes original science/live tables/locks.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
import time
import uuid
import zipfile
from d2a_archive_coverage_gate_v1 import identity
from d2a_archive_witness_view_v1 import archive_relative

ROOT=Path(__file__).resolve().parents[1]
SCOPE='SCOPED_PAIR_SCIENCE_REHEARSAL_NOT_FINAL_RELEASE'
PROTOCOL_SHA='0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6'
R1='inputs/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip'
R1_SHA='f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b'
HELPER='outputs/package_full_d2a_release_v2.py'
HELPER_SHA='1adc2b0e1acb326e9e63c8a852fa35d3b648abe553484b63f8cdbede8b842953'
PAIR=['work/d2a_cert_h160_terminal_balanced_average250',
      'work/d2a_cert_h160_terminal_balanced_point_last_fast_read']
SHARED=['work/d2a_core.py','work/d2a_cert_case.py','work/d2a_cert_verify.py','work/d2a_extract_r1.py',
        'work/d2a_PROTOCOL_v1.json','work/d2a_PROTOCOL_v1.sha256','work/d2a_cert_mean_review_binding.json',
        'work/d2a_metadata_guard.py','outputs/d2a_mean_risk_review_v1.md','outputs/d2a_source_map_v1.md',
        'outputs/d2a_protocol_v1.md',HELPER,'outputs/d2a_archive_witness_view_v1.py',
        'outputs/d2a_archive_coverage_gate_v1.py','outputs/d2a_science_zip_rehearsal_v1.py',
        'references/audit_20261007/r1_verification.md','references/audit_20261007/r1_verification_receipt.json',
        'references/audit_20261007/post_move_point_bound.md','references/audit_20261007/post_move_point_support.py',
        'references/audit_20261007/post_move_point_support.json']
ZIP=ROOT/'outputs/D2A_H160_TERMINAL_PAIR_SCIENCE_REHEARSAL_V1.zip'
PRECHECK=ROOT/'outputs/d2a_science_zip_rehearsal_precheck_v1.json'
RECEIPT=ROOT/'outputs/d2a_science_zip_rehearsal_receipt_v1.json'
MIN_RAM=8*2**30
MIN_DISK=6*2**30
sha=lambda b:hashlib.sha256(b).hexdigest()

def locate(n,root=ROOT):
    n=archive_relative(str(n).replace('\\','/'));p=(root/Path(*PurePosixPath(n).parts)).resolve()
    if not p.is_relative_to(root.resolve()) or p.is_symlink():raise ValueError('OUTSIDE_OWNED_ROOT '+n)
    return p
def small(n):
    p=locate(n)
    if p.stat().st_size>2*2**20:raise ValueError('PRECHECK_NOT_SMALL '+n)
    return p.read_bytes()
def obj(n):return json.loads(small(n))
def digest(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write_report(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def resource_snapshot():
    cmd='$o=Get-CimInstance Win32_OperatingSystem;$p=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match "^python"} | Select-Object ProcessId,ParentProcessId,CommandLine); [pscustomobject]@{free_ram_bytes=([long]$o.FreePhysicalMemory*1024);python_processes=$p}|ConvertTo-Json -Depth 4 -Compress'
    out=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',cmd],capture_output=True,text=True,encoding='utf-8',check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    result=json.loads(out.stdout);result['free_C_bytes']=shutil.disk_usage(ROOT).free
    return result
def check_resources(r):
    if r['free_ram_bytes']<MIN_RAM or r['free_C_bytes']<MIN_DISK:raise ValueError('SCOPED_RESOURCE_GATE_REJECTED')
    for p in r['python_processes']:
        cmd=p.get('CommandLine') or ''
        if any(n in cmd.replace('\\','/') for n in PAIR) or (re.search(r'--H\s+160(?:\s|$)',cmd) and '--family terminal_balanced' in cmd):
            raise ValueError('SELECTED_PAIR_HAS_ACTIVE_WRITER_OR_REPLAY '+cmd)

def precheck():
    resource=resource_snapshot();check_resources(resource)
    if struct.calcsize('P')!=8 or sys.version_info<(3,11):raise ValueError('64BIT_PYTHON_3_11_REQUIRED')
    if sha(small(HELPER))!=HELPER_SHA:raise ValueError('REVIEWED_HELPER_CHANGED')
    if sha(small('work/d2a_PROTOCOL_v1.json'))!=PROTOCOL_SHA:raise ValueError('FROZEN_PROTOCOL_CHANGED')
    binding=obj('work/d2a_cert_mean_review_binding.json')
    if binding['status']!='ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN' or sha(small(binding['report_path']))!=binding['report_sha256']:
        raise ValueError('MEAN_REVIEW_BINDING_NOT_ACCEPTED')
    expected={R1:R1_SHA};names=set(SHARED)|{R1};cases=[]
    for directory in PAIR:
        result=obj(directory+'/CASE_RESULT.json');receipt=obj(directory+'/STDLIB_VERIFICATION_RECEIPT.json')
        side=obj(directory+'/EVIDENCE_ARTIFACT_HASHES.json');case_hash=sha(small(directory+'/CASE_RESULT.json'))
        rhash=sha(small(directory+'/STDLIB_VERIFICATION_RECEIPT.json'))
        flags=['projection_KKT_exact','actual_protocol_exact','integer_interval_recursions_rechecked','Abel_and_supersolutions_rechecked','uniform_mean_event_risk_recomputed']
        if receipt['status']!='PASS_STDLIB_NEW_CASE_VERIFIER' or any(receipt.get(k) is not True for k in flags):raise ValueError('OLD_FULL_RECEIPT_NOT_ACCEPTED')
        if result['status'] not in {'CERTIFIED_TARGET_PASS','VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET'}:raise ValueError('CASE_NOT_CLOSED')
        if result['protocol_sha256']!=PROTOCOL_SHA or receipt['case_result_sha256']!=case_hash or side['case_result_sha256']!=case_hash:raise ValueError('CASE_RECEIPT_SIDECAR_BINDING')
        if {'path':'STDLIB_VERIFICATION_RECEIPT.json','sha256':rhash} not in side['verified_receipts']:raise ValueError('SIDECAR_OLD_RECEIPT_HASH')
        if receipt['independent_mean_math_review']['status']!='ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN' or receipt['independent_mean_math_review']['report_sha256']!=binding['report_sha256']:raise ValueError('CASE_MEAN_NOT_ACCEPTED')
        if result['calendar']['H_post_slots']!=160 or result['calendar']['family']!='terminal_balanced':raise ValueError('WRONG_SCOPED_CASE')
        record_path='work/d2a_cert_preflight/h160_terminal_balanced_'+result['readout']+'.json'
        record=obj(record_path);direction=obj(directory+'/DIRECTION.json')
        canonical={k:result[k] for k in ['protocol_sha256','calendar','readout']};canonical['direction']=direction
        if identity(record)!=identity(canonical):raise ValueError('EXACT_DIRECTION_CANONICAL_IDENTITY')
        names.add(record_path)
        paths=[p for p in locate(directory).rglob('*') if p.is_file()]
        if any(p.suffix=='.next' or p.is_symlink() for p in paths):raise ValueError('UNCOMMITTED_OR_SYMLINK_CASE')
        names.update(p.relative_to(ROOT).as_posix() for p in paths)
        for n,item in side['artifact_sha256'].items():
            name=directory+'/'+n.replace('\\','/');expected[name]=item['sha256']
            if locate(name).stat().st_size!=item['bytes']:raise ValueError('BOUND_ARTIFACT_SIZE')
        for k in ['prior_case_result_path','prior_full_stdlib_receipt_path']:
            if k in receipt:names.add(receipt[k].replace('\\','/'))
        witness=directory+'/audit/'+result['case']+'_ADJOINT_JET.json.gz'
        with locate(witness).open('rb') as stream:stream.seek(-4,2);isize=struct.unpack('<I',stream.read(4))[0]
        cases.append({'directory':directory,'case':result['case'],'identity':identity(canonical),'readout':result['readout'],
                      'original_target_status':result['status'],'case_result_sha256':case_hash,'original_receipt_sha256':rhash,
                      'witness':witness,'witness_sha256':expected[witness],'witness_bytes':locate(witness).stat().st_size,
                      'gzip_ISIZE_mod2p32_only':isize,'previous_verifier_seconds':receipt['elapsed_wall_seconds'],
                      'case_payload_bytes':sum(p.stat().st_size for p in paths),
                      'original_OS_readonly_all_files':all(p.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY for p in paths)})
    inventory=[]
    for n in sorted(names):
        p=locate(n);s=p.stat()
        if n not in expected:expected[n]=sha(small(n))
        elif s.st_size<=2*2**20 and sha(small(n))!=expected[n]:raise ValueError('SMALL_ARTIFACT_EXPECTED_HASH')
        inventory.append({'path':n,'bytes':s.st_size,'sha256':expected[n],'mtime_ns':s.st_mtime_ns})
    total=sum(i['bytes'] for i in inventory)
    if total>2**30:raise ValueError('SCOPED_PACKAGE_GT_1GiB')
    return {'scope':SCOPE,'status':'PASS_SMALL_METADATA_RESOURCE_AND_PAYLOAD_PRECHECK','scientific_ready':False,
            'cases':cases,'files':inventory,'estimated_archive_payload_bytes':total,
            'estimated_peak_scratch_bytes':locate(R1).stat().st_size+139638206+max(c['case_payload_bytes'] for c in cases)+2*2**20,
            'previous_pair_verifier_seconds':sum(c['previous_verifier_seconds'] for c in cases),'estimated_elapsed_seconds_range':[180,360],
            'resource':resource,'precheck_large_payload_bytes_hashed':0,'original_OS_readonly_required_or_changed':False,
            'source_immutability_scope':'Completed accepted hash-bound pair; original files are not OS readonly. Full input hashes and stat/tree checks before/after enforce scoped byte stability.',
            'full400_GO_faked_or_gate_changed':False,'live_csv_locks_PID_or_CASE_written':False,
            'python':{'executable':sys.executable,'version':platform.python_version(),'bits':struct.calcsize('P')*8},'captured_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}

def load_helper():
    spec=importlib.util.spec_from_file_location('scoped_reviewed_release_helpers',locate(HELPER))
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);return h
def clean_environment():
    env=dict(os.environ);env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None);env['PYTHONDONTWRITEBYTECODE']='1';return env
def run(command,cwd,base):
    started=time.perf_counter()
    with base.with_suffix('.stdout.log').open('x',encoding='utf-8') as out,base.with_suffix('.stderr.log').open('x',encoding='utf-8') as err:
        result=subprocess.run(command,cwd=cwd,stdout=out,stderr=err,env=clean_environment())
    if result.returncode:raise RuntimeError('SCOPED_COMMAND_FAILED '+str(base)+' exit='+str(result.returncode))
    return time.perf_counter()-started

def execute(plan):
    started=time.perf_counter();fresh=precheck()
    if fresh['files']!=plan['files']:raise ValueError('PRECHECK_INPUT_INVENTORY_CHANGED')
    if ZIP.exists() or ZIP.with_suffix('.zip.building').exists() or RECEIPT.exists():raise ValueError('IMMUTABLE_REHEARSAL_TARGET_ALREADY_EXISTS')
    helper=load_helper();logs=ROOT/'outputs'/('d2a_pair_rehearsal_logs_'+uuid.uuid4().hex[:8]);logs.mkdir(exist_ok=False)
    scratch=ROOT/'work'/('d2a_pair_replay_'+uuid.uuid4().hex[:8]);scratch.mkdir(exist_ok=False)
    temporary=ZIP.with_suffix('.zip.building');items=[]
    try:
        with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
            for item in plan['files']:
                p=locate(item['path']);h=hashlib.sha256();count=0
                with p.open('rb') as source,archive.open(item['path'],'w',force_zip64=True) as target:
                    while block:=source.read(2**20):h.update(block);count+=len(block);target.write(block)
                if count!=item['bytes'] or h.hexdigest()!=item['sha256'] or p.stat().st_mtime_ns!=item['mtime_ns']:raise ValueError('ORIGINAL_INPUT_CHANGED_WHILE_STREAMING '+item['path'])
                items.append({k:item[k] for k in ['path','bytes','sha256']})
            readme=(SCOPE+'\nOnly this immutable H160 terminal pair packaging/fresh-environment rehearsal.\n'
                    'average250 remains target PASS; point remains valid TARGET_NOT_MET.\n'
                    'Contains actual covariance jets, exact R1 ZIP and source/mean/provenance metadata.\n'
                    'Does not contain a synthetic400 table or grant final scientific-ready/full400 acceptance.\n'
                    'Use original full stdlib verifier from fresh ROOT after exact R1 bootstrap.\n').encode()
            archive.writestr('README_SCOPED_REHEARSAL.md',readme)
            items.append({'path':'README_SCOPED_REHEARSAL.md','bytes':len(readme),'sha256':sha(readme)})
            manifest={'scope':SCOPE,'scientific_ready':False,'full400':False,'protocol_sha256':PROTOCOL_SHA,
                      'cases':plan['cases'],'files':items,'R1_sha256':R1_SHA,'precheck':plan}
            raw=(json.dumps(manifest,indent=2)+'\n').encode();archive.writestr('MANIFEST.json',raw);archive.writestr('MANIFEST.sha256',sha(raw)+'  MANIFEST.json\n')
        os.rename(temporary,ZIP);os.chmod(ZIP,stat.S_IREAD);archive_hash=digest(ZIP)
        verified=set();results=[]
        with zipfile.ZipFile(ZIP) as archive:
            realraw=archive.read('MANIFEST.json')
            if sha(realraw)!=sha(raw) or archive.read('MANIFEST.sha256').decode().split()[0]!=sha(raw):raise ValueError('ACTUAL_MANIFEST_CHANGED')
            if set(archive.namelist())!={i['path'] for i in items}|{'MANIFEST.json','MANIFEST.sha256'}:raise ValueError('ACTUAL_MEMBER_SET_CHANGED')
            shared=[i for i in items if not any(i['path'].startswith(d+'/') for d in PAIR)]
            helper.extract_members(archive,shared,scratch,verified)
            bootstrap_seconds=run([sys.executable,'-S','-B','-X','utf8',str(scratch/'work/d2a_extract_r1.py')],scratch,logs/'fresh_R1_bootstrap')
            bootstrap=json.loads((scratch/'work/d2a_extraction_receipt.json').read_bytes())
            if bootstrap['archive_sha256_before']!=R1_SHA or bootstrap['archive_sha256_after']!=R1_SHA or bootstrap['extracted_files']!=463:raise ValueError('FRESH_R1_BOOTSTRAP_BINDING')
            write_report(logs/'fresh_R1_bootstrap_receipt.json',bootstrap)
            for case in plan['cases']:
                resource=resource_snapshot();check_resources(resource)
                subset=[i for i in items if i['path'].startswith(case['directory']+'/')]
                helper.extract_members(archive,subset,scratch,verified);directory=locate(case['directory'],scratch)
                elapsed=run([sys.executable,'-S','-B','-X','utf8',str(scratch/'work/d2a_cert_verify.py'),'--case-dir',str(directory)],scratch,logs/case['case'])
                freshreceipt=directory/'STDLIB_VERIFICATION_RECEIPT.json';r=json.loads(freshreceipt.read_bytes())
                flags=['projection_KKT_exact','actual_protocol_exact','integer_interval_recursions_rechecked','Abel_and_supersolutions_rechecked','uniform_mean_event_risk_recomputed']
                if r['status']!='PASS_STDLIB_NEW_CASE_VERIFIER' or any(r.get(k) is not True for k in flags) or r.get('numpy_loaded') is not False or r.get('scipy_loaded') is not False:raise ValueError('FRESH_CASE_FULL_VERIFIER_FLAGS')
                if r['case_result_sha256']!=case['case_result_sha256'] or r['scientific_target_status']!=case['original_target_status']:raise ValueError('FRESH_CASE_TARGET_OR_INPUT_BINDING_CHANGED')
                saved=logs/(case['case']+'_fresh_receipt.json');saved.write_bytes(freshreceipt.read_bytes())
                results.append({'case':case['case'],'directory':case['directory'],'fresh_receipt':str(saved),'fresh_receipt_sha256':digest(saved),
                                'full_verifier_seconds':elapsed,'target_status':r['scientific_target_status'],'full_stdlib_flags_passed':True,
                                'precase_resource':resource,'source':'Actual ZIP extracted case and actual ZIP sources; fresh R1 bootstrap; no original worktree replay.'})
                helper.cleanup_case(directory,scratch)
            if verified!={i['path'] for i in items}:raise ValueError('NOT_EVERY_ACTUAL_ZIP_PAYLOAD_HASHED')
        after=[]
        for item in plan['files']:
            p=locate(item['path']);value=digest(p)
            if value!=item['sha256'] or p.stat().st_size!=item['bytes'] or p.stat().st_mtime_ns!=item['mtime_ns']:raise ValueError('ORIGINAL_INPUT_CHANGED_AFTER_REPLAY '+item['path'])
            after.append({'path':item['path'],'sha256_before_streaming':item['sha256'],'sha256_after_replay':value,'bytes':item['bytes'],'unchanged':True})
        for d in PAIR:
            actual={p.relative_to(ROOT).as_posix() for p in locate(d).rglob('*') if p.is_file()}
            expected={i['path'] for i in plan['files'] if i['path'].startswith(d+'/')}
            if actual!=expected:raise ValueError('ORIGINAL_CASE_TREE_CHANGED')
        if digest(ZIP)!=archive_hash:raise ValueError('ACTUAL_ARCHIVE_CHANGED_AFTER_REPLAY')
        result={'scope':SCOPE,'status':'PASS_SCOPED_ACTUAL_ZIP_FRESH_R1_PAIR_FULL_STDLIB_REHEARSAL','scientific_ready':False,'full400':False,
                'archive':str(ZIP),'archive_sha256':archive_hash,'archive_bytes':ZIP.stat().st_size,'manifest_sha256':sha(raw),
                'archive_payloads_fully_hashed':len(verified),'case_replays':results,'original_inputs_before_after':after,
                'fresh_R1_bootstrap_seconds':bootstrap_seconds,'fresh_R1_bootstrap_receipt':str(logs/'fresh_R1_bootstrap_receipt.json'),
                'scratch_root':str(scratch),'log_root':str(logs),'successful_case_scratch_cleaned':True,'original_science_modified':False,
                'live_tables_locks_PID_written':False,'full400_GO_faked_or_gate_modified':False,'elapsed_seconds':time.perf_counter()-started,
                'source_sha256':sha(Path(__file__).read_bytes()),'final_resource':resource_snapshot()}
        write_report(RECEIPT,result)
        print(json.dumps({'status':result['status'],'cases':len(results),'archive_bytes':result['archive_bytes'],'elapsed_seconds':result['elapsed_seconds'],'scientific_ready':False}),flush=True)
    except Exception as error:
        write_report(logs/'FAILURE_SCOPED_REHEARSAL.json',{'scope':SCOPE,'status':'FAILED_PRESERVE_OWNED_SCRATCH','reason':str(error),'scientific_ready':False,'scratch_root':str(scratch),'archive_or_partial_retained':True})
        raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
    if args.execute:execute(json.loads(PRECHECK.read_bytes()))
    else:
        plan=precheck();write_report(PRECHECK,plan)
        print(json.dumps({k:plan[k] for k in ['status','scope','estimated_archive_payload_bytes','estimated_peak_scratch_bytes','previous_pair_verifier_seconds','estimated_elapsed_seconds_range','precheck_large_payload_bytes_hashed']}),flush=True)

if __name__=='__main__':main()
