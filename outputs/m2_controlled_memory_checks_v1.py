"""Exact fixed-order full-state/common-scalar-input checks for M2.
Standard library only. Initialized output covariance is compared to genuine span projections.
"""
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


models=[]
L2=[[F(1),F(0)],[F(1,3),F(2,3)]]
B2=[F(1),F(2)]
A2s=[
    ('zero2',[[F(0),F(0)],[F(0),F(0)]],F(1)),
    ('diagonal2',[[F(1,2),F(0)],[F(0),F(1,4)]],F(2)),
    ('nonnormal2',[[F(1,2),F(2)],[F(0),F(1,4)]],F(18)),
    ('rotation2',[[F(1,5),F(3,5)],[F(-2,5),F(3,10)]],F(10))
]
for name,A,mult in A2s:
    models.append({'name':name,'A':A,'L':L2,'B':B2,'sum_norm_multiplier':mult})
L3=[[F(1),F(0),F(0)],[F(1,3),F(2,3),F(0)],[F(0),F(1,5),F(3,4)]]
models.append({'name':'jordan3','A':[[F(1,2),F(1),F(0)],[F(0),F(1,2),F(1)],[F(0),F(0),F(1,2)]],
               'L':L3,'B':[F(1),F(-1),F(1,2)],'sum_norm_multiplier':F(14)})


class Channel:
    def __init__(self,model):
        self.model=model
        self.name=model['name']
        self.A=model['A']
        self.L=model['L']
        self.B=model['B']
        self.d=len(self.B)
        self.Q=mm(self.L,tr(self.L))
        self.Qinv=inverse(self.Q)
        self.f=mv(inverse(self.L),self.B)
        self.F=dot(self.f,self.f)
        self.powers=[eye(self.d)]
        self.cache={}
        self.Sbound=model['sum_norm_multiplier']*sum((abs(v) for v in self.B),F(0))
        self.Ccross=max(sum((abs(x) for x in row),F(0)) for row in self.Qinv)*self.Sbound**2

    def power(self,r):
        while len(self.powers)<=r:
            self.powers.append(mm(self.powers[-1],self.A))
        return self.powers[r]

    def interval(self,m):
        if m not in self.cache:
            blocks=[mm(self.power(m-j-1),self.L) for j in range(m)]
            W=[[F(0)]*self.d for _ in range(self.d)]
            for H in blocks:
                W=add(W,mm(H,tr(H)))
            Winv=inverse(W)
            M=[F(0)]*self.d
            N=[F(0)]*self.d
            for j in range(m):
                AB=mv(self.power(m-j-1),self.B)
                M=vadd(M,AB)
                N=vadd(N,scale(F(2*(j+1)-m-1,2),AB))
            beta=m*self.F-dot(M,mv(Winv,M))
            L1=-dot(M,mv(Winv,N))
            L2=self.F*sum((F(2*(j+1)-m-1,2)**2 for j in range(m)),F(0))-dot(N,mv(Winv,N))
            self.cache[m]=(blocks,W,Winv,beta,L1,L2)
        return self.cache[m]

    def project(self,x,intervals,start):
        out=[[F(0)]*self.d for _ in x]
        for left,right in intervals:
            m=right-left+1
            if m==1:
                out[left-start]=x[left-start][:]
                continue
            blocks,W,Winv,_,_,_=self.interval(m)
            val=[F(0)]*self.d
            for j,H in zip(range(left,right+1),blocks):
                val=vadd(val,mv(H,x[j-start]))
            v=mv(Winv,val)
            for j,H in zip(range(left,right+1),blocks):
                out[j-start]=mv(tr(H),v)
        return out


channels=[Channel(m) for m in models]
counts={'initialized_covariance_vs_projection':0,'full_control_neutrality':0,
        'beta_positive_monotone':0,'affine_center_bound':0,
        'global_weighted_zero':0,'projection_range':0,'dual_deficit_identity':0,
        'repair_energy':0,'repair_support':0,'oracle_affine_pair_identity':0,
        'local_iid_support':0,'singular_Q_boundary':0}
