import asyncio
import logging

from flynaf import config
from flynaf.night.motor import await_motor

_log = logging.getLogger(__name__)


async def screen_disagrees(vision, side: str, on: bool) -> bool:
    interval = config.VISION_DYNAMICS.light_check_interval_sec
    for _ in range(2):
        seen = await asyncio.to_thread(vision.light_on, side)
        if seen is None or seen == on:
            return False
        await asyncio.sleep(interval)
    return True


async def set_light(vision, controller, side: str, on: bool, corrections: int = 2) -> bool:
    await await_motor(getattr(controller, f'set_{side}_light')(on))
    for _ in range(corrections):
        if not await screen_disagrees(vision, side, on):
            return True
        _log.warning('the %s light button reads %s on screen, pressing it again',
                     side, 'off' if on else 'on')
        await await_motor(getattr(controller, f'press_{side}_light')(on))
    return not await screen_disagrees(vision, side, on)
