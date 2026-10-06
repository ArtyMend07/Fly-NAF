import asyncio

import pytest

from flynaf.night import monitor
from flynaf.night.state import SensoryState
from flynaf.telemetry import ConnectomeTelemetry


class Done:
    def wait(self, timeout=None):
        return True


class Screen:
    def __init__(self, up=False, ignored_flips=0):
        self.up = up
        self.ignored_flips = ignored_flips

    def is_camera_up(self):
        return self.up

    def is_camera_down(self):
        return not self.up


class Bar:
    def __init__(self, screen: Screen):
        self.screen = screen
        self.flips = 0

    def flip_tablet(self):
        self.flips += 1
        if self.screen.ignored_flips:
            self.screen.ignored_flips -= 1
        else:
            self.screen.up = not self.screen.up
        return Done()


class StubExplore:
    def __init__(self, wants=False, spent=True):
        self.wants_monitor = wants
        self.spent = spent
        self.commanded = False
        self.drive = 1.2


@pytest.fixture(autouse=True)
def quick_confirmation(monkeypatch):
    monkeypatch.setattr(monitor, 'ALREADY_THERE_SEC', 0.0)


def put(screen, up):
    bar = Bar(screen)
    reached = asyncio.run(monitor.put_tablet(screen, bar, up, confirm_sec=0.05))
    return reached, bar.flips


@pytest.mark.parametrize('start_up, wanted_up', [(False, True), (True, False)])
def test_one_gesture_puts_the_tablet_where_it_is_wanted(start_up, wanted_up):
    screen = Screen(up=start_up)

    assert put(screen, wanted_up) == (True, 1)
    assert screen.up is wanted_up


@pytest.mark.parametrize('up', [True, False])
def test_no_gesture_when_the_screen_already_shows_the_wanted_state(up):
    assert put(Screen(up=up), up) == (True, 0)


def test_a_gesture_the_game_ignored_is_reported_as_a_miss():
    screen = Screen(up=True, ignored_flips=1)

    assert put(screen, False) == (False, 1)
    assert screen.up is True


def test_putting_the_tablet_down_retries_until_the_screen_agrees():
    screen = Screen(up=True, ignored_flips=2)
    bar = Bar(screen)

    lowered = asyncio.run(monitor.put_tablet_down(screen, bar, attempts=4))

    assert lowered is True
    assert bar.flips == 3


def control(screen, state=None):
    state = state or SensoryState()
    telemetry = ConnectomeTelemetry()
    bar = Bar(screen)
    control_ = monitor.MonitorControl(screen, bar, telemetry, state)
    control_._confirm_sec = 0.05
    return control_, state, telemetry, bar


async def settle(control_, now, explore):
    for _ in range(50):
        control_._state.tablet_seen = control_._vision.up
        control_.update(now, explore, 0.0, look_pending=False)
        if control_._gesture is None:
            return
        await asyncio.sleep(0.01)


def test_the_tablet_does_not_rise_while_a_look_is_pending():
    control_, state, _, bar = control(Screen())

    async def scenario():
        control_.update(1000.0, StubExplore(wants=True), 0.0, look_pending=True)

    asyncio.run(scenario())

    assert bar.flips == 0
    assert control_.is_open is False


def test_the_fly_only_believes_the_tablet_is_up_once_the_map_is_on_screen():
    control_, state, telemetry, bar = control(Screen())

    async def scenario():
        await settle(control_, 1000.0, StubExplore(wants=True))

    asyncio.run(scenario())

    assert control_.is_open is True
    assert state.camera_open is True
    assert telemetry.stats['camera_pulls'] == 1


def test_a_raise_the_game_ignored_leaves_the_fly_believing_the_tablet_is_down():
    control_, state, telemetry, _ = control(Screen(ignored_flips=1))

    async def scenario():
        await settle(control_, 1000.0, StubExplore(wants=True))

    asyncio.run(scenario())

    assert control_.is_open is False
    assert state.camera_open is False
    assert telemetry.raises_missed == 1


def test_a_lowering_counts_only_when_the_map_has_left_the_screen():
    screen = Screen()
    control_, state, telemetry, _ = control(screen)

    async def scenario():
        await settle(control_, 1000.0, StubExplore(wants=True))
        screen.ignored_flips = 1
        await settle(control_, 1002.0, StubExplore(wants=False, spent=True))
        assert control_.is_open is True
        await settle(control_, 1010.0, StubExplore(wants=False, spent=True))

    asyncio.run(scenario())

    assert telemetry.monitor_stuck == 1
    assert control_.is_open is False
    assert state.camera_open is False
    assert screen.up is False


def test_a_tablet_found_on_screen_behind_the_flys_back_is_put_away():
    screen = Screen(up=True)
    control_, _, telemetry, bar = control(screen)

    async def scenario():
        await settle(control_, 1000.0, StubExplore(wants=False))

    asyncio.run(scenario())

    assert screen.up is False
    assert bar.flips == 1
    assert telemetry.tablet_found_up == 1
    assert control_.is_open is False


@pytest.mark.parametrize('ignored, door_closed', [(0, True), (2, False)])
def test_the_escape_closes_the_door_only_after_the_tablet_is_down(ignored, door_closed):
    screen = Screen()
    control_, _, _, _ = control(screen)
    closed = []

    async def reflex():
        assert screen.up is False
        closed.append(True)

    async def scenario():
        await settle(control_, 1000.0, StubExplore(wants=True))
        screen.ignored_flips = ignored
        control_.escape(1001.0, reflex)
        await control_._gesture[1]

    asyncio.run(scenario())

    assert bool(closed) is door_closed


@pytest.mark.parametrize('watched, still_open', [(1.0, True), (3.1, True), (3.3, False)])
def test_the_fly_only_tires_of_a_camera_after_it_could_read_it(watched, still_open):
    screen = Screen()
    control_, state, _, _ = control(screen)

    async def scenario():
        await settle(control_, 1000.0, StubExplore(wants=True))
        state.tablet_readable_at = 1000.0 + 1.2
        await settle(control_, 1000.0 + watched, StubExplore(wants=False, spent=True))

    asyncio.run(scenario())

    assert control_.is_open is still_open
