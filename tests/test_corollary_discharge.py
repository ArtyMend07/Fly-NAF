import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
import main

FULL_RATE = config.SIMULATION_PARAMS.base_sensory_rate_hz


class PannedVision:
    def __init__(self, camera_up):
        self._camera_up = camera_up

    def is_camera_up(self):
        return self._camera_up

    def get_left_sensory_rate(self):
        return 0.0

    def get_right_sensory_rate(self):
        return 0.0


class FacingController:
    def __init__(self, side):
        self.side = side

    def facing(self):
        return self.side


def _one_pass(camera_up, facing):
    vision = PannedVision(camera_up)
    controller = FacingController(facing)
    state = main.SensoryState()
    shutdown = asyncio.Event()

    async def scenario():
        task = asyncio.create_task(main._vision_task(vision, controller, state, shutdown))
        await asyncio.sleep(0.1)
        shutdown.set()
        await task

    asyncio.run(scenario())
    return state


def test_a_pan_the_fly_caused_itself_is_not_read_as_a_raised_tablet():
    """The camera-up detector compares a fixed patch of the office against a
    reference taken with the office centred. Holding a hallway light scrolls the
    office toward that side, which moves the whole patch and reads exactly like
    a tablet unless the fly discounts its own movement."""
    for side in ('left', 'right', 'panning'):
        state = _one_pass(camera_up=True, facing=side)
        assert state.cam_inhib == 0.0, f'the inhibitors were driven while facing {side}'
        assert state.office_centred is False


def test_a_raised_tablet_still_drives_the_inhibitors_when_centred():
    state = _one_pass(camera_up=True, facing='centre')

    assert state.cam_inhib == FULL_RATE
    assert state.office_centred is True


def test_a_centred_office_with_the_tablet_down_leaves_the_brain_free():
    state = _one_pass(camera_up=False, facing='centre')

    assert state.cam_inhib == 0.0


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
