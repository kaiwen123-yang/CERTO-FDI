"""Exact controller/settling comparisons for the common-input one-gap toy.

Python standard library only. The proof of general monotonicity, boundary
growth, and plateau reduction is in controller_settling_tradeoff_v1.md.
These checks do not prove a drift-profiled sharp theorem or nonlinear return.
"""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import math


def minimum_settle(c, alpha):
    """Minimal positive integer s with c**s <= alpha, without log rounding."""
    c, alpha = F(c), F(alpha)
    assert 0 < c < 1 and 0 < alpha < 1
    lo, hi = 0, 1
    while c ** hi > alpha:
        lo, hi = hi, 2 * hi
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if c ** mid <= alpha:
            hi = mid
        else:
            lo = mid
    assert c ** hi <= alpha < c ** (hi - 1)
    return hi


def gap_coefficient(c, k):
    c = F(c)
    assert c >= 0 and isinstance(k, int) and k >= 0
    m = k + 1
    a = sum((c ** j for j in range(m)), F(0))
    b = sum((c ** (2 * j) for j in range(m)), F(0))
    return F(m) - a * a / b


def gap_closed(c, k):
    c = F(c)
    assert 0 <= c < 1
    m = k + 1
    return F(m) - (1 + c) * (1 - c ** m) / ((1 - c) * (1 + c ** m))


def inverse(a):
    n = len(a)
    augmented = [row[:] + [F(i == j) for j in range(n)] for i, row in enumerate(a)]
    for col in range(n):
        pivot = next(i for i in range(col, n) if augmented[i][col])
        augmented[pivot], augmented[col] = augmented[col], augmented[pivot]
        scale = augmented[col][col]
        augmented[col] = [x / scale for x in augmented[col]]
        for row in range(n):
            if row != col:
                multiplier = augmented[row][col]
                augmented[row] = [x - multiplier * y for x, y in zip(augmented[row], augmented[col])]
    return [row[n:] for row in augmented]


def quadratic(v, a):
    return sum((v[i] * a[i][j] * v[j] for i in range(len(v)) for j in range(len(v))), F(0))


def physical_information_check(c, k, horizon=12, left_endpoint=2):
    """Independent dense marginal covariance: x0=0, external d=q=1.

    Delete x_(ell+1),...,x_(ell+k), retaining x_ell and x_(ell+k+1).
    No noise or controller state resets occur at the missing interval.
    """
    c = F(c)
    assert left_endpoint >= 1 and left_endpoint + k + 1 <= horizon
    factor = [[c ** (i - j) if i >= j else F(0) for j in range(horizon)] for i in range(horizon)]
    mean = [sum(row, F(0)) for row in factor]
    covariance = [[sum((factor[i][r] * factor[j][r] for r in range(horizon)), F(0)) for j in range(horizon)] for i in range(horizon)]
    full = quadratic(mean, inverse(covariance)) / 2
    missing = set(range(left_endpoint, left_endpoint + k))
    keep = [i for i in range(horizon) if i not in missing]
    marginal = [[covariance[i][j] for j in keep] for i in keep]
    observed = quadratic([mean[i] for i in keep], inverse(marginal)) / 2
    loss = full - observed
    assert full == F(horizon, 2)
    assert loss == gap_coefficient(c, k) / 2
    return {
        'horizon': horizon, 'retained_left_endpoint': left_endpoint,
        'missing_observation_indices_1based': sorted(i + 1 for i in missing),
        'full_KL_d1_q1': str(full), 'observed_KL_d1_q1': str(observed),
        'loss_KL_d1_q1': str(loss), 'dense_covariance_matches_gap_formula': True,
    }


def nth_root_floor(n, power):
    lo, hi = 0, max(1, n) + 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if mid ** power <= n:
            lo = mid
        else:
            hi = mid
    return lo


def root_bracket(alpha, power, bits=100):
    """Exact rational root or a certified dyadic isolating interval."""
    alpha = F(alpha)
    numerator = nth_root_floor(alpha.numerator, power)
    denominator = nth_root_floor(alpha.denominator, power)
    if numerator ** power == alpha.numerator and denominator ** power == alpha.denominator:
        root = F(numerator, denominator)
        return root, root
    lo, hi = F(0), F(1)
    for _ in range(bits):
        mid = (lo + hi) / 2
        if mid ** power <= alpha:
            lo = mid
        else:
            hi = mid
    assert lo ** power <= alpha <= hi ** power
    return lo, hi


def compact_candidates(alpha, low, high, move_slots):
    alpha, low, high = F(alpha), F(low), F(high)
    assert 0 < low <= high < 1 and isinstance(move_slots, int) and move_slots >= 0
    last = minimum_settle(high, alpha)
    rows = []
    for s in range(1, last + 1):
        # c_s=alpha**(1/s); inclusion tested without approximating roots.
        if low ** s <= alpha <= high ** s:
            lo, hi = root_bracket(alpha, s)
            k = move_slots + s
            value_lo, value_hi = gap_coefficient(hi, k), gap_coefficient(lo, k)
            assert value_lo <= value_hi
            rows.append({
                'label': f'c_{s}', 'settle_steps_at_root': s, 'missing_k': k,
                'controller_c_lower': str(lo), 'controller_c_upper': str(hi),
                'root_equation': f'c^{s}={alpha}', 'root_is_rational': lo == hi,
                'kappa_lower': str(value_lo), 'kappa_upper': str(value_hi),
                'display_c': float((lo + hi) / 2), 'display_kappa': float((value_lo + value_hi) / 2),
            })
    s = minimum_settle(high, alpha)
    value = gap_coefficient(high, move_slots + s)
    rows.append({
        'label': 'closed_upper_endpoint', 'settle_steps_at_root': s, 'missing_k': move_slots + s,
        'controller_c_lower': str(high), 'controller_c_upper': str(high),
        'root_equation': None, 'root_is_rational': True,
        'kappa_lower': str(value), 'kappa_upper': str(value),
        'display_c': float(high), 'display_kappa': float(value),
    })
    return rows


