import collections
import threading

import cv2
import numpy as np
import pytest

from flynaf import config
from flynaf.env.tablet_map import count_camera_buttons, design_size, to_design
from flynaf.env.vision import FNAFVision

WIDTH, HEIGHT = design_size()
BUTTON_SPOTS = [(160, 15), (140, 70), (40, 95), (120, 120), (300, 120), (20, 240),
                (100, 240), (100, 285), (210, 240), (210, 285), (310, 190)]


def static(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 120, size=(HEIGHT, WIDTH)).astype(np.uint8)


def camera_map(buttons=BUTTON_SPOTS, seed: int = 0) -> np.ndarray:
    frame = static(seed)
    for x, y in buttons:
        cv2.rectangle(frame, (x, y), (x + 55, y + 33), 255, thickness=2)
        cv2.rectangle(frame, (x + 3, y + 3), (x + 52, y + 30), 70, thickness=-1)
    return frame


def office(seed: int = 0) -> np.ndarray:
    frame = static(seed) // 2
    cv2.circle(frame, (300, 80), 18, 255, thickness=-1)
    cv2.line(frame, (0, 200), (WIDTH, 220), 230, thickness=3)
    return frame


@pytest.mark.parametrize('seed', range(4))
def test_the_eleven_camera_buttons_are_counted_over_any_feed(seed):
    assert count_camera_buttons(camera_map(seed=seed)) == len(BUTTON_SPOTS)


@pytest.mark.parametrize('seed', range(4))
def test_an_office_with_bright_lamps_and_edges_holds_no_camera_button(seed):
    assert count_camera_buttons(office(seed)) == 0


def test_the_count_survives_a_window_of_another_size():
    double = cv2.resize(camera_map(), (WIDTH * 2, HEIGHT * 2), interpolation=cv2.INTER_NEAREST)

    assert count_camera_buttons(to_design(double)) == len(BUTTON_SPOTS)


def eye_on(counts: list) -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision._buf_lock = threading.Lock()
    vision._min_buttons = config.CAMERA_DETECTION.min_buttons
    vision._map_buttons = collections.deque(counts, maxlen=config.CAMERA_DETECTION.agreeing_frames)
    return vision


@pytest.mark.parametrize('counts, up, down', [
    ([11, 11, 11], True, False),
    ([0, 0, 0], False, True),
    ([0, 13, 11], False, False),
    ([11, 11], False, False),
])
def test_the_tablet_state_needs_every_recent_frame_to_agree(counts, up, down):
    vision = eye_on(counts)

    assert vision.is_camera_up() is up
    assert vision.is_camera_down() is down
