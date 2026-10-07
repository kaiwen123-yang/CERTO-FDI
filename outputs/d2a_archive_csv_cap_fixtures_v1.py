"""Exact CSV metadata-cap unit; synthetic real ZIP only, no live/science/R1."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import io
import json
import os
import stat
import uuid
import zipfile
import d2a_archive_coverage_gate_v1 as gate
from d2a_archive_witness_view_v1 import ZipWitnessView

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'work'/('archive_csv_cap_fixture_'+uuid.uuid4().hex[:8])
tests=[];sha=lambda b:hashlib.sha256(b).hexdigest()
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'outputs'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def check(name,ok):
    tests.append({'name':name,'pass':bool(ok)})
    if not ok:raise AssertionError(name)
def rejects(name,call,code):
    try:call()
    except ValueError as e:check(name,code in str(e))
    else:check(name,False)
def sized(p,n):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('wb') as stream:stream.truncate(n)

def main():
    AREA.mkdir(exist_ok=False);recipe=load('csvcap_recipe','package_full_d2a_release_v2.py')
    fixture=load('csvcap_coverage_data','d2a_archive_coverage_gate_fixtures_v1.py')
    m,payload,science=fixture.make_data()
    rows=list(csv.DictReader(io.StringIO(payload[gate.TABLE].decode('utf-8'))))
    for r in rows:r['fixture_padding']='X'*7000
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    table=out.getvalue().encode('utf-8');payload[gate.TABLE]=table;m['table_sha256']=sha(table)
    m['files']=[{**i,'bytes':len(table),'sha256':sha(table)} if i['path']==gate.TABLE else i for i in m['files']]
    check('synthetic CSV truly exceeds2MiB and is within16MiB',2*1024**2<len(table)<=16*1024**2)
    raw=(json.dumps(m,indent=2)+'\n').encode('utf-8');archive=AREA/'actual_large_csv_small_zip.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,b in payload.items():z.writestr(n,b)
        z.writestr('MANIFEST.json',raw);z.writestr('MANIFEST.sha256',sha(raw)+'  MANIFEST.json\n')
    view=ZipWitnessView(archive,sha(raw));root=AREA/'immutable_original_metadata'
    with zipfile.ZipFile(archive) as z:selected,verified=recipe.extract_immutable_metadata_view(z,m['files'],root)
    p=root/gate.TABLE
    check('required CSV actually extracted and hash bound from real ZIP',gate.TABLE in verified and p.read_bytes()==table)
    check('snapshot small() reads >2MiB exact CSV bytes',recipe.small(recipe.TABLE_PATH,root)==table)
    if os.name=='nt':check('actual extracted CSV Windows readonly attribute',bool(p.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY))
    else:check('actual extracted CSV readonly file mode',not (p.stat().st_mode & stat.S_IWUSR))
    check('coverage actual CSV read permits this table and binds400 rows',gate.validate_immutable_metadata(m,root)['logical_rows']==400)
    check('no witness is extracted into small metadata view',not list(root.rglob('*.gz')))
    check('presence still only an index and no science claim',view.scope_info()['witness_payload_bytes_read']==0 and not view.scope_info()['scientific_arithmetic_verified'])
    edges=AREA/'cap_edges';csvpath=edges/recipe.TABLE_PATH
    sized(csvpath,16*1024**2)
    check('snapshot exact CSV accepts16MiB boundary',len(recipe.small(recipe.TABLE_PATH,edges))==16*1024**2)
    sized(csvpath,16*1024**2+1)
    rejects('snapshot exact CSV rejects16MiB+1',lambda:recipe.small(recipe.TABLE_PATH,edges),'Small-metadata cap exceeded')
    other='outputs/other_fixture.json';sized(edges/other,2*1024**2)
    check('snapshot other metadata accepts2MiB boundary',len(recipe.small(other,edges))==2*1024**2)
    sized(edges/other,2*1024**2+1)
    rejects('snapshot other metadata rejects2MiB+1',lambda:recipe.small(other,edges),'Small-metadata cap exceeded')
    too_big_table={'path':recipe.TABLE_PATH,'bytes':16*1024**2+1,'sha256':'a'*64}
    rejects('required CSV selector rejects >16MiB rather than filters',lambda:recipe.immutable_metadata_items([too_big_table]),'REQUIRED_TABLE_METADATA_CAP_EXCEEDED')
    oversizedroot=AREA/'must_not_be_created'
    with zipfile.ZipFile(archive) as z:
        rejects('extraction rejects required oversized CSV before creating view',lambda:recipe.extract_immutable_metadata_view(z,[too_big_table],oversizedroot),'REQUIRED_TABLE_METADATA_CAP_EXCEEDED')
    check('oversized required CSV leaves no partial view',not oversizedroot.exists())
    normal={'path':'outputs/noncanonical.csv','bytes':2*1024**2+1,'sha256':'a'*64}
    check('other >2MiB remains excluded from small selector',recipe.immutable_metadata_items([normal])==[])
    exact={'path':recipe.TABLE_PATH,'bytes':16*1024**2,'sha256':'a'*64}
    check('required CSV selector accepts exact16MiB boundary',recipe.immutable_metadata_items([exact])==[exact])
    many=[{'path':'outputs/small_'+str(i)+'.json','bytes':2*1024**2,'sha256':'a'*64} for i in range(129)]
    rejects('total small metadata cap remains256MiB',lambda:recipe.immutable_metadata_items(many),'TOTAL_IMMUTABLE_SMALL_METADATA_CAP_EXCEEDED')
    oldjson=json.loads((ROOT/'outputs/d2a_archive_coverage_gate_addendum_v1.json').read_text(encoding='utf-8'))
    history='references/release_recipe_history/97e36639d9291e72a93c84c822749f79eaa55d15af13c7bc5ff683916b5ee50f.py'
    check('previous recipe exact bytes preserved in history',sha((ROOT/history).read_bytes())=='97e36639d9291e72a93c84c822749f79eaa55d15af13c7bc5ff683916b5ee50f')
    for n,h in oldjson['initial_IO_artifacts_preserved_sha256'].items():check('initial IO artifact preserved: '+n,sha((ROOT/'outputs'/n).read_bytes())==h)
    for n,h in oldjson['current_source_sha256'].items():
        if n!='package_full_d2a_release_v2.py':check('coverage source preserved: '+n,sha((ROOT/'outputs'/n).read_bytes())==h)
    result={'status':'PASS_REAL_ZIP_EXACT_CSV_CAP_FIXTURES','test_count':len(tests),'tests':tests,
            'synthetic_CSV_bytes':len(table),'actual_tiny_zip_bytes':archive.stat().st_size,'actual_tiny_zip':str(archive),
            'exact_TABLE_cap_bytes':16*1024**2,'other_small_cap_bytes':2*1024**2,'total_cap_bytes':256*1024**2,
            'scientific_ready':False,'science_R1_or_active_table_executed_or_written':False,'real_large_witness_bytes_read':0,
            'source_sha256':{n:sha((ROOT/'outputs'/n).read_bytes()) for n in ['package_full_d2a_release_v2.py','d2a_archive_csv_cap_fixtures_v1.py']},
            'previous_recipe_history':history}
    (ROOT/'outputs/d2a_archive_csv_cap_fixture_results_v1.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':len(tests),'failures':sum(not t['pass'] for t in tests),'synthetic_CSV_bytes':len(table),'science_executed':False}))

if __name__=='__main__':main()
