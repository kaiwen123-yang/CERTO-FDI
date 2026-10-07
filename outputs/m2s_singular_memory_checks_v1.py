"""Standalone exact M2S checks, generated from owned standard-library helpers."""
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


models=[]
N2=[[F(0),F(1)],[F(0),F(0)]]
Z2=[[F(0),F(0)],[F(0),F(0)]]
B2=[F(0),F(1)]
for t,label in [(F(0),'eps0'),(F(1,2),'eps1_4'),(F(1),'eps1')]:
    G=[[F(0)],[F(1)]] if t==0 else [[t,F(0)],[F(0),F(1)]]
    models.append({'name':'current_'+label,'A':Z2,'G':G,'B':B2,'Sbound':F(1),'eps':t*t})
    models.append({'name':'memory_'+label,'A':N2,'G':G,'B':B2,'Sbound':F(2),'eps':t*t})
N3=[[F(0),F(1),F(0)],[F(0),F(0),F(1)],[F(0),F(0),F(0)]]
models += [
    {'name':'scaled_memory_eps1_100','A':[[F(0),F(1,2)],[F(0),F(0)]],
     'G':[[F(1,10),F(0)],[F(0),F(1)]],'B':B2,'Sbound':F(3,2),'eps':F(1,100),'gamma':F(1,2)},
    {'name':'scaled_memory_eps0','A':[[F(0),F(1,2)],[F(0),F(0)]],
     'G':[[F(0)],[F(1)]],'B':B2,'Sbound':F(3,2),'eps':F(0),'gamma':F(1,2)},
    {'name':'scaled_partial3','A':[[F(0),F(1,2),F(0)],[F(0),F(0),F(0)],[F(0),F(0),F(0)]],
     'G':[[F(0),F(0)],[F(1),F(0)],[F(0),F(1)]],
     'B':[F(0),F(1),F(0)],'Sbound':F(3,2)},
    {'name':'shift3','A':N3,'G':[[F(0)],[F(0)],[F(1)]],'B':[F(0),F(0),F(1)],'Sbound':F(3)},
    {'name':'partial_constant3','A':N3,'G':[[F(0),F(0)],[F(1),F(0)],[F(0),F(1)]],
     'B':[F(0),F(1),F(1)],'Sbound':F(6)},
    {'name':'scalar_reduced2','A':[[F(1,2),F(0)],[F(0),F(1,2)]],
     'G':[[F(0)],[F(1)]],'B':B2,'Sbound':F(2)},
    {'name':'diagonal_recovery2','A':[[F(1,2),F(0)],[F(0),F(1,4)]],
     'G':[[F(1)],[F(1)]],'B':[F(1),F(1)],'Sbound':F(4)},
    {'name':'jordan_recovery3','A':[[F(1,2),F(1),F(0)],[F(0),F(1,2),F(1)],[F(0),F(0),F(1,2)]],
     'G':[[F(0)],[F(0)],[F(1)]],'B':[F(0),F(0),F(1)],'Sbound':F(14)},
    {'name':'tiny_memory2','A':[[F(0),F(1,10)],[F(0),F(0)]],
     'G':[[F(0)],[F(1)]],'B':B2,'Sbound':F(11,10)}
]


