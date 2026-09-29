import asyncio
import logging

import config
from env.input_controller import FNAFController
from env.overlay import anchor_to_game, game_in_front, window_title
from env.vision import FNAFVision
from night.motor import await_motor

_log = logging.getLogger(__name__)

_WARMUP_COUNTDOWN = 10


async def calibrate_eye_references_live(vision: FNAFVision, controller: FNAFController, settle: float):
    _log.info('calibrating in %d seconds', _WARMUP_COUNTDOWN)
    for i in range(_WARMUP_COUNTDOWN, 0, -1):
        _log.info('T-%d', i)
        await asyncio.sleep(1.0)

    await await_motor(controller.set_left_light(True))
    await asyncio.sleep(settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_left_reference)
    _log.info('left reference captured')
    await await_motor(controller.set_left_light(False))

    await await_motor(controller.set_right_light(True))
    await asyncio.sleep(settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_right_reference)
    _log.info('right reference captured')
    await await_motor(controller.set_right_light(False))

    vision.save_reference_to_disk()


async def calibrate(vision: FNAFVision, controller: FNAFController, begin_night=None):
    settle = config.FORAGING_PARAMS.light_activation_settle_sec

    if begin_night is None:
        await countdown_to_the_night(config.BRAIN_VIEW.start_countdown_sec)
    else:
        await asyncio.get_event_loop().run_in_executor(None, begin_night)
    confirm_game_in_front()

    if vision.load_reference_from_disk():
        _log.info('loaded left/right eye references from disk, skipping live calibration')
    else:
        await calibrate_eye_references_live(vision, controller, settle)

    await await_motor(controller.centre_view())
    await asyncio.sleep(settle)
    vision.capture_camera_closed_reference()
    _log.info('office reference captured with the view centred')


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
