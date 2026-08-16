"""Frozen alarm-event accounting (kickoff §05.7).

Every definition below is fixed **before** any Stage 2B evaluation, because false alarms per
hour is the headline number of the stage and is extremely sensitive to how an "event" is
counted. Concretely:

* **window stride** — evaluation windows advance by ``window_stride_eval`` samples
  (16 at 500 Hz = 32 ms). Each healthy window therefore contributes 32 ms of healthy time.
* **alarm onset** — an alarm *event* starts at the first window whose (sequential-wrapped)
  alarm state rises 0 -> 1. A run of consecutive alarming windows is **one** event.
* **refractory** — after an onset, no new event may start for ``refractory_s`` (1.0 s) even if
  the alarm state drops and rises again. This is what keeps a single noisy fault segment from
  being counted as dozens of alarms.
* **event matching** — an alarm counts as detecting the fault event if its onset lies at or
  after the fault onset and no later than the end of the faulty segment plus
  ``event_match_tolerance_s``. Alarms before the fault onset are **false alarms**, never early
  detections.
* **detection delay** — measured from ``fault_onset_s`` to the matching alarm onset. A missed
  event has delay ``NaN`` and is never imputed with a cap.
* **episode boundary** — all sequential state (persistence counters, hysteresis latch, CUSUM
  statistic, refractory clock) resets at every episode boundary.

Window alarm rates and event alarm rates are reported separately; the headline is the event
rate. Nothing here uses fault labels to choose a parameter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class EventConfig:
    """The frozen accounting parameters, read from the config and echoed into every result."""

    window_stride_eval: int = 16
    control_dt_s: float = 0.002
    refractory_s: float = 1.0
    event_match_tolerance_s: float = 0.50
    episode_boundary_reset: bool = True
    missed_event_delay: float = float("nan")

    @property
    def window_dt_s(self) -> float:
        """Healthy time contributed by one evaluation window."""
        return self.window_stride_eval * self.control_dt_s

    @staticmethod
    def from_cfg(cfg: dict) -> "EventConfig":
        ea = cfg["event_accounting"]
        return EventConfig(
            window_stride_eval=int(ea["window_stride_eval"]),
            control_dt_s=float(cfg["simulation"]["control_dt_s"]),
            refractory_s=float(ea["refractory_s"]),
            event_match_tolerance_s=float(ea["event_match_tolerance_s"]),
            episode_boundary_reset=bool(ea["episode_boundary_reset"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"window_stride_eval": self.window_stride_eval, "control_dt_s": self.control_dt_s,
                "window_dt_s": self.window_dt_s, "refractory_s": self.refractory_s,
                "event_match_tolerance_s": self.event_match_tolerance_s,
                "episode_boundary_reset": self.episode_boundary_reset,
                "alarm_onset": "first window whose sequential-wrapped alarm state rises 0->1",
                "detection_delay_origin": "fault_onset_s",
                "missed_event_handling": "delay = NaN, never imputed",
                "pre_onset_alarms": "counted as false alarms, never as early detections"}


@dataclass
class EpisodeAlarms:
    """Alarm events extracted from one episode's time-ordered alarm state."""

    episode_id: str
    onsets_s: np.ndarray               # event onset times (window end times)
    onset_indices: np.ndarray          # index into the episode's window arrays
    n_events: int = 0
    healthy_seconds: float = 0.0
    faulty_seconds: float = 0.0
    meta: dict = field(default_factory=dict)


def extract_events(alarm: np.ndarray, t_end: np.ndarray, cfg: EventConfig, episode_id: str = "") -> EpisodeAlarms:
    """Collapse a boolean per-window alarm state into refractory-separated alarm events.

    ``alarm`` and ``t_end`` must already be sorted by window start and belong to a single
    episode (sequential state never crosses an episode boundary).
    """
    alarm = np.asarray(alarm, dtype=bool)
    t_end = np.asarray(t_end, dtype=float)
    onsets, idx = [], []
    last_onset = -np.inf
    prev = False
    for i, a in enumerate(alarm):
        rising = a and not prev
        if rising and (t_end[i] - last_onset) >= cfg.refractory_s:
            onsets.append(float(t_end[i]))
            idx.append(i)
            last_onset = float(t_end[i])
        prev = bool(a)
    return EpisodeAlarms(episode_id=episode_id, onsets_s=np.asarray(onsets, dtype=float),
                         onset_indices=np.asarray(idx, dtype=int), n_events=len(onsets))


