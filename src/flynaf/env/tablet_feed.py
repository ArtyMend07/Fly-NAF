import collections
import logging
import threading
import time

import cv2
import mss
import numpy as np

from flynaf import config
from flynaf.env import anchor

_log = logging.getLogger(__name__)


def prepare(frame: np.ndarray, pixels: int) -> np.ndarray:
    gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    small = cv2.resize(gray.astype(np.float32), (pixels, pixels), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0)


def bank_distance(frame: np.ndarray, bank: list) -> float:
    if not bank:
        return 0.0
    return min(float(np.mean((frame - reference) ** 2)) for reference in bank)


def bank_noise(bank: list) -> float:
    if len(bank) < 2:
        return 0.0
    return max(bank_distance(frame, bank[:i] + bank[i + 1:]) for i, frame in enumerate(bank))


def spread_sample(frames: list, count: int) -> list:
    if len(frames) <= count:
        return list(frames)
    step = len(frames) / count
    return [frames[int(i * step)] for i in range(count)]


class TabletFeed:
    def __init__(self, params=None):
        self._p = params or config.TABLET_VISION
        self._latest: collections.deque = collections.deque(maxlen=1)
        self._lock = threading.Lock()
        self._active = threading.Event()
        self._banks: dict = {}
        self._noise: dict = {}
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def activate(self):
        self._active.set()

    def deactivate(self):
        self._active.clear()
        with self._lock:
            self._latest.clear()

    def has_reference(self, camera: str) -> bool:
        return bool(self._banks.get(camera))

    def noise(self, camera: str) -> float:
        return self._noise.get(camera, 0.0)

    def contrast(self, camera: str) -> float | None:
        bank = self._banks.get(camera)
        with self._lock:
            frame = self._latest[-1] if self._latest else None
        if not bank or frame is None:
            return None
        return bank_distance(frame, bank)

    def capture_reference(self, camera: str) -> bool:
        frames = self._collect(self._p.reference_sweep_sec)
        bank = spread_sample(frames, self._p.reference_frames)
        if not bank:
            _log.warning('no frames arrived from the tablet while recording camera %s', camera)
            return False
        self._banks[camera] = bank
        self._noise[camera] = bank_noise(bank) * self._p.noise_margin
        _log.info('camera %s reference: %d frames, noise floor %.0f mse',
                  camera, len(bank), self._noise[camera])
        return True

    def _collect(self, seconds: float) -> list:
        frames, deadline, last = [], time.time() + seconds, None
        while time.time() < deadline:
            with self._lock:
                frame = self._latest[-1] if self._latest else None
            if frame is not None and frame is not last:
                frames.append(frame)
                last = frame
            time.sleep(self._p.capture_delay_sec)
        return frames

    def _capture_loop(self):
        with mss.MSS() as screen:
            while True:
                self._active.wait()
                frame = self._grab(screen)
                with self._lock:
                    if self._active.is_set():
                        self._latest.append(frame)
                time.sleep(self._p.capture_delay_sec)

    def _grab(self, screen) -> np.ndarray:
        centre_x, centre_y = anchor.point(self._p.feed_x, self._p.feed_y)
        size = anchor.size(self._p.feed_size)
        box = {'top': max(0, centre_y - size // 2), 'left': max(0, centre_x - size // 2),
               'width': size, 'height': size}
        return prepare(np.array(screen.grab(box)), self._p.feed_pixels)
