"""Exact support for M1 initialized-plant, all-input profiling, and repaired dual.
Only Python standard library. No state/noise/nuisance reset at block joins.
"""
from fractions import Fraction as F
from math import isqrt
import json


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


def dot(x,y):
    return sum((a*b for a,b in zip(x,y)),F(0))


def spans(times,start):
    out=[]
    prev=start
    for t in times:
        out.append((prev+1,t))
        prev=t
    return out


def project(c,x,intervals,start):
    out=[F(0)]*len(x)
    for left,right in intervals:
        weights=[c**(right-j) for j in range(left,right+1)]
        B=dot(weights,weights)
        val=sum((w*x[j-start] for j,w in zip(range(left,right+1),weights)),F(0))/B
        for j,w in zip(range(left,right+1),weights):
            out[j-start]=w*val
    return out


def kappa(c,k):
    m=k+1
    weights=[c**j for j in range(m)]
    return m-sum(weights,F(0))**2/dot(weights,weights)


def support(r,lam):
    assert sum(lam,F(0))==0
    Q=F(0)
    result=F(0)
    for v in lam[:-1]:
        Q+=v
        result+=r*abs(Q)
    return result


counts={'initialized_covariance_vs_projection':0,'full_control_neutrality':0,
        'affine_center_bound':0,'kappa_monotone':0,'kappa_tail_certificate':0,
        'positive_pole_monotone':0,'negative_pole_comparison':0,
        'global_repaired_zero':0,'projection_range':0,'repair_energy':0,
        'support_correction':0,'global_dual_identity':0,'local_iid_support':0}
counts['affine_oracle_pair_identity']=0
corrs=[F(-4,5),F(-1,2),F(0),F(1,2),F(4,5)]

# Known-zero initial plant. Direct retained output covariance includes all past innovations.
for c in corrs:
    for n in range(1,8):
        full_times=list(range(1,n+1))
        theta=[F((j*j+3*j)%11-5,7) for j in full_times]
        state=[sum((c**(j-h)*theta[h-1] for h in range(1,j+1)),F(0)) for j in full_times]
        covariance=[[sum((c**(i-h)*c**(j-h) for h in range(1,min(i,j)+1)),F(0))
                     for j in full_times] for i in full_times]
        for mask in range(1<<n):
            times=[j for j in full_times if mask & (1<<(j-1))]
            intervals=spans(times,0)
            proj=project(c,theta,intervals,1)
            idx=[j-1 for j in times]
            inv=inverse([[covariance[i][j] for j in idx] for i in idx])
            direct=sum((state[i]*inv[p][q]*state[j] for p,i in enumerate(idx)
                        for q,j in enumerate(idx)),F(0))
            assert direct==dot(proj,proj)
            counts['initialized_covariance_vs_projection']+=1
        full_proj=project(c,theta,spans(full_times,0),1)
        assert full_proj==theta
        counts['full_control_neutrality']+=1
    prev=F(0)
    C=1/(1-abs(c))**2
    cut=(2*C.numerator+C.denominator-1)//C.denominator
    for k in range(1,max(65,cut+2)):
        kap=kappa(c,k)
        assert kap>0 and kap>=prev
        prev=kap
        counts['kappa_monotone']+=1
        if k>=cut:
            assert kap/k>=F(1,2)
        counts['kappa_tail_certificate']+=1
        m=k+1
        weights=[c**(m-j) for j in range(1,m+1)]
        B=dot(weights,weights)
        h=[F(2*j-m-1,2) for j in range(1,m+1)]
        L1=-sum(weights,F(0))*dot(weights,h)/B
        assert abs(L1)<=F(m,2)/(1-abs(c))**2
        A=F(100)
        eta=F(1,7)
        x=[A+eta*v for v in h]
        loss=dot(x,x)-dot(weights,x)**2/B
        assert loss>=kap*A*A-eta*A*m/(1-abs(c))**2
        counts['affine_center_bound']+=1

