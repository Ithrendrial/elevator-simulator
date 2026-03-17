import settings as s
from .caller import Caller
from math import exp
from random import randint, random


class CustomCaller(Caller):
    """Caller with a time-varying Poisson demand profile over a 24-hour day.

    Profile assumptions:
    * 20:00-07:00: low fixed per-tick probability for night calls.
    * 07:00-08:00: smooth ramp-up to the 08:00 peak.
    * 08:00-20:00: 10-minute spike at the start of every hour, lower baseline in between.
    * 20:00-20:30: smooth ramp-down from the 20:00 peak.
    """

    DAY_SECONDS = 24 * 60 * 60
    DAY_START_SECONDS = 8 * 60 * 60
    DAY_END_SECONDS = 20 * 60 * 60
    NIGHT_END_SECONDS = 8 * 60 * 60
    SPIKE_DURATION_SECONDS = 10 * 60
    MORNING_RAMP_START_SECONDS = 7 * 60 * 60
    EVENING_RAMP_END_SECONDS = 20 * 60 * 60 + 30 * 60

    NIGHT_CALL_PROB_PER_TICK = 0.00017
    NIGHT_CALLS_PER_HOUR = 0.5
    DAY_BASE_CALLS_PER_HOUR = 12.0   # 10 calls expected over 50 minutes
    SPIKE_CALLS_PER_HOUR = 90.0      # 15 calls expected over 10 minutes

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.elapsed_time_seconds = 0

    def _incoming_call(self):
        return 0, randint(1, self.floors - 1)

    def _outgoing_call(self):
        return randint(1, self.floors - 1), 0

    def _interfloor_call(self):
        call_floor = randint(1, self.floors - 1)
        destination_floor = randint(1, self.floors - 1)
        while destination_floor == call_floor:
            destination_floor = randint(1, self.floors - 1)
        return call_floor, destination_floor

    def _sample_directional_call(self, time_of_day):
        # 07:00-08:00 ramp-up should be purely incoming.
        if self.MORNING_RAMP_START_SECONDS <= time_of_day < self.DAY_START_SECONDS:
            return self._incoming_call()

        # 20:00-07:00 should be purely outgoing.
        if time_of_day >= self.DAY_END_SECONDS or time_of_day < self.MORNING_RAMP_START_SECONDS:
            return self._outgoing_call()

        # 08:00-10:00: heavy incoming, some interfloor, little outgoing.
        if self.DAY_START_SECONDS <= time_of_day < self.DAY_START_SECONDS + 2 * 60 * 60:
            incoming_prob, interfloor_prob, outgoing_prob = 0.75, 0.20, 0.05
        # 10:00-18:00: balanced incoming/outgoing with interfloor dominant.
        elif self.DAY_START_SECONDS + 2 * 60 * 60 <= time_of_day < self.DAY_END_SECONDS - 2 * 60 * 60:
            incoming_prob, interfloor_prob, outgoing_prob = 0.25, 0.50, 0.25
        # 18:00-20:00: little incoming, some interfloor, heavily outgoing.
        else:
            incoming_prob, interfloor_prob, outgoing_prob = 0.05, 0.20, 0.75

        roll = random()
        if roll < incoming_prob:
            return self._incoming_call()
        if roll < incoming_prob + interfloor_prob:
            return self._interfloor_call()
        return self._outgoing_call()

    def _calls_per_hour(self, current_time_seconds):
        time_of_day = current_time_seconds % self.DAY_SECONDS

        final_spike_end = self.DAY_END_SECONDS + self.SPIKE_DURATION_SECONDS

        # 20:30-07:30 is handled separately via fixed per-tick night probability.
        if time_of_day >= self.EVENING_RAMP_END_SECONDS or time_of_day < self.MORNING_RAMP_START_SECONDS:
            return self.NIGHT_CALLS_PER_HOUR

        # 07:30-08:00: smooth ramp-up to the opening spike intensity.
        if self.MORNING_RAMP_START_SECONDS <= time_of_day < self.DAY_START_SECONDS:
            progress = (time_of_day - self.MORNING_RAMP_START_SECONDS) / (
                self.DAY_START_SECONDS - self.MORNING_RAMP_START_SECONDS
            )
            return self.NIGHT_CALLS_PER_HOUR + progress * (
                self.SPIKE_CALLS_PER_HOUR - self.NIGHT_CALLS_PER_HOUR
            )

        # 08:00-20:00: hourly spikes for first 10 minutes, lower baseline between spikes.
        if self.DAY_START_SECONDS <= time_of_day < self.DAY_END_SECONDS:
            seconds_since_day_start = time_of_day - self.DAY_START_SECONDS
            seconds_into_hour = seconds_since_day_start % (60 * 60)
            if seconds_into_hour < self.SPIKE_DURATION_SECONDS:
                return self.SPIKE_CALLS_PER_HOUR
            return self.DAY_BASE_CALLS_PER_HOUR

        # 20:00-20:10 final spike.
        if self.DAY_END_SECONDS <= time_of_day < final_spike_end:
            return self.SPIKE_CALLS_PER_HOUR

        # 20:10-20:30 smooth ramp-down to near-night levels.
        if final_spike_end <= time_of_day < self.EVENING_RAMP_END_SECONDS:
            progress = (time_of_day - final_spike_end) / (
                self.EVENING_RAMP_END_SECONDS - final_spike_end
            )
            return self.SPIKE_CALLS_PER_HOUR - progress * (
                self.SPIKE_CALLS_PER_HOUR - self.NIGHT_CALLS_PER_HOUR
            )

        return self.NIGHT_CALLS_PER_HOUR

    def generate_call(self):
        current_time_seconds = self.elapsed_time_seconds
        self.elapsed_time_seconds += s.TICK_LENGTH_IN_SECONDS
        time_of_day = current_time_seconds % self.DAY_SECONDS

        in_night_window = (
            time_of_day >= self.EVENING_RAMP_END_SECONDS
            or time_of_day < self.MORNING_RAMP_START_SECONDS
        )

        if in_night_window:
            if random() < self.NIGHT_CALL_PROB_PER_TICK:
                return self._sample_directional_call(time_of_day)
            return None, None

        calls_per_hour = self._calls_per_hour(current_time_seconds)
        lambda_tick = calls_per_hour * (s.TICK_LENGTH_IN_SECONDS / 3600.0)
        p_call_this_tick = 1.0 - exp(-lambda_tick)

        if random() >= p_call_this_tick:
            return None, None

        return self._sample_directional_call(time_of_day)