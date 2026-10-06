import asyncio
import logging

from flynaf import clock, config
from flynaf.night.monitor import put_tablet, put_tablet_down, screen_shows
from flynaf.night.motor import await_motor

_log = logging.getLogger(__name__)


async def capture_camera_references(feed, controller, vision, params=None) -> bool:
    params = params or config.TABLET_VISION
    if not await _raise_at_night_start(vision, controller, params):
        _log.warning('the camera map did not appear for the camera references, so the fly '
                     'will raise the tablet tonight without reading the feed')
        await _lower(vision, controller)
        return False

    feed.activate()
    try:
        recorded = [await _record(feed, controller, camera.name, params) for camera in params.cameras]
    finally:
        feed.deactivate()
        await _lower(vision, controller)
    return all(recorded)


async def _raise_at_night_start(vision, controller, params) -> bool:
    started = clock.now()
    if await put_tablet(vision, controller, True, config.CAMERA_DETECTION.flip_confirm_sec):
        return True
    if not await screen_shows(vision, True, params.start_raise_patience_sec):
        return False
    _log.info('the camera map came up %.1fs after the gesture, the game was still opening the night',
              clock.now() - started)
    return True


async def _record(feed, controller, camera: str, params) -> bool:
    await await_motor(controller.select_camera(camera))
    await asyncio.sleep(params.switch_settle_sec)
    return await asyncio.to_thread(feed.capture_reference, camera)


async def _lower(vision, controller):
    if not await put_tablet_down(vision, controller):
        _log.warning('the tablet stayed up after the camera references, lower it by hand')
