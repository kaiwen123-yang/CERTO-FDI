"""Final stopped-science publication supplement; no science/R1/remote actions.

Preserves11:11 publication materials; only newly closed canonical CASEs enter
an actual <=1GiB supplement ZIP. Cancelled pending case is stat/index only.
"""
from pathlib import Path, PurePosixPath
from datetime import datetime,timezone
from collections import Counter,defaultdict
import csv
import hashlib
import io
import json
import re
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'work/github_publication_stop_supplement_20261007'
REPORT=ROOT/'outputs/github_final_stop_supplement_v1.json'
OLD=ROOT/'work/github_review_publication_inventory_v1.json'
SCI={'CERTIFIED_TARGET_PASS','VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET'}
TABLE='work/d2a_cert_review_bound_table.csv'
PAIR='work/d2a_cert_review_bound_table_receipt.json'
CANCELLED='work/d2a_cert_h400_fixed40_point_last_fast_read'
sha=lambda b:hashlib.sha256(b).hexdigest()

def rel(n):
    n=str(n).replace('\\','/');p=PurePosixPath(n)
    if p.is_absolute() or '..' in p.parts or ':' in n:raise ValueError('Unsafe source path')
    return p.as_posix()
def source(n):
    p=(ROOT/Path(*PurePosixPath(rel(n)).parts)).resolve();p.relative_to(ROOT);return p
def small(n):
    p=source(n)
    if p.stat().st_size>16*2**20:raise ValueError('Only small metadata read before asset stream '+n)
    return p.read_bytes()
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def inactive():
    cmd='@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in @(62844,10032,75228) -or ($_.Name -match "^python" -and $_.CommandLine -match "d2a_cert_(batch|case|verify|publish_live)") } | Select-Object ProcessId,CommandLine)|ConvertTo-Json -Compress'
    p=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',cmd],capture_output=True,text=True,encoding='utf-8',check=True)
    rows=json.loads(p.stdout or '[]')
    if rows:raise ValueError('STOP_SUPPLEMENT_REQUIRES_ACTUAL_NO_RELATED_SCIENCE_PROCESS')
    return {'actual_CIM_related_processes':rows,'science_PIDs_checked':[62844,10032,75228],'all_absent':True}

