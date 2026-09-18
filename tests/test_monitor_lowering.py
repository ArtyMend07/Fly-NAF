import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main
from telemetry import ConnectomeTelemetry


class _ImmediateEvent:
    def wait(self, timeout=None):
        return True


import config

CONFIRM = config.CAMERA_DETECTION.lower_confirm_sec
BUDGET = config.CAMERA_DETECTION.lower_gesture_attempts


class ScriptedVision:
    def __init__(self, still_up_for: int):
        self.still_up_for = still_up_for
        self.checks = 0
        self.captures = 0
        self.clears = 0

    def clear_buffers(self):
        self.clears += 1

    def is_camera_up(self):
        self.checks += 1
        return self.checks <= self.still_up_for

    def capture_camera_closed_reference(self):
        self.captures += 1

    def camera_mse(self):
        return 4200.0


class RecordingController:
    def __init__(self):
        self.calls = []

    def facing(self):
        return 'centre'

    def close_camera(self, force=False):
        self.calls.append('close_camera')
        return _ImmediateEvent()

    def nudge_camera_bar(self):
        self.calls.append('nudge_camera_bar')
        return _ImmediateEvent()

    def open_camera(self):
        self.calls.append('open_camera')
        return _ImmediateEvent()


class StubExplore:
    def __init__(self, wants=False, spent=True):
        self.wants_monitor = wants
        self.spent = spent
        self.commanded = False
        self.drive = 1.2


def _lower(vision, controller, attempt=0, confirm=0.05):
    return asyncio.run(main._lower_monitor(
        vision, controller, settle_sec=0.02, confirm_sec=confirm,
        attempt=attempt, gesture_budget=BUDGET,
    ))


def test_the_reference_is_not_recaptured_while_the_tablet_is_still_up():
    vision = ScriptedVision(still_up_for=99)

    reanchored = asyncio.run(main._reanchor_office_reference(vision, 0.02, 0.05))

    assert reanchored is False
    assert vision.captures == 0


def test_the_reference_is_recaptured_once_the_office_is_back():
    vision = ScriptedVision(still_up_for=0)

    reanchored = asyncio.run(main._reanchor_office_reference(vision, 0.02, 0.05))

    assert reanchored is True
    assert vision.captures == 1
    assert vision.clears == 1


def test_one_early_reading_does_not_condemn_a_close_that_worked():
    """The gestures alternate, so declaring failure too soon makes the next
    attempt tap the bar and put the tablet straight back up. That flap is what
    left the fly blind for fifty seconds on 2026-09-17."""
    vision = ScriptedVision(still_up_for=1)
    controller = RecordingController()

    lowered = _lower(vision, controller)

    assert lowered is True
    assert controller.calls == ['close_camera']
    assert vision.captures == 1


def test_each_attempt_makes_exactly_one_gesture():
    vision = ScriptedVision(still_up_for=99)
    controller = RecordingController()

    assert _lower(vision, controller, attempt=0) is False
    assert controller.calls == ['close_camera']

    assert _lower(vision, RecordingController(), attempt=1) is False

    second = RecordingController()
    _lower(vision, second, attempt=1)
    assert second.calls == ['nudge_camera_bar']


def test_the_fly_stops_reaching_once_the_budget_is_spent():
    vision = ScriptedVision(still_up_for=99)
    controller = RecordingController()

    lowered = _lower(vision, controller, attempt=BUDGET)

    assert lowered is False
    assert controller.calls == []


def test_a_tablet_lowered_by_hand_is_picked_up_without_a_gesture():
    vision = ScriptedVision(still_up_for=0)
    controller = RecordingController()

    lowered = _lower(vision, controller, attempt=BUDGET)

    assert lowered is True
    assert controller.calls == []
    assert vision.captures == 1


async def _settle_lowering(monitor):
    while monitor._lowering is not None:
        await asyncio.wait_for(asyncio.shield(monitor._lowering), timeout=10.0)
        await asyncio.sleep(0)
        monitor.update(2000.0, StubExplore(wants=False, spent=True), 0.0, look_pending=False)


def _monitor(vision, controller):
    state = main.SensoryState()
    telemetry = ConnectomeTelemetry()
    return main.MonitorControl(vision, controller, telemetry, state), state, telemetry


def test_the_tablet_does_not_rise_while_a_look_is_pending():
    monitor, state, _ = _monitor(ScriptedVision(0), RecordingController())

    async def scenario():
        monitor.update(1000.0, StubExplore(wants=True), 0.0, look_pending=True)

    asyncio.run(scenario())

    assert monitor.is_open is False
    assert state.camera_open is False


def test_the_tablet_rises_when_nothing_else_is_running():
    controller = RecordingController()
    monitor, state, telemetry = _monitor(ScriptedVision(0), controller)

    async def scenario():
        monitor.update(1000.0, StubExplore(wants=True), 0.0, look_pending=False)

    asyncio.run(scenario())

    assert monitor.is_open is True
    assert state.camera_open is True
    assert 'open_camera' in controller.calls
    assert telemetry.stats['camera_pulls'] == 1


def test_the_tablet_stays_up_until_the_screen_confirms_it_came_down():
    vision = ScriptedVision(still_up_for=99)
    controller = RecordingController()
    monitor, state, telemetry = _monitor(vision, controller)

    async def scenario():
        monitor.update(1000.0, StubExplore(wants=True), 0.0, look_pending=False)
        bored = StubExplore(wants=False, spent=True)
        monitor.update(1002.0, bored, 0.0, look_pending=False)
        await _settle_lowering(monitor)

    asyncio.run(scenario())

    assert monitor.is_open is True
    assert state.camera_open is True
    assert telemetry.monitor_stuck == 1


def test_a_confirmed_lowering_clears_the_open_state():
    vision = ScriptedVision(still_up_for=0)
    controller = RecordingController()
    monitor, state, telemetry = _monitor(vision, controller)

    async def scenario():
        monitor.update(1000.0, StubExplore(wants=True), 0.0, look_pending=False)
        bored = StubExplore(wants=False, spent=True)
        monitor.update(1002.0, bored, 0.0, look_pending=False)
        await _settle_lowering(monitor)

    asyncio.run(scenario())

    assert monitor.is_open is False
    assert state.camera_open is False
    assert telemetry.monitor_stuck == 0
    assert len(telemetry.camera_watches) == 1


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
