"""Exact finite checks for a common-input, deterministic-initialization loop."""
from fractions import Fraction as F
from pathlib import Path
import json

def inverse(a):
    n = len(a)
    b = [row[:] + [F(i == j) for j in range(n)] for i, row in enumerate(a)]
    for j in range(n):
        p = next(i for i in range(j, n) if b[i][j])
        b[p], b[j] = b[j], b[p]
        scale = b[j][j]
        b[j] = [x / scale for x in b[j]]
        for i in range(n):
            if i != j:
                coeff = b[i][j]
                b[i] = [x - coeff * y for x, y in zip(b[i], b[j])]
    return [row[n:] for row in b]

def quad(v, a):
    return sum((v[i] * a[i][j] * v[j] for i in range(len(v)) for j in range(len(v))), F(0))

rows = []
H = 12
for c in [F(-1, 2), F(0), F(1, 2), F(4, 5)]:
    factor = [[c ** (i - j) if j <= i else F(0) for j in range(H)] for i in range(H)]
    mean = [sum(row, F(0)) for row in factor]
    cov = [[sum((factor[i][r] * factor[j][r] for r in range(H)), F(0)) for j in range(H)] for i in range(H)]
    full = quad(mean, inverse(cov))
    assert full == H
    for k in [0, 1, 3, 5]:
        missing = set(range(3, 3 + k))
        keep = [i for i in range(H) if i not in missing]
        kept = quad([mean[i] for i in keep], inverse([[cov[i][j] for j in keep] for i in keep]))
        m = k + 1
        Am = sum((c ** r for r in range(m)), F(0))
        Bm = sum((c ** (2 * r) for r in range(m)), F(0))
        predicted = m - Am ** 2 / Bm
        assert full - kept == predicted
        rows.append({'closed_loop_c': str(c), 'missing_k': k, 'full_quadratic_information_d1_q1': str(full), 'deficit_quadratic_information': str(predicted)})
result = {'scope': 'Known constant external input, deterministic x0=0, q=d=1. Q=2 KL. Not a nuisance-profiled schedule theorem.', 'status': 'PASS', 'exact_cases': len(rows), 'rows': rows}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'exact_cases': len(rows)}))