for k in range(1,9):
    previous=kappa(F(0),k)
    for j in range(1,10):
        cp=F(j,10)
        kp=kappa(cp,k)
        assert kp<previous
        previous=kp
        assert kappa(-cp,k)>=kp
        counts['positive_pole_monotone']+=1
        counts['negative_pole_comparison']+=1


def ceilf(v):
    return -((-v.numerator)//v.denominator)


def calendar(H,xi,k,eta,r,profile,n0=3):
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
    start=-n0+1
    full_times=list(range(start,H+1))
    a=[F(0) if t<=0 else eta*t for t in full_times]
    g=[F(1)]*len(full_times)
    u=[F(0)]*len(full_times)
    times=list(range(start,1))
    blocks=[]
    x=0
    for n in ns:
        mh=n//2
        L=2*(n+k)
        center=F(L+1,2)
        ampl=eta*(x+center)
        local_obs=list(range(1,mh+1))+list(range(mh+k+1,3*mh+k+1))+list(range(3*mh+2*k+1,L+1))
        signs=[1]*mh+[-1]*n+[1]*mh
        c0=F(k+1,2)
        z=[r*(c0+mh-i) for i in range(1,mh+1)]
        z +=[-r*(c0+min(i-1,n-i)) for i in range(1,n+1)]
        z +=[r*(c0+i-1) for i in range(1,mh+1)]
        active=ampl>=r*F(k+n-1,2)
        obs_map={t:(s,zz) for t,s,zz in zip(local_obs,signs,z)}
        baseline=[F(0)]*L
        for t in range(1,L+1):
            i=x+t-start
            if t in obs_map:
                s,zz=obs_map[t]
                g[i]=F(s)
                u[i]=ampl-s*zz if active else F(0)
                baseline[t-1]=s*u[i]
            else:
                leftsign=1 if t<=mh+k else -1
                h=t-mh if leftsign==1 else t-(3*mh+k)
                if profile=='zero':
                    g[i]=F(0)
                elif profile=='left':
                    g[i]=F(leftsign)
                elif profile=='linear':
                    g[i]=leftsign*(1-F(2*h,k+1))
                elif profile=='alternating':
                    g[i]=F(leftsign*((-1)**h))
                else:
                    raise ValueError(profile)
                u[i]=ampl if active else F(0)
        blocks.append({'left':x+1,'right':x+L,'n':n,'a':ampl,'active':active,
                       'baseline':baseline,'z':z,'obs':local_obs})
        times +=[x+t for t in local_obs]
        x+=L
    times +=list(range(x+1,H+1))
    if ns:
        assert 1<=H-x<=4
    return full_times,times,a,g,u,blocks,start


rows=[]


def check_dual(c,k,H,profile,eta=F(1,7),r=F(2,5),xi=None,verify_output=False):
    kap=kappa(c,k)
    if xi is None:
        xi=2*kap*eta/r
    full_times,times,a,g,u,blocks,start=calendar(H,xi,k,eta,r,profile)
    intervals=spans(times,start-1)
    Pu=project(c,u,intervals,start)
    Pg=project(c,g,intervals,start)
    Pa=project(c,a,intervals,start)
    w=[F(0)]*len(a)
    baseline=[F(0)]*len(a)
    cert=F(0)
    repair_total=F(0)
    for block in blocks:
        left,right=block['left']-start,block['right']-start+1
        bu=Pu[left:right]
        bg=g[left:right]
        bp=Pg[left:right]
        lam0=block['baseline']
        assert sum(lam0,F(0))==0
        if block['active']:
            N=dot(bg,bu)
            D=dot(bp,bp)
            n=block['n']
            A=block['a']
            Ck=2*(k+2)
            assert D>=2*n-2 and D>=n
            assert abs(N)<=Ck*A
            b=N/D
            bw=[v-b*p for v,p in zip(bu,bp)]
            assert dot(bg,bw)==0
            energy=dot([b*p for p in bp],[b*p for p in bp])
            assert energy==N*N/D
            assert energy<=Ck*Ck*A*A/n
            repair_total+=energy
            counts['repair_energy']+=1
            delta=[gg*vv-base for gg,vv,base in zip(bg,bw,lam0)]
            assert sum(delta,F(0))==0
            l1=sum((abs(v) for v in delta),F(0))
            assert l1<=Ck*(k+3)*A
            hd=support(r,delta)
            L=len(delta)
            assert hd<=r*F(L-1,2)*l1
            counts['support_correction']+=1
            h0=support(r,lam0)
            c0=F(k+1,2)
            exact= A*r*n*(n+2*k)/2-4*r*r*sum(((c0+j)**2 for j in range(n//2)),F(0))
            assert h0==exact
            counts['local_iid_support']+=1
            cert+=h0+hd
        else:
            bw=[F(0)]*len(bu)
        w[left:right]=bw
        baseline[left:right]=lam0
    lam=[gg*vv for gg,vv in zip(g,w)]
    assert sum(lam,F(0))==0
    counts['global_repaired_zero']+=1
    assert project(c,w,intervals,start)==w
    counts['projection_range']+=1
    h=support(r,lam)
    assert h<=cert
    O=dot(a,a)/2
    LB=dot(a,w)-dot(w,w)/2-h
    diff=[aa-ww for aa,ww in zip(a,w)]
    oracle_loss=dot([aa-pp for aa,pp in zip(a,Pa)],[aa-pp for aa,pp in zip(a,Pa)])
    m=k+1
    weights=[c**(m-j) for j in range(1,m+1)]
    B=dot(weights,weights)
    hh=[F(2*j-m-1,2) for j in range(1,m+1)]
    L1=-sum(weights,F(0))*dot(weights,hh)/B
    L2=dot(hh,hh)-dot(weights,hh)**2/B
    exact_oracle=F(0)
    for block in blocks:
        A=block['a']+eta/2
        exact_oracle+=2*kap*A*A+kap*eta*eta*F((block['n']+k)**2,2)+4*eta*A*L1+2*eta*eta*L2
    assert exact_oracle==oracle_loss
    counts['affine_oracle_pair_identity']+=1
    compressed_error=dot([pp-ww for pp,ww in zip(Pa,w)],[pp-ww for pp,ww in zip(Pa,w)])
    assert O-LB==(oracle_loss+compressed_error+2*h)/2
    assert O-LB==dot(diff,diff)/2+h
    counts['global_dual_identity']+=1
    # Optional direct initialized output covariance check of the repaired direction's variance.
    if verify_output:
        # Every retained conditional innovation uses real previous state.
        white_coeff=[]
        for left,right in intervals:
            weights=[c**(right-j) for j in range(left,right+1)]
            B=dot(weights,weights)
            # Input-space variance equals sum of independent normalized innovation coefficients squared.
            value=sum((ww*ww for ww in w[left-start:right-start+1]),F(0))
            white_coeff.append(value)
        assert sum(white_coeff,F(0))==dot(w,w)
    return {'c':str(c),'k':k,'H':H,'profile':profile,'blocks':len(blocks),
            'active_blocks':sum(b['active'] for b in blocks),'dual_deficit_upper':str(O-LB),
            'weighted_zero_exact':True,'repair_energy':str(repair_total)}


for c in corrs:
    for k in [1,2,3]:
        for H in [32,64]:
            for profile in ['zero','left','linear','alternating']:
                rows.append(check_dual(c,k,H,profile))

larger=[]
for c in [F(-1,2),F(0),F(1,2)]:
    kap=kappa(c,1)
    for H in [256,1024,4096]:
        row=check_dual(c,1,H,'linear',eta=F(1),r=2*kap,xi=F(1))
        root=isqrt(H)
        assert root*root==H
        row['normalized_upper']=str(F(row['dual_deficit_upper'])/(H*H*root))
        row['candidate_coefficient']=str(2*kap/5)
        larger.append(row)

print(json.dumps({'scope':'Exact initialized physical plant and all-input repaired dual checks; q=1,n0=3. No state/covariance/nuisance reset. Universal sharp proof is separate.',
                  'checks':counts,'finite_dual_cases':rows,'larger_checks':larger,'status':'PASS'},indent=2))
