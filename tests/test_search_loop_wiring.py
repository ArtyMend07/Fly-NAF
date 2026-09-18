"""Drives the real `_engine_task` and `_saccade_task` against fakes.

The unit tests cover the decision; this covers the hand-off between the loop
that decides and the loop that acts, which is where the old design went wrong:
the decision used to live inside the coroutine that blocks for two seconds
every time the fly looks at something.
"""
import asyncio
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch

import config
import main
from telemetry import ConnectomeTelemetry

NEURONS = 8
TYPICAL = 30.0


class FakeEngine:
    """Replays a drift of the shape the real eye populations produce, and never
    fires a motor neuron, so only the search path can act.

    The drift is written against the wall clock rather than the iteration
    count, because that is the axis the accumulator's time constants live on.
    Its sign holds for two seconds, as measured, and its amplitude rises after
    a while: a swing of unchanging size can never reach the bound by design,
    so a fake that produced one would prove nothing.
    """

    def __init__(self):
        self.frame_dt = 0.01
        self.eye_membrane_diff = 0.0
        # Flat, so the monitor decision never fires and only the search path
        # can move the fly in this test.
        self.explore_membrane = -230.0
        self.sensory_span = 100
        self.l_motor_idx = [0]
        self.r_motor_idx = [1]
        self.explore_idx = [2]
        self.l_sensory_idx = [3]
        self.r_sensory_idx = [4]
        self.frames = 0
        self.driven_frames = {'left': 0, 'right': 0}
        self._t0 = None

    def step(self, state, now):
        self.frames += 1
        if self._t0 is None:
            self._t0 = now
        age = now - self._t0
        sign = 1.0 if int(age / 2.0) % 2 == 0 else -1.0
        amplitude = TYPICAL if age < 4.0 else 3.0 * TYPICAL
        self.eye_membrane_diff = amplitude * sign
        return torch.zeros(1, NEURONS)


class FakeController:
    def facing(self):
        return 'centre'

    def __init__(self, state=None):
        self.calls = []
        self.log = []
        self.tablet = []
        self._state = state

    def _done(self, name):
        self.calls.append(name)
        # Recording the gaze flags at the moment of each click is what makes the
        # ordering checkable: turn the light on, confirm it, *then* open the eye.
        gaze = None
        if self._state is not None:
            if self._state.check_left:
                gaze = 'left'
            elif self._state.check_right:
                gaze = 'right'
        self.log.append((name, gaze))
        self.tablet.append((name, bool(self._state and self._state.camera_open)))
        return _ImmediateEvent()

    def set_left_light(self, on):
        return self._done(f'left_light_{"on" if on else "off"}')

    def set_right_light(self, on):
        return self._done(f'right_light_{"on" if on else "off"}')

    def open_left_door(self):
        return self._done('open_left_door')

    def open_right_door(self):
        return self._done('open_right_door')

    def trigger_left_door(self):
        return self._done('trigger_left_door')

    def trigger_right_door(self):
        return self._done('trigger_right_door')

    def centre_view(self):
        return self._done('centre_view')

    def open_camera(self):
        return self._done('open_camera')

    def close_camera(self, force=False):
        return self._done('close_camera')

    def nudge_camera_bar(self):
        return self._done('nudge_camera_bar')


class _ImmediateEvent:
    def wait(self, timeout=None):
        return True


class FakeVision:
    def __init__(self):
        self.peaks = {'left': 0.0, 'right': 0.0}
        self.ref_left = None
        self.ref_right = None

    def reset_peak_mse(self, side):
        self.peaks[side] = 0.0

    def peak_mse(self, side):
        return self.peaks[side]

    def is_camera_up(self):
        return False

    def get_left_sensory_rate(self):
        return 0.0

    def get_right_sensory_rate(self):
        return 0.0

    def camera_mse(self):
        return 0.0

    def clear_buffers(self):
        pass

    def load_reference_from_disk(self):
        return True

    def capture_camera_closed_reference(self):
        pass


class FakeFeed:
    def publish(self, indices):
        pass


class ExploringEngine(FakeEngine):
    def step(self, state, now):
        spikes = super().step(state, now)
        age = now - self._t0
        swing = 1.0 if int(age / 1.5) % 2 == 0 else -1.0
        self.explore_membrane = -230.0 + swing * (2.0 if age < 3.0 else 9.0)
        return spikes


async def _office_is_up(_seconds):
    return None


