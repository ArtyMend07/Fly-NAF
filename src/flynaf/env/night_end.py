import threading
import time

import cv2
import numpy as np

from flynaf import clock, config
from flynaf.audit.hud import to_design, usage_bars
from flynaf.env import anchor, capture

DARK = 'dark'
STATIC = 'static'


def read_screen(frame: np.ndarray) -> tuple:
    design = to_design(frame)
    gray = cv2.cvtColor(design, cv2.COLOR_BGR2GRAY)
    return usage_bars(design) > 0, float(gray.mean())


class NightEnd:
    def __init__(self, params=None):
        self._p = params or config.NIGHT_END
        self._hud_seen = False
        self._gone_since = None
        self.over_at = None
        self.ending = None

    def update(self, hud: bool, brightness: float, now: float) -> str | None:
        if hud:
            self._hud_seen = True
            self._gone_since = None
            return self.ending
        if not self._hud_seen:
            return self.ending
        if self._gone_since is None:
            self._gone_since = now
        if self.ending is None and now - self._gone_since >= self._p.hud_gone_sec:
            self.ending, self.over_at = DARK, now
        if self.ending == DARK and brightness >= self._p.static_level:
            self.ending = STATIC
        return self.ending

    def gave_up(self, now: float) -> bool:
        return self.ending == DARK and now - self.over_at >= self._p.ending_watch_sec


class NightEndWatch:
    def __init__(self, params=None):
        self._p = params or config.NIGHT_END
        self._night = NightEnd(self._p)
        self._lock = threading.Lock()

    def start(self):
        threading.Thread(
            target=capture.keep_capturing,
            args=(self._grab_once, 'night end', config.VISION_DYNAMICS.capture_retry_sec),
            daemon=True,
        ).start()

    def ending(self) -> str | None:
        with self._lock:
            return self._night.ending

    def gave_up(self, now: float) -> bool:
        with self._lock:
            return self._night.gave_up(now)

    def _grab_once(self, screen):
        rect = anchor.game_rect()
        if rect is not None:
            left, top, width, height = rect
            shot = np.asarray(screen.grab({'left': left, 'top': top, 'width': width, 'height': height}))
            hud, brightness = read_screen(shot[..., :3])
            with self._lock:
                self._night.update(hud, brightness, clock.now())
        time.sleep(self._p.check_interval_sec)
