"""Read-only scientific publication inventory; no remote/science actions.

Only writes this task's inventory and true small unfinished-table snapshot.
Never copies a live CASE, hashes big jets, starts jobs or changes Git config.
"""
from pathlib import Path
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
DEST=ROOT/'work/github_review_publication_inventory_v1.json'
CSV=ROOT/'work/github_review_publication_inventory_v1.csv'
SCI={'CERTIFIED_TARGET_PASS','VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET'}
HARD=100*2**20
sha=lambda b:hashlib.sha256(b).hexdigest()

def relative(n):
    n=str(n).replace('\\','/');p=Path(n)
    if p.is_absolute() or '..' in p.parts or ':' in n:raise ValueError('Unsafe inventory path')
    return n
def read(n,cap=16*2**20):
    p=ROOT/relative(n)
    if p.stat().st_size>cap:raise ValueError('Inventory only reads small metadata '+n)
    return p.read_bytes()
def obj(n):return json.loads(read(n))
def stage(n):
    if n.startswith(('research/','CURRENT_STATE','RESEARCH_PLAN','GOAL_PROMPT','README','source_index','inputs/README','.git')):return '00_provenance_and_paused_state'
    if n.startswith('outputs/d2a_runtime_checkpoint_v1/'):return '02_runtime_checkpoint_v1_historical'
    if n.startswith('outputs/d2a_runtime_guard_delta_v2/'):return '02_current_runtime_guard_delta'
    if 'science_zip_rehearsal' in n or 'native_owned_case_cleanup' in n or 'pair_rehearsal_logs_' in n:return '03_H160_actual_scoped_science_rehearsal'
    if n.startswith('work/d2a_cert_preflight/') or n.startswith('work/d2a_'):return '02_current_runnable_runtime_and_frozen400_directions'
    if n.startswith(('outputs/d2a_archive_','outputs/full_d2a_','outputs/package_full_d2a_','references/release_recipe_history/')):return '04_full400_unfinished_release_recipe'
    if n.startswith('outputs/d2a_'):return '04_full400_unfinished_and_scoped_figure'
    if any(k in n for k in ['manuscript','submission','certo_fdi_control_memory_draft','citation','bibliography','tac_','novelty','prior_art','feedback_']):return '05_current_R8_manuscript_and_review'
    return '01_theory_proof_checks_and_history'

