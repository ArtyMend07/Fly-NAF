import asyncio
import collections
import threading
from unittest.mock import patch

import numpy as np
import pytest

from flynaf import config
from flynaf.env.vision import FNAFVision
from flynaf.night import calibration
from flynaf.night.doors import DoorControl
from flynaf.night.state import SensoryState
from flynaf.night.tasks import remember_a_clear_look
from flynaf.telemetry import ConnectomeTelemetry

FRAME = 0.1
SIZE = 16


class MotorEvent:
    def __init__(self, finished=True):
        self.finished = finished

    def wait(self, timeout=None):
        return self.finished

    def is_set(self):
        return self.finished


class DoorButtons:
    def __init__(self, finished=True):
        self.calls = []
        self.finished = finished

    def __getattr__(self, name):
        if name.startswith('_') or 'door' not in name:
            raise AttributeError(name)

        def press():
            self.calls.append(name)
            return MotorEvent(self.finished)
        return press


def closed_door(side='left', finished=True):
    state = SensoryState()
    buttons = DoorButtons(finished)
    telemetry = ConnectomeTelemetry()
    doors = DoorControl(buttons, telemetry, state)
    doors.on_giant_fiber(side, now=1.0)
    return doors, buttons, telemetry, state


def run_frames(doors, start: float, seconds: float):
    now = start
    for _ in range(int(seconds / FRAME)):
        now += FRAME
        doors.update(now, FRAME)
    return now


def test_a_decayed_hold_without_a_clearing_look_keeps_the_door_shut():
    doors, buttons, _, state = closed_door()

    run_frames(doors, 1.0, 20.0)

    assert doors.closed['left']
    assert state.door_closed['left']
    assert buttons.calls == ['trigger_left_door']


def test_a_clear_look_after_the_slam_opens_the_door_once_the_hold_has_decayed():
    doors, buttons, telemetry, state = closed_door()
    state.cleared_at['left'] = 2.0

    now = run_frames(doors, 1.0, 1.0)
    assert doors.closed['left'], 'the door opened while the defensive state was still high'

    run_frames(doors, now, 10.0)
    assert not doors.closed['left']
    assert not state.door_closed['left']
    assert buttons.calls == ['trigger_left_door', 'open_left_door']
    assert telemetry.stats['left_door_releases'] == 1


def test_a_clear_look_from_before_the_slam_does_not_count():
    doors, buttons, _, state = closed_door()
    state.cleared_at['left'] = 0.5

    run_frames(doors, 1.0, 20.0)

    assert doors.closed['left']


def test_a_threat_seen_through_the_window_renews_the_hold_and_voids_older_clear_looks():
    doors, buttons, telemetry, state = closed_door()
    state.cleared_at['left'] = 2.0
    now = run_frames(doors, 1.0, 2.0)

    assert doors.on_giant_fiber('left', now) is False
    run_frames(doors, now, 20.0)

    assert doors.closed['left']
    assert telemetry.stats['left_hold_renewals'] == 1
    assert buttons.calls == ['trigger_left_door']


def test_the_door_waits_for_the_tablet_to_come_down():
    doors, buttons, _, state = closed_door()
    state.cleared_at['left'] = 2.0
    state.camera_open = True

    now = run_frames(doors, 1.0, 20.0)
    assert doors.closed['left']

    state.camera_open = False
    run_frames(doors, now, FRAME)
    assert not doors.closed['left']


@pytest.mark.parametrize('finished, blind', [(False, True), (True, False)])
def test_the_eye_is_blind_only_while_the_door_is_moving(finished, blind):
    doors, _, _, state = closed_door(finished=finished)

    now = run_frames(doors, 1.0, 2.0)

    assert (state.blind_until['left'] > now) is blind


@pytest.mark.parametrize('fired, driven, blind_until, lit, clear', [
    (False, 0, 0.0, True, True),
    (True, 0, 0.0, True, False),
    (False, 3, 0.0, True, False),
    (False, 0, 99.0, True, False),
    (False, 0, 0.0, False, False),
])
def test_only_a_sighted_lit_look_that_found_nothing_counts_as_clear(fired, driven, blind_until, lit, clear):
    state = SensoryState()
    state.look_started['right'] = 10.0
    state.blind_until['right'] = blind_until

    remember_a_clear_look(state, 'right', fired, driven, lit)

    assert (state.cleared_at['right'] > 0.0) is clear


def eye_with_both_references():
    vision = FNAFVision.__new__(FNAFVision)
    vision._buf_lock = threading.Lock()
    vision.mse_threshold = config.FORAGING_PARAMS.mse_threshold
    vision.closed_mse_threshold = config.FORAGING_PARAMS.closed_door_mse_threshold
    vision._peak_mse = {'left': 0.0, 'right': 0.0}
    vision._last_mse = {'left': 0.0, 'right': 0.0}
    vision._threat_written_left = True
    vision._threat_written_right = True
    vision._distance_cache = {}
    open_view = np.zeros((SIZE, SIZE), dtype=np.float32)
    shut_view = np.full((SIZE, SIZE), 120.0, dtype=np.float32)
    vision.banks = {
        (side, closed): [shut_view if closed else open_view]
        for side in ('left', 'right') for closed in (False, True)
    }
    vision._left_buf = collections.deque([shut_view] * 3, maxlen=5)
    vision._right_buf = collections.deque([shut_view] * 3, maxlen=5)
    vision._window_bufs = {
        side: collections.deque([shut_view] * 3, maxlen=5) for side in ('left', 'right')
    }
    return vision


@pytest.mark.parametrize('side', ['left', 'right'])
def test_the_eye_compares_a_closed_door_with_what_a_closed_door_looks_like(side):
    vision = eye_with_both_references()
    read = getattr(vision, f'get_{side}_sensory_rate')

    assert read(door_closed=False) == 1.0, 'the open-door reference should see the door itself'
    assert read(door_closed=True) == 0.0, 'an empty window behind a closed door read as a threat'


@pytest.mark.parametrize('side', ['left', 'right'])
def test_a_shadow_in_the_window_behind_a_closed_door_drives_the_eye(side):
    vision = eye_with_both_references()
    shadow = np.full((SIZE, SIZE), 120.0 - 60.0, dtype=np.float32)
    vision._window_bufs[side].extend([shadow] * 3)

    assert getattr(vision, f'get_{side}_sensory_rate')(door_closed=True) == 1.0


class CalibrationRig:
    def __init__(self):
        self.order = []

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        if name == 'light_on':
            return lambda side: None

        def act(*args):
            self.order.append(name if not args or name == 'capture_bank' else f'{name}({args[0]})')
            if name == 'capture_bank':
                self.order[-1] = f'bank({args[0]}, closed={args[1]}, {"dark" if len(args) == 3 else "lit"})'
                return 1
            return MotorEvent()
        return act


@pytest.mark.parametrize('side', ['left', 'right'])
def test_the_open_hallway_is_recorded_lit_and_dark_and_the_closed_window_only_lit(side):
    rig = CalibrationRig()

    async def no_wait(_seconds):
        return None

    with patch.object(calibration.asyncio, 'sleep', new=no_wait):
        asyncio.run(calibration.calibrate_hallway(rig, rig, side, settle=0.0))

    assert rig.order == [
        f'set_{side}_light(True)', f'bank({side}, closed=False, lit)',
        f'set_{side}_light(False)', f'bank({side}, closed=False, dark)',
        f'trigger_{side}_door',
        f'set_{side}_light(True)', f'bank({side}, closed=True, lit)',
        f'set_{side}_light(False)',
        f'open_{side}_door',
    ]
