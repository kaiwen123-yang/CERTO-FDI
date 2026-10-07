"""Resume only documented cleanup failure + not-yet-run point case.

Preserves original wrapper/ZIP/precheck/failure/avg receipt. No avg scientific
rerun, global policy changes, full400 gate edits or original science writes.
"""
from pathlib import Path
import hashlib
import json
import re
import stat
import sys
import time
import zipfile
import d2a_science_zip_rehearsal_v1 as original
from d2a_archive_witness_view_v1 import ZipWitnessView
from d2a_native_owned_case_cleanup_v1 import cleanup_owned_case

ROOT=original.ROOT
LOGS=ROOT/'outputs/d2a_pair_rehearsal_logs_e9098928'
WRAPPER_SHA='2d324aefaa33cb869b79c94bd57aaeb7be6c4b05ec38056118e061e07edb8186'
AVG_RECEIPT_SHA='2ae7eadea94432484964ecc4cdafaae5e4f3efec863dbd53fb1b158e0a6bf019'
RESUME_RECEIPT=ROOT/'outputs/d2a_science_zip_rehearsal_resume_receipt_v1.json'
sha=lambda b:hashlib.sha256(b).hexdigest()

def required(receipt,case,files):
    flags=['projection_KKT_exact','actual_protocol_exact','integer_interval_recursions_rechecked','Abel_and_supersolutions_rechecked','uniform_mean_event_risk_recomputed']
    if receipt['status']!='PASS_STDLIB_NEW_CASE_VERIFIER' or any(receipt.get(k) is not True for k in flags):raise ValueError('FULL_SCIENCE_FLAGS_NOT_PASS')
    if receipt['case_result_sha256']!=case['case_result_sha256'] or receipt['scientific_target_status']!=case['original_target_status'] or receipt['case']!=case['case']:raise ValueError('FRESH_RESULT_TARGET_OR_CASE_BINDING')
    if receipt.get('numpy_loaded') is not False or receipt.get('scipy_loaded') is not False:raise ValueError('NOT_INDEPENDENT_STDLIB_SCOPE')
    if receipt['independent_mean_math_review']['status']!='ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN':raise ValueError('MEAN_NOT_ACCEPTED')
    for n,item in receipt['artifact_sha256'].items():
        archived=files[case['directory']+'/'+n.replace('\\','/')]
        if item['sha256']!=archived['sha256'] or item['bytes']!=archived['bytes']:raise ValueError('FRESH_ARITHMETIC_ARTIFACT_NOT_ARCHIVE_BYTES')

