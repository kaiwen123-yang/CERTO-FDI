"""Standalone asymmetric moment repair supplement."""
from fractions import Fraction as F
from math import isqrt
import json


def dot(x,y):
    return sum((a*b for a,b in zip(x,y)),F(0))


def eye(n):
    return [[F(i==j) for j in range(n)] for i in range(n)]


def tr(a):
    return [list(row) for row in zip(*a)]


def mm(a,b):
    bt=tr(b)
    return [[dot(row,col) for col in bt] for row in a]


def mv(a,v):
    return [dot(row,v) for row in a]


def add(a,b):
    return [[x+y for x,y in zip(ar,br)] for ar,br in zip(a,b)]


def inverse(a):
    n=len(a)
    if not n:
        return []
    b=[row[:] + [F(i==j) for j in range(n)] for i,row in enumerate(a)]
    for j in range(n):
        p=next(i for i in range(j,n) if b[i][j])
        b[p],b[j]=b[j],b[p]
        d=b[j][j]
        b[j]=[v/d for v in b[j]]
        for i in range(n):
            if i!=j:
                c=b[i][j]
                b[i]=[v-c*w for v,w in zip(b[i],b[j])]
    return [row[n:] for row in b]


def flat(vs):
    return [x for v in vs for x in v]


def norm2(vs):
    return sum((dot(v,v) for v in vs),F(0))


def vadd(x,y):
    return [a+b for a,b in zip(x,y)]


def vsub(x,y):
    return [a-b for a,b in zip(x,y)]


def scale(s,v):
    return [s*x for x in v]


def spans(times,start):
    out=[]
    for right in times:
        out.append((start+1,right))
        start=right
    return out


def pivot_columns(a):
    if not a:
        return []
    b=[row[:] for row in a]
    r=0
    piv=[]
    for c in range(len(b[0])):
        i=next((i for i in range(r,len(b)) if b[i][c]),None)
        if i is None:
            continue
        b[r],b[i]=b[i],b[r]
        value=b[r][c]
        b[r]=[x/value for x in b[r]]
        for i in range(len(b)):
            if i!=r:
                value=b[i][c]
                b[i]=[x-value*y for x,y in zip(b[i],b[r])]
        piv.append(c)
        r+=1
        if r==len(b):
            break
    return piv


pinv_count=0
def pinverse(a):
    global pinv_count
    n=len(a)
    if not n:
        return []
    piv=pivot_columns(a)
    if not piv:
        return [[F(0)]*n for _ in range(n)]
    U=[[row[j] for j in piv] for row in a]
    Uplus=mm(inverse(mm(tr(U),U)),tr(U))
    C=mm(mm(Uplus,a),tr(Uplus))
    result=mm(mm(tr(Uplus),inverse(C)),Uplus)
    assert tr(result)==result
    assert mm(mm(a,result),a)==a
    assert mm(mm(result,a),result)==result
    assert tr(mm(a,result))==mm(a,result)
    assert tr(mm(result,a))==mm(result,a)
    pinv_count+=1
    return result


def determinant(a):
    n=len(a)
    if n==0:
        return F(1)
    if n==1:
        return a[0][0]
    return sum(((-1)**j*a[0][j]*determinant([row[:j]+row[j+1:] for row in a[1:]])
                for j in range(n)),F(0))


def assert_psd(a):
    n=len(a)
    assert a==tr(a)
    for mask in range(1,1<<n):
        idx=[i for i in range(n) if mask&(1<<i)]
        assert determinant([[a[i][j] for j in idx] for i in idx])>=0


cases=[
    {'name':'M1_negative_scalar','A':[[F(-1,2)]],'G':[[F(1)]],'B':[F(1)]},
    {'name':'M1_positive_scalar','A':[[F(1,2)]],'G':[[F(1)]],'B':[F(1)]},
    {'name':'M2_nonnormal_SPD','A':[[F(1,2),F(2)],[F(0),F(1,4)]],
     'G':[[F(1),F(0)],[F(1,3),F(2,3)]],'B':[F(1),F(2)]},
    {'name':'M2_scaled_copy_SPD','A':[[F(0),F(1,2)],[F(0),F(0)]],
     'G':[[F(1,10),F(0)],[F(0),F(1)]],'B':[F(0),F(1)]},
    {'name':'M2S_scaled_copy_singular','A':[[F(0),F(1,2)],[F(0),F(0)]],
     'G':[[F(0)],[F(1)]],'B':[F(0),F(1)]},
    {'name':'M2S_partial_constant_mode','A':[[F(0),F(1),F(0)],[F(0),F(0),F(1)],[F(0),F(0),F(0)]],
     'G':[[F(0),F(0)],[F(1),F(0)],[F(0),F(1)]],'B':[F(0),F(1),F(1)]}
]


def support(r,lam):
    assert sum(lam,F(0))==0
    Q=F(0)
    value=F(0)
    for x in lam[:-1]:
        Q+=x
        value+=r*abs(Q)
    return value


def block_project(A,G,x,intervals):
    d=len(A)
    p=len(G[0])
    cache={}
    powers=[eye(d)]
    def power(j):
        while len(powers)<=j:
            powers.append(mm(powers[-1],A))
        return powers[j]
    out=[[F(0)]*p for _ in x]
    for left,right in intervals:
        m=right-left+1
        blocks=[mm(power(m-j-1),G) for j in range(m)]
        W=[[F(0)]*d for _ in range(d)]
        for H in blocks:
            W=add(W,mm(H,tr(H)))
        dag=pinverse(W)
        mu=[F(0)]*d
        for j,H in zip(range(left,right+1),blocks):
            mu=vadd(mu,mv(H,x[j]))
        y=mv(dag,mu)
        for j,H in zip(range(left,right+1),blocks):
            out[j]=mv(tr(H),y)
        cache[(left,right)]=(blocks,dag)
    return out,cache,power


