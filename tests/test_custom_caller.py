from caller.custom_caller import CustomCaller
from settings import EPISODE_LENGTH, TICK_LENGTH_IN_SECONDS, NUM_FLOORS
import random


def _collect_call_times(days):
    random.seed(12345)
    caller = CustomCaller()
    ticks_per_day = (24 * 60 * 60) // TICK_LENGTH_IN_SECONDS
    total_ticks = days * ticks_per_day
    call_times = []

    for tick in range(total_ticks):
        src, dest = caller.generate_call()
        if src is None:
            assert dest is None
            continue

        call_times.append((tick * TICK_LENGTH_IN_SECONDS) % (24 * 60 * 60))

        assert src != dest
        assert 0 <= src < NUM_FLOORS
        assert 0 <= dest < NUM_FLOORS

    return call_times


def _collect_calls(days):
    random.seed(12345)
    caller = CustomCaller()
    ticks_per_day = (24 * 60 * 60) // TICK_LENGTH_IN_SECONDS
    total_ticks = days * ticks_per_day
    calls = []

    for tick in range(total_ticks):
        src, dest = caller.generate_call()
        if src is None:
            continue
        t = (tick * TICK_LENGTH_IN_SECONDS) % (24 * 60 * 60)
        calls.append((t, src, dest))
    return calls


def _window_calls(calls, start_sec, end_sec):
    return [(t, src, dest) for t, src, dest in calls if start_sec <= t < end_sec]


def _avg_calls_per_day_in_window(call_times, days, start_sec, end_sec):
    return sum(start_sec <= t < end_sec for t in call_times) / days


def test_custom_caller_profile_shape():
    days = 120
    call_times = _collect_call_times(days=days)

    # Night baseline period from 20:30 to 07:00 should average about 2-3 calls/night.
    overnight_calls = _avg_calls_per_day_in_window(call_times, days, 20 * 3600 + 30 * 60, 24 * 3600)
    overnight_calls += _avg_calls_per_day_in_window(call_times, days, 0, 7 * 3600)
    assert 2.0 <= overnight_calls <= 3.0

    # Morning spike 08:00-08:10 should be around 15 calls/day.
    morning_spike = _avg_calls_per_day_in_window(call_times, days, 8 * 3600, 8 * 3600 + 10 * 60)
    assert 11.0 <= morning_spike <= 19.0

    # Midday inter-spike baseline should be around 10 calls per 50-minute block.
    midday_baseline = _avg_calls_per_day_in_window(
        call_times,
        days,
        12 * 3600 + 10 * 60,
        13 * 3600,
    )
    assert 7.0 <= midday_baseline <= 13.5

    # Midday spike should dominate the baseline period.
    midday_spike = _avg_calls_per_day_in_window(call_times, days, 12 * 3600, 12 * 3600 + 10 * 60)
    assert midday_spike > midday_baseline

    # Night should be much lighter than a midday spike block.
    midday_spike = _avg_calls_per_day_in_window(call_times, days, 12 * 3600, 12 * 3600 + 10 * 60)
    assert overnight_calls < midday_spike


def test_custom_caller_respects_episode_horizon():
    caller = CustomCaller()
    for _ in range(EPISODE_LENGTH):
        src, dest = caller.generate_call()
        if src is not None:
            assert src != dest


def test_custom_caller_directional_mix_over_day():
    calls = _collect_calls(days=200)

    morning_ramp = _window_calls(calls, 7 * 3600, 8 * 3600)
    assert len(morning_ramp) > 0
    assert all(src == 0 and dest != 0 for _, src, dest in morning_ramp)

    early_day = _window_calls(calls, 8 * 3600, 10 * 3600)
    assert len(early_day) > 0
    early_incoming_ratio = sum(src == 0 and dest != 0 for _, src, dest in early_day) / len(early_day)
    assert early_incoming_ratio >= 0.65

    midday_window = _window_calls(calls, 12 * 3600 + 10 * 60, 13 * 3600)
    assert len(midday_window) > 0
    midday_interfloor_ratio = sum(src != 0 and dest != 0 for _, src, dest in midday_window) / len(midday_window)
    assert midday_interfloor_ratio >= 0.45

    late_day = _window_calls(calls, 18 * 3600, 20 * 3600)
    assert len(late_day) > 0
    late_outgoing_ratio = sum(src != 0 and dest == 0 for _, src, dest in late_day) / len(late_day)
    assert late_outgoing_ratio >= 0.65

    evening_and_night = _window_calls(calls, 20 * 3600, 24 * 3600)
    evening_and_night += _window_calls(calls, 0, 7 * 3600)
    assert len(evening_and_night) > 0
    assert all(src != 0 and dest == 0 for _, src, dest in evening_and_night)