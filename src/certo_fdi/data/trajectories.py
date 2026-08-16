"""Healthy reference-trajectory families with analytic derivatives (joint space)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from certo_fdi.data.schema import OTHER_JOINT_CENTER_RANGES, REGIONS


@dataclass
class Trajectory:
    family: str
    q: np.ndarray  # (T,n)
    qd: np.ndarray
    qdd: np.ndarray
    center: np.ndarray
    meta: dict


def sample_center(rng: np.random.Generator, region_id: int, n: int = 7) -> np.ndarray:
    reg = REGIONS[region_id]
    c = np.zeros(n)
    c[0] = rng.uniform(*reg["q1"])
    c[1] = rng.uniform(*reg["q2"])
    for j, (lo, hi) in OTHER_JOINT_CENTER_RANGES.items():
        c[j] = rng.uniform(lo, hi)
    return c


def _clip_amplitudes(center: np.ndarray, amp: np.ndarray, lower: np.ndarray, upper: np.ndarray, margin: float = 0.08) -> np.ndarray:
    room = np.minimum(center - (lower + margin), (upper - margin) - center)
    return np.minimum(amp, np.maximum(room, 0.02))


def multisine(t: np.ndarray, center: np.ndarray, rng: np.random.Generator, speed_scale: float, lower, upper, velocity_limit, *, harmonics: int = 3, base_freq_range=(0.08, 0.16), periodic: bool = False) -> Trajectory:
    n = center.size
    f0 = rng.uniform(*base_freq_range) * speed_scale
    freqs = f0 * np.arange(1, harmonics + 1) if periodic else f0 * (np.arange(1, harmonics + 1) + rng.uniform(-0.15, 0.15, size=harmonics))
    amp_total = rng.uniform(0.25, 0.6, size=n)
    amp_total = _clip_amplitudes(center, amp_total, lower, upper)
    weights = rng.dirichlet(np.ones(harmonics) * 2.0, size=n)  # (n, harmonics)
    amps = weights * amp_total[:, None]
    phases = rng.uniform(0, 2 * np.pi, size=(n, harmonics))
    # velocity safety: rescale so peak |qd| <= 0.6 * limit
    w = 2 * np.pi * freqs
    peak_v = (amps * w[None, :]).sum(1)
    scale = np.minimum(1.0, 0.6 * velocity_limit / np.maximum(peak_v, 1e-9))
    amps = amps * scale[:, None]
    q = center[None, :] + np.einsum("nk,tk->tn", amps, np.sin(np.outer(t, w) + 0))
    q = center[None, :] + sum(amps[:, k][None, :] * np.sin(w[k] * t[:, None] + phases[:, k][None, :]) for k in range(harmonics))
    qd = sum(amps[:, k][None, :] * w[k] * np.cos(w[k] * t[:, None] + phases[:, k][None, :]) for k in range(harmonics))
    qdd = sum(-amps[:, k][None, :] * w[k] ** 2 * np.sin(w[k] * t[:, None] + phases[:, k][None, :]) for k in range(harmonics))
    # start at rest: blend-in over the first 1 s from center to trajectory
    blend = np.clip(t / 1.0, 0.0, 1.0)
    s = 10 * blend**3 - 15 * blend**4 + 6 * blend**5
    sd = (30 * blend**2 - 60 * blend**3 + 30 * blend**4) * (blend < 1.0)
    sdd = (60 * blend - 180 * blend**2 + 120 * blend**3) * (blend < 1.0)
    dq = q - center[None, :]
    q_b = center[None, :] + s[:, None] * dq
    qd_b = sd[:, None] * dq + s[:, None] * qd
    qdd_b = sdd[:, None] * dq + 2 * sd[:, None] * qd + s[:, None] * qdd
    return Trajectory("periodic" if periodic else "multisine", q_b, qd_b, qdd_b, center, {"f0_hz": float(f0), "freqs_hz": freqs.tolist(), "amps": amps.tolist()})


def _minjerk(tau: np.ndarray):
    s = 10 * tau**3 - 15 * tau**4 + 6 * tau**5
    sd = 30 * tau**2 - 60 * tau**3 + 30 * tau**4
    sdd = 60 * tau - 180 * tau**2 + 120 * tau**3
    return s, sd, sdd


def minjerk_p2p(t: np.ndarray, center: np.ndarray, rng: np.random.Generator, speed_scale: float, lower, upper, velocity_limit, *, segment_s=(1.6, 3.0), dwell_s=0.25) -> Trajectory:
    n = center.size
    amp = _clip_amplitudes(center, rng.uniform(0.3, 0.6, size=n), lower, upper)
    waypoints = [center.copy()]
    T_end = float(t[-1])
    times = [0.0]
    now = 0.0
    while now < T_end + 1.0:
        seg = rng.uniform(*segment_s) / speed_scale
        wp = center + rng.uniform(-1, 1, size=n) * amp
        # respect velocity limit: min-jerk peak velocity = 1.875 * dist / T
        dist = np.abs(wp - waypoints[-1])
        needed = 1.875 * dist / (0.6 * velocity_limit)
        seg = max(seg, float(needed.max()))
        waypoints.append(wp)
        times.append(now + seg)
        now += seg + dwell_s
    q = np.zeros((t.size, n))
    qd = np.zeros_like(q)
    qdd = np.zeros_like(q)
    for k in range(len(waypoints) - 1):
        t0, t1 = times[k], times[k + 1]
        a, b = waypoints[k], waypoints[k + 1]
        mask = (t >= t0) & (t < t1)
        tau = (t[mask] - t0) / (t1 - t0)
        s, sd, sdd = _minjerk(tau)
        q[mask] = a + s[:, None] * (b - a)
        qd[mask] = sd[:, None] * (b - a) / (t1 - t0)
        qdd[mask] = sdd[:, None] * (b - a) / (t1 - t0) ** 2
        # dwell
        if k + 1 < len(times):
            dw = (t >= t1) & (t < (times[k + 1] + dwell_s))
            q[dw] = b
    last = t >= times[-1]
    q[last] = waypoints[-1]
    return Trajectory("minjerk_p2p", q, qd, qdd, center, {"n_segments": len(waypoints) - 1})


def make_trajectory(family: str, t: np.ndarray, region_id: int, rng: np.random.Generator, speed_scale: float, lower, upper, velocity_limit) -> Trajectory:
    center = sample_center(rng, region_id, n=lower.size)
    if family == "multisine":
        return multisine(t, center, rng, speed_scale, lower, upper, velocity_limit)
    if family == "periodic":
        return multisine(t, center, rng, speed_scale, lower, upper, velocity_limit, harmonics=2, base_freq_range=(0.2, 0.3), periodic=True)
    if family == "minjerk_p2p":
        return minjerk_p2p(t, center, rng, speed_scale, lower, upper, velocity_limit)
    raise ValueError(family)
