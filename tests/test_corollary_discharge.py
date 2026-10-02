import asyncio

import pytest

from flynaf import config
from flynaf.night import tasks
from flynaf.night.state import SensoryState

FULL_RATE = config.SIMULATION_PARAMS.base_sensory_rate_hz


class MapOnScreen:
    def __init__(self, camera_up):
        self._camera_up = camera_up

    def is_camera_up(self):
        return self._camera_up

    def get_left_sensory_rate(self, door_closed=False):
        return 0.0

    def get_right_sensory_rate(self, door_closed=False):
        return 0.0


def one_pass(camera_up, state=None):
    state = state or SensoryState()
    shutdown = asyncio.Event()

    async def scenario():
        task = asyncio.create_task(tasks.vision_task(MapOnScreen(camera_up), None, state, shutdown))
        await asyncio.sleep(0.1)
        shutdown.set()
        await task

    asyncio.run(scenario())
    return state


@pytest.mark.parametrize('camera_up, inhibitors', [(True, FULL_RATE), (False, 0.0)])
def test_the_inhibitors_follow_the_camera_map_on_screen(camera_up, inhibitors):
    state = one_pass(camera_up)

    assert state.tablet_seen is camera_up
    assert state.cam_inhib == inhibitors


def test_the_screen_wins_over_what_the_fly_believes():
    state = one_pass(camera_up=True, state=SensoryState(camera_open=False))

    assert state.cam_inhib == FULL_RATE
