from fractions import Fraction as F
import json

def inverse(a):
    n=len(a)
    b=[row[:] + [F(i==j) for j in range(n)] for i,row in enumerate(a)]
    for j in range(n):
        p=next(i for i in range(j,n) if b[i][j])
        b[p],b[j]=b[j],b[p]
        d=b[j][j]
        b[j]=[x/d for x in b[j]]
        for i in range(n):
            if i!=j:
                q=b[i][j]
                b[i]=[x-q*y for x,y in zip(b[i],b[j])]
    return [row[n:] for row in b]

rows=[]
for rho in [F(-1,2),F(0),F(1,2),F(4,5)]:
    n=16
    covariance=[[rho**abs(i-j) for j in range(n)] for i in range(n)]
    full=sum(map(sum,inverse(covariance)),F(0))
    for k in [1,3]:
        keep=[i for i in range(n) if i not in range(6,6+k)]
        retained=sum(map(sum,inverse([[covariance[i][j] for j in keep] for i in keep])),F(0))
        m=k+1
        predicted=m*(1-rho)/(1+rho)-(1-rho**m)/(1+rho**m)
        assert full-retained==predicted
        nu=(1-rho)/(1+rho)
        rows.append({'rho':str(rho),'missing_k':k,'information_deficit_coefficient':str(predicted),'effective_k':str(predicted/nu)})
print(json.dumps({'scope':'Exact known-mean AR(1) Gaussian oracle gap. Unit stationary variance. No nuisance profiling, no controller synthesis, no D2-a scan.','checks':len(rows),'rows':rows},indent=2))
