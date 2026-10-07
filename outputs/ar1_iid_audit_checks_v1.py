"""Independent exact checks of local iid projection support and loss factors."""
from fractions import Fraction as F
import json

rows = 0
for k in range(1, 7):
    for n in range(2, 26, 2):
        m = n//2
        L = 2*(n+k)
        c = F(L+1, 2)
        times = list(range(1, m+1))+list(range(m+k+1, 3*m+k+1))+list(range(3*m+2*k+1, L+1))
        signs = [1]*m+[-1]*n+[1]*m
        for r in [F(1, 7), F(2, 3)]:
            c0 = F(k+1, 2)
            for margin in [F(0), F(1, 3), F(100)]:
                a = r*F(k+n-1, 2)+margin
                z = [r*(c0+m-i) for i in range(1, m+1)]
                z += [-r*(c0+min(i-1, n-i)) for i in range(1, n+1)]
                z += [r*(c0+i-1) for i in range(1, m+1)]
                w = [a*s-v for s,v in zip(signs,z)]
                assert sum(w, F(0)) == 0
                Q = F(0)
                support = F(0)
                for j in range(len(w)-1):
                    Q += w[j]
                    dt = times[j+1]-times[j]
                    assert abs(z[j+1]-z[j]) <= r*dt
                    support += r*dt*abs(Q)
                    if Q:
                        assert z[j+1]-z[j] == -r*dt*(1 if Q > 0 else -1)
                assert support == sum((u*v for u,v in zip(w,z)), F(0))
                normw = sum((v*v for v in w), F(0))
                loss = a*r*n*(n+2*k)-4*r*r*sum(((c0+j)**2 for j in range(m)), F(0))
                assert 2*n*a*a-normw == loss
                assert sum((u*s*(t-c) for u,s,t in zip(w,signs,times)), F(0)) == 0
                eta = F(3, 11)
                target = [s*(a+eta*(t-c)) for s,t in zip(signs,times)]
                assert sum((u*v for u,v in zip(w,target)), F(0)) == sum((u*a*s for u,s in zip(w,signs)), F(0))
                assert sum((v*v for v in target), F(0)) == 2*n*a*a+eta*eta*sum(((t-c)**2 for t in times), F(0))
                rows += 1
print(json.dumps({'scope':'Independent local iid exact KKT/support/affine/Lc checks. No historical MC or whole sharp asymptotic execution.',
                  'exact_cases':rows,'status':'PASS'},indent=2))