class Channel:
    def __init__(self,model):
        self.model=model
        self.name=model['name']
        self.A=model['A']
        self.G=model['G']
        self.B=model['B']
        self.d=len(self.B)
        self.p=len(self.G[0])
        self.Q=mm(self.G,tr(self.G))
        Gplus=mm(inverse(mm(tr(self.G),self.G)),tr(self.G))
        self.f=mv(Gplus,self.B)
        assert mv(self.G,self.f)==self.B
        self.F=dot(self.f,self.f)
        assert self.F>0
        self.powers=[eye(self.d)]
        self.cache={}
        self.Sbound=model['Sbound']
        self.Gammabound=max(sum((abs(v) for v in row),F(0))
                            for m in range(1,self.d+1) for row in self.interval(m)[2])
        self.Ccross=self.Gammabound*self.Sbound*self.Sbound
        ranks=[len(pivot_columns(self.interval(m)[1])) for m in range(1,self.d+1)]
        self.reach_rank=ranks[-1]
        self.reach_index=next(i+1 for i,r in enumerate(ranks) if r==self.reach_rank)
        assert self.reach_index<=self.reach_rank-self.p+1
        assert mm(mm(tr(self.G),self.interval(1)[2]),self.G)==eye(self.p)

    def power(self,r):
        while len(self.powers)<=r:
            self.powers.append(mm(self.powers[-1],self.A))
        return self.powers[r]

    def interval(self,m):
        if m not in self.cache:
            blocks=[mm(self.power(m-j-1),self.G) for j in range(m)]
            W=[[F(0)]*self.d for _ in range(self.d)]
            for H in blocks:
                W=add(W,mm(H,tr(H)))
            Wdag=pinverse(W)
            M=[F(0)]*self.d
            N=[F(0)]*self.d
            for j in range(m):
                AB=mv(self.power(m-j-1),self.B)
                M=vadd(M,AB)
                N=vadd(N,scale(F(2*(j+1)-m-1,2),AB))
            assert mv(mm(W,Wdag),M)==M
            beta=m*self.F-dot(M,mv(Wdag,M))
            L1=-dot(M,mv(Wdag,N))
            L2=self.F*sum((F(2*(j+1)-m-1,2)**2 for j in range(m)),F(0))-dot(N,mv(Wdag,N))
            self.cache[m]=(blocks,W,Wdag,beta,L1,L2)
        return self.cache[m]

    def project(self,x,intervals,start):
        out=[[F(0)]*self.p for _ in x]
        for left,right in intervals:
            m=right-left+1
            if m==1:
                out[left-start]=x[left-start][:]
                continue
            blocks,W,Wdag,_,_,_=self.interval(m)
            val=[F(0)]*self.d
            for j,H in zip(range(left,right+1),blocks):
                val=vadd(val,mv(H,x[j-start]))
            v=mv(Wdag,val)
            for j,H in zip(range(left,right+1),blocks):
                out[j-start]=mv(tr(H),v)
        return out


channels=[Channel(m) for m in models]
counts={'initialized_covariance_vs_projection':0,'common_covariance_image':0,
        'full_control_neutrality':0,'beta_nonnegative_monotone':0,
        'constant_mode_rowspace_criterion':0,'finite_rank_recovery_bound':0,
        'partial_mode_not_full_input_recovery':0,'affine_center_bound':0,
        'pseudoinverse_after_reach_stabilization':0,
        'global_weighted_zero':0,'projection_range':0,'dual_deficit_identity':0,
        'repair_energy':0,'repair_support':0,'oracle_affine_pair_identity':0,
        'local_iid_support':0,'epsilon_formula':0}
