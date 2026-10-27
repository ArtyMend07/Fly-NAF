from collections import deque

from flynaf import config
from flynaf.env import hallway_bank
from flynaf.night.neurons import side_of
from flynaf.night.tablet.transduction import clamp_unit, loom_level

SIDES = ('left', 'right')
FULL_FIELD_LOOM = {f'{kind}_{side}': 1.0 for kind in ('loom_size', 'loom_speed') for side in SIDES}


def without_side(drive: dict, side: str) -> dict:
    return {population: level for population, level in drive.items() if side_of(population) != side}


class ThresholdEye:
    def read(self, vision, side: str, door_closed: bool, now: float) -> dict:
        rate = getattr(vision, f'get_{side}_sensory_rate')(door_closed)
        return {f'eye_{side}': rate, f'wide_field_{side}': rate} if rate > 0.0 else {}


class LoomingEye:
    def __init__(self, params=None, window_sec: float | None = None):
        self._p = params or config.HALLWAY_VISION
        self._window = window_sec or 1.0 / config.SIMULATION_PARAMS.target_fps
        self._shares = {side: deque() for side in SIDES}

    def read(self, vision, side: str, door_closed: bool, now: float) -> dict:
        getattr(vision, f'get_{side}_sensory_rate')(door_closed)
        seen = vision.evidence(side, door_closed)
        if seen is None:
            return {}
        _distance, frame, reference = seen
        p = self._p
        share = hallway_bank.changed_share(frame, reference, p.view_scale, p.cell_pixels, p.cell_noise_mse)
        return self.transduce(side, share, now)

    def transduce(self, side: str, share: float, now: float) -> dict:
        p = self._p
        growth = self._growth(side, share, now)
        if share >= p.wide_field_share:
            return {f'wide_field_{side}': 1.0}
        size = loom_level(share, p.loom_share_floor, p.loom_share_span)
        if size == 0.0:
            return {}
        drive = {f'loom_size_{side}': size, f'wide_field_{side}': size}
        speed = clamp_unit(growth / p.loom_speed_span_per_sec)
        if speed > 0.0:
            drive[f'loom_speed_{side}'] = speed
        return drive

    def _growth(self, side: str, share: float, now: float) -> float:
        shares = self._shares[side]
        if not shares or now - shares[-1][0] > self._window:
            shares.clear()
            shares.append((now - self._window, 0.0))
        while len(shares) > 1 and shares[1][0] <= now - self._window:
            shares.popleft()
        then, earlier = shares[0]
        shares.append((now, share))
        return (share - earlier) / max(now - then, self._window)


def build_eye(params=None):
    params = params or config.HALLWAY_VISION
    return LoomingEye(params) if params.looming else ThresholdEye()
