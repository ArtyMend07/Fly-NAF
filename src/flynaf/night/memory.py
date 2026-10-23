import math
from dataclasses import dataclass, field

from flynaf import config

SIDES = ('left', 'right')


class FadingTrace:
    def __init__(self, decay_sec: float, base_rate_hz: float | None = None):
        self._decay_sec = decay_sec
        rate = base_rate_hz or config.SIMULATION_PARAMS.base_sensory_rate_hz
        self._faintest = 1.0 / rate
        self._strength = dict.fromkeys(SIDES, 0.0)
        self._at = dict.fromkeys(SIDES, 0.0)

    def level(self, now: float, side: str) -> float:
        elapsed = max(0.0, now - self._at[side])
        level = self._strength[side] * math.exp(-elapsed / self._decay_sec)
        return level if level >= self._faintest else 0.0

    def add(self, side: str, amount: float, now: float) -> float:
        self._strength[side] = min(1.0, self.level(now, side) + max(0.0, amount))
        self._at[side] = now
        return self._strength[side]

    def present(self, now: float) -> dict:
        levels = {side: self.level(now, side) for side in SIDES}
        return {side: level for side, level in levels.items() if level > 0.0}


class OrientationMemory:
    def __init__(self, params=None):
        p = params or config.MEMORY_DYNAMICS
        self._decay_sec = p.orientation_sec
        self._resting = {'left': p.ring_resting_left, 'right': p.ring_resting_right}
        self._sighting = {'left': p.ring_sighting_left, 'right': p.ring_sighting_right}
        self._above_rest = dict.fromkeys(SIDES, 0.0)
        self._at = 0.0

    def imprint(self, ring_spikes: dict, now: float):
        keep = math.exp(-max(0.0, now - self._at) / self._decay_sec)
        self._at = now
        for side, count in ring_spikes.items():
            written = (count - self._resting[side]) / self._sighting[side]
            self._above_rest[side] = min(1.0, max(-1.0, self._above_rest[side] * keep + written))

    def level(self, now: float, side: str) -> float:
        return self._above_rest[side] * math.exp(-max(0.0, now - self._at) / self._decay_sec)


class DefensiveState:
    def __init__(self, decay_sec: float | None = None, base_rate_hz: float | None = None):
        decay = config.MEMORY_DYNAMICS.defence_sec if decay_sec is None else decay_sec
        self._trace = FadingTrace(decay, base_rate_hz)

    def threat(self, side: str, strength: float, now: float) -> float:
        return self._trace.add(side, strength, now)

    def level(self, now: float, side: str) -> float:
        return self._trace.level(now, side)

    def pull(self, now: float) -> float:
        return self.level(now, 'left') - self.level(now, 'right')


def quickened(seconds: float, arousal: float, quickening: float | None = None) -> float:
    factor = config.FORAGING_PARAMS.arousal_quickening if quickening is None else quickening
    return seconds / (1.0 + factor * min(1.0, max(0.0, arousal)))


class Vigilance:
    def __init__(self, decay_sec: float | None = None, base_rate_hz: float | None = None):
        decay = config.MEMORY_DYNAMICS.vigilance_sec if decay_sec is None else decay_sec
        self._trace = FadingTrace(decay, base_rate_hz)

    def sighted(self, side: str, strength: float, now: float) -> float:
        return self._trace.add(side, strength, now)

    def level(self, now: float, side: str) -> float:
        return self._trace.level(now, side)

    def arousal(self, now: float) -> float:
        return max(self._trace.present(now).values(), default=0.0)

    def pull(self, now: float) -> float:
        return self.level(now, 'left') - self.level(now, 'right')


@dataclass
class Memories:
    orientation: OrientationMemory = field(default_factory=OrientationMemory)
    defence: DefensiveState = field(default_factory=DefensiveState)
    vigilance: Vigilance = field(default_factory=Vigilance)