counts['physical_statistic_realization']=0
counts['full_state_score_variance']=0
model_rows=[]
for ch in channels:
    prev=F(0)
    for m in range(2,21):
        blocks,W,Wdag,beta,L1,L2=ch.interval(m)
        assert beta>=0 and beta>=prev
        prev=beta
        counts['beta_nonnegative_monotone']+=1
        recovered=all(mv(tr(H),mv(Wdag, [sum((mv(ch.power(r),ch.B)[i] for r in range(m)),F(0))
                                      for i in range(ch.d)]))==ch.f for H in blocks)
        assert recovered==(beta==0)
        counts['constant_mode_rowspace_criterion']+=1
        if m-1>=ch.reach_index:
            assert beta>0
            counts['finite_rank_recovery_bound']+=1
        if beta==0 and len(pivot_columns(W))<m*ch.p:
            counts['partial_mode_not_full_input_recovery']+=1
        assert L2>=0 and abs(L1)<=F(m,2)*ch.Ccross
        if beta==0:
            assert L1==0
        counts['affine_center_bound']+=1
        if m>=ch.d:
            assert len(pivot_columns(W))==ch.reach_rank
            Wdagd=ch.interval(ch.d)[2]
            assert_psd([[a-b for a,b in zip(ar,br)] for ar,br in zip(Wdagd,Wdag)])
            counts['pseudoinverse_after_reach_stabilization']+=1
    for n in range(1,5):
        times=list(range(1,n+1))
        theta=[F((j*j+3*j)%11-5,7) for j in times]
        inp=[scale(v,ch.f) for v in theta]
        states=[]
        for t in times:
            mu=[F(0)]*ch.d
            for h in range(1,t+1):
                mu=vadd(mu,scale(theta[h-1],mv(ch.power(t-h),ch.B)))
            states.append(mu)
        cov=[[None]*n for _ in range(n)]
        for i in times:
            for j in times:
                C=[[F(0)]*ch.d for _ in range(ch.d)]
                for h in range(1,min(i,j)+1):
                    C=add(C,mm(mm(ch.power(i-h),ch.Q),tr(ch.power(j-h))))
                cov[i-1][j-1]=C
        for mask in range(1<<n):
            kept=[i for i in times if mask & (1<<(i-1))]
            proj=ch.project(inp,spans(kept,0),1)
            full_cov=[]
            for i in kept:
                for r in range(ch.d):
                    full_cov.append([cov[i-1][j-1][r][s] for j in kept for s in range(ch.d)])
            dag=pinverse(full_cov)
            mu=flat([states[i-1] for i in kept])
            if mu:
                assert mv(mm(full_cov,dag),mu)==mu
                exact=dot(mu,mv(dag,mu))
            else:
                exact=F(0)
            assert exact==norm2(proj)
            counts['initialized_covariance_vs_projection']+=1
            counts['common_covariance_image']+=1
        assert ch.project(inp,spans(times,0),1)==inp
        counts['full_control_neutrality']+=1
    if 'eps' in ch.model:
        eps=ch.model['eps']
        if ch.name.startswith('current'):
            assert ch.interval(2)[3]==1 and ch.interval(3)[3]==2
        else:
            gamma=ch.model.get('gamma',F(1))
            assert ch.interval(2)[3]==eps/(eps+gamma*gamma)
            assert ch.interval(3)[3]==(gamma*gamma+2*eps)/(eps+gamma*gamma)
        counts['epsilon_formula']+=1
    model_rows.append({'model':ch.name,'dimension':ch.d,'noise_rank':ch.p,
                       'reached_rank':ch.reach_rank,'reach_index':ch.reach_index,
                       'F':str(ch.F),'beta_k1':str(ch.interval(2)[3]),
                       'beta_k2':str(ch.interval(3)[3]),'Gamma_upper':str(ch.Gammabound)})

