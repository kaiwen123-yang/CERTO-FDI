"""Exact-rational support for ar1_information_lemmas_v1.md; no external deps."""
from fractions import Fraction as F
import json


def inverse(a):
    n = len(a)
    b = [row[:] + [F(i == j) for j in range(n)] for i, row in enumerate(a)]
    for j in range(n):
        p = next(i for i in range(j, n) if b[i][j])
        b[p], b[j] = b[j], b[p]
        d = b[j][j]
        b[j] = [x / d for x in b[j]]
        for i in range(n):
            if i != j:
                c = b[i][j]
                b[i] = [x - c * y for x, y in zip(b[i], b[j])]
    return [row[n:] for row in b]


def energy_matrix(rho, times, x):
    q = inverse([[rho ** abs(i - j) for j in times] for i in times])
    return sum((x[i] * q[i][j] * x[j] for i in range(len(x)) for j in range(len(x))), F(0))


def energy_markov(rho, times, x):
    if not times:
        return F(0)
    return x[0] ** 2 + sum(((x[j] - rho ** (times[j] - times[j-1]) * x[j-1]) ** 2 /
                           (1 - rho ** (2 * (times[j] - times[j-1]))) for j in range(1, len(x))), F(0))


def w(rho, m):
    return (1 - rho ** m) / (1 + rho ** m)


def beta(rho, k):
    return (k + 1) * w(rho, 1) - w(rho, k + 1)


def block_energy(rho, times, x):
    if not times:
        return F(0)
    nu = w(rho, 1)
    c = rho / (1 + rho)
    d = rho / (1 - rho * rho)
    value = nu * sum((v*v for v in x), F(0)) + c * (x[0]**2 + x[-1]**2)
    for j in range(1, len(x)):
        m = times[j] - times[j-1]
        u, v = x[j-1], x[j]
        if m == 1:
            value += d * (v-u)**2
        else:
            rm = rho**m
            am = 1/(1-rm**2) - 1/(1+rho)
            value += am*(u*u+v*v) - 2*rm*u*v/(1-rm**2)
    return value


checks = {'markov_vs_matrix': 0, 'constant_multigap': 0, 'block_identity': 0,
          'smooth_gap_bound': 0, 'jump_counterexample': 0,
          'raw_full_class_bridge': 0, 'affine_reflection': 0}
rows = []
for rho in [F(-4, 5), F(-1, 2), F(0), F(1, 2), F(4, 5)]:
    for n in range(1, 9):
        full_times = list(range(n))
        full_const = energy_markov(rho, full_times, [F(1)]*n)
        for mask in range(1 << n):
            times = [i for i in full_times if mask & (1 << i)]
            x = [F((i*i + 3*i) % 7 - 3, 3) for i in times]
            qm = energy_markov(rho, times, x)
            assert qm == energy_matrix(rho, times, x)
            checks['markov_vs_matrix'] += 1
            assert qm == block_energy(rho, times, x)
            checks['block_identity'] += 1
            if times:
                expected_loss = (times[0] + n-1-times[-1])*w(rho, 1)
                expected_loss += sum((beta(rho, times[j]-times[j-1]-1) for j in range(1, len(times))), F(0))
            else:
                expected_loss = full_const
            loss = full_const-energy_markov(rho, times, [F(1)]*len(times))
            assert loss == expected_loss
            assert loss >= 0
            checks['constant_multigap'] += 1
            a_raw = [F(i, 7) for i in full_times]
            z_raw = [F(100)+F(i % 3, 5) for i in full_times]
            signs = [(-1)**(i//2) for i in full_times]
            xr = [a_raw[i]-signs[i]*z_raw[i] for i in times]
            actual = energy_markov(rho, times, xr)
            if times:
                c = rho/(1+rho)
                d = rho/(1-rho*rho)
                surrogate = w(rho, 1)*sum((v*v for v in xr), F(0))+c*(xr[0]**2+xr[-1]**2)
                remainder = F(0)
                for j in range(1, len(times)):
                    left, right = times[j-1], times[j]
                    m = right-left
                    u, v = xr[j-1], xr[j]
                    if m == 1 and signs[left] == signs[right]:
                        remainder += d*(v-u)**2
                    else:
                        rm = rho**m
                        am = 1/(1-rm*rm)-1/(1+rho)
                        surrogate += am*(u*u+v*v)-2*rm*u*v/(1-rm*rm)
                assert actual-surrogate == remainder
                assert abs(remainder) <= abs(d)*(n-1)*(F(1, 7)+F(2, 5))**2
            else:
                assert actual == 0
            checks['raw_full_class_bridge'] += 1
    for k in range(0, 7):
        m = k+1
        assert beta(rho, k) >= 0
        assert (beta(rho, k) == 0) == (k == 0)
        # Avoid radicals: |cross| <= sqrt(beta*D), then expand square.
        a = F(7, 3)
        delta = [F(j, 5) for j in range(m+1)]
        full = list(range(m+1))
        endpoints = [0, m]
        if m == 1:
            endpoints = full
        def gap(v):
            return energy_markov(rho, full, v)-energy_markov(rho, endpoints, [v[j] for j in endpoints])
        b = beta(rho, k)
        gd = gap(delta)
        C = (1+abs(rho))/(1-abs(rho))
        D = C*F(1, 25)*sum(j*j for j in range(m+1))
        cross = (gap([F(1)+v for v in delta])-b-gd)/2
        assert 0 <= gd <= D
        assert cross*cross <= b*D
        assert gap([a+v for v in delta]) == a*a*b+2*a*cross+gd
        checks['smooth_gap_bound'] += 1
        centered = [F(2*j-m, 2) for j in range(m+1)]
        affine = [a+F(2, 7)*v for v in centered]
        E = gap(centered)
        assert E >= 0
        assert gap(affine) == a*a*b+F(4, 49)*E
        checks['affine_reflection'] += 1

# Legal full-history z=H, a=0, raw x=-s*z. Missing sample retains old task.
rho = F(1, 2)
for H in [16, 64, 256]:
    J = int(H**0.5)
    # Horizon and amplitude both H; separated internal gaps; J=sqrt(H).
    full_times = list(range(H))
    missing = {((j+1)*H)//(J+1) for j in range(J)}
    x = [F(((-1)**sum(i > g for g in missing))*H) for i in full_times]
    keep = [i for i in full_times if i not in missing]
    loss = energy_markov(rho, full_times, x)-energy_markov(rho, keep, [x[i] for i in keep])
    wrong_constant_loss = J*beta(rho, 1)*H*H
    expected = J*F(5, 3)*H*H
    assert loss == expected
    assert loss-wrong_constant_loss == J*F(8, 5)*H*H
    checks['jump_counterexample'] += 1
    rows.append({'horizon_and_amplitude_H': H, 'gaps_J': J, 'raw_quadratic_loss': str(loss),
                 'wrong_constant_gap_loss': str(wrong_constant_loss),
                 'quadratic_error': str(loss-wrong_constant_loss),
                 'KL_error': str((loss-wrong_constant_loss)/2)})

report = {'scope': 'Exact rational finite checks; equations use squared Mahalanobis Q, KL=Q/2. No proof of minimax sharp coefficient.',
          'checks': checks, 'counterexample_rows': rows}
print(json.dumps(report, ensure_ascii=False, indent=2))
