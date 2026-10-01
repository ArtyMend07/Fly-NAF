import asyncio
import logging

from flynaf import config
from flynaf.night.monitor import lower_monitor
from flynaf.night.motor import await_motor

_log = logging.getLogger(__name__)


async def capture_camera_references(feed, controller, vision, params=None) -> bool:
    params = params or config.TABLET_VISION
    await await_motor(controller.open_camera())
    await asyncio.sleep(params.raise_settle_sec)
    if not vision.is_camera_up():
        _log.warning('the tablet did not come up for the camera references, so the fly '
                     'will raise it tonight without reading the feed')
        await put_tablet_down(vision, controller)
        return False

    feed.activate()
    try:
        recorded = [await _record(feed, controller, camera.name, params) for camera in params.cameras]
    finally:
        feed.deactivate()
        await put_tablet_down(vision, controller)
    return all(recorded)


async def _record(feed, controller, camera: str, params) -> bool:
    await await_motor(controller.select_camera(camera))
    await asyncio.sleep(params.switch_settle_sec)
    return await asyncio.get_event_loop().run_in_executor(None, feed.capture_reference, camera)


async def put_tablet_down(vision, controller) -> bool:
    detection = config.CAMERA_DETECTION
    for attempt in range(detection.lower_gesture_attempts):
        if await lower_monitor(
            vision, controller, detection.close_settle_sec, detection.lower_confirm_sec,
            attempt, detection.lower_gesture_attempts,
        ):
            return True
    _log.warning('the tablet stayed up after the camera references, lower it by hand')
    return False
