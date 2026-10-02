import collections
import os
import threading

import numpy as np

from flynaf.env.vision import FNAFVision


def make_vision() -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision.mse_threshold = 40.0
    vision.banks = {(side, closed): [] for side in ('left', 'right') for closed in (False, True)}
    vision._distance_cache = {}
    vision.debug_dir = os.path.join(os.path.dirname(__file__), '_scratch_vision_debug')
    os.makedirs(vision.debug_dir, exist_ok=True)
    vision._left_buf = collections.deque(maxlen=5)
    vision._right_buf = collections.deque(maxlen=5)
    vision._window_bufs = {side: collections.deque(maxlen=5) for side in ('left', 'right')}
    vision._map_buttons = collections.deque(maxlen=3)
    vision._buf_lock = threading.Lock()
    vision._threat_written_left = False
    vision._threat_written_right = False
    return vision


def test_clear_buffers_empties_every_queue():
    vision = make_vision()
    vision._left_buf.append(np.zeros((2, 2), dtype=np.float32))
    vision._right_buf.append(np.zeros((2, 2), dtype=np.float32))
    for buf in vision._window_bufs.values():
        buf.append(np.zeros((2, 2), dtype=np.float32))
    vision._map_buttons.append(11)

    vision.clear_buffers()

    assert len(vision._left_buf) == 0
    assert len(vision._right_buf) == 0
    assert all(len(buf) == 0 for buf in vision._window_bufs.values())
    assert len(vision._map_buttons) == 0
    assert not vision.is_camera_up() and not vision.is_camera_down()


def test_sensory_rate_does_not_crash_on_empty_buffer_after_clear():
    vision = make_vision()
    for bank in vision.banks.values():
        bank.append(np.zeros((2, 2), dtype=np.float32))
    vision.clear_buffers()

    assert vision.get_left_sensory_rate() == 0.0
    assert vision.get_right_sensory_rate() == 0.0


if __name__ == '__main__':
    test_clear_buffers_empties_every_queue()
    test_sensory_rate_does_not_crash_on_empty_buffer_after_clear()
    print('ok')