def ceilf(v):
    return -((-v.numerator)//v.denominator)


def support(r,lam):
    assert sum(lam,F(0))==0
    total=F(0)
    Q=F(0)
    for a in lam[:-1]:
        Q+=a
        total+=r*abs(Q)
    return total


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
        q,rem=divmod((H-1-used)//4,len(ns))
        ns=[n+2*(q+(j<rem)) for j,n in enumerate(ns)]
    start=-n0+1
    ft=list(range(start,H+1))
    a=[F(0) if t<=0 else eta*t for t in ft]
    g=[F(1)]*len(ft)
    aux=[F(0)]*len(ft)
    times=list(range(start,1))
    blocks=[]
    x=0
    for n in ns:
        mh=n//2
        L=2*(n+k)
        A=eta*(x+F(L+1,2))
        obs=list(range(1,mh+1))+list(range(mh+k+1,3*mh+k+1))+list(range(3*mh+2*k+1,L+1))
        s=[1]*mh+[-1]*n+[1]*mh
        c0=F(k+1,2)
        z=[r*(c0+mh-i) for i in range(1,mh+1)]
        z +=[-r*(c0+min(i-1,n-i)) for i in range(1,n+1)]
        z +=[r*(c0+i-1) for i in range(1,mh+1)]
        active=A>=r*F(k+n-1,2)
        om={t:(ss,zz) for t,ss,zz in zip(obs,s,z)}
        base=[F(0)]*L
        for t in range(1,L+1):
            idx=x+t-start
            if t in om:
                ss,zz=om[t]
                g[idx]=F(ss)
                aux[idx]=A-ss*zz if active else F(0)
                base[t-1]=ss*aux[idx]
            else:
                ls=1 if t<=mh+k else -1
                h=t-mh if ls==1 else t-(3*mh+k)
                if profile=='zero':
                    g[idx]=F(0)
                elif profile=='linear':
                    g[idx]=ls*(1-F(2*h,k+1))
                elif profile=='alternating':
                    g[idx]=F(ls*((-1)**h))
                else:
                    raise ValueError(profile)
                aux[idx]=A if active else F(0)
        blocks.append({'left':x+1,'right':x+L,'n':n,'A':A,'active':active,'baseline':base})
        times +=[x+t for t in obs]
        x+=L
    times +=list(range(x+1,H+1))
    if ns:
        assert 1<=H-x<=4
    return start,a,g,aux,times,blocks


def check_dual(ch,k,H,profile,eta=F(1,7),r=F(2,5),xi=None):
    beta=ch.interval(k+1)[3]
    if xi is None:
        xi=2*beta*eta/(ch.F*r) if beta>0 else F(1)
    start,a,g,aux,times,blocks=calendar(H,xi,k,eta,r,profile)
    ints=spans(times,start-1)
    aa=[scale(v,ch.f) for v in a]
    hh=[scale(v,ch.f) for v in g]
    uu=[scale(v,ch.f) for v in aux]
    Pu=ch.project(uu,ints,start)
    Ph=ch.project(hh,ints,start)
    Pa=ch.project(aa,ints,start)
    v=[[F(0)]*ch.p for _ in a]
    hcert=F(0)
    repair=F(0)
    for block in blocks:
        left=block['left']-start
        right=block['right']-start+1
        bh=hh[left:right]
        bu=Pu[left:right]
        bp=Ph[left:right]
        lam0=scale(ch.F,block['baseline'])
        assert sum(lam0,F(0))==0
        if block['active']:
            A=block['A']
            n=block['n']
            Ck=2*(k+2)
            N=sum((dot(x,y) for x,y in zip(bh,bu)),F(0))
            D=norm2(bp)
            assert D>=ch.F*(2*n-2) and D>=ch.F*n
            assert abs(N)<=Ck*ch.F*A
            al=N/D
            bv=[vsub(x,scale(al,y)) for x,y in zip(bu,bp)]
            assert sum((dot(x,y) for x,y in zip(bh,bv)),F(0))==0
            en=al*al*D
            assert en==N*N/D and en<=Ck*Ck*ch.F*A*A/n
            repair+=en
            counts['repair_energy']+=1
            dl=[dot(hh0,vv)-l0 for hh0,vv,l0 in zip(bh,bv,lam0)]
            assert sum(dl,F(0))==0
            l1=sum((abs(vv) for vv in dl),F(0))
            assert l1<=Ck*(k+3)*ch.F*A
            hd=support(r,dl)
            assert hd<=r*F(len(dl)-1,2)*l1
            counts['repair_support']+=1
            h0=support(r,lam0)
            c0=F(k+1,2)
            exp=ch.F*(A*r*n*(n+2*k)/2-4*r*r*sum(((c0+j)**2 for j in range(n//2)),F(0)))
            assert h0==exp
            counts['local_iid_support']+=1
            hcert+=h0+hd
        else:
            bv=[[F(0)]*ch.p for _ in bu]
        v[left:right]=bv
    lam=[dot(hh0,vv) for hh0,vv in zip(hh,v)]
    assert sum(lam,F(0))==0
    counts['global_weighted_zero']+=1
    assert ch.project(v,ints,start)==v
    counts['projection_range']+=1

    rawpsi={t:[F(0)]*ch.d for t in times}
    for left,right in ints:
        Hspan,Wspan,Wdagspan,_,_,_=ch.interval(right-left+1)
        Hv=[F(0)]*ch.d
        for j,Hj in zip(range(left,right+1),Hspan):
            Hv=vadd(Hv,mv(Hj,v[j-start]))
        statecoef=mv(Wdagspan,Hv)
        rawpsi[right]=vadd(rawpsi[right],statecoef)
        if left-1>=start:
            assert left-1 in rawpsi
            rawpsi[left-1]=vsub(rawpsi[left-1],mv(tr(ch.power(right-left+1)),statecoef))
    adj=[F(0)]*ch.d
    physical_input=[[F(0)]*ch.p for _ in a]
    for j in range(start+len(a)-1,start-1,-1):
        adj=vadd(rawpsi.get(j,[F(0)]*ch.d),mv(tr(ch.A),adj))
        physical_input[j-start]=mv(tr(ch.G),adj)
    assert physical_input==v
    assert norm2(physical_input)==norm2(v)
    counts['physical_statistic_realization']+=1
    counts['full_state_score_variance']+=1
    h=support(r,lam)
    assert h<=hcert
    O=norm2(aa)/2
    LB=sum((dot(x,y) for x,y in zip(aa,v)),F(0))-norm2(v)/2-h
    loss=norm2([vsub(x,y) for x,y in zip(aa,Pa)])
    err=norm2([vsub(x,y) for x,y in zip(Pa,v)])
    assert O-LB==(loss+err+2*h)/2
    assert O-LB==norm2([vsub(x,y) for x,y in zip(aa,v)])/2+h
    counts['dual_deficit_identity']+=1
    _,_,_,beta,L1,L2=ch.interval(k+1)
    exact=F(0)
    for block in blocks:
        Ac=block['A']+eta/2
        exact+=2*beta*Ac*Ac+beta*eta*eta*F((block['n']+k)**2,2)+4*eta*Ac*L1+2*eta*eta*L2
    assert exact==loss
    counts['oracle_affine_pair_identity']+=1
    return {'model':ch.name,'k':k,'H':H,'profile':profile,'blocks':len(blocks),
            'dual_deficit_upper':str(O-LB),'weighted_zero_exact':True,'repair_energy':str(repair)}


rows=[]
for ch in channels:
    for k in [1,2]:
        for H in [32,64]:
            for profile in ['zero','linear','alternating']:
                rows.append(check_dual(ch,k,H,profile))

zero_sanity=[]
ch=next(c for c in channels if c.name=='memory_eps0')
assert ch.interval(2)[3]==0
for xi in [F(1),F(1,4),F(1,16)]:
    for H in [256,1024]:
        row=check_dual(ch,1,H,'linear',eta=F(1),r=F(2,5),xi=xi)
        root=isqrt(H)
        assert root*root==H
        rootxi=F(isqrt(xi.numerator),isqrt(xi.denominator))
        assert rootxi*rootxi==xi
        row['xi']=str(xi)
        row['fixed_xi_upper_coefficient']=str(ch.F*F(2,5)*rootxi/10)
        row['normalized_upper']=str(F(row['dual_deficit_upper'])/(H*H*root))
        row['optimal_H_5_2_coefficient']='0, via xi->0 only after H limit; not a lower-exponent claim'
        zero_sanity.append(row)

print(json.dumps({'scope':'Exact common-support low-rank physical process, full states, one scalar healthy input. Moore-Penrose checks and true input projections; no reset.',
                  'models':model_rows,'checks':counts,'penrose_matrix_checks':pinv_count,
                  'finite_dual_cases':rows,'zero_penalty_ordered_limit_sanity':zero_sanity,
                  'status':'PASS'},indent=2))
