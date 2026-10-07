"""Exact finite checks of the full-precision AR(1) attaining dual.
No independent initialization, no covariance reset, no external dependencies.
"""
from fractions import Fraction as F
import json
from math import isqrt


def ceilf(v):
    return -((-v.numerator)//v.denominator)


def markov(rho, times, x):
    if not times:
        return F(0)
    return x[0]**2+sum(((x[j]-rho**(times[j]-times[j-1])*x[j-1])**2 /
                        (1-rho**(2*(times[j]-times[j-1]))) for j in range(1,len(times))),F(0))


def precision(rho,times):
    diag=[F(0)]*len(times)
    off=[]
    diag[0]=F(1)
    for j in range(1,len(times)):
        a=rho**(times[j]-times[j-1])
        D=1-a*a
        diag[j]+=1/D
        diag[j-1]+=a*a/D
        off.append(-a/D)
    return diag,off


def apply(diag,off,x):
    return [diag[i]*x[i]+(off[i-1]*x[i-1] if i else 0)+
            (off[i]*x[i+1] if i+1<len(x) else 0) for i in range(len(x))]


def dot(x,y):
    return sum((a*b for a,b in zip(x,y)),F(0))


def support(r,times,lam):
    assert sum(lam,F(0))==0
    Q=F(0)
    result=F(0)
    for j in range(len(times)-1):
        Q+=lam[j]
        result+=r*(times[j+1]-times[j])*abs(Q)
    return result


def calendar(H,xi,k,eta,r,rho0=F(0),n0=3):
    ns=[]
    used=0
    ell=1
    while True:
        n=2*ceilf(xi*ell/2)
        if used+2*(n+k)>H-1:
            break
        ns.append(n)
        used+=2*(n+k)
        ell+=1
    if ns:
        units=(H-1-used)//4
        q,rem=divmod(units,len(ns))
        ns=[n+2*(q+(j<rem)) for j,n in enumerate(ns)]
        used=sum(2*(n+k) for n in ns)
    times=list(range(-n0+1,1))
    signs=[1]*n0
    aux=[F(0)]*n0
    blocks=[]
    gaps=[]
    start=0
    for n in ns:
        m=n//2
        L=2*(n+k)
        c=F(L+1,2)
        a=rho0+eta*(start+c)
        local_times=list(range(1,m+1))+list(range(m+k+1,3*m+k+1))+list(range(3*m+2*k+1,L+1))
        local_signs=[1]*m+[-1]*n+[1]*m
        c0=F(k+1,2)
        z=[r*(c0+m-i) for i in range(1,m+1)]
        z +=[-r*(c0+min(i-1,n-i)) for i in range(1,n+1)]
        z +=[r*(c0+i-1) for i in range(1,m+1)]
        active=a>=r*F(k+n-1,2)
        u=[a-s*v if active else F(0) for s,v in zip(local_signs,z)]
        offset=len(times)
        blocks.append({'n':n,'a':a,'times':[start+t for t in local_times],
                       'signs':local_signs,'u':u,'active':active,'z':z})
        gaps +=[(offset+m-1,offset+m),(offset+m+n-1,offset+m+n)]
        times +=[start+t for t in local_times]
        signs +=local_signs
        aux +=u
        start+=L
    times +=list(range(start+1,H+1))
    signs +=[1]*(H-start)
    aux +=[F(0)]*(H-start)
    target=[F(0) if t<=0 else rho0+eta*t for t in times]
    assert aux[0]==aux[-1]==0
    if ns:
        assert 1<=H-start<=4
    return times,signs,aux,target,blocks,gaps


counts={'full_signed_zero':0,'precision_pair_decomposition':0,'support_bound':0,
        'covariance_variance_identity':0,'dual_deficit_identity':0,'oracle_gap_identity':0,
        'iid_local_support':0}
rows=[]


def check(rho,k,H,eta,r,xi,rho0=F(0),check_covariance=True):
    nu=(1-rho)/(1+rho)
    m=k+1
    wm=(1-rho**m)/(1+rho**m)
    beta=m*nu-wm
    delta=(wm-nu)/2
    d=rho/(1-rho*rho)
    times,signs,u,a,blocks,gaps=calendar(H,xi,k,eta,r,rho0)
    diag,off=precision(rho,times)
    v=apply(diag,off,u)
    lam=[s*q for s,q in zip(signs,v)]
    assert sum(lam,F(0))==0
    counts['full_signed_zero']+=1
    expected=[nu*s*q for s,q in zip(signs,u)]
    paircost=F(0)
    for j in range(len(times)-1):
        if times[j+1]-times[j]==1:
            assert signs[j]==signs[j+1]
            b=signs[j]*d*(u[j]-u[j+1])
            expected[j]+=b
            expected[j+1]-=b
            paircost+=r*abs(d)*abs(u[j]-u[j+1])
    for left,right in gaps:
        assert u[left]==u[right]
        assert signs[left]==-signs[right]
        b=delta*u[left]*signs[left]
        expected[left]+=b
        expected[right]-=b
        paircost+=r*(k+1)*abs(delta)*abs(u[left])
    assert expected==lam
    counts['precision_pair_decomposition']+=1
    hlocal=F(0)
    for block in blocks:
        if block['active']:
            local=support(r,block['times'],[s*q for s,q in zip(block['signs'],block['u'])])
            n=block['n']
            c0=F(k+1,2)
            direct=block['a']*r*n*(n+2*k)/2-4*r*r*sum(((c0+j)**2 for j in range(n//2)),F(0))
            assert local==direct
            assert local==dot([s*q for s,q in zip(block['signs'],block['u'])],block['z'])
            hlocal+=local
            counts['iid_local_support']+=1
    h=support(r,times,lam)
    assert h<=nu*hlocal+paircost
    counts['support_bound']+=1
    if check_covariance:
        covv=[sum((rho**abs(t-q)*b for q,b in zip(times,v)),F(0)) for t in times]
        assert covv==u
        assert dot(v,covv)==dot(u,v)
        counts['covariance_variance_identity']+=1
    full_times=list(range(-2,H+1))
    full_a=[F(0) if t<=0 else rho0+eta*t for t in full_times]
    O=markov(rho,full_times,full_a)/2
    Oobs=markov(rho,times,a)/2
    LB=dot(v,a)-dot(u,v)/2-h
    e=[x-y for x,y in zip(a,u)]
    deficit_upper=O-LB
    assert deficit_upper==O-Oobs+markov(rho,times,e)/2+h
    counts['dual_deficit_identity']+=1
    centered=[F(2*j-m,2) for j in range(m+1)]
    E=markov(rho,list(range(m+1)),centered)-markov(rho,[0,m],[centered[0],centered[-1]])
    exactloss=F(0)
    for left,right in gaps:
        A=rho0+eta*F(times[left]+times[right],2)
        exactloss+=(beta*A*A+eta*eta*E)/2
    assert O-Oobs==exactloss
    counts['oracle_gap_identity']+=1
    return {'rho':str(rho),'k':k,'H':H,'blocks':len(blocks),
            'active_blocks':sum(b['active'] for b in blocks),'dual_deficit_upper':str(deficit_upper),
            'signed_zero':True,'full_covariance_retained':True}


for rho in [F(-4,5),F(-1,2),F(0),F(1,2),F(4,5)]:
    for k in [1,2,3]:
        nu=(1-rho)/(1+rho)
        beta=(k+1)*nu-(1-rho**(k+1))/(1+rho**(k+1))
        eta=F(1,7)
        r=F(2,5)
        xi=2*beta*eta/(nu*r)
        for H in [32,64]:
            rows.append(check(rho,k,H,eta,r,xi))

# Exact larger schedules with rational limiting coefficient: eta=xi=1,
# r=2*beta/nu gives candidate coefficient 2*beta/5. No fit is used as proof.
asymptotic_rows=[]
for rho in [F(-1,2),F(0),F(1,2)]:
    nu=(1-rho)/(1+rho)
    beta=2*nu-(1-rho*rho)/(1+rho*rho)
    for H in [256,1024,4096]:
        row=check(rho,1,H,F(1),2*beta/nu,F(1),check_covariance=False)
        value=F(row['dual_deficit_upper'])
        root=isqrt(H)
        assert root*root==H
        row['normalized_upper']=str(value/(H*H*root))
        row['candidate_coefficient']=str(2*beta/5)
        asymptotic_rows.append(row)

print(json.dumps({'scope':'Exact global colored dual and support checks; no reset and no numerical projection. Asymptotic proof is separate.',
                  'checks':counts,'finite_cases':rows,'larger_schedule_checks':asymptotic_rows,'status':'PASS'},indent=2))