async def _play(seconds: float, engine=None):
    engine = engine or FakeEngine()
    state = main.SensoryState()
    controller = FakeController(state)
    saccade = main.SaccadeRequest()
    telemetry = ConnectomeTelemetry()
    shutdown = asyncio.Event()
    calibrated = asyncio.Event()
    calibrated.set()

    gaze = []

    async def watch_gaze():
        while not shutdown.is_set():
            if state.check_left:
                gaze.append('left')
            elif state.check_right:
                gaze.append('right')
            await asyncio.sleep(engine.frame_dt / 2)

    async def stop():
        await asyncio.sleep(seconds)
        shutdown.set()

    vision_task = asyncio.create_task(main._vision_task(
        FakeVision(), controller, state, shutdown,
    ))
    engine_task = asyncio.create_task(main._engine_task(
        engine, FakeVision(), controller, state, shutdown, telemetry,
        calibrated, FakeFeed(), {}, saccade,
    ))
    view_ready = asyncio.Event()
    view_ready.set()
    saccade_task = asyncio.create_task(main._saccade_task(
        engine, FakeVision(), controller, state, shutdown, telemetry, calibrated,
        saccade, view_ready,
    ))
    watcher = asyncio.create_task(watch_gaze())
    await stop()
    for task in (engine_task, saccade_task, watcher, vision_task):
        task.cancel()
    results = await asyncio.gather(
        engine_task, saccade_task, watcher, vision_task, return_exceptions=True
    )
    # A task that dies here would otherwise leave the fly simply not looking,
    # with nothing to say why. That is the failure mode this whole file exists
    # to catch, so it must never be swallowed.
    for outcome in results:
        if isinstance(outcome, BaseException) and not isinstance(outcome, asyncio.CancelledError):
            raise outcome
    return controller, telemetry, gaze


def _run(seconds, engine=None):
    with patch.object(main, '_countdown_to_the_night', new=_office_is_up):
        return asyncio.run(_play(seconds, engine))


def test_no_light_check_runs_while_the_tablet_is_up():
    controller, telemetry, _ = _run(30.0, ExploringEngine())
    assert telemetry.stats['camera_pulls'] > 0, 'the tablet never went up in this scenario'
    offenders = [name for name, up in controller.tablet if up and 'light' in name]
    assert not offenders, f'the fly reached for the lights with the tablet up: {offenders}'


def test_the_loop_actually_produces_looks():
    controller, telemetry, gaze = _run(12.0)
    looks = telemetry.stats['left_light_saccades'] + telemetry.stats['right_light_saccades']
    assert looks > 0, 'the engine loop never asked for a single look'
    assert gaze, 'the light went on but the eye was never opened'


def test_the_light_goes_on_before_the_eye_opens_and_off_after():
    """The sequence the operator asked for: switch the light on, confirm it
    reached the game, look down the hallway, and only then take the next
    action. The complaint that started this was a fly whose light appeared to
    come on after it had already turned away."""
    controller, telemetry, gaze = _run(12.0)
    lights = [(name, seen) for name, seen in controller.log if 'light' in name]
    assert lights, 'no light was ever switched'
    assert lights[0][0].endswith('_on'), f'first light call was {lights[0][0]}'

    for name, seen in lights:
        side = name.split('_')[0]
        if name.endswith('_on'):
            assert seen is None, f'the eye was already open on the {seen} when {name} fired'
        else:
            assert seen != side, f'{name} fired while still looking at the {side}'

    # never two ons in a row: one look is fully finished before the next starts
    for earlier, later in zip(lights, lights[1:]):
        assert earlier[0].endswith('_on') != later[0].endswith('_on'), f'{earlier} then {later}'


def test_both_hallways_get_looked_at():
    _, telemetry, _ = _run(20.0)
    assert telemetry.stats['left_light_saccades'] > 0
    assert telemetry.stats['right_light_saccades'] > 0


def test_the_report_says_who_decided():
    _, telemetry, _ = _run(20.0)
    assert sum(telemetry.saccade_reasons.values()) > 0
    guard = telemetry.saccade_reasons['guard']
    total = sum(telemetry.saccade_reasons.values())
    assert guard < total, 'every look came from the clock again'


def test_no_second_look_is_requested_while_one_is_running():
    """The request slot is the interlock; without it the engine loop would keep
    posting sides at 10 Hz and the effector would run them back to back."""
    controller, _, _ = _run(12.0)
    lights = [c for c in controller.calls if 'light' in c]
    on_calls = [c for c in lights if c.endswith('_on')]
    off_calls = [c for c in lights if c.endswith('_off')]
    assert abs(len(on_calls) - len(off_calls)) <= 1


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
