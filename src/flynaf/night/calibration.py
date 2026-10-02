import asyncio
import logging

from flynaf import config
from flynaf.env.input_controller import FNAFController
from flynaf.env.overlay import anchor_to_game, game_in_front, window_title
from flynaf.env.vision import FNAFVision
from flynaf.night.lights import set_light
from flynaf.night.monitor import put_tablet_down
from flynaf.night.motor import await_motor
from flynaf.night.tablet.references import capture_camera_references

_log = logging.getLogger(__name__)

_WARMUP_COUNTDOWN = 10


async def calibrate_eye_references_live(vision: FNAFVision, controller: FNAFController, settle: float):
    _log.info('calibrating in %d seconds', _WARMUP_COUNTDOWN)
    for i in range(_WARMUP_COUNTDOWN, 0, -1):
        _log.info('T-%d', i)
        await asyncio.sleep(1.0)

    for side in ('left', 'right'):
        await calibrate_hallway(vision, controller, side, settle)
    vision.save_reference_to_disk()


async def calibrate_hallway(vision: FNAFVision, controller: FNAFController, side: str, settle: float):
    door_settle = settle + config.DOOR_DYNAMICS.motion_settle_sec
    for door_closed in (False, True):
        if door_closed:
            await await_motor(getattr(controller, f'trigger_{side}_door')())
            await asyncio.sleep(door_settle)
        await record_hallway_views(vision, controller, side, door_closed, settle)
    await await_motor(getattr(controller, f'open_{side}_door')())
    await asyncio.sleep(door_settle)


async def record_hallway_views(vision: FNAFVision, controller: FNAFController, side: str,
                               door_closed: bool, settle: float):
    if not await set_light(vision, controller, side, True):
        _log.warning('the %s light did not come on while its references were recorded', side)
    await asyncio.sleep(settle)
    lit = await asyncio.to_thread(vision.capture_bank, side, door_closed, None, door_closed)
    await set_light(vision, controller, side, False)
    await asyncio.sleep(settle)
    if door_closed:
        _log.info('%s window behind the closed door: %d lit view', side, lit)
        return
    dark = await asyncio.to_thread(vision.capture_bank, side, door_closed, settle)
    _log.info('%s hallway with the door open: %d lit views and %d dark', side, lit, dark)


async def calibrate(vision: FNAFVision, controller: FNAFController, begin_night=None, tablet_feed=None):
    settle = config.FORAGING_PARAMS.light_activation_settle_sec

    if begin_night is None:
        await countdown_to_the_night(config.BRAIN_VIEW.start_countdown_sec)
    else:
        await asyncio.to_thread(begin_night)
    confirm_game_in_front()
    await start_with_the_tablet_down(vision, controller)

    if vision.load_reference_from_disk():
        _log.info('loaded left/right eye references from disk, skipping live calibration')
    else:
        await calibrate_eye_references_live(vision, controller, settle)

    if tablet_feed is not None and await capture_camera_references(tablet_feed, controller, vision):
        _log.info('camera references captured for %s',
                  ', '.join(camera.name for camera in config.TABLET_VISION.cameras))


async def start_with_the_tablet_down(vision: FNAFVision, controller: FNAFController):
    if await put_tablet_down(vision, controller):
        return
    _log.warning('the camera map is still on screen after %d gestures, lower the tablet by hand',
                 config.CAMERA_DETECTION.lower_gesture_attempts)


async def countdown_to_the_night(seconds: float):
    _log.info('the panel is up. Go to the game and start the night, beginning in %.0fs', seconds)
    remaining = int(seconds)
    while remaining > 0:
        await asyncio.sleep(1.0)
        remaining -= 1
        if remaining and (remaining <= 3 or remaining % 5 == 0):
            _log.info('T-%d', remaining)


def confirm_game_in_front():
    game = game_in_front()
    if game:
        _log.info('starting, the night is on screen in %r', window_title(game) or '<untitled>')
        anchor_to_game()
        return
    _log.warning(
        'starting anyway, but %s is not the window in front, so every capture will read '
        'whatever is', config.BRAIN_VIEW.game_process,
    )
