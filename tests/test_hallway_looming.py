import asyncio
import collections
import dataclasses
import threading

import numpy as np
import pytest

from flynaf import config
from flynaf.env import hallway_bank
from flynaf.env.vision import FNAFVision
from flynaf.night import tasks
from flynaf.night.hallway import LoomingEye, ThresholdEye, build_eye, without_side
from flynaf.night.state import SensoryState

WINDOW = 0.1
SIZE = 320
EMPTY = np.full((SIZE, SIZE), 60.0, dtype=np.float32)


def with_figure(rows: slice, columns: slice, contrast: float = 30.0) -> np.ndarray:
    frame = EMPTY.copy()
    frame[rows, columns] += contrast
    return frame


def share(frame: np.ndarray) -> float:
    p = config.HALLWAY_VISION
    return hallway_bank.changed_share(frame, EMPTY, p.view_scale, p.cell_pixels, p.cell_noise_mse)


@pytest.mark.parametrize('frame, expected', [
    (EMPTY, 0.0),
    (EMPTY + 5.0, 0.0),
    (with_figure(slice(0, 160), slice(0, 160)), 0.25),
    (EMPTY + 30.0, 1.0),
])
def test_the_share_counts_the_cells_that_differ_beyond_the_noise(frame, expected):
    assert share(frame) == pytest.approx(expected)


def readings(eye: LoomingEye, shares: list, start: float = 0.0, step: float = 0.05) -> list:
    return [eye.transduce('left', value, start + i * step) for i, value in enumerate(shares)]


def test_a_figure_that_appears_drives_lplc2_with_its_size_and_lc4_once_with_its_growth():
    first, during, later = readings(LoomingEye(window_sec=WINDOW), [0.22, 0.22, 0.22, 0.22, 0.22])[::2]

    assert first['loom_size_left'] == pytest.approx(0.4)
    assert first['wide_field_left'] == pytest.approx(0.4)
    assert first['loom_speed_left'] == pytest.approx(0.22 / WINDOW / 3.0)
    assert 'loom_speed_left' not in later
    assert later['loom_size_left'] == pytest.approx(0.4)


@pytest.mark.parametrize('value', [0.0, 0.04, 0.08])
def test_a_change_below_the_floor_drives_nothing(value):
    assert LoomingEye(window_sec=WINDOW).transduce('left', value, 0.0) == {}


@pytest.mark.parametrize('value', [0.6, 0.9, 1.0])
def test_a_change_across_most_of_the_window_reaches_only_the_wide_field_neurons(value):
    assert LoomingEye(window_sec=WINDOW).transduce('right', value, 0.0) == {'wide_field_right': 1.0}


def test_a_new_look_after_a_gap_sees_the_figure_appear_again():
    eye = LoomingEye(window_sec=WINDOW)
    readings(eye, [0.3, 0.3, 0.3, 0.3])
    again = eye.transduce('left', 0.3, 3.0)
    assert again['loom_speed_left'] == pytest.approx(1.0)


def test_the_sides_keep_separate_histories():
    eye = LoomingEye(window_sec=WINDOW)
    readings(eye, [0.3, 0.3, 0.3, 0.3])
    assert 'loom_speed_right' in eye.transduce('right', 0.3, 0.16)


def vision_seeing(frames: list) -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision._buf_lock = threading.Lock()
    vision.mse_threshold = config.FORAGING_PARAMS.mse_threshold
    vision.closed_mse_threshold = config.FORAGING_PARAMS.closed_door_mse_threshold
    vision._peak_mse = {'left': 0.0, 'right': 0.0}
    vision._last_mse = {'left': 0.0, 'right': 0.0}
    vision._threat_written_left = True
    vision._threat_written_right = True
    vision._distance_cache = {}
    vision.banks = {(side, closed): [EMPTY] for side in ('left', 'right') for closed in (False, True)}
    vision._left_buf = collections.deque(frames, maxlen=5)
    vision._right_buf = collections.deque(frames, maxlen=5)
    return vision


def test_the_looming_eye_reads_the_hallway_and_keeps_the_contrast_bookkeeping():
    vision = vision_seeing([with_figure(slice(0, 320), slice(0, 120))] * 5)
    drive = LoomingEye(window_sec=WINDOW).read(vision, 'left', False, 0.0)
    assert set(drive) == {'loom_size_left', 'loom_speed_left', 'wide_field_left'}
    assert vision.peak_mse('left') > 0.0


def test_the_threshold_eye_drives_the_whole_cluster_as_before():
    figure = with_figure(slice(0, 320), slice(0, 120), contrast=60.0)
    assert ThresholdEye().read(vision_seeing([figure] * 5), 'right', False, 0.0) == {
        'eye_right': 1.0, 'wide_field_right': 1.0,
    }
    assert ThresholdEye().read(vision_seeing([EMPTY] * 5), 'right', False, 0.0) == {}


@pytest.mark.parametrize('looming, kind', [(0, ThresholdEye), (1, LoomingEye)])
def test_the_knob_picks_the_eye(looming, kind):
    assert isinstance(build_eye(dataclasses.replace(config.HALLWAY_VISION, looming=looming)), kind)


def test_a_giant_fiber_answer_clears_only_its_own_side():
    drive = {'loom_size_left': 0.4, 'loom_speed_left': 0.7, 'eye_right': 1.0}
    assert without_side(drive, 'left') == {'eye_right': 1.0}


class OfficeInView:
    def is_camera_up(self):
        return False


class FixedEye:
    def read(self, vision, side, door_closed, now):
        return {f'loom_size_{side}': 0.4, f'loom_speed_{side}': 0.7}


def test_the_vision_task_hands_the_eye_drive_to_the_brain():
    state = SensoryState(check_left=True)
    shutdown = asyncio.Event()

    async def scenario():
        task = asyncio.create_task(tasks.vision_task(OfficeInView(), None, state, shutdown, eye=FixedEye()))
        await asyncio.sleep(0.1)
        shutdown.set()
        await task

    asyncio.run(scenario())
    assert state.hallway_drive == {'loom_size_left': 0.4, 'loom_speed_left': 0.7}
    assert state.left_rate == pytest.approx(0.7)
    assert state.right_rate == 0.0