def healthy_false_alarms(
    alarm: np.ndarray, t_end: np.ndarray, label: np.ndarray, cfg: EventConfig, episode_id: str = "",
) -> dict[str, float]:
    """False-alarm events and healthy exposure time for one episode.

    A false alarm is an alarm event whose onset falls on a **label == 0** window. On a fault
    episode this includes any alarm raised before the fault onset.
    """
    label = np.asarray(label).astype(int)
    ev = extract_events(alarm, t_end, cfg, episode_id)
    healthy_windows = int((label == 0).sum())
    healthy_s = healthy_windows * cfg.window_dt_s
    n_fa = int(sum(1 for i in ev.onset_indices if label[i] == 0))
    return {"episode_id": episode_id, "n_false_alarm_events": n_fa, "healthy_seconds": healthy_s,
            "n_healthy_windows": healthy_windows,
            "n_alarming_healthy_windows": int(np.asarray(alarm, dtype=bool)[label == 0].sum()),
            "n_alarm_events": ev.n_events}


def fault_event_detection(
    alarm: np.ndarray, t_end: np.ndarray, label: np.ndarray, onset_s: float, cfg: EventConfig,
    episode_id: str = "",
) -> dict[str, Any]:
    """Detection outcome for the single fault event of one fault episode.

    Returns the match, the delay from ``onset_s``, and the index of the matching alarm so that
    localization can be evaluated *conditional on a detected event*.
    """
    label = np.asarray(label).astype(int)
    t_end = np.asarray(t_end, dtype=float)
    ev = extract_events(alarm, t_end, cfg, episode_id)
    faulty = label == 1
    if not faulty.any():
        return {"episode_id": episode_id, "has_event": False, "detected": False,
                "delay_s": cfg.missed_event_delay, "match_index": -1,
                "n_false_alarm_events": int(sum(1 for i in ev.onset_indices if label[i] == 0))}
    seg_end = float(t_end[faulty].max())
    window_hi = seg_end + cfg.event_match_tolerance_s
    match_i, delay = -1, cfg.missed_event_delay
    for i, t in zip(ev.onset_indices, ev.onsets_s):
        if t >= onset_s and t <= window_hi:
            match_i, delay = int(i), float(t - onset_s)
            break
    return {"episode_id": episode_id, "has_event": True, "detected": bool(match_i >= 0),
            "delay_s": delay, "match_index": match_i,
            "fault_onset_s": float(onset_s), "fault_segment_end_s": seg_end,
            "n_alarm_events": ev.n_events,
            "n_false_alarm_events": int(sum(1 for i in ev.onset_indices if label[i] == 0)),
            "n_faulty_windows": int(faulty.sum())}


def aggregate_events(
    healthy_rows: list[dict], fault_rows: list[dict], cfg: EventConfig,
) -> dict[str, float]:
    """Pool per-episode outcomes into the reported event metrics.

    ``false_alarms_per_hour`` uses **total healthy exposure across episodes**, including the
    pre-onset healthy portion of fault episodes, so the denominator is the real observed
    healthy time and not an episode count.
    """
    fa = sum(int(r["n_false_alarm_events"]) for r in healthy_rows) + sum(int(r.get("n_false_alarm_events", 0)) for r in fault_rows)
    healthy_s = sum(float(r["healthy_seconds"]) for r in healthy_rows) + sum(float(r.get("healthy_seconds", 0.0)) for r in fault_rows)
    events = [r for r in fault_rows if r.get("has_event")]
    n_ev = len(events)
    det = [r for r in events if r["detected"]]
    delays = np.array([r["delay_s"] for r in det], dtype=float)
    tp, fn, fp = len(det), n_ev - len(det), fa
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    hours = healthy_s / SECONDS_PER_HOUR
    return {
        "n_fault_events": n_ev,
        "n_detected": len(det),
        "event_tpr": (len(det) / n_ev) if n_ev else float("nan"),
        "n_false_alarm_events": int(fa),
        "healthy_hours": hours,
        "false_alarms_per_hour": (fa / hours) if hours > 0 else float("nan"),
        "arl0_hours": (hours / fa) if fa > 0 else float("inf"),
        "event_precision": prec,
        "event_recall": rec,
        "event_f1": (2 * prec * rec / max(prec + rec, 1e-12)) if (prec + rec) > 0 else 0.0,
        "detection_delay_median_s": float(np.median(delays)) if delays.size else float("nan"),
        "detection_delay_p90_s": float(np.percentile(delays, 90)) if delays.size else float("nan"),
        "detection_delay_p95_s": float(np.percentile(delays, 95)) if delays.size else float("nan"),
        "detection_delay_mean_s": float(np.mean(delays)) if delays.size else float("nan"),
    }


def window_alarm_rate(alarm: np.ndarray, label: np.ndarray) -> dict[str, float]:
    """Window-level rates, reported separately from the event rates (never the headline)."""
    alarm = np.asarray(alarm, dtype=bool)
    label = np.asarray(label).astype(int)
    return {"window_alarm_rate_healthy": float(alarm[label == 0].mean()) if (label == 0).any() else float("nan"),
            "window_alarm_rate_faulty": float(alarm[label == 1].mean()) if (label == 1).any() else float("nan"),
            "n_windows": int(len(alarm))}
