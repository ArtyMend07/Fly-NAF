import collections
import os
import sys
import threading
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from env.vision import FNAFVision


def make_vision(calib_frames=5, calib_delay=0.01) -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision.mse_threshold = 1500.0
    vision._calib_frames = calib_frames
    vision._calib_delay = calib_delay
    vision.ref_left = None
    vision.ref_right = None
    vision._ref_camera_closed = None
    vision.debug_dir = os.path.join(os.path.dirname(__file__), '_scratch_vision_debug')
    os.makedirs(vision.debug_dir, exist_ok=True)
    vision._left_buf = collections.deque(maxlen=5)
    vision._right_buf = collections.deque(maxlen=5)
    vision._cam_buf = collections.deque(maxlen=1)
    vision._buf_lock = threading.Lock()
    vision._threat_written_left = False
    vision._threat_written_right = False
    return vision


def test_clear_buffers_empties_all_three_queues():
    vision = make_vision()
    vision._left_buf.append(np.zeros((2, 2), dtype=np.float32))
    vision._right_buf.append(np.zeros((2, 2), dtype=np.float32))
    vision._cam_buf.append(np.zeros((2, 2), dtype=np.float32))

    vision.clear_buffers()

    assert len(vision._left_buf) == 0
    assert len(vision._right_buf) == 0
    assert len(vision._cam_buf) == 0


def test_capture_camera_closed_reference_waits_for_frame_after_clear():
    vision = make_vision(calib_frames=20, calib_delay=0.01)
    vision.clear_buffers()

    fresh_frame = np.full((2, 2), 42.0, dtype=np.float32)

    def populate_after_delay():
        time.sleep(0.03)
        with vision._buf_lock:
            vision._cam_buf.append(fresh_frame)

    threading.Thread(target=populate_after_delay).start()
    vision.capture_camera_closed_reference()

    assert vision._ref_camera_closed is not None
    assert np.array_equal(vision._ref_camera_closed, fresh_frame)


def test_capture_camera_closed_reference_gives_up_when_buffer_stays_empty():
    vision = make_vision(calib_frames=3, calib_delay=0.01)

    vision.capture_camera_closed_reference()

    assert vision._ref_camera_closed is None


def test_sensory_rate_does_not_crash_on_empty_buffer_after_clear():
    vision = make_vision()
    vision.ref_left = np.zeros((2, 2), dtype=np.float32)
    vision.ref_right = np.zeros((2, 2), dtype=np.float32)
    vision.clear_buffers()

    assert vision.get_left_sensory_rate() == 0.0
    assert vision.get_right_sensory_rate() == 0.0


if __name__ == '__main__':
    test_clear_buffers_empties_all_three_queues()
    test_capture_camera_closed_reference_waits_for_frame_after_clear()
    test_capture_camera_closed_reference_gives_up_when_buffer_stays_empty()
    test_sensory_rate_does_not_crash_on_empty_buffer_after_clear()
    print('ok')