def main():
    now=datetime.now(timezone.utc);stamp=now.strftime('%Y%m%dT%H%M%SZ')
    proc=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
        '@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match "^python"} | Select-Object ProcessId,ParentProcessId,CommandLine)|ConvertTo-Json -Compress'],capture_output=True,text=True,encoding='utf-8',check=True)
    processes=json.loads(proc.stdout or '[]');processes=processes if isinstance(processes,list) else [processes]
    active=set()
    for process in processes:
        cmd=process.get('CommandLine') or ''
        if 'd2a_cert_case.py' not in cmd:continue
        args={k:v for k,v in re.findall(r'--(H|family|readout|stage-endpoint)\s+([A-Za-z0-9_]+)',cmd)}
        if {'H','family','readout'}<=set(args):
            active.add('work/d2a_cert_h'+args['H']+'_'+args['family']+('_S'+args['stage-endpoint'] if 'stage-endpoint' in args else '')+'_'+args['readout'])
    table_path='work/d2a_cert_review_bound_table.csv';raw=read(table_path);tablehash=sha(raw)
    table_receipt=obj('work/d2a_cert_review_bound_table_receipt.json')
    if table_receipt['table_sha256']!=tablehash:raise ValueError('Atomic table/receipt snapshot changed; recapture later, do not publish mismatched view')
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));counts=Counter(r['risk_status'] for r in rows)
    snap=ROOT/'work'/('github_publication_snapshot_'+stamp);(snap/'work').mkdir(parents=True,exist_ok=False)
    (snap/table_path).write_bytes(raw)
    receipt_raw=read('work/d2a_cert_review_bound_table_receipt.json')
    if json.loads(receipt_raw)['table_sha256']!=tablehash:raise ValueError('Table receipt changed during capture')
    (snap/'work/d2a_cert_review_bound_table_receipt.json').write_bytes(receipt_raw)
    # No CASE is copied. Frozen direction/source bytes are listed for a later
    # explicit allowlist copy, and completed CASEs are metadata/stat indexed.
    tracked=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0')
    candidates={n for n in tracked if n and (ROOT/n).is_file()}
    candidates.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'outputs').iterdir() if p.is_file())
    for folder in ['outputs/d2a_pair_rehearsal_logs_e9098928','outputs/d2a_runtime_guard_delta_v2']:
        candidates.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file())
    runtime=obj('outputs/d2a_runtime_checkpoint_v1/SNAPSHOT_METADATA.json')['source_files']
    candidates.update(n for n in runtime if n.startswith('work/') and (ROOT/n).is_file())
    candidates.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'work').glob('d2a_*.py'))
    candidates.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'work/d2a_cert_preflight').glob('*.json'))
    mutable={'outputs/d2a_partial_first_success_v1.json','work/d2a_cert_review_bound_table.csv',
             'work/d2a_cert_review_bound_table_receipt.json','work/d2a_cert_partial_first_success.json',
             'work/d2a_cert_partial_table.csv','work/d2a_cert_checkpoint.json','work/d2a_cert_batch_checkpoint.json',
             'work/d2a_cert_live_publisher_checkpoint.json','work/d2a_cert_batch_stdout.log'}
    entries=[]
    known={i['path']:i['sha256'] for i in obj('source_index.json')['files']}
    for n in sorted(candidates):
        p=ROOT/n;s=p.stat();route='Git';reason='Stable owned source/review artifact; preserve original relative path and exact bytes.'
        if n in mutable or n.endswith('.lock') or '_owner_session' in n:route='snapshot_only';reason='Mutable/control state; do not publish as immutable current acceptance.'
        if n.endswith('.zip'):
            route='Release_asset';reason='Immutable stage bundle; prefer release asset even if small.'
        if s.st_size>HARD:route='Release_asset';reason='Exceeds ordinary Git100MiB; needs release asset.'
        value=sha(read(n)) if s.st_size<=16*2**20 and route not in {'snapshot_only'} else known.get(n)
        if route=='Release_asset' and n=='outputs/D2A_H160_TERMINAL_PAIR_SCIENCE_REHEARSAL_V1.zip':value=obj('outputs/d2a_science_zip_rehearsal_receipt_v1.json')['archive_sha256']
        for v in [1,2]:
            if n==f'outputs/CERTO_FDI_THEORY_CHECKPOINT_20261007_V{v}.zip':value=obj(f'outputs/theory_checkpoint_archive_receipt_v{v}.json').get('archive_sha256',value)
        entries.append({'path':n,'destination':n,'stage':stage(n),'route':route,'bytes':s.st_size,'sha256':value,
                        'sha_scope':'Read current small bytes' if s.st_size<=16*2**20 and route!='snapshot_only' else 'Existing prior receipt/index only; no big bytes read this task',
                        'mtime_ns':s.st_mtime_ns,'reason':reason})
    # User-owned originals are downloadable assets with their original hashes.
    for n,expected in [('inputs/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip','f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b'),
        ('inputs/CERTO_FDI_TAC_ADMISSION_REVISION_20260909_FULL.zip','2b70de9459f4dd3b48202d14695587f7acb7c63df0a04bed769cad001321c4b9')]:
        entries.append({'path':n,'destination':n,'stage':'00_original_user_research_inputs','route':'Release_asset','bytes':(ROOT/n).stat().st_size,
                        'sha256':expected,'sha_scope':'Existing imported-copy/source receipts; not rehashed in this plan','reason':'Preserve full original archive/source/index/hash; do not add into ordinary Git.'})
    bydir=defaultdict(list)
    for r in rows:
        if r['risk_status'] in SCI:bydir[relative(r['certificate_reference'])].append(r)
    completed=[];hold=[]
    for d,case_rows in sorted(bydir.items()):
        try:
            if d in active:raise ValueError('Actual active writer target')
            r=case_rows[0];case_raw=read(d+'/CASE_RESULT.json');receipt_raw=read(relative(r['current_receipt_path']))
            if sha(case_raw)!=r['case_result_sha256'] or sha(receipt_raw)!=r['current_receipt_sha256']:raise ValueError('Current small CASE/receipt hash does not bind captured CSV')
            result=json.loads(case_raw);receipt=json.loads(receipt_raw)
            if receipt['case_result_sha256']!=r['case_result_sha256'] or receipt['independent_mean_math_review']['status']!='ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN':raise ValueError('CASE/mean/receipt incomplete')
            binding=receipt.get('artifact_sha256')
            if binding is None:
                side_raw=read(relative(r['evidence_hash_binding_path']))
                if sha(side_raw)!=r['evidence_hash_binding_sha256']:raise ValueError('Sidecar hash not bound')
                side=json.loads(side_raw);binding=side['artifact_sha256']
                if {'path':Path(relative(r['current_receipt_path'])).name,'sha256':r['current_receipt_sha256']} not in side['verified_receipts']:raise ValueError('Selected receipt not bound to artifacts')
            files=[]
            for p in sorted((ROOT/d).rglob('*')):
                if not p.is_file():continue
                n=p.relative_to(ROOT).as_posix();s=p.stat();local=p.relative_to(ROOT/d).as_posix();b=binding.get(local,binding.get(local.replace('/','\\')))
                metadata=(s.st_size<=16*2**20 and '_ADJOINT_JET' not in p.name and not p.name.endswith('.gz'))
                value=sha(read(n)) if metadata else (b['sha256'] if b else None)
                if b and s.st_size!=b['bytes']:raise ValueError('Bound payload size changed')
                files.append({'path':n,'bytes':s.st_size,'sha256':value,'mtime_ns':s.st_mtime_ns,
                              'sha_scope':'Current small metadata bytes' if metadata else 'Expected prior artifact binding; must fully hash/check during later stream packaging'})
            completed.append({'directory':d,'logical_rows':[list((int(x['H_post_slots']),x['family'],int(x['stage_endpoint']) if x['stage_endpoint'] else None,x['readout'])) for x in case_rows],
                              'case':result['case'],'status':result['status'],'case_result_sha256':sha(case_raw),'selected_receipt_sha256':sha(receipt_raw),
                              'payload_bytes':sum(x['bytes'] for x in files),'files':files,'copy_now':False,'route':'Release_case_bundle_with_full_witness_and_metadata',
                              'claim_scope':'Existing completed case at captured CSV timestamp; not fresh complete400/release acceptance.'})
        except (ValueError,KeyError,OSError) as e:hold.append({'directory':d,'reason':str(e),'copy_now':False})
    history=[]
    for folder in sorted((ROOT/'work').glob('d2a_cert_recovery_*')):
        if not folder.is_dir():continue
        files=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in folder.rglob('*') if p.is_file()]
        history.append({'directory':folder.relative_to(ROOT).as_posix(),'files':files,'payload_bytes':sum(x['bytes'] for x in files),
                        'route':'Release_history_bundle','scope':'Interrupted/failed/recovery historical evidence, not current science PASS','full_SHA_required_when_packaged':True})
    excluded=[]
    for folder in ['work/literature_20261007','work/literature_control_extension']:
        excluded.extend({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'route':'Do_not_publish_fulltext','replacement':'Verified primary URL/DOI/version/locator metadata'} for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix.lower() in {'.pdf','.txt'})
    summary={'rows':len(rows),'risk_counts':dict(counts),'table_sha256':tablehash,'snapshot_utc':now.isoformat(),'full400_complete':False,
             'snapshot_root':str(snap),'table_changed_after_inventory':sha(read(table_path))!=tablehash,
             'background_processes_observed':processes,'active_science_directories_excluded':sorted(active),
             'completed_canonical_case_count':len(completed),'completed_case_bytes':sum(x['payload_bytes'] for x in completed),
             'history_bytes':sum(x['payload_bytes'] for x in history),'held_case_count':len(hold)}
    result={'schema':'github-scientific-publication-inventory-v1','captured_utc':now.isoformat(),'repo':'kaiwen123-yang/CERTO-FDI','repo_visibility':'PUBLIC',
            'goal_paused_background400_continues':True,'remote_mutations_performed':False,'source_or_live_CASE_copied':False,
            'exact_bytes_git_attributes_required':'* -text; preserve source existing .gitattributes, do not change global core.autocrlf',
            'entries':entries,'time_snapshot':summary,'completed_case_bundle_candidates':completed,'held_cases':hold,'history_bundle_candidates':history,
            'thirdparty_fulltext_excluded':excluded,'big_science_body_bytes_hashed':0,
            'packaging_gate':'Recheck active target, captured CASE/receipt hashes and every selected file stat/tree before and after actual stream. Full hashes expected during build; do not claim files verified from this size inventory alone.'}
    DEST.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    with CSV.open('w',encoding='utf-8',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=['stage','route','path','destination','bytes','sha256','sha_scope']);writer.writeheader()
        writer.writerows({k:e.get(k,'') for k in writer.fieldnames} for e in entries)
    print(json.dumps({'inventory_entries':len(entries),'source_Git_bytes':sum(e['bytes'] for e in entries if e['route']=='Git'),'completed_cases':len(completed),
                      'cold_completed_bytes':summary['completed_case_bytes'],'cold_history_bytes':summary['history_bytes'],'held_cases':len(hold),
                      'snapshot_risk_counts':dict(counts),'snapshot_utc':summary['snapshot_utc'],'big_bytes_hashed':0}),flush=True)

if __name__=='__main__':main()
