import collections
import os
import sys
import threading

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
from env.vision import FNAFVision

SIZE = 32


def _eye(frames):
    vision = FNAFVision.__new__(FNAFVision)
    vision._buf_lock = threading.Lock()
    vision.mse_threshold = config.FORAGING_PARAMS.mse_threshold
    vision._peak_mse = {'left': 0.0, 'right': 0.0}
    vision._threat_written_left = True
    vision._threat_written_right = True
    vision.ref_left = np.zeros((SIZE, SIZE), dtype=np.float32)
    vision.ref_right = np.zeros((SIZE, SIZE), dtype=np.float32)
    vision._left_buf = collections.deque(frames, maxlen=5)
    vision._right_buf = collections.deque(frames, maxlen=5)
    return vision


def _intruder():
    return np.full((SIZE, SIZE), 80.0, dtype=np.float32)


def _dim_flicker():
    return np.zeros((SIZE, SIZE), dtype=np.float32)


def test_one_dim_flicker_frame_used_to_hide_an_intruder():
    """The hallway light flickers, so any buffer holds a frame that resembles
    the unlit reference. Reading the minimum meant the least alarming frame
    decided, and a lit-up Bonnie reported clear on most samples."""
    buffer = [_intruder(), _intruder(), _dim_flicker(), _intruder(), _intruder()]
    vision = _eye(buffer)

    quiet, _ = vision._get_min_mse_from_buffer(vision.ref_left, vision._left_buf)
    loudest, _ = vision._get_peak_mse_from_buffer(vision.ref_left, vision._left_buf)

    assert quiet < vision.mse_threshold
    assert loudest > vision.mse_threshold


def test_the_eye_now_reports_the_strongest_recent_evidence():
    buffer = [_intruder(), _intruder(), _dim_flicker(), _intruder(), _intruder()]
    vision = _eye(buffer)

    assert vision.get_left_sensory_rate() == 1.0
    assert vision.get_right_sensory_rate() == 1.0


def test_an_empty_hallway_still_reads_clear():
    vision = _eye([_dim_flicker()] * 5)

    assert vision.get_left_sensory_rate() == 0.0
    assert vision.peak_mse('left') < vision.mse_threshold


def test_the_peak_is_recorded_even_when_below_the_threshold():
    faint = np.full((SIZE, SIZE), 5.0, dtype=np.float32)
    vision = _eye([faint] * 5)

    vision.get_left_sensory_rate()

    assert vision.peak_mse('left') == 25.0


def test_the_tablet_trigger_sits_between_the_measured_office_and_tablet():
    """Measured on 2026-09-17: the office patch reads 182 to 294 with the tablet
    down and 2703 to 3646 with it up. The old trigger of 100 sat inside the
    office's own variation, so a lowering could never be confirmed."""
    trigger = config.CAMERA_DETECTION.mse_trigger

    assert trigger > 294
    assert trigger < 2703


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