model_rows=[]

for ch in channels:
    prev=F(0)
    for m in range(2,34):
        _,_,_,beta,L1,L2=ch.interval(m)
        assert beta>0 and beta>=prev
        prev=beta
        counts['beta_positive_monotone']+=1
        assert L2>=0
        assert abs(L1)<=F(m,2)*ch.Ccross
        AA=F(100)
        eta=F(1,7)
        exact=beta*AA*AA+2*eta*AA*L1+eta*eta*L2
        assert exact>=beta*AA*AA-ch.Ccross*eta*AA*m
        counts['affine_center_bound']+=1
    for n in range(1,5):
        times=list(range(1,n+1))
        theta=[F((j*j+3*j)%11-5,7) for j in times]
        inp=[scale(a,ch.f) for a in theta]
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
            inv=inverse(full_cov)
            mu=flat([states[i-1] for i in kept])
            exact=dot(mu,mv(inv,mu)) if mu else F(0)
            assert exact==norm2(proj)
            counts['initialized_covariance_vs_projection']+=1
        assert ch.project(inp,spans(times,0),1)==inp
        counts['full_control_neutrality']+=1
    model_rows.append({'model':ch.name,'dimension':ch.d,'F':str(ch.F),
                       'beta_k1':str(ch.interval(2)[3]),'beta_k2':str(ch.interval(3)[3]),
                       'sum_norm_bound':str(ch.Sbound)})


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
        xi=2*beta*eta/(ch.F*r)
    start,a,g,aux,times,blocks=calendar(H,xi,k,eta,r,profile)
    ints=spans(times,start-1)
    aa=[scale(v,ch.f) for v in a]
    hh=[scale(v,ch.f) for v in g]
    uu=[scale(v,ch.f) for v in aux]
    Pu=ch.project(uu,ints,start)
    Ph=ch.project(hh,ints,start)
    Pa=ch.project(aa,ints,start)
    v=[[F(0)]*ch.d for _ in a]
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
            bv=[[F(0)]*ch.d for _ in bu]
        v[left:right]=bv
    lam=[dot(hh0,vv) for hh0,vv in zip(hh,v)]
    assert sum(lam,F(0))==0
    counts['global_weighted_zero']+=1
    assert ch.project(v,ints,start)==v
    counts['projection_range']+=1
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
larger=[]
for ch in channels[1:]:
    beta=ch.interval(2)[3]
    for H in [256,1024]:
        row=check_dual(ch,1,H,'linear',eta=F(1),r=2*beta/ch.F,xi=F(1))
        root=isqrt(H)
        assert root*root==H
        row['normalized_upper']=str(F(row['dual_deficit_upper'])/(H*H*root))
        row['candidate_coefficient']=str(2*beta/5)
        larger.append(row)

# Boundary of Q positive definiteness: a stable shift register with rank-one noise.
# x_j=(v_{j-1},v_j), v_j=a_j+g_jb_j+xi_j. One retained x_2 recovers both innovations.
A=[[F(0),F(1)],[F(0),F(0)]]
B=[F(0),F(1)]
Q=[[F(0),F(0)],[F(0),F(1)]]
AB=mv(A,B)
W=add(Q,mm(mm(A,Q),tr(A)))
M=vadd(B,AB)
assert W==eye(2)
assert dot(M,mv(inverse(W),M))==2
counts['singular_Q_boundary']+=1

print(json.dumps({'scope':'Exact full-state fixed-order initialized plant with common scalar B input and SPD Q. No vector nuisance, no reset; universal proof separate.',
                  'models':model_rows,'checks':counts,'finite_dual_cases':rows,
                  'larger_parameter_normalized_sanity':larger,
                  'singular_Q_boundary':'Stable shift register with rank-one innovation recovers both scalar inputs at one retained vector; gap loss zero, outside SPD-Q theorem.',
                  'status':'PASS'},indent=2))

