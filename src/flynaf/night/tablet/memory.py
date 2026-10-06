import math

from flynaf import config


class ObjectMemory:
    def __init__(self, decay_sec: float, base_rate_hz: float | None = None):
        self._decay_sec = decay_sec
        rate = base_rate_hz or config.SIMULATION_PARAMS.base_sensory_rate_hz
        self._faintest = 1.0 / rate
        self._side = None
        self._strength = 0.0
        self._at = 0.0

    def remember(self, side: str, strength: float, now: float) -> bool:
        if strength <= self.level(now, side):
            return False
        self._side, self._strength, self._at = side, strength, now
        return True

    def level(self, now: float, side: str | None = None) -> float:
        if self._side is None or (side is not None and side != self._side):
            return 0.0
        level = self._strength * math.exp(-max(0.0, now - self._at) / self._decay_sec)
        return level if level >= self._faintest else 0.0

    def drive(self, now: float) -> dict:
        level = self.level(now)
        if level == 0.0:
            return {}
        return {f'loom_size_{self._side}': level, f'loom_speed_{self._side}': level}