def main():
    started=time.perf_counter()
    if original.digest(ROOT/'outputs/d2a_science_zip_rehearsal_v1.py')!=WRAPPER_SHA:raise ValueError('HISTORICAL_WRAPPER_CHANGED')
    if RESUME_RECEIPT.exists() or original.RECEIPT.exists():raise ValueError('NEVER_OVERWRITE_REHEARSAL_ACCEPTANCE')
    plan=json.loads(original.PRECHECK.read_bytes());current=original.precheck()
    if current['files']!=plan['files']:raise ValueError('ORIGINAL_INPUTS_NOT_PRECHECK_SNAPSHOT')
    failure_path=LOGS/'FAILURE_SCOPED_REHEARSAL.json';failure=json.loads(failure_path.read_bytes())
    scratch=Path(failure['scratch_root']).resolve()
    if scratch.parent!=(ROOT/'work').resolve() or not re.fullmatch(r'd2a_pair_replay_[0-9a-f]{8}',scratch.name):raise ValueError('NOT_THE_OWNED_FAILED_SCRATCH')
    if not original.ZIP.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:raise ValueError('ACTUAL_ZIP_NOT_READONLY')
    archive_hash=original.digest(original.ZIP);results=[];verified=set();helper=original.load_helper()
    try:
        with zipfile.ZipFile(original.ZIP) as archive:
            raw=archive.read('MANIFEST.json');m=json.loads(raw);view=ZipWitnessView(original.ZIP,sha(raw))
            if m['scope']!=original.SCOPE or m['precheck']['files']!=plan['files']:raise ValueError('ACTUAL_ARCHIVE_NOT_THIS_SCOPED_PRECHECK')
            files={i['path']:i for i in m['files']}
            if set(archive.namelist())!=set(files)|{'MANIFEST.json','MANIFEST.sha256'}:raise ValueError('ACTUAL_PAYLOAD_MEMBER_SET')
            # Lost in-memory bookkeeping from the failed first wrapper is
            # recovered by real full ZIP stream hashes, never by dummy paths.
            for n,item in files.items():
                h=hashlib.sha256();count=0
                with archive.open(n) as source:
                    while block:=source.read(2**20):h.update(block);count+=len(block)
                if count!=item['bytes'] or h.hexdigest()!=item['sha256']:raise ValueError('ACTUAL_ZIP_FULL_PAYLOAD_HASH '+n)
                verified.add(n)
            for n,item in files.items():
                if any(n.startswith(d+'/') for d in original.PAIR):continue
                p=original.locate(n,scratch)
                if original.digest(p)!=item['sha256']:raise ValueError('INITIAL_FRESH_SHARED_ROOT_CHANGED '+n)
            bootstrap_path=LOGS/'fresh_R1_bootstrap_receipt.json';bootstrap=json.loads(bootstrap_path.read_bytes())
            if bootstrap['archive_sha256_before']!=original.R1_SHA or bootstrap['archive_sha256_after']!=original.R1_SHA or bootstrap['extracted_files']!=463:raise ValueError('NOT_ORIGINAL_FRESH_R1_BOOTSTRAP')
            avg,point=plan['cases'];savedavg=LOGS/(avg['case']+'_fresh_receipt.json')
            if original.digest(savedavg)!=AVG_RECEIPT_SHA:raise ValueError('INITIAL_AVG_TRUE_FULL_RECEIPT_CHANGED')
            avgr=json.loads(savedavg.read_bytes());required(avgr,avg,files)
            avgdirectory=original.locate(avg['directory'],scratch)
            if original.digest(avgdirectory/'STDLIB_VERIFICATION_RECEIPT.json')!=AVG_RECEIPT_SHA:raise ValueError('INITIAL_AVG现场_RECEIPT_CHANGED')
            cleanup_avg=cleanup_owned_case(avgdirectory,scratch);original.write_report(LOGS/(avg['case']+'_cleanup_recovery.json'),cleanup_avg)
            results.append({'case':avg['case'],'identity':avg['identity'],'target_status':avgr['scientific_target_status'],
                            'fresh_receipt':str(savedavg),'fresh_receipt_sha256':AVG_RECEIPT_SHA,'full_verifier_seconds':avgr['elapsed_wall_seconds'],
                            'execution':'First wrapper actually verified avg from this actual ZIP/fresh ROOT; not scientifically rerun during resume.','cleanup_recovery':cleanup_avg})
            resource=original.resource_snapshot();original.check_resources(resource)
            pointdirectory=original.locate(point['directory'],scratch)
            if pointdirectory.exists() or (LOGS/(point['case']+'.stdout.log')).exists():raise ValueError('POINT_BRANCH_ALREADY_STARTED')
            helper.extract_members(archive,[i for i in m['files'] if i['path'].startswith(point['directory']+'/')],scratch,set())
            elapsed=original.run([sys.executable,'-S','-B','-X','utf8',str(scratch/'work/d2a_cert_verify.py'),'--case-dir',str(pointdirectory)],scratch,LOGS/point['case'])
            pointfile=pointdirectory/'STDLIB_VERIFICATION_RECEIPT.json';pointr=json.loads(pointfile.read_bytes());required(pointr,point,files)
            savedpoint=LOGS/(point['case']+'_fresh_receipt.json');savedpoint.write_bytes(pointfile.read_bytes())
            cleanup_point=cleanup_owned_case(pointdirectory,scratch);original.write_report(LOGS/(point['case']+'_cleanup_recovery.json'),cleanup_point)
            results.append({'case':point['case'],'identity':point['identity'],'target_status':pointr['scientific_target_status'],
                            'fresh_receipt':str(savedpoint),'fresh_receipt_sha256':original.digest(savedpoint),'full_verifier_seconds':elapsed,
                            'execution':'First and only point full-S execution, actual ZIP case/source and same fresh R1 ROOT.','precase_resource':resource,'cleanup_recovery':cleanup_point})
        r1_destination=Path(bootstrap['destination'])
        r1_destination.relative_to(scratch)
        for n,h in bootstrap['file_sha256'].items():
            if original.digest(original.locate(n,r1_destination))!=h:raise ValueError('FRESH_R1_SOURCE_TREE_CHANGED_AFTER_PAIR '+n)
        after=[]
        for item in plan['files']:
            p=original.locate(item['path']);h=original.digest(p)
            if h!=item['sha256'] or p.stat().st_size!=item['bytes'] or p.stat().st_mtime_ns!=item['mtime_ns']:raise ValueError('ORIGINAL_INPUT_CHANGED_AFTER_PAIR '+item['path'])
            after.append({'path':item['path'],'sha256_before_streaming':item['sha256'],'sha256_after_pair':h,'bytes':item['bytes'],'unchanged':True})
        for d in original.PAIR:
            actual={p.relative_to(ROOT).as_posix() for p in original.locate(d).rglob('*') if p.is_file()}
            if actual!={i['path'] for i in plan['files'] if i['path'].startswith(d+'/')}:raise ValueError('ORIGINAL_CASE_TREE_CHANGED')
        if original.digest(original.ZIP)!=archive_hash:raise ValueError('ACTUAL_ZIP_CHANGED_DURING_RESUME')
        report={'scope':original.SCOPE,'status':'PASS_SCOPED_PAIR_ACTUAL_ZIP_FRESH_R1_FULL_STDLIB_AFTER_DOCUMENTED_CLEANUP_RECOVERY',
                'scientific_ready':False,'full400':False,'initial_wrapper_status':'FAILED_AFTER_AVG_FULL_VERIFIER_AT_NATIVE_PS_FILE_CLEANUP',
                'initial_wrapper_sha256':WRAPPER_SHA,'initial_failure':str(failure_path),'initial_failure_sha256':original.digest(failure_path),
                'archive':str(original.ZIP),'archive_sha256':archive_hash,'archive_bytes':original.ZIP.stat().st_size,'manifest_sha256':sha(raw),
                'actual_zip_payloads_fully_hashed':len(verified),'fresh_R1_bootstrap_files':463,'fresh_R1_all_file_hashes_unchanged_after_pair':True,
                'case_replays':results,'original_inputs_before_after':after,'scratch_root':str(scratch),'log_root':str(LOGS),
                'successful_case_scratch_cleaned':True,'original_science_or_live_csv_locks_PID_written':False,
                'full400_GO_or_quiescence_or_coverage_gate_changed':False,'resume_elapsed_seconds':time.perf_counter()-started,
                'execution_provenance':{'science_sources':'Original immutable scoped actual ZIP; same fresh R1 bootstrap; original full-S verifier.',
                                       'cleanup_source':'New reviewed native inline cleanup component outside original ZIP; original -File failure retained.'},
                'source_sha256':{n:original.digest(ROOT/'outputs'/n) for n in ['d2a_science_zip_rehearsal_resume_v1.py','d2a_native_owned_case_cleanup_v1.py','package_full_d2a_release_v3.py']},
                'final_resource':original.resource_snapshot()}
        original.write_report(RESUME_RECEIPT,report);original.write_report(original.RECEIPT,report)
        print(json.dumps({k:report[k] for k in ['status','archive_bytes','actual_zip_payloads_fully_hashed','resume_elapsed_seconds','scientific_ready']}),flush=True)
    except Exception as e:
        original.write_report(LOGS/'FAILURE_SCOPED_RESUME.json',{'status':'FAIL_RESUME_PRESERVE_OWNED_SCRATCH','reason':str(e),'scientific_ready':False})
        raise

if __name__=='__main__':main()