def run():
    alpha, move_slots = F(81, 100), 0
    family = [F(4, 5), F(9, 10), F(19, 20)]
    finite = []
    for c in family:
        s = minimum_settle(c, alpha)
        k = move_slots + s
        coefficient = gap_coefficient(c, k)
        assert coefficient == gap_closed(c, k)
        finite.append({
            'lambda': '1', 'closed_loop_c': str(c), 'feedback_K': str(1 - c),
            'move_slots': move_slots, 'settle_steps': s, 'missing_k': k,
            'settled_error_ratio': str(c ** s), 'previous_error_ratio': str(c ** (s - 1)),
            'settle_minimal_exact': c ** s <= alpha < c ** (s - 1),
            'kappa': str(coefficient), 'kappa_display': float(coefficient),
            'physical_covariance_check': physical_information_check(c, k),
        })
    assert [r['settle_steps'] for r in finite] == [1, 2, 5]
    best = min(finite, key=lambda row: F(row['kappa']))
    assert best['closed_loop_c'] == '9/10'
    strict_comparisons = [{
        'other_c': row['closed_loop_c'],
        'kappa_other_minus_best': str(F(row['kappa']) - F(best['kappa'])),
        'strictly_positive': F(row['kappa']) > F(best['kappa']),
    } for row in finite if row is not best]
    assert all(row['strictly_positive'] for row in strict_comparisons)

    monotone_checks = 0
    for k in [1, 2, 3, 5, 8]:
        grid = [F(j, 20) for j in range(20)]
        values = [gap_coefficient(c, k) for c in grid]
        assert all(a > b for a, b in zip(values, values[1:]))
        for c in grid:
            assert gap_coefficient(c, k) == gap_closed(c, k)
            m = k + 1
            aa = sum((c ** j for j in range(m)), F(0))
            bb = sum((c ** (2 * j) for j in range(m)), F(0))
            increment = (bb - aa * c ** m) ** 2 / (bb * (bb + c ** (2 * m)))
            assert gap_coefficient(c, k + 1) - gap_coefficient(c, k) == increment > 0
            monotone_checks += 1

    candidates = compact_candidates(alpha, F(4, 5), F(19, 20), move_slots)
    optimum = next(row for row in candidates if row['label'] == 'c_1')
    best_value = F(optimum['kappa_lower'])
    assert optimum['kappa_lower'] == optimum['kappa_upper'] == '361/16561'
    assert all(F(row['kappa_lower']) > best_value for row in candidates if row is not optimum)
    global_margins = [{
        'other_label': row['label'],
        'certified_lower_margin_over_c1': str(F(row['kappa_lower']) - best_value),
    } for row in candidates if row is not optimum]

    length = -math.log(float(alpha))
    asymptotic_constant = length - 2 * math.tanh(length / 2)
    boundary = []
    for scale in [20, 100, 200, 1000, 5000]:
        c = F(scale - 1, scale)
        s = minimum_settle(c, alpha)
        coefficient = gap_closed(c, move_slots + s)
        log_decay = -math.log(float(c))
        boundary.append({
            'c': str(c), 'settle_steps': s, 'missing_k': move_slots + s,
            'kappa_display': float(coefficient),
            'minus_log_c_times_kappa_display': log_decay * float(coefficient),
            'minus_log_c_times_settle_display': log_decay * s,
            'fits_horizon12_internal_gap_at_ell2': 2 + move_slots + s + 1 <= 12,
            'boundary_diagnostic_only': True,
            'outside_compact_design_family': c > F(19, 20),
        })

    result = {
        'status': 'PASS_EXACT_FINITE_CHECKS_AND_CERTIFIED_COMPACT_EXAMPLE',
        'scope': 'Known constant external input, common plant lambda1, d=q=1 and x0=0. Exact one-gap information. Homogeneous recovery is an admissibility contract, not a noisy/nonlinear return guarantee. No M1 drift-sharp claim.',
        'recovery_ratio': str(alpha), 'homogeneous_initial_bound_E': '1', 'homogeneous_tolerance_epsilon': str(alpha),
        'move_slots_fixed': move_slots, 'finite_family': finite,
        'finite_family_best_c': best['closed_loop_c'], 'finite_family_strict_comparisons': strict_comparisons,
        'fixed_k_rational_diagnostics_count': monotone_checks,
        'all_nonnegative_c_monotonicity_false_outside_stable_interval': {
            'k': 1, 'kappa_c1': str(gap_coefficient(F(1), 1)), 'kappa_c2': str(gap_coefficient(F(2), 1)),
        },
        'compact_interval': ['4/5', '19/20'], 'compact_candidates': candidates,
        'compact_global_optimum_c': '81/100', 'compact_global_optimum_kappa': str(best_value),
        'compact_strict_comparison_certificates': global_margins,
        'near_unit_boundary': {
            'L_display': length, 'limit_constant_display': asymptotic_constant,
            'exact_symbolic_limit': '(-log c)*kappa(c,k(c)) -> L-2*tanh(L/2)>0, L=-log(alpha)',
            'proof_not_inferred_from_numeric_sequence': True, 'rows': boundary,
        },
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    output = Path(__file__).with_suffix('.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': result['status'], 'finite_best_c': result['finite_family_best_c'],
        'compact_global_optimum_c': result['compact_global_optimum_c'],
        'compact_candidates': len(candidates), 'exact_physical_covariance_cases': len(finite),
        'rational_diagnostic_checks': monotone_checks,
    }))


if __name__ == '__main__':
    run()
