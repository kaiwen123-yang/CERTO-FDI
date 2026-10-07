"""Explicit local publication allowlist/code staging/cold case asset recipe.

No gh/git mutation, science execution or original-source deletes. Default is
--plan. --stage-code needs a new owned root; --build-cold-assets streams only
the already inventoried closed cases/history, rechecking active targets/stat.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[1]
INVENTORY=ROOT/'work/github_review_publication_inventory_v1.json'
LIMIT=2**30
PAYLOAD_LIMIT=LIMIT-4*2**20
sha=lambda b:hashlib.sha256(b).hexdigest()
def safe(n):
    n=str(n).replace('\\','/');p=PurePosixPath(n)
    if p.is_absolute() or '..' in p.parts or ':' in n:raise ValueError('Unsafe source path')
    q=(ROOT/Path(*p.parts)).resolve();q.relative_to(ROOT);return q
def owned(prefix,target):
    target=Path(target).resolve()
    if target.parent!=(ROOT/'work').resolve() or not re.fullmatch(prefix+r'_[A-Za-z0-9_]+',target.name):raise ValueError('Owned new work-root namespace required')
    if target.exists():raise ValueError('Never overwrite an existing staging root')
    target.mkdir();return target
def writer_dirs():
    c='@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match "^python"} | Select-Object CommandLine)|ConvertTo-Json -Compress'
    p=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',c],capture_output=True,text=True,encoding='utf-8',check=True)
    rows=json.loads(p.stdout or '[]');rows=rows if isinstance(rows,list) else [rows];dirs=set()
    for r in rows:
        s=r.get('CommandLine') or ''
        if 'd2a_cert_case.py' not in s:continue
        a=dict(re.findall(r'--(H|family|readout|stage-endpoint)\s+([A-Za-z0-9_]+)',s))
        if {'H','family','readout'}<=set(a):dirs.add('work/d2a_cert_h'+a['H']+'_'+a['family']+('_S'+a['stage-endpoint'] if 'stage-endpoint' in a else '')+'_'+a['readout'])
    return dirs
def groups(inventory):
    units=[]
    for c in inventory['completed_case_bundle_candidates']:
        units.append({'kind':'closed_case','directory':c['directory'],'bytes':c['payload_bytes'],'files':c['files'],
                      'case':c['case'],'logical_rows':c['logical_rows'],'original_classification':c['status']})
    for h in inventory['history_bundle_candidates']:
        units.append({'kind':'failed_or_interrupted_history','directory':h['directory'],'bytes':h['payload_bytes'],'files':h['files'],'scope':h['scope']})
    result=[];current=[];size=0
    for unit in units:
        if unit['bytes']>PAYLOAD_LIMIT:raise ValueError('One case/history exceeds1GiB; explicit multi-part file plan required '+unit['directory'])
        if size+unit['bytes']>PAYLOAD_LIMIT and current:result.append(current);current=[];size=0
        current.append(unit);size+=unit['bytes']
    if current:result.append(current)
    return result
def stage_code(inv,target):
    root=owned('github_publication_code',target);copied=[]
    for e in inv['entries']:
        if e['route']!='Git':continue
        source=safe(e['path']);raw=source.read_bytes()
        if sha(raw)!=e['sha256']:raise ValueError('Allowlist source changed; recapture inventory '+e['path'])
        dest=root/Path(*PurePosixPath(e['destination']).parts);dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as out:out.write(raw)
        copied.append({'path':e['destination'],'bytes':len(raw),'sha256':sha(raw),'stage':e['stage']})
    # A true dated table/receipt snapshot is review evidence, not authoritative
    # ROOT/work current400 completion. It never restores live control files.
    snap=Path(inv['time_snapshot']['snapshot_root'])
    for source in snap.rglob('*'):
        if not source.is_file():continue
        n='publication_snapshots/'+snap.name+'/'+source.relative_to(snap).as_posix();raw=source.read_bytes()
        dest=root/Path(*PurePosixPath(n).parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        copied.append({'path':n,'bytes':len(raw),'sha256':sha(raw),'stage':'04_full400_unfinished_time_snapshot'})
        # The exact captured table/paired receipt are also supplied at their
        # runnable ROOT paths, with an explicit dated snapshot status below.
        if source.relative_to(snap).as_posix() in {'work/d2a_cert_review_bound_table.csv','work/d2a_cert_review_bound_table_receipt.json'}:
            direct=root/source.relative_to(snap);direct.parent.mkdir(parents=True,exist_ok=True)
            with direct.open('xb') as out:out.write(raw)
            copied.append({'path':source.relative_to(snap).as_posix(),'bytes':len(raw),'sha256':sha(raw),'stage':'04_dated_snapshot_at_runnable_ROOT'})
    live=writer_dirs();small_metadata_bytes=0;small_metadata_files=0
    for case in inv['completed_case_bundle_candidates']:
        if case['directory'] in live:raise ValueError('Captured cold case is now an active writer; do not copy it')
        for item in case['files']:
            source=safe(item['path'])
            if '_ADJOINT_JET' in source.name or source.name.endswith('.gz') or source.suffix.lower() not in {'.json','.md','.log'}:
                continue
            if item['bytes']>16*2**20 or not item.get('sha256'):raise ValueError('Completed CASE review metadata missing a small byte binding')
            raw=source.read_bytes()
            if len(raw)!=item['bytes'] or sha(raw)!=item['sha256']:raise ValueError('Completed CASE small metadata changed '+item['path'])
            dest=root/Path(*PurePosixPath(item['path']).parts);dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as out:out.write(raw)
            copied.append({'path':item['path'],'bytes':len(raw),'sha256':sha(raw),'stage':'04_closed_CASE_small_metadata_review_only_no_witness'})
            small_metadata_bytes+=len(raw);small_metadata_files+=1
    status={'scope':'DATED_UNFINISHED400_REVIEW_SNAPSHOT','captured_utc':inv['time_snapshot']['snapshot_utc'],
            'table_sha256':inv['time_snapshot']['table_sha256'],'risk_counts':inv['time_snapshot']['risk_counts'],
            'goal_paused_background_producer_continues_elsewhere':True,'this_is_live_table':False,'full400':False,'scientific_ready':False,
            'root_table_and_receipt_are_exact_immutable_capture':True,'small_closed_CASE_metadata_in_ROOT':True,
            'large_witnesses_in_Git':False,'full_scientific_verifier_requires_matching_witness_R1_release_assets':True,
            'missing_pending_CASE_is_explicit_pending_not_fake_PASS':True}
    (root/'PUBLICATION_SNAPSHOT_STATUS.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    extra=['work/github_review_publication_inventory_v1.py','work/github_review_publication_prepare_v1.py',
           'work/github_review_publication_inventory_v1.json','work/github_review_publication_inventory_v1.csv',
           'work/github_review_publication_prepare_plan_v1.json','outputs/github_review_publication_plan_v1.md',
           'outputs/github_review_publication_plan_v1.json']
    for n in extra:
        source=safe(n)
        if not source.is_file():raise ValueError('Publication planner deliverable must exist before stage copy '+n)
        raw=source.read_bytes();dest=root/Path(*PurePosixPath(n).parts);dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            if dest.read_bytes()!=raw:raise ValueError('Planner source changed since allowlist '+n)
            continue
        with dest.open('xb') as out:out.write(raw)
        copied.append({'path':n,'bytes':len(raw),'sha256':sha(raw),'stage':'00_publication_allowlist_and_plan'})
    index={'scope':'UNFINISHED400_CURRENT_EXISTING_CASE_REVIEW_INDEX_NO_FINAL_SCIENCE_ACCEPTANCE',
           'captured_utc':inv['time_snapshot']['snapshot_utc'],'table_sha256':inv['time_snapshot']['table_sha256'],
           'scientific_ready':False,'full400':False,'asset_group_limit_bytes':LIMIT,
           'groups':[{'asset_name':f'D2A_UNFINISHED_COLD_CASES_{i:03d}.zip','directories':[u['directory'] for u in g],
                      'payload_bytes':sum(u['bytes'] for u in g),'actual_asset_SHA_pending_build':True} for i,g in enumerate(groups(inv),1)],
           'cases':inv['completed_case_bundle_candidates'],'active_cases_not_copied':inv['time_snapshot']['active_science_directories_excluded']}
    (root/'D2A_COMPLETED_CASE_ASSET_INDEX.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    manifest={'scope':'REVIEW_SOURCE_RUNTIME_AND_UNFINISHED_SNAPSHOT_NOT_FINAL_SCIENCE','scientific_ready':False,'repo':inv['repo'],
              'source_relative_ROOT_preserved':True,'source_inventory_sha256':sha(INVENTORY.read_bytes()),'files':copied}
    (root/'PUBLICATION_SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'staging_root':str(root),'files':len(copied),'bytes':sum(x['bytes'] for x in copied),
                      'closed_CASE_small_metadata_files':small_metadata_files,'closed_CASE_small_metadata_bytes':small_metadata_bytes,'remote_mutations':False}))
def build_assets(inv,target):
    root=owned('github_publication_assets',target);assets=[]
    for number,group in enumerate(groups(inv),1):
        live=writer_dirs()
        if any(u['directory'] in live for u in group):raise ValueError('Live CASE excluded; recapture later')
        for unit in group:
            before={p.relative_to(ROOT).as_posix() for p in safe(unit['directory']).rglob('*') if p.is_file()}
            if before!={x['path'] for x in unit['files']}:raise ValueError('Case tree changed before packaging '+unit['directory'])
        target_zip=root/(f'D2A_UNFINISHED_COLD_CASES_{number:03d}.zip');files=[]
        with zipfile.ZipFile(target_zip,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
            for unit in group:
                for item in unit['files']:
                    p=safe(item['path']);s=p.stat()
                    if s.st_size!=item['bytes'] or s.st_mtime_ns!=item['mtime_ns']:raise ValueError('Cold payload stat changed '+item['path'])
                    h=hashlib.sha256();count=0
                    with p.open('rb') as source,archive.open(item['path'],'w',force_zip64=True) as dest:
                        while block:=source.read(2**20):h.update(block);count+=len(block);dest.write(block)
                    if count!=item['bytes'] or p.stat().st_mtime_ns!=item['mtime_ns'] or (item.get('sha256') and h.hexdigest()!=item['sha256']):raise ValueError('Cold bytes changed or prior binding mismatch '+item['path'])
                    files.append({'path':item['path'],'bytes':count,'sha256':h.hexdigest(),'prior_bound_sha256':item.get('sha256')})
            manifest={'scope':'D2A_UNFINISHED400_EXISTING_COLD_CASE_BYTE_SNAPSHOT_NO_FRESH_SCIENCE_REPLAY','scientific_ready':False,'full400':False,
                      'time_snapshot':inv['time_snapshot']['snapshot_utc'],'table_sha256':inv['time_snapshot']['table_sha256'],
                      'group':number,'units':[{k:v for k,v in u.items() if k!='files'} for u in group],'files':files}
            raw=(json.dumps(manifest,indent=2)+'\n').encode();archive.writestr('MANIFEST.json',raw);archive.writestr('MANIFEST.sha256',sha(raw)+'  MANIFEST.json\n')
        if target_zip.stat().st_size>=LIMIT:raise ValueError('Asset>=1GiB, preserve unuploaded output for review')
        # Real uploaded-file candidates are re-read member-wise for byte/CRC
        # acceptance. This is packaging integrity, never scientific arithmetic.
        with zipfile.ZipFile(target_zip) as archive:
            if set(archive.namelist())!={x['path'] for x in files}|{'MANIFEST.json','MANIFEST.sha256'}:raise ValueError('Actual asset member set')
            for item in files:
                with archive.open(item['path']) as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
                if h!=item['sha256']:raise ValueError('Actual asset payload hash')
        for unit in group:
            after={p.relative_to(ROOT).as_posix() for p in safe(unit['directory']).rglob('*') if p.is_file()}
            if after!={x['path'] for x in unit['files']}:raise ValueError('Case tree changed after packaging')
            for item in unit['files']:
                s=safe(item['path']).stat()
                if s.st_size!=item['bytes'] or s.st_mtime_ns!=item['mtime_ns']:raise ValueError('Source changed after packaging')
        with target_zip.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        assets.append({'path':str(target_zip),'bytes':target_zip.stat().st_size,'sha256':digest,'manifest_sha256':sha(raw),
                       'actual_zip_payloads_hashed':len(files),'scientific_ready':False})
        (root/'BUILT_ASSETS.json').write_text(json.dumps({'scope':'UNFINISHED_SCIENCE_REVIEW_ASSETS','assets':assets,'remote_mutations':False},indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'asset':target_zip.name,'bytes':target_zip.stat().st_size,'sha256':digest,'scientific_ready':False}),flush=True)
def main():
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group();m.add_argument('--stage-code');m.add_argument('--build-cold-assets');a=p.parse_args()
    inv=json.loads(INVENTORY.read_bytes())
    if a.stage_code:stage_code(inv,a.stage_code)
    elif a.build_cold_assets:build_assets(inv,a.build_cold_assets)
    else:
        g=groups(inv);report={'scope':'PLAN_ONLY_NO_ASSETS_BUILT','groups':len(g),'max_group_payload_bytes':max(sum(x['bytes'] for x in v) for v in g),
            'cold_payload_total_bytes':sum(sum(x['bytes'] for x in v) for v in g),'asset_limit_bytes':LIMIT,'scientific_ready':False,'remote_mutations':False}
        (ROOT/'work/github_review_publication_prepare_plan_v1.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
