"""Read-only ZIP support calculation; does not import or execute package code."""
from fractions import Fraction as F
from pathlib import Path
import zipfile, json, math, hashlib, argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--zip',type=Path,default=Path(r'C:\Users\ykw\Downloads\CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919_R1_20260926.zip'))
ZIP = parser.parse_args().zip
OUT = Path(__file__).resolve().parent / 'post_move_point_support.json'
EXPECTED_ZIP_SHA256 = 'f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b'
with ZIP.open('rb') as source_archive:
    archive_digest = hashlib.sha256()
    for archive_chunk in iter(lambda: source_archive.read(1024 * 1024), b''):
        archive_digest.update(archive_chunk)
    archive_sha256 = archive_digest.hexdigest()
if archive_sha256 != EXPECTED_ZIP_SHA256:
    raise ValueError('This derivation is pinned to the audited R1 ZIP; archive SHA256 does not match.')

def upper(x, digits=18):
    s=10**digits
    return F(-((-x.numerator*s)//x.denominator),s)

def sqrt_upper(x, digits=18):
    assert x >= 0
    s=10**digits
    k=math.isqrt(x.numerator*s*s//x.denominator)
    if F(k*k,s*s)<x:k+=1
    ans=F(k,s)
    assert ans*ans>=x
    return ans

def inverse(a):
    n=len(a);b=[row[:]+[F(i==j) for j in range(n)] for i,row in enumerate(a)]
    for k in range(n):
        p=next(i for i in range(k,n) if b[i][k])
        b[k],b[p]=b[p],b[k]
        d=b[k][k];b[k]=[x/d for x in b[k]]
        for i in range(n):
            if i!=k:
                d=b[i][k]
                b[i]=[x-d*y for x,y in zip(b[i],b[k])]
    result=[row[n:] for row in b]
    assert all(sum((a[i][k]*result[k][j] for k in range(n)),F(0))==F(i==j) for i in range(n) for j in range(n))
    return result

sources={}
with zipfile.ZipFile(ZIP) as z:
    names=z.namelist()
    an=next(n for n in names if n.endswith('NONLINEAR_ADMISSION_20260919/audit/ADMISSION_CERTIFICATE.json'))
    hn=next(n.rsplit('/audit/',1)[0]+'/' for n in names if n.endswith('POINT_READOUT_CERTIFICATE.json'))
    assert '/CERTO_FDI_STAGE_D1_CALENDAR_RISK_20260919/' in an
    assert '/CERTO_FDI_STAGE_D1_CALENDAR_RISK_20260919/' in hn
    tn=next(n for n in names if n.startswith(hn) and n.endswith('/audit/TANGENT_LIFTS.json'))
    def read(n,fields):
        raw=z.read(n);sources[n]={'sha256':hashlib.sha256(raw).hexdigest(),'selected_fields':fields}
        return json.loads(raw)
    a=read(an,['rho','entry.bounded_move_defect_radius','tail.start_step','tail.initial_nonlinear_gap','tail.W_candidate','moving_defect_output_memory_prefactor'])
    h=read(hn+'audit/FROZEN_HOLD_CERTIFICATE.json',['witnesses.acceleration_gain'])
    dec=read(hn+'audit/DECAY_RATE_REFINED.json',['candidates[rho=197/200].P'])
    tangent=read(tn,['geometry.M0'])
    rho=F(a['rho']);n0=a['tail']['start_step']
    P=[[F(x) for x in row] for row in next(x for x in dec['candidates'] if x['rho']==str(rho))['P']]
    Pinv=inverse(P)
    # Entries of M0 are already certified rational enclosing intervals.
    massabs=[max(abs(F(x[0])),abs(F(x[1]))) for x in tangent['geometry']['M0'][3]]
    cabs=[40*x for x in massabs]+[80*x for x in massabs]+[80*x for x in massabs]
    re=[F(x) for x in a['entry']['bounded_move_defect_radius']]
    r4=[F(x) for x in a['tail']['initial_nonlinear_gap']]
    W=[F(x) for x in a['tail']['W_candidate']]
    Ha=[[F(x) for x in row] for row in h['witnesses']['acceleration_gain']]
    assert all(x>=0 for row in Ha for x in row)
    def H(b):
        p=sqrt_upper(sum((b[i]*abs(P[i][j])*b[j] for i in range(18) for j in range(18)),F(0)))
        return [sqrt_upper(Pinv[i][i])*p for i in range(18)]
    def dot(x,y):return sum((p*q for p,q in zip(x,y)),F(0))
    entry_pref=upper(dot(cabs,H(re)))
    transient_pref=upper(dot(cabs,H(r4)))
    tail=upper(dot(cabs,[dot(row,W) for row in Ha]))
    old_avg_pref=F(a['moving_defect_output_memory_prefactor'])
    avg_factor=(1-rho**250)/(250*(1-rho))
    metric_entry_pref=upper(old_avg_pref/avg_factor)
    rows=[]
    for n in [1500,1750,2000,2500]:
        entry=upper(entry_pref*rho**n)
        metric_entry=upper(metric_entry_pref*rho**n)
        transient=upper(transient_pref*rho**(n-n0))
        rows.append({'n':n,'entry_coordinate':str(entry),'entry_metric_from_average_prefactor':str(metric_entry),'nonlinear_transient':str(transient),'tail':str(tail),'total_coordinate':str(upper(entry+transient+tail)),'total_metric_entry':str(upper(metric_entry+transient+tail))})
    result={'status':'CONDITIONAL_INHERITED_TUBE_LINEAR_SUPPORT_ONLY','arithmetic':'fractions.Fraction; exact inverse checked; square roots rounded upward at 1e-18; displayed bound sums rounded upward at 1e-18','time_origin':'n=0 at movement end/hold start; first full admitted slot ends n=1750','rho':str(rho),'tail_start':n0,'source_files':sources,'C4_absolute_upper':list(map(str,cabs)),'entry_coordinate_prefactor':str(entry_pref),'entry_metric_prefactor_from_existing_average':str(metric_entry_pref),'nonlinear_transient_prefactor':str(transient_pref),'tail':str(tail),'rows':rows,'limitations':['Uses existing certificate premises without rerunning their verifier.','No new nonlinear trajectories, variation equations, D2-a scan, mean certificate, or point covariance certificate.','The exact support arithmetic is conditional on inherited state tube/event/model validity.']}
result['archive_sha256'] = archive_sha256
OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('saved',OUT)
for row in rows:
    print(row['n'],{k:float(F(v)) for k,v in row.items() if k!='n'})
