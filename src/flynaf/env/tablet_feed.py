import collections
import logging
import threading
import time

import cv2
import mss
import numpy as np

from flynaf import clock, config
from flynaf.env import anchor

_log = logging.getLogger(__name__)


def feed_size(params=None) -> tuple:
    params = params or config.TABLET_VISION
    left, top, right, bottom = params.view
    return ((right - left) // params.view_scale, (bottom - top) // params.view_scale)


def prepare(frame: np.ndarray, size: tuple) -> np.ndarray:
    gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    small = cv2.resize(gray.astype(np.float32), size, interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0)


def view_mask(params=None) -> np.ndarray:
    params = params or config.TABLET_VISION
    width, height = feed_size(params)
    left, top = params.view[:2]
    scale = params.view_scale
    mask = np.ones((height, width), bool)
    for hud_left, hud_top, hud_right, hud_bottom in params.hud:
        rows = slice(max(0, (hud_top - top) // scale), max(0, -(-(hud_bottom - top) // scale)))
        cols = slice(max(0, (hud_left - left) // scale), max(0, -(-(hud_right - left) // scale)))
        mask[rows, cols] = False
    return mask


def _overlap(frame: np.ndarray, references: np.ndarray, mask: np.ndarray, shift: int) -> tuple:
    width = frame.shape[1]
    if shift >= 0:
        ahead, behind = slice(shift, width), slice(0, width - shift)
    else:
        ahead, behind = slice(0, width + shift), slice(-shift, width)
    return frame[:, ahead], references[..., behind], mask[:, ahead] & mask[:, behind]


def _cell_means(squared: np.ndarray, mask: np.ndarray, cell: int) -> tuple:
    height, width = (squared.shape[-2] // cell) * cell, (squared.shape[-1] // cell) * cell
    rows, columns = height // cell, width // cell
    lead = squared.shape[:-2]
    sums = np.where(mask, squared, 0.0)[..., :height, :width].reshape(*lead, rows, cell, columns, cell)
    seen = mask[:height, :width].astype(np.float32).reshape(rows, cell, columns, cell).sum(axis=(1, 3))
    means = sums.sum(axis=(-3, -1)) / np.maximum(seen, 1.0)
    return means.reshape(*lead, -1), (seen > 0.6 * cell * cell).ravel()


def _global_mse(frame, references, mask, shift) -> np.ndarray:
    seen, recorded, shared = _overlap(frame, references, mask, shift)
    difference = recorded - seen
    return (difference * difference * shared).sum(axis=(-2, -1)) / max(1, int(shared.sum()))


def _nearest_alignments(frame, references, mask, params) -> list:
    reach = max(0, min(params.pan_reach // params.view_scale, frame.shape[1] // 2))
    coarse = max(1, params.pan_coarse_step)
    shifts = list(range(-reach, reach + 1, coarse))
    errors = np.stack([_global_mse(frame, references, mask, s) for s in shifts])
    best = errors.min(axis=0)
    chosen = np.argsort(best)[:max(1, params.nearest_references)]
    alignments = []
    for index in chosen:
        start = shifts[int(errors[:, index].argmin())]
        around = range(max(-reach, start - coarse + 1), min(reach, start + coarse - 1) + 1)
        reference = references[index]
        alignments.append((reference, min(around, key=lambda s: float(_global_mse(frame, reference, mask, s)))))
    return alignments


def strongest_cells(difference: np.ndarray, mask: np.ndarray, cell: int, count: int) -> float:
    means, covered = _cell_means(difference, mask, cell)
    means = np.where(covered, means, 0.0)
    if means.size == 0:
        return float(difference[mask].mean()) if mask.any() else 0.0
    return float(np.sort(means)[::-1][:count].mean())


def bank_distance(frame: np.ndarray, bank: list, mask: np.ndarray | None = None,
                  params=None) -> float:
    if not bank:
        return 0.0
    params = params or config.TABLET_VISION
    mask = np.ones(frame.shape, bool) if mask is None else mask
    distances = []
    for reference, shift in _nearest_alignments(frame, np.stack(bank), mask, params):
        seen, recorded, shared = _overlap(frame, reference, mask, shift)
        distances.append(strongest_cells(
            (recorded - seen) ** 2, shared, params.cell_pixels, params.strongest_cells,
        ))
    return min(distances)


def bank_noise(bank: list, mask: np.ndarray | None = None, params=None) -> float:
    if len(bank) < 2:
        return 0.0
    return max(
        bank_distance(frame, bank[:i] + bank[i + 1:], mask, params) for i, frame in enumerate(bank)
    )


def spread_sample(frames: list, count: int) -> list:
    if len(frames) <= count:
        return list(frames)
    step = len(frames) / count
    return [frames[int(i * step)] for i in range(count)]


class TabletFeed:
    def __init__(self, params=None):
        self._p = params or config.TABLET_VISION
        self._size = feed_size(self._p)
        self._mask = view_mask(self._p)
        self._latest: collections.deque = collections.deque(maxlen=1)
        self._lock = threading.Lock()
        self._active = threading.Event()
        self._banks: dict = {}
        self._noise: dict = {}
        self._watching = None
        self._reading = (None, None)
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def activate(self):
        self._active.set()

    def deactivate(self):
        self._active.clear()
        with self._lock:
            self._latest.clear()
            self._watching = None
            self._reading = (None, None)

    def has_reference(self, camera: str) -> bool:
        return bool(self._banks.get(camera))

    def noise(self, camera: str) -> float:
        return self._noise.get(camera, 0.0)

    def contrast(self, camera: str) -> float | None:
        with self._lock:
            self._watching = camera
            read_camera, read_contrast = self._reading
        return read_contrast if read_camera == camera else None

    def capture_reference(self, camera: str) -> bool:
        frames = self._collect(self._p.reference_sweep_sec)
        bank = spread_sample(frames, self._p.reference_frames)
        if not bank:
            _log.warning('no frames arrived from the tablet while recording camera %s', camera)
            return False
        self._banks[camera] = bank
        self._noise[camera] = bank_noise(bank, self._mask, self._p) * self._p.noise_margin
        _log.info('camera %s reference: %d frames, noise floor %.0f',
                  camera, len(bank), self._noise[camera])
        return True

    def _collect(self, seconds: float) -> list:
        frames, deadline, last = [], clock.now() + seconds, None
        while clock.now() < deadline:
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
                    camera = self._watching
                self._read(camera, frame)
                time.sleep(self._p.capture_delay_sec)

    def _read(self, camera: str | None, frame: np.ndarray):
        bank = self._banks.get(camera)
        if not bank:
            return
        contrast = bank_distance(frame, bank, self._mask, self._p)
        with self._lock:
            if self._watching == camera:
                self._reading = (camera, contrast)

    def _grab(self, screen) -> np.ndarray:
        left, top, right, bottom = self._p.view
        x0, y0 = anchor.point(left, top)
        x1, y1 = anchor.point(right, bottom)
        box = {'top': y0, 'left': x0, 'width': max(1, x1 - x0), 'height': max(1, y1 - y0)}
        return prepare(np.array(screen.grab(box)), self._size)
