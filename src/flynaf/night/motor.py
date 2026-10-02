import asyncio
import logging

_log = logging.getLogger(__name__)


async def await_motor(done, timeout_sec: float = 6.0):
    finished = await asyncio.to_thread(done.wait, timeout_sec)
    if not finished:
        _log.warning('motor command did not complete within %.0fs', timeout_sec)
    return finished
