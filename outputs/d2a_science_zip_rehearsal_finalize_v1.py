"""Long-path-safe final bookkeeping only; no science/R1 execution or cleanup.

Reuses actual avg+point full-S receipts from first wrapper/resume, preserves
both operational failures, hashes actual ZIP/source inputs and fresh R1 tree.
"""
from pathlib import Path
import hashlib
import json
import os
import stat
import time
import zipfile
import d2a_science_zip_rehearsal_v1 as original
import d2a_science_zip_rehearsal_resume_v1 as resumed
from d2a_archive_witness_view_v1 import ZipWitnessView

ROOT=original.ROOT;LOGS=resumed.LOGS
FINAL=ROOT/'outputs/d2a_science_zip_rehearsal_finalization_receipt_v1.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
def hash_long(p):
    value=str(Path(p).resolve())
    if os.name=='nt' and not value.startswith('\\\\?\\'):value='\\\\?\\'+value
    with open(value,'rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    started=time.perf_counter()
    if FINAL.exists() or original.RECEIPT.exists():raise ValueError('NEVER_OVERWRITE_ACCEPTANCE_RECEIPT')
    if hash_long(ROOT/'outputs/d2a_science_zip_rehearsal_v1.py')!=resumed.WRAPPER_SHA:raise ValueError('ORIGINAL_WRAPPER_CHANGED')
    plan=json.loads(original.PRECHECK.read_bytes())
    with zipfile.ZipFile(original.ZIP) as archive:
        raw=archive.read('MANIFEST.json');m=json.loads(raw);view=ZipWitnessView(original.ZIP,sha(raw))
        if m['scope']!=original.SCOPE or m['precheck']['files']!=plan['files']:raise ValueError('NOT_ORIGINAL_SCOPED_PAIR_ZIP')
        files={i['path']:i for i in m['files']}
        if set(archive.namelist())!=set(files)|{'MANIFEST.json','MANIFEST.sha256'}:raise ValueError('ARCHIVE_PAYLOAD_SET')
        hashed=[]
        for n,item in files.items():
            h=hashlib.sha256();count=0
            with archive.open(n) as stream:
                while block:=stream.read(2**20):h.update(block);count+=len(block)
            if count!=item['bytes'] or h.hexdigest()!=item['sha256']:raise ValueError('ACTUAL_ZIP_PAYLOAD_HASH '+n)
            hashed.append({'path':n,'bytes':count,'sha256':h.hexdigest(),'actual_zip_stream_fully_verified':True})
    if not original.ZIP.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:raise ValueError('ZIP_NOT_READONLY')
    archive_hash=hash_long(original.ZIP)
    failure0=LOGS/'FAILURE_SCOPED_REHEARSAL.json';failure1=LOGS/'FAILURE_SCOPED_RESUME.json'
    for p in [failure0,failure1]:
        if not p.is_file():raise ValueError('OPERATIONAL_FAILURE_HISTORY_MISSING')
    scratch=Path(json.loads(failure0.read_bytes())['scratch_root']).resolve()
    scratch.relative_to((ROOT/'work').resolve())
    bootstrap_path=LOGS/'fresh_R1_bootstrap_receipt.json';bootstrap=json.loads(bootstrap_path.read_bytes())
    if bootstrap['extracted_files']!=463 or bootstrap['archive_sha256_before']!=original.R1_SHA or bootstrap['archive_sha256_after']!=original.R1_SHA:
        raise ValueError('ORIGINAL_FRESH_R1_BOOTSTRAP_NOT_ACCEPTED')
    destination=Path(bootstrap['destination']).resolve();destination.relative_to(scratch)
    for n,h in bootstrap['file_sha256'].items():
        if hash_long(original.locate(n,destination))!=h:raise ValueError('FRESH_R1_SOURCE_CHANGED '+n)
    # Also bind the shared science source/mean/report/bootstrap ZIP actually
    # used in the fresh ROOT; no original-working-tree source fallback.
    for n,item in files.items():
        if not any(n.startswith(d+'/') for d in original.PAIR):
            if hash_long(original.locate(n,scratch))!=item['sha256']:raise ValueError('FRESH_SHARED_SOURCE_CHANGED '+n)
    cases=[]
    for index,c in enumerate(plan['cases']):
        saved=LOGS/(c['case']+'_fresh_receipt.json');r=json.loads(saved.read_bytes());resumed.required(r,c,files)
        if index==0 and hash_long(saved)!=resumed.AVG_RECEIPT_SHA:raise ValueError('HISTORICAL_TRUE_AVG_RECEIPT_CHANGED')
        cleanup_path=LOGS/(c['case']+'_cleanup_recovery.json');cleanup=json.loads(cleanup_path.read_bytes())
        if cleanup['status']!='PASS_GUARDED_OWNED_SCRATCH_CASE_CLEANUP' or cleanup['machine_or_user_execution_policy_changed'] or cleanup['global_environment_changed']:
            raise ValueError('UNSAFE_OR_FAILED_CLEANUP')
        if original.locate(c['directory'],scratch).exists():raise ValueError('SUCCESS_CASE_SCRATCH_NOT_CLEANED')
        cases.append({'case':c['case'],'identity':c['identity'],'directory':c['directory'],'target_status':r['scientific_target_status'],
                      'fresh_receipt':str(saved),'fresh_receipt_sha256':hash_long(saved),'verifier_reported_seconds':r['elapsed_wall_seconds'],
                      'stdout':str(LOGS/(c['case']+'.stdout.log')),'stderr':str(LOGS/(c['case']+'.stderr.log')),
                      'fresh_receipt_full_flags_and_artifact_binding_passed':True,'science_execution_count':1,
                      'execution_phase':'Original wrapper' if index==0 else 'Documented cleanup-recovery resume',
                      'cleanup_receipt':str(cleanup_path),'cleanup_receipt_sha256':hash_long(cleanup_path)})
    after=[]
    for item in plan['files']:
        p=original.locate(item['path']);h=hash_long(p)
        if h!=item['sha256'] or p.stat().st_size!=item['bytes'] or p.stat().st_mtime_ns!=item['mtime_ns']:raise ValueError('ORIGINAL_INPUT_CHANGED '+item['path'])
        after.append({'path':item['path'],'bound_expected_sha256_before_streaming':item['sha256'],
                      'before_first_science_stream_copy_matched':True,'sha256_after_complete_pair':h,
                      'bytes':item['bytes'],'stat_and_hash_unchanged':True})
    for d in original.PAIR:
        tree={p.relative_to(ROOT).as_posix() for p in original.locate(d).rglob('*') if p.is_file()}
        if tree!={i['path'] for i in plan['files'] if i['path'].startswith(d+'/')}:raise ValueError('ORIGINAL_CASE_TREE_CHANGED')
    if hash_long(original.ZIP)!=archive_hash:raise ValueError('IMMUTABLE_ZIP_CHANGED_DURING_FINALIZATION')
    sources=['d2a_science_zip_rehearsal_v1.py','d2a_science_zip_rehearsal_resume_v1.py','d2a_science_zip_rehearsal_finalize_v1.py',
             'd2a_native_owned_case_cleanup_v1.py','package_full_d2a_release_v2.py','package_full_d2a_release_v3.py']
    report={'scope':original.SCOPE,'status':'PASS_SCOPED_ACTUAL_ZIP_FRESH_R1_PAIR_AFTER_DOCUMENTED_NATIVE_CLEANUP_AND_LONGPATH_BOOKKEEPING_RECOVERY',
            'scientific_ready':False,'full400':False,'archive':str(original.ZIP),'archive_sha256':archive_hash,
            'archive_bytes':original.ZIP.stat().st_size,'manifest_sha256':sha(raw),'actual_zip_payloads_fully_hashed':len(hashed),
            'actual_zip_payload_hash_receipts':hashed,'original_inputs_before_after':after,'case_replays':cases,
            'fresh_R1_bootstrap_receipt':str(bootstrap_path),'fresh_R1_bootstrap_receipt_sha256':hash_long(bootstrap_path),
            'fresh_R1_source_files_all463_hash_checked_after_pair':True,'actual_fresh_shared_science_sources_hash_checked':True,
            'initial_wrapper_result':'FAILED_AFTER_TRUE_AVG_SCIENCE_AT_PS_FILE_CLEANUP','first_resume_result':'BOTH_SCIENCE_CASES_PASSED_CLEANED_THEN_NORMAL_PATH_R1_BOOKKEEPING_FAILED',
            'operational_failure_history':[{'path':str(p),'sha256':hash_long(p)} for p in [failure0,failure1]],
            'diagnostics':[{'path':str(ROOT/'outputs'/n),'sha256':hash_long(ROOT/'outputs'/n)} for n in ['d2a_science_zip_rehearsal_cleanup_diagnostic_v1.json','d2a_native_owned_case_cleanup_fixture_v1.json','d2a_science_zip_rehearsal_longpath_diagnostic_v1.json']],
            'scratch_root':str(scratch),'log_root':str(LOGS),'successful_new_case_scratch_cleaned':True,'failed_history_and_shared_root_retained':True,
            'original_science_or_live_csv_locks_PID_written':False,'global_policy_or_env_modified':False,'full400_GO_quiescence_coverage_caps_modified':False,
            'finalization_only_no_science_or_R1_executed':True,'finalization_elapsed_seconds':time.perf_counter()-started,
            'execution_provenance':{'science':'Exact original actual ZIP source/case bytes and one fresh R1 ROOT; original -S -B -X utf8 full verifier once per distinct readout.',
                                    'cleanup':'New native inline guarded component outside original ZIP; native -File failure retained.',
                                    'finalization':'New Windows extended-path readonly hashes; normal-path bookkeeping failure retained.'},
            'source_sha256':{n:hash_long(ROOT/'outputs'/n) for n in sources},'final_resource':original.resource_snapshot()}
    original.write_report(FINAL,report);original.write_report(original.RECEIPT,report)
    print(json.dumps({k:report[k] for k in ['status','archive_bytes','actual_zip_payloads_fully_hashed','finalization_elapsed_seconds','scientific_ready']}),flush=True)

if __name__=='__main__':main()
