"""Real tiny-ZIP IO fixtures only; no R1, live table, witness arithmetic or science."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import os
import stat
import uuid
import zipfile
from unittest.mock import patch
from d2a_archive_witness_view_v1 import FilesystemWitnessView,ZipWitnessView,WitnessViewError

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'work'/('archive_io_fixture_'+uuid.uuid4().hex[:8])
W='work/d2a_cert_h60_terminal_balanced_average250/audit/D2A_H60_TERMINAL_BALANCED_AVERAGE250_ADJOINT_JET.json.gz'
M='work/d2a_cert_h60_terminal_balanced_average250/CASE_RESULT.json'
PAYLOAD=gzip.compress(b'{"tiny_fixture_only":true}',mtime=0)
META=b'{"scope":"actual tiny-ZIP small metadata; no science"}\n'
sha=lambda data:hashlib.sha256(data).hexdigest()
tests=[]

def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'outputs'/filename)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def make(name,payloads=None,items=None,extra=None):
    payloads=payloads if payloads is not None else {W:PAYLOAD,M:META}
    items=items if items is not None else [{'path':n,'bytes':len(b),'sha256':sha(b)} for n,b in payloads.items()]
    raw=(json.dumps({'schema':'REAL_TINY_IO_FIXTURE_NOT_SCIENCE','files':items},indent=2)+'\n').encode()
    p=AREA/(name+'.zip')
    with zipfile.ZipFile(p,'x',compression=zipfile.ZIP_STORED) as z:
        for n,b in payloads.items():z.writestr(n,b)
        if extra:z.writestr(extra,b'unsafe tiny fixture')
        z.writestr('MANIFEST.json',raw);z.writestr('MANIFEST.sha256',sha(raw)+'  MANIFEST.json\n')
    return p,sha(raw)

def check(name,condition):
    tests.append({'name':name,'pass':bool(condition)})
    if not condition:raise AssertionError(name)

def rejects(name,call,expected):
    try:call()
    except WitnessViewError as error:check(name,expected in str(error))
    else:check(name,False)

def main():
    AREA.mkdir(exist_ok=False)
    original={n:sha((ROOT/'outputs'/n).read_bytes()) for n in ['d2a_full_grid_acceptance_v1.py','package_full_d2a_release_v1.py','full_d2a_release_contract_v1.md','full_d2a_release_contract_v1.json']}
    good,mhash=make('good')
    opened=[];old_open=zipfile.ZipFile.open
    def watched_open(self,name,*args,**kwargs):
        label=name.filename if isinstance(name,zipfile.ZipInfo) else str(name)
        opened.append(label)
        if label.endswith('_ADJOINT_JET.json.gz'):raise AssertionError('Availability opened a witness body')
        return old_open(self,name,*args,**kwargs)
    with patch.object(zipfile.ZipFile,'open',watched_open):
        view=ZipWitnessView(good,mhash)
        check('real ZIP presence, central-directory size and receipt/manifest SHA mapping',view.available(W,sha(PAYLOAD),len(PAYLOAD)))
        check('Windows relative query separators normalized',view.available(W.replace('/','\\'),sha(PAYLOAD),len(PAYLOAD)))
    check('availability never opens witness body',not any(n.endswith('_ADJOINT_JET.json.gz') for n in opened))
    check('scope does not claim large payload hash/arithmetic',view.scope_info()['witness_payload_hash_verified'] is False and view.scope_info()['scientific_arithmetic_verified'] is False)
    items=[{'path':W,'bytes':len(PAYLOAD),'sha256':sha(PAYLOAD)},{'path':M,'bytes':len(META),'sha256':sha(META)}]
    missing,h=make('missing_member',{M:META},items)
    check('manifest cannot supply absent real member',ZipWitnessView(missing,h).available(W,sha(PAYLOAD),len(PAYLOAD)) is False)
    unmapped,h=make('missing_manifest_entry',{W:PAYLOAD,M:META},items[1:])
    check('central member without manifest mapping rejected',ZipWitnessView(unmapped,h).available(W,sha(PAYLOAD),len(PAYLOAD)) is False)
    rejects('external manifest hash mismatch',lambda:ZipWitnessView(good,'0'*64),'MANIFEST_SHA_BINDING_MISMATCH')
    badmap,h=make('wrong_mapping',items=[{**items[0],'sha256':'0'*64},items[1]])
    rejects('receipt-to-manifest payload hash mismatch',lambda:ZipWitnessView(badmap,h).available(W,sha(PAYLOAD),len(PAYLOAD)),'WITNESS_MANIFEST_SHA_MAPPING_MISMATCH')
    wrongsize,h=make('wrong_actual_size',{W:PAYLOAD+b'X',M:META},items)
    rejects('actual member size disagrees with manifest/receipt',lambda:ZipWitnessView(wrongsize,h).available(W,sha(PAYLOAD),len(PAYLOAD)),'WITNESS_MEMBER_SIZE_MISMATCH')
    rejects('caller wrong size binding',lambda:view.available(W,sha(PAYLOAD),len(PAYLOAD)+1),'WITNESS_MEMBER_SIZE_MISMATCH')
    unsafe,h=make('unsafe_namespace',extra='work/../../outside.json')
    rejects('unsafe central-directory namespace',lambda:ZipWitnessView(unsafe,h),'UNSAFE_ARCHIVE_NAMESPACE')
    winunsafe,h=make('unsafe_windows_namespace',extra='work/CON/receipt.json')
    rejects('Windows device namespace rejected',lambda:ZipWitnessView(winunsafe,h),'UNSAFE_WINDOWS_ARCHIVE_NAMESPACE')
    winspace,h=make('unsafe_windows_trailing_space',extra='work/name /receipt.json')
    rejects('Windows trailing-space alias rejected',lambda:ZipWitnessView(winspace,h),'UNSAFE_WINDOWS_ARCHIVE_NAMESPACE')
    rejects('unsafe witness query namespace',lambda:view.available('../outside.gz',sha(PAYLOAD),len(PAYLOAD)),'UNSAFE_ARCHIVE_NAMESPACE')
    wrongcase=W.replace('D2A_H60_TERMINAL_BALANCED','D2A_H60_FIXED40')
    rejects('case/name mismatch',lambda:view.available(wrongcase,sha(PAYLOAD),len(PAYLOAD)),'CASE_WITNESS_NAME_MISMATCH')
    corrupt,h=make('same_size_body_corruption',{W:b'X'*len(PAYLOAD),M:META},items)
    check('same-size body corruption deliberately not certified/detected by presence view',ZipWitnessView(corrupt,h).available(W,sha(PAYLOAD),len(PAYLOAD)))
    # Extract only real small metadata from the actual ZIP. No witness is touched.
    recipe=module('fixture_recipe_v2','package_full_d2a_release_v2.py')
    metadata_root=AREA/'immutable_metadata_view';meta=metadata_root/M
    with zipfile.ZipFile(good) as actual_zip:
        selected,verified=recipe.extract_immutable_metadata_view(actual_zip,items,metadata_root)
    check('recipe small metadata selected/extracted/hashed from actual ZIP',selected==items[1:] and verified=={M})
    if os.name=='nt':check('recipe metadata leaf Windows readonly attribute set',bool(meta.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY))
    else:check('recipe metadata leaf readonly mode set',not (meta.stat().st_mode & stat.S_IWUSR))
    before=meta.read_bytes()
    v1=module('fixture_fullgrid_v1','d2a_full_grid_acceptance_v1.py')
    v2=module('fixture_fullgrid_v2','d2a_full_grid_acceptance_v2.py')
    reader=v2.SmallReader(metadata_root,view)
    check('v2 reads actual archived original small metadata',reader.obj(M,sha(META))==json.loads(META))
    check('presence works with no extracted/dummy witness',not (metadata_root/W).exists() and reader.witness_available(W,sha(PAYLOAD),len(PAYLOAD)))
    check('immutable metadata view remains byte-identical',meta.read_bytes()==before)
    replayroot=AREA/'independent_replay_root';replaymeta=replayroot/M;replaywitness=replayroot/W
    replaymeta.parent.mkdir(parents=True);replaywitness.parent.mkdir(parents=True)
    with zipfile.ZipFile(good) as actual_zip:recipe.extract_members(actual_zip,items,replayroot,set())
    replaymeta.write_bytes(b'{"fresh_receipt_rewritten_by_fixture":true}\n')
    replaywitness.unlink()
    recipe.check_immutable_metadata_view(selected,metadata_root)
    check('replay metadata rewrites cannot mutate archived original view',meta.read_bytes()==before and replaymeta.read_bytes()!=before)
    check('actual-ZIP availability survives real isolated replay-witness removal',not replaywitness.exists() and reader.witness_available(W,sha(PAYLOAD),len(PAYLOAD)))
    fsroot=AREA/'filesystem_fixture';f=fsroot/W;f.parent.mkdir(parents=True);f.write_bytes(PAYLOAD)
    old=v1.SmallReader(fsroot);new=v2.SmallReader(fsroot)
    check('filesystem default matches original contained is_file semantics',old.path(W).is_file()==new.witness_available(W,'0'*64,999)==True)
    check('filesystem missing agrees with original',old.path(W+'missing').is_file()==new.witness_available(W+'missing','0'*64,999)==False)
    check('v1/v2 metadata self-tests unchanged',v1.self_test()==v2.self_test())
    for n,h in original.items():check('immutable baseline preserved: '+n,sha((ROOT/'outputs'/n).read_bytes())==h)
    result={'status':'PASS_REAL_TINY_ZIP_IO_BRIDGE_FIXTURES','fixture_root':str(AREA),'tests':tests,'test_count':len(tests),
            'fixture_witness_uncompressed_bytes':len(PAYLOAD),'real_large_witness_bytes_read':0,'science_or_R1_executed':False,
            'live_tables_locks_PID_main_or_v1_sources_modified':False,'metadata_view_source':'Only actual tiny ZIP member bytes; no worktree fallback/no dummy gzip.',
            'large_payload_hash_or_arithmetic_certified':False,'source_sha256':{n:sha((ROOT/'outputs'/n).read_bytes()) for n in ['d2a_archive_witness_view_v1.py','d2a_full_grid_acceptance_v2.py','package_full_d2a_release_v2.py','d2a_archive_view_bridge_fixtures_v1.py']},'baseline_sha256':original}
    (ROOT/'outputs/d2a_archive_view_bridge_fixture_results_v1.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'tests':len(tests),'failures':sum(not t['pass'] for t in tests),'big_witness_or_science':False}))

if __name__=='__main__':main()
