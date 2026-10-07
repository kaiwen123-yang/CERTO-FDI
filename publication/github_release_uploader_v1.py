"""Explicit authenticated19-asset publication upload, at most3 workers.

Never clobbers/deletes uploaded assets. Deletes only a failed partial asset
created by this worker, records it, and allows one bounded upload retry.
No science, theorem, source-content or global credential/config changes.
"""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
import subprocess
import threading
import time
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'work/github_release_upload_manifest.json'
REPO='kaiwen123-yang/CERTO-FDI'
TAGS={'review-20261007-source-and-theory','review-20261007-h160-rehearsal','review-20261007-full400-partial','legacy-pre-theory-20261007/main'}
OUT=ROOT/'outputs/github_release_upload_receipt_v1.json'
PROGRESS=ROOT/'outputs/github_release_upload_progress_v1.json'
LOGS=ROOT/'outputs/github_release_upload_logs_v1'
LOCK=threading.Lock();RESULTS={};EVENTS=[]
utc=lambda:datetime.now(timezone.utc).isoformat()
sha=lambda b:hashlib.sha256(b).hexdigest()

def command(argv,check=True):
    p=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    if check and p.returncode:raise RuntimeError(json.dumps({'command':argv,'exit':p.returncode,'stdout':p.stdout[-2000:],'stderr':p.stderr[-2000:]}))
    return p
def api(endpoint,method='GET'):
    return json.loads(command(['gh','api','--method',method,endpoint]).stdout or '{}')
def release(tag):return api('repos/'+REPO+'/releases/tags/'+quote(tag,safe=''))
def observe(tag,name):
    found=[a for a in release(tag)['assets'] if a['name']==name]
    if len(found)>1:raise RuntimeError('Duplicate remote asset name')
    return found[0] if found else None
def accepted(asset,item):
    if not asset or asset.get('state')!='uploaded' or asset.get('size')!=item['bytes']:return False
    digest=asset.get('digest')
    if digest and digest!='sha256:'+item['sha256']:return False
    return True
def remote_fields(asset):
    return {k:asset.get(k) for k in ['id','name','state','size','digest','browser_download_url','created_at','updated_at']}
def write_atomic(p,value):
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');t.replace(p)
def save():
    snapshot={'schema':'github-release-upload-progress-v1','repo':REPO,'updated_utc':utc(),'assets':list(RESULTS.values()),'events':list(EVENTS),
              'completed_assets':sum(x['status'] in {'ACCEPTED_REMOTE_SHA256','UPLOADED_SIZE_ONLY_DIGEST_UNAVAILABLE'} for x in RESULTS.values()),
              'active_assets':sum(x['status']=='UPLOADING' for x in RESULTS.values()),'asset_total':19,'full400':False,'scientific_ready':False}
    write_atomic(PROGRESS,snapshot)
def update(name,value):
    with LOCK:RESULTS[name]=value;save()
def event(value):
    with LOCK:EVENTS.append(value);save()
def finish(item,asset,prior,attempts):
    digest=asset.get('digest');result={'release_tag':item['release_tag'],'name':item['name'],'local':item['local'],
        'expected_bytes':item['bytes'],'expected_sha256':item['sha256'],'status':'ACCEPTED_REMOTE_SHA256' if digest else 'UPLOADED_SIZE_ONLY_DIGEST_UNAVAILABLE',
        'remote':remote_fields(asset),'remote_SHA256_verified':digest=='sha256:'+item['sha256'],'remote_digest_available':bool(digest),
        'reused_existing_uploaded_asset':prior,'upload_attempts':attempts,'verified_utc':utc()}
    update(item['name'],result)
    print(json.dumps({'asset':item['name'],'status':result['status'],'bytes':item['bytes'],'remote_id':asset['id']}),flush=True)
    return result
