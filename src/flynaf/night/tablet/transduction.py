import math


def clamp_unit(value: float) -> float:
    return min(1.0, max(0.0, value))


def figure_level(contrast: float, noise: float, span: float) -> float:
    return clamp_unit((contrast - noise) / span)


class LoomChannel:
    def __init__(self, size_span: float, speed_span_per_sec: float, speed_decay_sec: float):
        self._size_span = size_span
        self._speed_span = speed_span_per_sec
        self._decay_sec = speed_decay_sec
        self._previous = None
        self._previous_at = 0.0
        self.speed = 0.0

    def reset(self):
        self._previous = None
        self.speed = 0.0

    def update(self, contrast: float, noise: float, now: float) -> tuple:
        size = clamp_unit((contrast - noise) / self._size_span)
        if self._previous is None:
            self._previous, self._previous_at = contrast, now
            return size, 0.0
        elapsed = max(now - self._previous_at, 1e-3)
        growth = max(0.0, contrast - self._previous) / elapsed
        held = self.speed * math.exp(-elapsed / self._decay_sec)
        self.speed = max(held, clamp_unit(growth / self._speed_span))
        self._previous, self._previous_at = contrast, now
        return size, self.speed


def camera_drive(channel: str, side: str, levels: dict) -> dict:
    if channel == 'figure':
        return {f'figure_{side}': levels.get('figure', 0.0)}
    return {
        f'loom_size_{side}': levels.get('size', 0.0),
        f'loom_speed_{side}': levels.get('speed', 0.0),
    }
