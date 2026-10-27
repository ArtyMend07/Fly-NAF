import asyncio
import dataclasses
import threading

import numpy as np
import pytest
import torch

from flynaf import config
from flynaf.env import input_controller
from flynaf.env.night_end import DARK, STATIC, NightEnd, read_screen
from flynaf.night import tasks
from flynaf.night.hallway import FULL_FIELD_LOOM
from flynaf.night.state import SensoryState
from flynaf.telemetry import ConnectomeTelemetry

OFFICE, STATIC_GREY = 13.0, 40.0


def office_with_power(bars: int) -> np.ndarray:
    audit = config.NIGHT_AUDIT
    frame = np.full((720, 1280, 3), 12, dtype=np.uint8)
    top, bottom = audit.usage_bar_rows
    half = audit.usage_bar_half_width
    for centre in audit.usage_bar_centres[:bars]:
        frame[top:bottom, centre - half:centre + half] = (0, 200, 0)
    return frame


@pytest.mark.parametrize('bars, hud', [(0, False), (1, True), (3, True)])
def test_the_power_meter_tells_whether_a_night_is_on_screen(bars, hud):
    assert read_screen(office_with_power(bars))[0] is hud


def watch(readings: list, step: float = 0.25) -> list:
    night = NightEnd()
    return [night.update(hud, brightness, i * step) for i, (hud, brightness) in enumerate(readings)]


def test_the_menu_before_the_night_ends_nothing():
    assert set(watch([(False, 31.0)] * 40)) == {None}


def test_a_tablet_flip_that_hides_the_meter_for_a_moment_ends_nothing():
    readings = [(True, OFFICE)] * 4 + [(False, OFFICE)] * 2 + [(True, OFFICE)] * 4
    assert set(watch(readings)) == {None}


def test_the_static_after_a_jumpscare_ends_the_night_two_seconds_later():
    endings = watch([(True, OFFICE)] * 4 + [(False, STATIC_GREY)] * 12)
    assert endings.index(STATIC) == 4 + round(config.NIGHT_END.hud_gone_sec / 0.25)


def test_a_dark_office_stops_the_fly_and_waits_for_the_jumpscare():
    endings = watch([(True, OFFICE)] * 2 + [(False, 4.0)] * 20 + [(False, STATIC_GREY)])
    assert DARK in endings
    assert endings[-1] == STATIC


def test_no_jumpscare_within_the_wait_lets_the_fly_go():
    night = NightEnd(dataclasses.replace(config.NIGHT_END, ending_watch_sec=5.0))
    night.update(True, OFFICE, 0.0)
    for i in range(1, 40):
        night.update(False, 3.0, i * 0.25)
    assert night.ending == DARK
    assert night.gave_up(10.0)


def test_a_halted_controller_skips_every_action(monkeypatch):
    monkeypatch.setattr(input_controller, '_HALTED', threading.Event())
    assert input_controller._may_act(None, 'flip_tablet')
    input_controller.halt()
    assert not input_controller._may_act(None, 'flip_tablet')


class Endings:
    def __init__(self, endings):
        self._endings = list(endings)

    def ending(self):
        return self._endings.pop(0) if len(self._endings) > 1 else self._endings[0]

    def gave_up(self, now):
        return False


class Hands:
    def __init__(self):
        self.halted = 0

    def halt(self):
        self.halted += 1


def test_the_fly_stops_acting_once_and_learns_of_the_jumpscare(monkeypatch):
    monkeypatch.setattr(config, 'NIGHT_END', dataclasses.replace(config.NIGHT_END, check_interval_sec=0.0))
    state, hands, shutdown = SensoryState(), Hands(), asyncio.Event()
    seen = []

    async def scenario():
        task = asyncio.create_task(tasks.night_end_task(
            Endings([None, DARK, DARK, STATIC]), hands, state, shutdown, ConnectomeTelemetry()))
        for _ in range(20):
            seen.append(state.night_over)
            await asyncio.sleep(0)
        shutdown.set()
        await task

    asyncio.run(scenario())
    assert hands.halted == 1
    assert seen[-1] == STATIC and DARK in seen


class StartledEngine:
    frame_dt = 0.0
    eye_membrane_diff = explore_membrane = 0.0
    l_motor_idx, r_motor_idx = [0], [1]
    l_escape_idx, r_escape_idx = [2], [3]
    l_explore_idx = r_explore_idx = [4]
    l_sensory_idx, r_sensory_idx = [5], [6]
    l_ring_idx = r_ring_idx = [7]

    def __init__(self):
        self.seen = []

    def step(self, state, now):
        self.seen.append(dict(state.hallway_drive))
        spikes = torch.zeros(1, 8)
        if len(self.seen) >= 4:
            spikes[0, :2] = 1.0
        return spikes


class Feed:
    def __init__(self):
        self.published = 0
        self.traced = []

    def publish(self, indices, panel=None):
        self.published += 1

    def trace_escape(self, side, target, sources, door_moved):
        self.traced.append((side, target, list(sources), door_moved))


class Eyes:
    mse_threshold = 40.0

    def last_mse(self, side):
        return 0.0


class Doors:
    closed = {'left': False, 'right': False}


class Monitor:
    is_open = False


class Trace:
    def frame(self, *args):
        pass


def test_the_jumpscare_reaches_both_eyes_and_draws_each_giant_fiber_once(monkeypatch):
    monkeypatch.setattr(config, 'NIGHT_END', dataclasses.replace(config.NIGHT_END, ending_hold_sec=0.0))
    engine, feed = StartledEngine(), Feed()
    asyncio.run(tasks.the_last_look(engine, feed, Trace(), ConnectomeTelemetry(), Eyes(), Doors(), Monitor()))
    assert engine.seen == [FULL_FIELD_LOOM] * config.NIGHT_END.last_look_frames
    assert feed.published == config.NIGHT_END.last_look_frames
    assert feed.traced == [('left', 0, [5], False), ('right', 1, [6], False)]