def worker(item):
    name=item['name'];tag=item['release_tag'];p=(ROOT/item['local']).resolve();p.relative_to(ROOT)
    s=p.stat()
    base={'release_tag':tag,'name':name,'expected_bytes':item['bytes'],'expected_sha256':item['sha256'],'local':item['local']}
    if p.name!=name or s.st_size!=item['bytes'] or item['bytes']>=2*2**30:raise RuntimeError('Local asset path/name/size invalid '+name)
    existing=observe(tag,name)
    if accepted(existing,item):return finish(item,existing,True,0)
    if existing:
        result={**base,'status':'EXISTING_REMOTE_CONFLICT_PRESERVED','remote':remote_fields(existing),'remote_SHA256_verified':False}
        update(name,result);return result
    owned_ids=set()
    for attempt in [1,2]:
        update(name,{**base,'status':'UPLOADING','attempt':attempt,'started_utc':utc()})
        path=LOGS/(name+'.attempt'+str(attempt))
        with path.with_suffix(path.suffix+'.stdout.log').open('x',encoding='utf-8') as stdout,path.with_suffix(path.suffix+'.stderr.log').open('x',encoding='utf-8') as stderr:
            result=subprocess.run(['gh','release','upload',tag,str(p),'--repo',REPO],stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        current=observe(tag,name)
        if current:owned_ids.add(current['id'])
        if p.stat().st_size!=s.st_size or p.stat().st_mtime_ns!=s.st_mtime_ns:raise RuntimeError('Local upload asset changed '+name)
        if accepted(current,item):return finish(item,current,False,attempt)
        event({'asset':name,'attempt':attempt,'exit':result.returncode,'observed_remote':remote_fields(current) if current else None,
               'stdout_log':str(path.with_suffix(path.suffix+'.stdout.log')),'stderr_log':str(path.with_suffix(path.suffix+'.stderr.log')),'utc':utc()})
        if current and current.get('state')=='uploaded':
            held={**base,'status':'UPLOADED_REMOTE_DIGEST_OR_SIZE_CONFLICT_PRESERVED','remote':remote_fields(current),'remote_SHA256_verified':False}
            update(name,held);return held
        if current:
            if current['id'] not in owned_ids or current.get('state')=='uploaded':raise RuntimeError('Cannot delete non-owned/success asset')
            command(['gh','api','--method','DELETE','repos/'+REPO+'/releases/assets/'+str(current['id'])])
            event({'asset':name,'deleted_failed_partial_remote_id':current['id'],'state':current.get('state'),'own_current_run_only':True,'utc':utc()})
        if attempt==1:time.sleep(5)
    failure={**base,'status':'FAILED_AFTER_BOUNDED_RETRY','remote_SHA256_verified':False,'upload_attempts':2};update(name,failure);return failure

def main():
    started=time.perf_counter();mraw=MANIFEST.read_bytes();m=json.loads(mraw)
    if m['repository']!=REPO or m['full400_complete'] is not False or m['scientific_ready'] is not False:raise ValueError('Frozen publication manifest scope/target invalid')
    items=m['assets']
    if len(items)!=19 or len({(i['release_tag'],i['name']) for i in items})!=19 or {i['release_tag'] for i in items}!=TAGS:raise ValueError('Expected exact19assets/4tags')
    if any(not re.fullmatch(r'[0-9a-f]{64}',i['sha256']) for i in items):raise ValueError('Expected SHA missing')
    login=command(['gh','api','user','--jq','.login']).stdout.strip()
    if login!='kaiwen123-yang':raise ValueError('Authenticated owner mismatch')
    if OUT.exists() or LOGS.exists():raise ValueError('Uploader existing receipt/logs: inspect actual process/state, never restart on timeout')
    LOGS.mkdir();releases={tag:release(tag) for tag in sorted(TAGS)}
    if any(not x['prerelease'] for x in releases.values()):raise ValueError('Expected review prerelease')
    for item in items:update(item['name'],{'release_tag':item['release_tag'],'name':item['name'],'status':'QUEUED','expected_bytes':item['bytes']})
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(worker,item):item for item in items}
        for future,item in futures.items():
            try:future.result()
            except Exception as error:update(item['name'],{'release_tag':item['release_tag'],'name':item['name'],'status':'FAILED_EXCEPTION','reason':str(error),'remote_SHA256_verified':False})
    # Fresh authenticated remote metadata for all four releases, independent
    # of per-worker cached observations. No download or clobber required.
    final={tag:release(tag) for tag in sorted(TAGS)};rows=[]
    for item in items:
        found=[a for a in final[item['release_tag']]['assets'] if a['name']==item['name']]
        asset=found[0] if len(found)==1 else None;row=dict(RESULTS[item['name']])
        row['fresh_final_remote_observation']=remote_fields(asset) if asset else None
        row['fresh_final_state_size_accepted']=accepted(asset,item)
        row['fresh_final_digest_SHA256_verified']=bool(asset and asset.get('digest')=='sha256:'+item['sha256'])
        rows.append(row)
    if MANIFEST.read_bytes()!=mraw:raise ValueError('Upload manifest changed')
    good=all(r['fresh_final_state_size_accepted'] for r in rows);digests=all(r['fresh_final_digest_SHA256_verified'] for r in rows)
    report={'schema':'github-release-upload-receipt-v1','repo':REPO,'authorized_publication_only':True,'status':'PASS_ALL19_REMOTE_STATE_SIZE_SHA256' if good and digests else 'UPLOADED_ALL19_REMOTE_SIZE_WITH_DIGEST_GAPS' if good else 'INCOMPLETE_OR_REMOTE_CONFLICT',
            'manifest_sha256':sha(mraw),'asset_count':19,'total_expected_bytes':sum(i['bytes'] for i in items),'maximum_parallel_uploads':3,
            'all_remote_asset_state_and_size_accepted':good,'all_remote_digest_SHA256_verified':digests,'assets':rows,
            'release_ids':{tag:value['id'] for tag,value in final.items()},'events':EVENTS,'elapsed_seconds':time.perf_counter()-started,
            'completed_utc':utc(),'source_sha256':sha(Path(__file__).read_bytes()),'full400':False,'scientific_ready':False,
            'user_requested_task_end_and_science_stopped':m['final_stop'],'science_theory_R1_or_model_actions_performed':False,
            'remote_successful_assets_clobbered_or_deleted':False,'log_root':str(LOGS)}
    write_atomic(OUT,report)
    md=['# GitHub Release upload receipt v1','',report['status'],'',f'Repository: https://github.com/{REPO}',
        f'19 assets / {report["total_expected_bytes"]:,} bytes; maximum3 parallel uploads.',
        f'All remote state/size accepted: {good}. All API digest SHA256 verified: {digests}.',
        '','Only user-authorized publication; no science/R1/theory actions. full400=false; scientific_ready=false.',
        '','| Release | Asset | Bytes | Remote ID | State | API SHA256 verified |','|---|---|---:|---:|---|---|']
    for row in rows:
        remote=row['fresh_final_remote_observation'] or {}
        md.append(f'| {row["release_tag"]} | {row["name"]} | {remote.get("size")} | {remote.get("id")} | {remote.get("state")} | {row["fresh_final_digest_SHA256_verified"]} |')
    (ROOT/'outputs/github_release_upload_receipt_v1.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'assets':19,'bytes':report['total_expected_bytes'],'elapsed_seconds':report['elapsed_seconds'],'remote_all_SHA256':digests}),flush=True)

if __name__=='__main__':main()
