"""Small exact support for independent colored converse review."""
from fractions import Fraction as F
import json


def coeff(rho, ell):
    nu = (1-rho)/(1+rho)
    m = ell+1
    beta = m*nu-(1-rho**m)/(1+rho**m)
    return nu, beta


checks = {'beta_ratio_identity': 0, 'beta_monotone': 0,
          'finite_tail_bstar_certificate': 0, 'convex_split_absorption': 0,
          'm_positive_amgm': 0, 'm_zero': 0}
certificates = []
for rho in [F(-4,5), F(-1,2), F(0), F(1,2), F(4,5)]:
    nu = (1-rho)/(1+rho)
    Cnorm = (1+abs(rho))/(1-abs(rho))
    # beta/l >= nu-Cnorm/l >= nu/2 for l >= ceil(2*Cnorm/nu).
    ratio = 2*Cnorm/nu
    cutoff = max(1, (ratio.numerator+ratio.denominator-1)//ratio.denominator)
    finite = [coeff(rho, ell)[1]/ell for ell in range(1, cutoff)]
    bstar_lower = min([nu/2]+finite)
    assert bstar_lower > 0
    certificates.append({'rho':str(rho),'tail_cutoff':cutoff,'certified_bstar_lower':str(bstar_lower)})
    prev = F(0)
    for ell in range(1, max(65, cutoff+2)):
        m = ell+1
        nu, beta = coeff(rho, ell)
        Am = sum((rho**j for j in range(m)), F(0))
        Bm = sum((rho**(2*j) for j in range(m)), F(0))
        assert beta/nu == m-Am*Am/Bm
        assert beta > 0
        checks['beta_ratio_identity'] += 1
        assert beta >= prev
        prev = beta
        checks['beta_monotone'] += 1
        if ell >= cutoff:
            assert beta/ell >= nu/2
        assert beta/ell >= bstar_lower
        checks['finite_tail_bstar_certificate'] += 1
    theta = F(1,7)
    r = F(1,3)
    A = F(1000000)
    _, beta = coeff(rho, 1)
    W = (1-theta)*beta
    for L in [3, 10, 30]:
        C = r*(2*A-r*L/2)/4
        assert C > 0
        # Equivalent squared absorption condition, all terms nonnegative.
        assert (theta*bstar_lower*A*A/4)**2 >= 4*A*A*nu*C*W
        checks['convex_split_absorption'] += 1
        for d in range(L+1):
            if d == L:
                assert theta*bstar_lower*A*A*d/4 >= 0
                checks['m_zero'] += 1
                continue
            for m in range(1, L-d+1):
                left = nu*C*F((L-d)**2,m)+W*A*A*m
                assert left*left >= 4*A*A*nu*C*W*(L-d)**2
                checks['m_positive_amgm'] += 1

print(json.dumps({'scope':'Exact small algebra support; theorem universality follows from proofs, not this finite check.',
                  'checks':checks,'bstar_certificates':certificates,'status':'PASS'},indent=2))
