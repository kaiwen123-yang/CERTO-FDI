"""Synthetic 400-row inventory plus real tiny ZIP; no science/R1/live reads."""
from pathlib import Path
import copy
import csv
import hashlib
import importlib.util
import io
import json
import uuid
import zipfile
import d2a_archive_coverage_gate_v1 as gate
from d2a_archive_witness_view_v1 import ZipWitnessView

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'work'/('archive_coverage_fixture_'+uuid.uuid4().hex[:8])
tests=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=lambda d:(json.dumps(d,sort_keys=True)+'\n').encode('utf-8')

def check(name,ok):
    tests.append({'name':name,'pass':bool(ok)})
    if not ok:raise AssertionError(name)
def rejects(name,call,code):
    try:call()
    except ValueError as e:check(name,code in str(e))
    else:check(name,False)

def make_data():
    payload={};rows=[];mappings=[];cases={};science_rows={}
    chosen={(40,'fixed20',None,'average250'):'one',(40,'fixed40',None,'average250'):'one',
            (60,'terminal_balanced',None,'point_last_fast_read'):'two'}
    keys=sorted(gate.expected_keys(),key=lambda k:(k[0],k[1],k[2] or 0,k[3]))
    for index,k in enumerate(keys):
        h,f,s,r=k;tag=chosen.get(k);d='work/d2a_cert_h'+str(h)+'_fixture_'+str(tag)+'_'+r
        rec={'protocol_sha256':gate.PROTOCOL_SHA,'readout':r,
             'calendar':{'H_post_slots':h,'family':f,'stage_endpoint':s,'T_fast_steps':(h+4)*250,
                         'moves':[],'observations':[{'fixture_only':True}]},
             'direction':{'physical':['1'],'fixture_only':True} if tag else None}
        n='work/d2a_cert_preflight/fixture_row_'+str(index)+'.json';b=raw(rec);payload[n]=b
        ident=gate.identity(rec);status='CERTIFIED_TARGET_PASS' if tag else gate.ZERO
        row={'H_post_slots':str(h),'family':f,'stage_endpoint':str(s) if s is not None else '',
             'readout':r,'risk_status':status,'direction_record_path':n,
             'direction_record_sha256':sha(b),'certificate_reference':d if tag else '',
             'case_result_sha256':''}
        mappings.append({'row':index,'key':list(k),'identity':ident,'status':status,
                         'direction_record':n,'canonical_case':ident if tag else None})
        if tag:
            case_id=('D2A_'+Path(d).name[len('d2a_cert_'):]).upper()
            if ident not in cases:
                result={'case':case_id,'protocol_sha256':gate.PROTOCOL_SHA,'calendar':rec['calendar'],'readout':r}
                payload[d+'/CASE_RESULT.json']=raw(result);payload[d+'/DIRECTION.json']=raw(rec['direction'])
                for name in ['SUMMARY.json','ACTUAL_PROTOCOL.json','PROJECTION_CERTIFICATE.json',
                             'audit/'+case_id+'_DIRECTION_CERTIFICATE.json']:
                    payload[d+'/'+name]=raw({'fixture_only':name})
                payload[d+'/audit/'+case_id+'_ADJOINT_JET.json.gz']=b'tiny fixture body, never scientific'
                artifacts={name:{'bytes':len(v),'sha256':sha(v)} for n,v in payload.items()
                           if n.startswith(d+'/') for name in [n[len(d)+1:]]
                           if name not in {'CASE_RESULT.json','SUMMARY.json'}}
                cases[ident]={'case_id':case_id,'directory':d,'rows':[],'artifact_hashes':artifacts}
            cases[ident]['rows'].append(index);row['case_result_sha256']=sha(payload[d+'/CASE_RESULT.json'])
            science_rows[index]=ident
        rows.append(row)
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    payload[gate.TABLE]=out.getvalue().encode('utf-8')
    m={'schema':'TINY_SYNTHETIC_COVERAGE_FIXTURE_NOT_SCIENCE','protocol_sha256':gate.PROTOCOL_SHA,
       'table_sha256':sha(payload[gate.TABLE]),'row_mappings':mappings,'cases':cases,
       'files':[{'path':n,'bytes':len(v),'sha256':sha(v)} for n,v in sorted(payload.items())]}
    return m,payload,science_rows

