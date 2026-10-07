"""D2-a v1 deterministic calendar and direction utilities.

The inherited scientific source is never changed by this module. All physical
times and calendar arithmetic use integers or Fraction.
"""
from fractions import Fraction as F
import math

GRID = (40, 60, 80, 100, 120, 160, 200, 240, 300, 400, 500, 600)
PREFIX = 4
L = 250
K = 12
ETA = F(3, 40000)
B = F("0.03313047037856")
RATE = F("0.000414130879732")
XI = 2 * K * ETA / RATE

def ceil_fraction(x):
    return -((-x.numerator) // x.denominator)

def terminal(H):
    """Exact-integer version of frozen/validate_sharp.py:schedule."""
    ns, used, ell = [], 0, 1
    while True:
        n = 2 * ceil_fraction(XI * ell / 2)
        if used + 2 * (n + K) > H:
            break
        ns.append(n)
        used += 2 * (n + K)
        ell += 1
    if ns:
        quotient, remainder = divmod((H - used) // 4, len(ns))
        ns = [n + 2 * quotient + (2 if i < remainder else 0)
              for i, n in enumerate(ns)]
    nodes, tasks, blocks, offset = [], [], [], 0
    for n in ns:
        half, duration = n // 2, 2 * (n + K)
        rel = list(range(1, half + 1))
        rel += list(range(half + K + 1, 3 * half + K + 1))
        rel += list(range(3 * half + 2 * K + 1, duration + 1))
        nodes.extend(offset + j for j in rel)
        tasks.extend([1] * half + [-1] * n + [1] * half)
        blocks.append({"post_offset": offset, "n": n, "duration_slots": duration})
        offset += duration
    nodes.extend(range(offset + 1, H + 1))
    tasks.extend([1] * (H - offset))
    return nodes, tasks, blocks

def fixed(H, n):
    """Original tail suppression rule, preserved without repairing tails."""
    nodes, tasks, used, task = [], [], 0, 1
    while used < H:
        count = min(n, H - used)
        nodes.extend(range(used + 1, used + count + 1))
        tasks.extend([task] * count)
        used += count
        if H - used <= K:
            nodes.extend(range(used + 1, H + 1))
            tasks.extend([task] * (H - used))
            break
        used += K
        task = -task
    return nodes, tasks, []

def calendar(H, family, stage_endpoint=None):
    assert H in GRID
    if family == "stay":
        post, tasks, blocks = list(range(1, H + 1)), [1] * H, []
    elif family.startswith("fixed"):
        n = int(family[5:])
        assert n in (20, 40, 76)
        post, tasks, blocks = fixed(H, n)
    elif family == "terminal_balanced":
        post, tasks, blocks = terminal(H)
    elif family == "switch_then_stay":
        assert stage_endpoint in range(20, H + 1, 20)
        post, tasks, blocks = terminal(stage_endpoint)
        post += list(range(stage_endpoint + 1, H + 1))
        tasks += [1] * (H - stage_endpoint)
    else:
        raise ValueError(family)
    relative_nodes = list(range(1 - PREFIX, 1)) + post
    all_tasks = [1] * PREFIX + tasks
    slots = [j + PREFIX - 1 for j in relative_nodes]
    missing = sorted(set(range(H + PREFIX)) - set(slots))
    gaps = []
    for slot in missing:
        if not gaps or slot != gaps[-1][-1] + 1:
            gaps.append([slot])
        else:
            gaps[-1].append(slot)
    errors = []
    if any(len(gap) != K for gap in gaps):
        errors.append("GAP_NOT_K_SLOTS")
    moves = [(gap[0] * L, gap[0] * L + 1500) for gap in gaps]
    for index, (start, stop) in enumerate(moves):
        if index == 0 and start < 1750:
            errors.append("SOURCE_HOLD_BEFORE_FIRST_MOVE_LT_1750")
        if index and start - moves[index - 1][1] < 1750:
            errors.append("POSTARRIVAL_HOLD_BEFORE_REMOVE_LT_1750")
    observations = []
    for node, slot, task in zip(relative_nodes, slots, all_tasks):
        completed = [(a, b) for a, b in moves if b <= slot * L]
        arrival = completed[-1][1] if completed else 0
        start, point, availability = slot * L, (slot + 1) * L - 1, (slot + 1) * L
        source = not completed
        if not source and start - arrival < 1500:
            errors.append("READ_BEFORE_1500_SETTLE_STEPS")
        observations.append({
            "relative_node": node, "slot_zero_based": slot, "task": task,
            "source_segment": source, "hold_start_age_steps": start - arrival,
            "point_hold_age_steps": point - arrival,
            "average_indices": [start, availability],
            "point_index": point, "point_sample_time_s": str(F(point, 1000)),
            "available_time_s": str(F(availability, 1000)),
            "sample_average_time_s": str(F(2 * start + L - 1, 2000)),
            "continuous_slot_midpoint_s": str(F(2 * slot + 1, 8)),
        })
    assert slots == sorted(set(slots))
    return {"H_post_slots": H, "family": family, "stage_endpoint": stage_endpoint,
            "T_fast_steps": (H + PREFIX) * L, "prefix_slots": PREFIX,
            "moves": [list(x) for x in moves], "observations": observations,
            "completed_symmetric_blocks": len(blocks), "blocks": blocks,
            "validation_errors": sorted(set(errors)),
            "physical_contract_validated": not errors,
            "elapsed_seconds": str(F(H + PREFIX, 4)),
            "postfault_horizon_seconds": str(F(H, 4))}

def all_members():
    for H in GRID:
        for family in ("stay", "fixed20", "fixed40", "fixed76", "terminal_balanced"):
            yield calendar(H, family)
        for endpoint in range(20, H + 1, 20):
            yield calendar(H, "switch_then_stay", endpoint)

def sqrt_upper(x, digits=18):
    x = F(x)
    assert x >= 0
    scale = 10 ** digits
    numerator = math.isqrt(x.numerator * scale * scale // x.denominator)
    if numerator * numerator * x.denominator < x.numerator * scale * scale:
        numerator += 1
    answer = F(numerator, scale)
    assert answer * answer >= x
    return answer

def normalize_raw(raw, tasks):
    """Rational near-unit physical direction; zero moments are preserved only
    when the exact projected residual has zero moment.
    """
    raw = list(map(F, raw))
    if not any(raw):
        return None
    scale = 10 ** 12
    rounded = [round(x * scale) for x in raw]
    if not any(rounded):
        return None
    preserve_zero = sum(raw) == 0
    if preserve_zero:
        last = max(i for i, x in enumerate(rounded) if x)
        rounded[last] -= sum(rounded)
    rational = [F(x, scale) for x in rounded]
    norm = sqrt_upper(sum((x * x for x in rational), F(0)))
    if not norm:
        return None
    signed = [x / norm for x in rational]
    physical = [task * x for task, x in zip(tasks, signed)]
    return {"raw": raw, "rounded": rational, "normalizer": norm,
            "signed": signed, "physical": physical,
            "raw_norm_squared": sum((x*x for x in raw), F(0)),
            "direction_norm_squared": sum((x*x for x in physical), F(0)),
            "exact_zero_moment_preserved": preserve_zero,
            "rounding_l1": sum((abs(a-b) for a,b in zip(raw,rational)), F(0))}