def main():
    if STAGE.exists() or REPORT.exists():raise ValueError('Never overwrite a final-stop supplement')
    observed=datetime.now(timezone.utc).isoformat();os_state=inactive()
    oldraw=OLD.read_bytes();old=json.loads(oldraw);old_dirs={c['directory'] for c in old['completed_case_bundle_candidates']}
    table=small(TABLE);paired=small(PAIR);receipt=json.loads(paired);th=sha(table)
    if receipt['table_sha256']!=th or receipt['complete_full_table'] is not False:raise ValueError('Stable strict table/receipt binding missing')
    rows=list(csv.DictReader(io.StringIO(table.decode('utf-8-sig'))));counts=Counter(r['risk_status'] for r in rows)
    if len(rows)!=400:raise ValueError('Not exact400 row snapshot')
    bydir=defaultdict(list)
    for r in rows:
        if r['risk_status'] in SCI:bydir[rel(r['certificate_reference'])].append(r)
    new_dirs=sorted(set(bydir)-old_dirs)
    if not old_dirs<=set(bydir):raise ValueError('Old frozen closed CASE removed from final snapshot')
    if CANCELLED in new_dirs:raise ValueError('Cancelled pending CASE cannot enter supplement SCI')
    selected=[];cases=[];stage_files=[]
    for d in new_dirs:
        if not re.fullmatch(r'work/d2a_cert_h\d+_[A-Za-z0-9_]+',d):raise ValueError('CASE namespace')
        r=bydir[d][0];case_raw=small(d+'/CASE_RESULT.json');vr_raw=small(rel(r['current_receipt_path']));c=json.loads(case_raw);vr=json.loads(vr_raw)
        if sha(case_raw)!=r['case_result_sha256'] or sha(vr_raw)!=r['current_receipt_sha256'] or vr['case_result_sha256']!=r['case_result_sha256']:raise ValueError('New CASE/receipt not captured strict binding')
        if c['status']!=r['risk_status'] or vr['status'] not in {'PASS_STDLIB_NEW_CASE_VERIFIER','PASS_STDLIB_DERIVED_REBINDING'}:raise ValueError('New CASE not accepted closed classification')
        if vr['independent_mean_math_review']['status']!='ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN':raise ValueError('New CASE mean review missing')
        binding=vr.get('artifact_sha256')
        if binding is None:
            braw=small(rel(r['evidence_hash_binding_path']));side=json.loads(braw)
            if sha(braw)!=r['evidence_hash_binding_sha256'] or {'path':Path(rel(r['current_receipt_path'])).name,'sha256':r['current_receipt_sha256']} not in side['verified_receipts']:raise ValueError('New artifact sidecar not bound')
            binding=side['artifact_sha256']
        casefiles=[]
        for p in sorted(source(d).rglob('*')):
            if not p.is_file():continue
            n=p.relative_to(ROOT).as_posix();s=p.stat();local=p.relative_to(source(d)).as_posix();b=binding.get(local,binding.get(local.replace('/','\\')))
            ismeta='_ADJOINT_JET' not in p.name and not p.name.endswith('.gz') and p.suffix.lower() in {'.json','.md','.log'}
            expected=sha(small(n)) if ismeta else b.get('sha256') if b else None
            if b and s.st_size!=b['bytes']:raise ValueError('Bound new payload size mismatch')
            item={'path':n,'bytes':s.st_size,'expected_sha256':expected,'mtime_ns':s.st_mtime_ns,'metadata_in_Git':ismeta}
            casefiles.append(item);selected.append(item)
        cases.append({'directory':d,'case':c['case'],'status':c['status'],'case_result_sha256':sha(case_raw),
                      'selected_receipt_sha256':sha(vr_raw),'logical_rows':[{k:r[k] for k in ['H_post_slots','family','stage_endpoint','readout','risk_status']} for r in bydir[d]],
                      'payload_bytes':sum(i['bytes'] for i in casefiles),'files':casefiles})
    if sum(i['bytes'] for i in selected)>2**30-4*2**20:raise ValueError('New delta needs explicit Asset012+ splitting')
    STAGE.mkdir()
    for n,raw in [(TABLE,table),(PAIR,paired)]:
        for path in [STAGE/n,STAGE/'publication_snapshots/final_stop_20261007'/n]:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        stage_files.append({'path':n,'bytes':len(raw),'sha256':sha(raw),'scope':'LATEST_FINAL_STOP_DATED_SNAPSHOT_NOT_FULL400'})
    for item in selected:
        if not item['metadata_in_Git']:continue
        raw=small(item['path'])
        if sha(raw)!=item['expected_sha256']:raise ValueError('New small CASE metadata changed')
        p=STAGE/item['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        stage_files.append({'path':item['path'],'bytes':len(raw),'sha256':sha(raw),'scope':'NEW_ACCEPTED_CASE_SMALL_METADATA'})
    stopped_rows=[{k:r.get(k,'') for k in ['H_post_slots','family','stage_endpoint','readout','risk_status','certificate_reference']} for r in rows if r['H_post_slots']=='400' and r['family']=='fixed40' and r['readout']=='point_last_fast_read']
    stop_files=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in sorted(source(CANCELLED).rglob('*')) if p.is_file()]
    stop_index={'scope':'USER_CANCELLED_PENDING_STDLIB_SITE_INDEX_NOT_SCIENCE_FAILURE_OR_PASS','directory':CANCELLED,
                'strict_rows':stopped_rows,'matched_current_pass_receipt':False,'included_in_science_assets':False,'files':stop_files,
                'generated_CASE_present':source(CANCELLED+'/CASE_RESULT.json').is_file(),
                'full_STDLIB_receipt_present':source(CANCELLED+'/STDLIB_VERIFICATION_RECEIPT.json').is_file()}
    write(STAGE/'publication_snapshots/final_stop_20261007/STOP_SITE_INDEX.json',stop_index)
    statuses={'scope':'FINAL_STOP_PUBLICATION_SNAPSHOT_NOT_COMPLETE_SCIENCE','observed_utc':observed,
              'goal_status':'PAUSED_NOT_FALSE_COMPLETED','user_requested_task_end':True,'background_science_and_publisher_stopped':True,
              'actual_process_check':os_state,'older_snapshot_utc':old['time_snapshot']['snapshot_utc'],'older_snapshot_preserved':True,
              'latest_stop_table_sha256':th,'rows':400,'risk_counts':dict(counts),'new_canonical_cases':len(cases),
              'total_old_and_new_canonical_cases':len(bydir),'full400':False,'scientific_ready':False,'this_is_live_table':False,
              'cancelled_pending_case_scientific_status':'NOT_RUN; not relabelled FAIL/PASS','new_CASEs_receipt_binding_accepted':True}
    write(STAGE/'PUBLICATION_SNAPSHOT_STATUS_LATEST_STOP.json',statuses)
    assets=STAGE/'release_assets';assets.mkdir();asset=assets/'D2A_UNFINISHED_COLD_CASES_011_FINAL_STOP.zip';payload=[]
    with zipfile.ZipFile(asset,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
        for item in selected:
            p=source(item['path']);s=p.stat()
            if s.st_size!=item['bytes'] or s.st_mtime_ns!=item['mtime_ns']:raise ValueError('Selected stopped source changed')
            h=hashlib.sha256();count=0
            with p.open('rb') as src,archive.open(item['path'],'w',force_zip64=True) as dst:
                while block:=src.read(2**20):h.update(block);count+=len(block);dst.write(block)
            if count!=item['bytes'] or (item['expected_sha256'] and h.hexdigest()!=item['expected_sha256']):raise ValueError('Actual new payload prior SHA binding mismatch')
            payload.append({'path':item['path'],'bytes':count,'sha256':h.hexdigest()})
        manifest={'scope':'FINAL_STOP_NEW_COMPLETED_CASE_BYTE_SUPPLEMENT_NOT_FULL400_OR_NEW_SCIENCE_REPLAY','scientific_ready':False,'full400':False,
                  'observed_utc':observed,'old_inventory_sha256':sha(oldraw),'old_snapshot_utc':old['time_snapshot']['snapshot_utc'],
                  'latest_stop_table_sha256':th,'new_CASEs':cases,'files':payload,'excluded_cancelled_case':CANCELLED}
        raw=(json.dumps(manifest,indent=2)+'\n').encode();archive.writestr('MANIFEST.json',raw);archive.writestr('MANIFEST.sha256',sha(raw)+'  MANIFEST.json\n')
    if asset.stat().st_size>=2**30:raise ValueError('Supplement asset>=1GiB')
    with zipfile.ZipFile(asset) as archive:
        if set(archive.namelist())!={i['path'] for i in payload}|{'MANIFEST.json','MANIFEST.sha256'}:raise ValueError('Actual asset member set mismatch')
        for item in payload:
            with archive.open(item['path']) as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
            if h!=item['sha256']:raise ValueError('Actual ZIP full-member hash mismatch')
    for case in cases:
        tree={p.relative_to(ROOT).as_posix() for p in source(case['directory']).rglob('*') if p.is_file()}
        if tree!={i['path'] for i in case['files']}:raise ValueError('Stopped CASE tree changed')
    for item in selected:
        s=source(item['path']).stat()
        if s.st_size!=item['bytes'] or s.st_mtime_ns!=item['mtime_ns']:raise ValueError('Source changed during asset packaging')
    if small(TABLE)!=table or small(PAIR)!=paired or OLD.read_bytes()!=oldraw:raise ValueError('Frozen publication or stop snapshot changed')
    inactive()
    with asset.open('rb') as stream:asset_sha=hashlib.file_digest(stream,'sha256').hexdigest()
    for n in ['outputs/github_final_stop_supplement_v1.py','work/github_final_stop_supplement_builder_v1.py']:
        p=ROOT/n
        if p.is_file():
            dest=STAGE/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
            stage_files.append({'path':n,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'scope':'PUBLICATION_ONLY_BUILDER_NO_SCIENCE_OR_REMOTE'})
    result={'schema':'github-final-stop-publication-supplement-v1','status':'PASS_ACTUAL_NEW_COMPLETED_CASE_BYTE_SUPPLEMENT_FINAL_STOP',
            'scope':manifest['scope'],'source_sha256':sha(Path(__file__).read_bytes()),'observed_utc':observed,'scientific_ready':False,'full400':False,
            'old_1111_inventory_sha256':sha(oldraw),'old_1111_materials_modified':False,'latest_stop_table_sha256':th,'risk_counts':dict(counts),
            'old_canonical_cases':len(old_dirs),'new_canonical_cases':len(cases),'total_canonical_cases':len(bydir),'new_CASEs':cases,
            'stage_root':str(STAGE),'metadata_stage_files':stage_files,'cancelled_stop_index':stop_index,'latest_stop_status':statuses,
            'asset':{'path':str(asset),'bytes':asset.stat().st_size,'sha256':asset_sha,'manifest_sha256':sha(raw),
                     'actual_payloads_fully_hashed':len(payload),'actual_ZIP_reopened_member_SHA_and_CRC_checked':True},
            'original_selected_source_tree_stat_and_prior_hash_bindings_unchanged':True,'actual_CIM_no_science_before_after':True,
            'science_R1_theory_or_remote_actions_performed':False,'root_code_claims_ledger_master_or_old_publication_modified':False}
    write(STAGE/'GITHUB_FINAL_STOP_SUPPLEMENT_MANIFEST.json',result);write(REPORT,result)
    print(json.dumps({'status':result['status'],'new_cases':len(cases),'total_cases':len(bydir),'asset_bytes':asset.stat().st_size,'asset_sha256':asset_sha,
                      'asset_path':str(asset),'stage_root':str(STAGE),'full400':False}),flush=True)
if __name__=='__main__':main()
