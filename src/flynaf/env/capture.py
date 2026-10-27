import logging
import time

import mss
from mss.exception import ScreenShotError

_log = logging.getLogger(__name__)


def keep_capturing(grab_once, name: str, retry_sec: float):
    failing = False
    while True:
        try:
            with mss.MSS() as screen:
                while True:
                    grab_once(screen)
                    if failing:
                        _log.info('%s capture is back', name)
                        failing = False
        except ScreenShotError as exc:
            if not failing:
                _log.warning('%s capture failed, the last frame stays until it comes back: %s', name, exc)
            failing = True
            time.sleep(retry_sec)
