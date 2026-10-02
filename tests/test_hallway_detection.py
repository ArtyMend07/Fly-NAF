import collections
import threading

import numpy as np
import pytest

from flynaf import config
from flynaf.env import hallway_bank
from flynaf.env.vision import FNAFVision

SIZE = 32
LIT = np.full((SIZE, SIZE), 20.0, dtype=np.float32)
FLICKER = np.full((SIZE, SIZE), 8.0, dtype=np.float32)
DARK = np.full((SIZE, SIZE), 5.0, dtype=np.float32)


def dim_figure_in_the_doorway() -> np.ndarray:
    frame = LIT.copy()
    frame[4:28, 6:20] = 42.0
    return frame


def eye(frames, bank=(LIT, FLICKER, DARK)) -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision._buf_lock = threading.Lock()
    vision.mse_threshold = config.FORAGING_PARAMS.mse_threshold
    vision.closed_mse_threshold = config.FORAGING_PARAMS.closed_door_mse_threshold
    vision._peak_mse = {'left': 0.0, 'right': 0.0}
    vision._last_mse = {'left': 0.0, 'right': 0.0}
    vision._threat_written_left = True
    vision._threat_written_right = True
    vision._distance_cache = {}
    vision.banks = {(side, closed): list(bank) for side in ('left', 'right') for closed in (False, True)}
    vision._left_buf = collections.deque(frames, maxlen=5)
    vision._right_buf = collections.deque(frames, maxlen=5)
    return vision


def test_a_dim_figure_too_faint_for_the_old_threshold_drives_the_eye():
    figure = dim_figure_in_the_doorway()
    assert hallway_bank.frame_distance(figure, LIT) < 1500.0

    assert eye([figure] * 5).get_left_sensory_rate() == 1.0


@pytest.mark.parametrize('frames', [
    [LIT] * 5,
    [FLICKER] * 5,
    [DARK] * 5,
    [LIT, FLICKER, LIT, DARK, LIT],
])
def test_every_view_calibrated_at_midnight_reads_as_empty(frames):
    vision = eye(frames)

    assert vision.get_left_sensory_rate() == 0.0
    assert vision.peak_mse('left') < vision.mse_threshold


def test_a_flicker_frame_cannot_hide_a_figure_that_stays():
    figure = dim_figure_in_the_doorway()

    assert eye([figure, figure, FLICKER, figure, figure]).get_right_sensory_rate() == 1.0


def test_a_single_odd_frame_does_not_make_a_threat():
    figure = dim_figure_in_the_doorway()

    assert eye([LIT, LIT, figure, LIT, LIT]).get_left_sensory_rate() == 0.0


def test_a_flicker_left_out_of_the_bank_is_still_absorbed_when_it_is_brief():
    vision = eye([LIT, FLICKER, LIT, FLICKER, LIT], bank=(LIT, DARK))

    assert vision.get_left_sensory_rate() == 0.0


def test_the_threshold_sits_under_bonnie_as_measured_in_a_live_night():
    """On 2026-10-01 Bonnie in the lit left doorway was 124 from the lit view and
    118 from the flicker view, while every empty frame matched one of them exactly."""
    assert 0.0 < config.FORAGING_PARAMS.mse_threshold < 118.0 / 2
    assert 0.0 < config.FORAGING_PARAMS.closed_door_mse_threshold < 118.0
