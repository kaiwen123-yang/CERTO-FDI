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



cases=[
 {'name':'scaled_copy','A':[[F(0),F(1,2)],[F(0),F(0)]],
  'G':[[F(0)],[F(1)]],'B':[F(0),F(1)],'Lz':2},
 {'name':'partial_constant','A':[[F(0),F(1),F(0)],[F(0),F(0),F(1)],[F(0),F(0),F(0)]],
  'G':[[F(0),F(0)],[F(1),F(0)],[F(0),F(1)]],'B':[F(0),F(1),F(1)],'Lz':2}
]
records=[]
for case in cases:
 A,G,B=case['A'],case['G'],case['B'];d=len(A);p=len(G[0])
 f=mv(mm(inverse(mm(tr(G),G)),tr(G)),B);Fisher=dot(f,f)
 for m in range(1,6):
  xx=[f[:] for _ in range(m)]
  px,_,_=block_project(A,G,xx,[(0,m-1)])
  beta=norm2([vsub(x,y) for x,y in zip(xx,px)])
  assert (beta==0)==(m<=case['Lz'])
 for H in [32,65,128]:
  threshold=F(6);M=F(1);s=F(1);g=[F(1)];times=[0];holds=0;moves=0
  while len(g)<=H:
   while len(g)<=H and s*M<threshold:
    g.append(s);M+=s;times.append(len(g)-1);holds+=1
   if len(g)>H:break
   remain=H-(len(g)-1)
   if remain<3:
    for _ in range(remain):
     g.append(s);M+=s;times.append(len(g)-1);holds+=1
    break
   profile=F(1,3) if s==1 else F(-2,3)
   g.append(profile);M+=profile;moves+=1;s=-s
  assert len(g)==H+1 and times[-1]==H
  cumulative=F(0);largest=F(0)
  for gj in g:
   cumulative+=gj;largest=max(largest,abs(cumulative))
  assert largest<=9
  intervals=spans(times,-1)
  singletons=sum(left==right and right>0 for left,right in intervals)
  assert singletons>=F(H,3)
  rho=F(2);eta=F(1,7);r=F(1)
  theta=[scale(F(0) if j==0 else rho+eta*j,f) for j in range(H+1)]
  h=[scale(gj,f) for gj in g]
  w,cache,power=block_project(A,G,theta,intervals)
  pp,_,_=block_project(A,G,h,intervals)
  E=norm2([vsub(x,y) for x,y in zip(theta,w)])
  assert E<=moves*eta*eta*Fisher*F(1,2)
  N=sum((dot(hj,wj) for hj,wj in zip(h,w)),F(0))
  D=norm2(pp);assert D>=Fisher*singletons
  alpha=N/D
  v=[vsub(wj,scale(alpha,pj)) for wj,pj in zip(w,pp)]
  lam=[dot(hj,vj) for hj,vj in zip(h,v)]
  assert sum(lam,F(0))==0
  vv,_,_=block_project(A,G,v,intervals);assert vv==v
  err=norm2([vsub(x,y) for x,y in zip(theta,v)])
  assert err==E+N*N/D
  hv=support(r,lam);deficitbound=err/2+hv
  raw={t:[F(0)]*d for t in times}
  for left,right in intervals:
   blocks,dag=cache[(left,right)];Hv=[F(0)]*d
   for j,hh in zip(range(left,right+1),blocks):Hv=vadd(Hv,mv(hh,v[j]))
   sc=mv(dag,Hv);raw[right]=vadd(raw[right],sc)
   if left-1>=0:raw[left-1]=vsub(raw[left-1],mv(tr(power(right-left+1)),sc))
  adj=[F(0)]*d;realized=[[F(0)]*p for _ in v]
  for j in range(H,-1,-1):
   adj=vadd(raw.get(j,[F(0)]*d),mv(tr(A),adj));realized[j]=mv(tr(G),adj)
  assert realized==v and norm2(realized)==norm2(v)
  # Legal lower witness in the zero-span late case.
  z=[r*gj/2 for gj in g]
  assert all(abs(zj-zi)<=r for zi,zj in zip(z,z[1:]))
  healthy=[scale(gj*zj,f) for gj,zj in zip(g,z)]
  ph,_,_=block_project(A,G,healthy,intervals)
  witness=E/2+sum((dot(a,b) for a,b in zip(w,ph)),F(0))-norm2(ph)/2
  assert witness>0
  records.append({'model':case['name'],'H':H,'moves':moves,
   'singleton_count':singletons,'max_cumulative_g':str(largest),
   'oracle_norm_loss':str(E),'N':str(N),'D':str(D),'alpha':str(alpha),
   'energy_error':str(err),'support':str(hv),
   'upper_deficit_over_H2':str(deficitbound/(H*H)),
   'legal_lower_witness_over_H2':str(witness/(H*H)),
   'actual_raw_statistic':True})
algebra=[]
for Lz in range(2,21):
 eps=F(1,4*Lz+2)
 bracket=eps*(1-eps)/(2*Lz)-eps*eps
 assert bracket==eps/(4*Lz) and bracket>0
 algebra.append({'Lz':Lz,'epsilon':str(eps),'bracket':str(bracket)})
print(json.dumps({'scope':'Six new balancing/global-repair calendars plus lower-coefficient algebra; inherited M2S table not rerun.',
 'calendars':records,'epsilon_checks':algebra,'status':'PASS'},indent=2))