records=[]
for case in cases:
    A,G,B=case['A'],case['G'],case['B']
    d,p=len(A),len(G[0])
    f=mv(mm(inverse(mm(tr(G),G)),tr(G)),B)
    assert mv(G,f)==B
    Fisher=dot(f,f)
    r=F(1)
    eta=F(1,7)
    amp=F(10)
    # One actual prefix reading j=0, known initial state at j=-1.
    # Actual H=10 post-onset inputs have rho0=10-eta*(11/2)>=0.
    rho0=amp-eta*F(11,2)
    g=[F(1),F(1),F(1),F(1,3),F(-1),F(-1),F(-1),F(-1),F(-2,3),F(1),F(1)]
    aux=[F(0),F(8),F(9),F(10),F(9),F(8),F(8),F(9),F(10),F(9),F(8)]
    lam0=[F(0),F(8),F(9),F(0),F(-9),F(-8),F(-8),F(-9),F(0),F(9),F(8)]
    lam0=scale(Fisher,lam0)
    times=[0,1,2,4,5,6,7,9,10]
    intervals=spans(times,-1)
    U=[scale(a,f) for a in aux]
    actual_h=[scale(gg,f) for gg in g]
    repair_h=actual_h[:]
    repair_h[0]=[F(0)]*p
    PU,cache,power=block_project(A,G,U,intervals)
    Ph,_,_=block_project(A,G,repair_h,intervals)
    N=sum((dot(hh,u) for hh,u in zip(actual_h,PU)),F(0))
    D=norm2(Ph)
    assert D>=Fisher*6 and D>=Fisher*4
    assert N!=0
    alpha=N/D
    v=[vsub(u,scale(alpha,h)) for u,h in zip(PU,Ph)]
    lam=[dot(hh,vv) for hh,vv in zip(actual_h,v)]
    assert sum(lam,F(0))==0
    projected_v,_,_=block_project(A,G,v,intervals)
    assert projected_v==v
    repair=norm2([vsub(vv,uu) for vv,uu in zip(v,PU)])
    assert repair==N*N/D and repair>0
    assert abs(N)<=6*Fisher*amp
    assert repair<=36*Fisher*amp*amp/4
    delta=[x-y for x,y in zip(lam,lam0)]
    assert sum(delta,F(0))==0
    assert sum((abs(x) for x in delta),F(0))<=24*Fisher*amp
    h0=support(r,lam0)
    hd=support(r,delta)
    hv=support(r,lam)
    assert h0==100*Fisher
    assert hv<=h0+hd
    # Construct the actual raw retained-state statistic and pull it back through
    # the full initialized physical plant. Prefix noise must cancel, not reset.
    raw={t:[F(0)]*d for t in times}
    for left,right in intervals:
        blocks,dag=cache[(left,right)]
        Hv=[F(0)]*d
        for j,H in zip(range(left,right+1),blocks):
            Hv=vadd(Hv,mv(H,v[j]))
        statecoef=mv(dag,Hv)
        raw[right]=vadd(raw[right],statecoef)
        if left-1>=0:
            raw[left-1]=vsub(raw[left-1],mv(tr(power(right-left+1)),statecoef))
    adj=[F(0)]*d
    realized=[[F(0)]*p for _ in v]
    for j in range(10,-1,-1):
        adj=vadd(raw.get(j,[F(0)]*d),mv(tr(A),adj))
        realized[j]=mv(tr(G),adj)
    assert realized==v and norm2(realized)==norm2(v)
    target=[F(0)]+[rho0+eta*j for j in range(1,11)]
    theta=[scale(a,f) for a in target]
    Pa,_,_=block_project(A,G,theta,intervals)
    loss=norm2([vsub(a,b) for a,b in zip(theta,Pa)])
    O=norm2(theta)/2
    LB=sum((dot(a,b) for a,b in zip(theta,v)),F(0))-norm2(v)/2-hv
    assert O-LB==loss/2+norm2([vsub(a,b) for a,b in zip(Pa,v)])/2+hv
    if case['name']=='M1_negative_scalar':
        assert N==F(8,15)
        assert D==F(383,45)
        assert alpha==F(24,383)
        assert repair==F(64,1915)
        assert h0==100 and hd==F(10251,383) and hv==F(35773,383)
        assert loss==F(178309,490)
    records.append({'model':case['name'],'prefix_readings':1,'post_horizon':10,
                    'half_hold':2,'gap_span':2,'k':1,'r':str(r),'eta':str(eta),
                    'rho0':str(rho0),'center_amplitude':str(amp),
                    'first_gap_g':'1/3','second_gap_g':'-2/3','F':str(Fisher),
                    'N_before':str(N),'D':str(D),'alpha':str(alpha),
                    'repair_energy':str(repair),'mass_after':str(sum(lam,F(0))),
                    'support_baseline':str(h0),'support_correction':str(hd),
                    'support_repaired':str(hv),'oracle_norm_loss':str(loss),
                    'unrepaired_support_infinite':True,
                    'physical_raw_statistic_realized':True,'state_noise_variance_equals_input_norm':True})
print(json.dumps({'scope':'Only new asymmetric nonzero-mass repair cases; no rerun of inherited large tables. Real initialized prefix/state statistic, all-input scalar healthy class.',
                  'cases':records,'nonzero_repairs':len(records),'status':'PASS'},indent=2))
