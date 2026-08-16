"""The frozen alarm-event accounting behaves as specified (kickoff §05.7)."""

from __future__ import annotations

import numpy as np
import yaml
from pathlib import Path

from certo_fdi.stage2b import event_accounting as EA

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "configs" / "stage2b_contact_loadpath.yaml").read_text())
EC = EA.EventConfig.from_cfg(CFG)


def _t(n):
    return np.arange(n) * EC.window_dt_s


def test_window_time_is_the_evaluation_stride():
    assert EC.window_stride_eval == 16 and EC.control_dt_s == 0.002
    assert abs(EC.window_dt_s - 0.032) < 1e-12


def test_a_run_of_alarming_windows_is_one_event():
    alarm = np.zeros(40, bool)
    alarm[5:15] = True
    ev = EA.extract_events(alarm, _t(40), EC)
    assert ev.n_events == 1
    assert abs(ev.onsets_s[0] - 5 * EC.window_dt_s) < 1e-12


def test_refractory_merges_nearby_bursts_and_admits_distant_ones():
    alarm = np.zeros(200, bool)
    alarm[10:12] = True          # t = 0.32 s
    alarm[20:22] = True          # t = 0.64 s -> inside the 1.0 s refractory, merged
    alarm[100:102] = True        # t = 3.20 s -> new event
    ev = EA.extract_events(alarm, _t(200), EC)
    assert ev.n_events == 2
    np.testing.assert_allclose(ev.onsets_s, [10 * EC.window_dt_s, 100 * EC.window_dt_s])


def test_state_resets_at_the_episode_boundary():
    """Two episodes each ending in an alarm must give two events, not one merged run."""
    a = np.zeros(30, bool); a[-3:] = True
    b = np.zeros(30, bool); b[:3] = True
    ea = EA.extract_events(a, _t(30), EC, "ep_a")
    eb = EA.extract_events(b, _t(30), EC, "ep_b")
    assert ea.n_events == 1 and eb.n_events == 1
    assert EC.episode_boundary_reset is True


def test_pre_onset_alarms_are_false_alarms_not_early_detections():
    n = 200
    label = np.zeros(n, int); label[120:] = 1
    onset = 120 * EC.window_dt_s
    alarm = np.zeros(n, bool); alarm[20:22] = True        # well before onset
    out = EA.fault_event_detection(alarm, _t(n), label, onset, EC, "e")
    assert out["has_event"] is True
    assert out["detected"] is False                        # never counted as an early detection
    assert out["n_false_alarm_events"] == 1
    assert out["delay_s"] != out["delay_s"]                # NaN, not imputed


def test_detection_delay_is_measured_from_fault_onset():
    n = 200
    label = np.zeros(n, int); label[100:] = 1
    onset = 100 * EC.window_dt_s
    alarm = np.zeros(n, bool); alarm[105:110] = True
    out = EA.fault_event_detection(alarm, _t(n), label, onset, EC, "e")
    assert out["detected"] is True
    np.testing.assert_allclose(out["delay_s"], 5 * EC.window_dt_s)
    assert out["match_index"] == 105


def test_an_alarm_far_after_the_segment_does_not_match():
    n = 300
    label = np.zeros(n, int); label[100:150] = 1
    onset = 100 * EC.window_dt_s
    alarm = np.zeros(n, bool)
    alarm[250:252] = True                                  # long after the segment + tolerance
    out = EA.fault_event_detection(alarm, _t(n), label, onset, EC, "e")
    assert out["detected"] is False
    assert out["n_false_alarm_events"] == 1


def test_false_alarms_per_hour_uses_observed_healthy_time():
    n = 1125                                               # 1125 * 0.032 s = 36 s of healthy time
    label = np.zeros(n, int)
    alarm = np.zeros(n, bool)
    for k in range(6):                                     # 6 well-separated events
        alarm[k * 100] = True
    rows = [EA.healthy_false_alarms(alarm, _t(n), label, EC, "e")]
    agg = EA.aggregate_events(rows, [], EC)
    np.testing.assert_allclose(agg["healthy_hours"], n * EC.window_dt_s / 3600.0)
    np.testing.assert_allclose(agg["false_alarms_per_hour"], 6 / (n * EC.window_dt_s / 3600.0))
    np.testing.assert_allclose(agg["arl0_hours"], (n * EC.window_dt_s / 3600.0) / 6)


def test_missed_events_are_not_imputed_and_delays_exclude_them():
    n = 200
    label = np.zeros(n, int); label[100:] = 1
    onset = 100 * EC.window_dt_s
    hit = EA.fault_event_detection(np.r_[np.zeros(105, bool), np.ones(5, bool), np.zeros(90, bool)],
                                   _t(n), label, onset, EC, "hit")
    miss = EA.fault_event_detection(np.zeros(n, bool), _t(n), label, onset, EC, "miss")
    agg = EA.aggregate_events([], [hit, miss], EC)
    assert agg["n_fault_events"] == 2 and agg["n_detected"] == 1
    np.testing.assert_allclose(agg["event_tpr"], 0.5)
    np.testing.assert_allclose(agg["detection_delay_median_s"], 5 * EC.window_dt_s)   # only the hit


def test_window_and_event_rates_are_reported_separately():
    n = 100
    label = np.zeros(n, int); label[50:] = 1
    alarm = np.zeros(n, bool); alarm[10:40] = True
    w = EA.window_alarm_rate(alarm, label)
    assert 0 < w["window_alarm_rate_healthy"] < 1
    assert w["window_alarm_rate_faulty"] == 0.0
    ev = EA.extract_events(alarm, _t(n), EC)
    assert ev.n_events == 1                                # 30 alarming windows, one event
    assert EC.to_dict()["pre_onset_alarms"].startswith("counted as false alarms")