def main():
    AREA.mkdir(exist_ok=False);m,payload,science=make_data();original=copy.deepcopy(m)
    first=next(iter(m['cases']));other=next(k for k in m['cases'] if k!=first)
    check('valid exactly400 rows/3 science rows/2 canonical cases accepted',gate.validate_manifest_inventory(m)['science_rows']==3 and len(m['cases'])==2)
    bad=copy.deepcopy(m);bad['cases'].pop(first)
    rejects('omitted science case rejected before shared extraction',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_CANONICAL_CASE_SET_NOT_EXACT')
    bad=copy.deepcopy(m);bad['row_mappings'].pop()
    rejects('missing row rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_ROW_INDEX_NOT_EXACT')
    bad=copy.deepcopy(m);bad['row_mappings'][-1]=bad['row_mappings'][0].copy()
    rejects('duplicate row index rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_ROW_INDEX_NOT_EXACT')
    bad=copy.deepcopy(m);bad['row_mappings'][-1]['key']=bad['row_mappings'][0]['key']
    rejects('duplicate/missing logical key rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_LOGICAL_KEY_INVENTORY_NOT_EXACT')
    bad=copy.deepcopy(m);bad['cases']['f'*64]=copy.deepcopy(bad['cases'][first])
    rejects('extra canonical case rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_CANONICAL_CASE_SET_NOT_EXACT')
    bad=copy.deepcopy(m);bad['cases'][first]['rows'].pop()
    rejects('wrong/incomplete case row set rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_CASE_ROW_SET_NOT_EXACT')
    bad=copy.deepcopy(m);bad['cases'][first]['rows'].append(bad['cases'][first]['rows'][0])
    rejects('duplicate case row rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_CASE_ROW_SET_NOT_EXACT')
    bad=copy.deepcopy(m);bad['cases'][first]['directory']=bad['cases'][other]['directory']
    rejects('wrong canonical directory/name rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_CASE_DIRECTORY_NAME_BINDING')
    bad=copy.deepcopy(m);bad['row_mappings'][next(iter(science))]['canonical_case']=other
    rejects('wrong canonical identity rejected',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_SCIENCE_CANONICAL_IDENTITY_MISMATCH')
    bad=copy.deepcopy(m);bad['files'].append({'path':'work/d2a_cert_h80_orphan_average250/audit/D2A_H80_ORPHAN_AVERAGE250_ADJOINT_JET.json.gz','sha256':'a'*64,'bytes':1})
    rejects('orphan currentcase witness cannot be shared hash-only payload',lambda:gate.validate_manifest_inventory(bad),'COVERAGE_ORPHAN_CURRENT_CASE_WITNESS')
    archive=AREA/'actual_tiny_coverage.zip';manifest=raw(m)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as z:
        for n,b in payload.items():z.writestr(n,b)
        z.writestr('MANIFEST.json',manifest);z.writestr('MANIFEST.sha256',sha(manifest)+'  MANIFEST.json\n')
    spec=importlib.util.spec_from_file_location('coverage_recipe_v2',ROOT/'outputs/package_full_d2a_release_v2.py')
    recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
    view=ZipWitnessView(archive,sha(manifest));root=AREA/'original_metadata'
    with zipfile.ZipFile(archive) as z:
        actual=json.loads(z.read('MANIFEST.json'));gate.validate_manifest_inventory(actual)
        selected,verified=recipe.extract_immutable_metadata_view(z,actual['files'],root)
    binding=gate.validate_immutable_metadata(actual,root)
    check('actual tiny ZIP metadata binds all400 CSV/direction rows and canonical cases',binding['logical_rows']==400 and binding['science_rows']==3 and binding['canonical_cases']==2)
    check('actual tiny ZIP metadata view contains no witness/dummy payload',not any(n.endswith('.gz') for n in verified) and not list(root.rglob('*.gz')))
    bad=copy.deepcopy(m);index=next(iter(science));bad['row_mappings'][index]['status']='VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET'
    rejects('manifest status must bind actual immutable CSV',lambda:gate.validate_immutable_metadata(bad,root),'COVERAGE_MAPPING_ACTUAL_CSV_DIRECTION_BINDING')
    bad=copy.deepcopy(m);case=bad['cases'].pop(first);bad['cases']['e'*64]=case
    for r in bad['row_mappings']:
        if r['identity']==first:r['identity']='e'*64;r['canonical_case']='e'*64
    rejects('coherent forged manifest identity still rejected by actual direction',lambda:gate.validate_immutable_metadata(bad,root),'COVERAGE_MAPPING_ACTUAL_CSV_DIRECTION_BINDING')
    bad=copy.deepcopy(m);bad['row_mappings'][0]['direction_record']=bad['row_mappings'][1]['direction_record']
    rejects('direction member mapping binds actual CSV path/hash',lambda:gate.validate_immutable_metadata(bad,root),'COVERAGE_MAPPING_ACTUAL_CSV_DIRECTION_BINDING')
    bad=copy.deepcopy(m);wrongpayload=dict(payload)
    actualrows=list(csv.DictReader(io.StringIO(payload[gate.TABLE].decode('utf-8'))))
    actualrows[next(iter(science))]['certificate_reference']=m['cases'][other]['directory']
    text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(actualrows[0]));writer.writeheader();writer.writerows(actualrows)
    wrongpayload[gate.TABLE]=text.getvalue().encode('utf-8');bad['table_sha256']=sha(wrongpayload[gate.TABLE])
    bad['files']=[{**i,'bytes':len(wrongpayload[gate.TABLE]),'sha256':bad['table_sha256']} if i['path']==gate.TABLE else i for i in bad['files']]
    wrongzip=AREA/'actual_tiny_wrong_csv_directory.zip';badmanifest=raw(bad)
    with zipfile.ZipFile(wrongzip,'x',compression=zipfile.ZIP_STORED) as z:
        for n,b in wrongpayload.items():z.writestr(n,b)
        z.writestr('MANIFEST.json',badmanifest);z.writestr('MANIFEST.sha256',sha(badmanifest)+'  MANIFEST.json\n')
    wrongroot=AREA/'original_metadata_wrong_directory'
    with zipfile.ZipFile(wrongzip) as z:recipe.extract_immutable_metadata_view(z,bad['files'],wrongroot)
    rejects('actual ZIP CSV certificate_reference must bind canonical directory',lambda:gate.validate_immutable_metadata(bad,wrongroot),'COVERAGE_CSV_CANONICAL_DIRECTORY_BINDING')
    records=[{'identity':key,'case':c['case_id'],'directory':c['directory'],
              'status':'PASS_FULL_INDEPENDENT_CASE_VERIFIER','fresh_receipt_sha256':'b'*64} for key,c in m['cases'].items()]
    check('complete synthetic replay records accepted only as coverage contract',gate.record_case_replays(m,records)['fresh_canonical_case_replays']==2)
    rejects('missing fresh replay rejected',lambda:gate.record_case_replays(m,records[:-1]),'COVERAGE_FRESH_REPLAY_SET_NOT_EXACT')
    rejects('duplicate replay identity rejected',lambda:gate.record_case_replays(m,[records[0],records[0]]),'COVERAGE_FRESH_REPLAY_SET_NOT_EXACT')
    wrong=copy.deepcopy(records);wrong[0]['directory']=m['cases'][other]['directory']
    rejects('fresh replay wrong directory rejected',lambda:gate.record_case_replays(m,wrong),'COVERAGE_FRESH_REPLAY_CASE_BINDING')
    check('pure gates do not mutate supplied manifest',m==original)
    result={'status':'PASS_REAL_TINY_ZIP_AND_PURE_REPLAY_COVERAGE_FIXTURES','test_count':len(tests),'tests':tests,
            'synthetic_logical_rows':400,'synthetic_science_rows':3,'synthetic_cases':2,'actual_tiny_zip':str(archive),
            'actual_tiny_zip_bytes':archive.stat().st_size,'real_science_or_R1_executed':False,
            'real_large_witness_bytes_read':0,'scientific_ready':False,'synthetic_receipt_records_are_real_replays':False,
            'source_sha256':{n:sha((ROOT/'outputs'/n).read_bytes()) for n in ['d2a_archive_coverage_gate_v1.py','package_full_d2a_release_v2.py','d2a_archive_coverage_gate_fixtures_v1.py']}}
    (ROOT/'outputs/d2a_archive_coverage_gate_fixture_results_v1.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':len(tests),'failures':sum(not x['pass'] for x in tests),'science_executed':False}))

if __name__=='__main__':main()
