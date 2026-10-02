import asyncio

import pytest

from flynaf.night import monitor, tasks
from flynaf.night.doors import DoorControl
from flynaf.night.state import SensoryState
from flynaf.telemetry import ConnectomeTelemetry


class _Done:
    def wait(self, timeout=None):
        return True

    def is_set(self):
        return True


class RecordingController:
    def __init__(self):
        self.calls = []
        self.tablet_up = False

    def __getattr__(self, name):
        if name.startswith('_') or name == 'tablet_up':
            raise AttributeError(name)

        def record(*args, **kwargs):
            self.calls.append(name)
            if name == 'flip_tablet':
                self.tablet_up = not self.tablet_up
            return _Done()
        return record


class ScreenVision:
    def __init__(self, controller: RecordingController):
        self._controller = controller

    def is_camera_up(self):
        return self._controller.tablet_up

    def is_camera_down(self):
        return not self._controller.tablet_up


@pytest.fixture(autouse=True)
def quick_confirmation(monkeypatch):
    monkeypatch.setattr(monitor, 'ALREADY_THERE_SEC', 0.0)


class StubTablet:
    camera = '2A'

    def __init__(self, escape_side):
        self.escape_side = escape_side
        self.lowered = 0

    def on_raise(self, now):
        pass

    def on_lower(self):
        self.lowered += 1

    def update(self, now, explore_fired, escape_fired):
        return self.escape_side


class StubExplore:
    wants_monitor = True
    spent = False
    commanded = False
    drive = 1.2


async def _raised(escape_side='left'):
    state = SensoryState()
    controller = RecordingController()
    telemetry = ConnectomeTelemetry()
    tablet = StubTablet(escape_side)
    control = monitor.MonitorControl(ScreenVision(controller), controller, telemetry, state, tablet)
    control._confirm_sec = 0.05
    for _ in range(100):
        control.update(1.0, StubExplore(), 0.0, look_pending=False)
        if control.is_open:
            break
        await asyncio.sleep(0.01)
    doors = DoorControl(controller, telemetry, state)
    return control, doors, controller, telemetry, state, tablet


async def _escape_and_settle(escape_side='left'):
    control, doors, controller, telemetry, state, tablet = await _raised(escape_side)
    tasks.watch_the_tablet(tablet, control, doors, telemetry, state, now=2.0)
    for _ in range(300):
        control.update(3.0, StubExplore(), 0.0, look_pending=False)
        if not control.is_open:
            break
        await asyncio.sleep(0.02)
    return control, doors, controller, telemetry, state, tablet


def _run(escape_side='left'):
    return asyncio.run(_escape_and_settle(escape_side))


def test_the_tablet_is_seen_going_down_before_the_door_is_pressed():
    control, doors, controller, telemetry, state, tablet = _run('left')
    order = [call for call in controller.calls if call != 'select_camera']
    assert order[:3] == ['flip_tablet', 'flip_tablet', 'trigger_left_door'], order
    assert not control.is_open
    assert doors.closed['left'] and not doors.closed['right']
    assert state.camera_open is False


def test_the_escape_is_reported_as_its_own_release_and_door_cause():
    control, doors, controller, telemetry, state, tablet = _run('right')
    assert telemetry.camera_release_reasons['escape'] == 1
    assert telemetry.stats['right_door_panics'] == 1
    assert telemetry.tablet_escapes == {'2A right': 1}
    assert tablet.lowered >= 1


def test_no_escape_is_started_without_a_dnp04_spike():
    async def scenario():
        control, doors, controller, telemetry, state, tablet = await _raised(escape_side=None)
        tasks.watch_the_tablet(tablet, control, doors, telemetry, state, now=2.0)
        return control, doors, controller
    control, doors, controller = asyncio.run(scenario())
    assert control.is_open
    assert controller.calls == ['flip_tablet']
    assert not any(doors.closed.values())


def test_a_second_escape_waits_for_the_first_lowering():
    async def twice():
        control, doors, controller, telemetry, state, tablet = await _raised('left')
        first = control.escape(2.0, _noop)
        second = control.escape(2.1, _noop)
        await asyncio.sleep(0)
        return first, second
    assert asyncio.run(twice()) == (True, False)


async def _noop():
    return None


def test_the_giant_fiber_leaves_the_door_alone_while_the_tablet_is_up():
    state = SensoryState(camera_open=True)
    controller = RecordingController()
    doors = DoorControl(controller, ConnectomeTelemetry(), state)
    assert doors.on_giant_fiber('left', now=1.0) is False
    assert controller.calls == []
    assert not doors.refractory('left', now=1.0)


def test_a_door_is_slammed_once_and_reopened_after_the_hold_decays_and_a_look_clears_it():
    state = SensoryState()
    controller = RecordingController()
    doors = DoorControl(controller, ConnectomeTelemetry(), state)
    assert doors.on_giant_fiber('left', now=1.0) is True
    assert doors.on_giant_fiber('left', now=5.0) is False
    assert controller.calls == ['trigger_left_door']

    state.cleared_at['left'] = 9.0
    for frame in range(200):
        doors.update(now=6.0 + frame * 0.1, frame_elapsed=0.1)
    assert controller.calls == ['trigger_left_door', 'open_left_door']
    assert not doors.closed['left']


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
