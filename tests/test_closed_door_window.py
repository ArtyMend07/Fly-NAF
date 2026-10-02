import collections
import threading
from unittest.mock import patch

import numpy as np
import pytest

from flynaf import config
from flynaf.env import vision as vision_module
from flynaf.env.vision import FNAFVision

HEIGHT, WIDTH = 36, 20
SHADOW_MEASURED = (420, 263, 517, 541)


def window_scene(streak: bool, head: bool) -> np.ndarray:
    frame = np.full((HEIGHT, WIDTH), 40.0, dtype=np.float32)
    if streak:
        frame[:, 11:13] = 200.0
    if head:
        frame[6:20, 9:17] = 5.0
    return frame


LIT_EMPTY = window_scene(streak=True, head=False)
FLICKER = window_scene(streak=False, head=False)
BONNIE = window_scene(streak=False, head=True)


class Replay:
    def __init__(self, frames):
        self._frames = list(frames)
        self._shown = 0

    def __bool__(self):
        return True

    def __getitem__(self, _index):
        frame = self._frames[min(self._shown, len(self._frames) - 1)]
        self._shown += 1
        return frame


def eye() -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision._buf_lock = threading.Lock()
    vision.mse_threshold = config.FORAGING_PARAMS.mse_threshold
    vision.closed_mse_threshold = config.FORAGING_PARAMS.closed_door_mse_threshold
    vision._peak_mse = {'left': 0.0, 'right': 0.0}
    vision._last_mse = {'left': 0.0, 'right': 0.0}
    vision._threat_written_left = True
    vision._threat_written_right = True
    vision._distance_cache = {}
    vision._sweep_sec = 0.05
    vision._bank_tolerance = config.VISION_DYNAMICS.bank_tolerance_mse
    vision._capture_delay = 0.0
    vision.banks = {(side, closed): [] for side in ('left', 'right') for closed in (False, True)}
    vision._window_bufs = {side: collections.deque(maxlen=5) for side in ('left', 'right')}
    return vision


def record_the_closed_window(vision: FNAFVision, frames: list):
    vision._window_bufs['left'] = Replay(frames)
    with patch.object(vision_module.time, 'sleep', lambda _s: None):
        vision.capture_bank('left', True, None, True)
    vision._window_bufs['left'] = collections.deque(maxlen=5)


def test_the_closed_window_bank_keeps_only_the_lit_view():
    vision = eye()

    record_the_closed_window(vision, [FLICKER, LIT_EMPTY, FLICKER, FLICKER])

    assert len(vision.banks[('left', True)]) == 1
    assert np.array_equal(vision.banks[('left', True)][0], LIT_EMPTY)


@pytest.mark.parametrize('seen, driven', [(LIT_EMPTY, 0.0), (BONNIE, 1.0)])
def test_bonnie_behind_the_closed_door_drives_the_eye_and_the_empty_window_does_not(seen, driven):
    vision = eye()
    record_the_closed_window(vision, [FLICKER, LIT_EMPTY])
    vision._window_bufs['left'].extend([seen] * 3)

    assert vision.get_left_sensory_rate(door_closed=True) == driven


def test_the_left_window_holds_the_whole_shadow_measured_on_night_2():
    left, top, right, bottom = config.VISION_CALIBRATION.left_window
    shadow_left, shadow_top, shadow_right, shadow_bottom = SHADOW_MEASURED

    assert left <= shadow_left and right >= shadow_right
    assert top <= shadow_top and bottom >= shadow_bottom
