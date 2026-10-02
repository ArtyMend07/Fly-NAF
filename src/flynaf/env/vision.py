import collections
import json
import logging
import os
import threading
import time

import cv2
import mss
import numpy as np

from flynaf import config
from flynaf.env import anchor, desktop, hallway_bank, tablet_map

_log = logging.getLogger(__name__)

SIDES = ('left', 'right')


class FNAFVision:
    def __init__(self):
        self.mse_threshold = config.FORAGING_PARAMS.mse_threshold
        self.closed_mse_threshold = config.FORAGING_PARAMS.closed_door_mse_threshold

        self.l_x = config.VISION_CALIBRATION.left_target_x
        self.l_y = config.VISION_CALIBRATION.left_target_y
        self.l_bbox = config.VISION_CALIBRATION.left_bbox_size

        self.r_x = config.VISION_CALIBRATION.right_target_x
        self.r_y = config.VISION_CALIBRATION.right_target_y
        self.r_bbox = config.VISION_CALIBRATION.right_bbox_size

        self.windows = {
            'left': config.VISION_CALIBRATION.left_window,
            'right': config.VISION_CALIBRATION.right_window,
        }

        self._min_buttons = config.CAMERA_DETECTION.min_buttons

        self._buf_size = config.VISION_DYNAMICS.frame_buffer_size
        self._sweep_sec = config.VISION_DYNAMICS.reference_sweep_sec
        self._bank_tolerance = config.VISION_DYNAMICS.bank_tolerance_mse
        self._capture_delay = config.VISION_DYNAMICS.capture_delay_sec

        self.banks = {(side, closed): [] for side in SIDES for closed in (False, True)}
        self._distance_cache = {}

        self.debug_dir = os.path.join(config.PROJECT_ROOT, 'logs', 'vision_debug')
        os.makedirs(self.debug_dir, exist_ok=True)

        self.reference_dir = os.path.join(config.PROJECT_ROOT, 'logs', 'vision_reference')
        os.makedirs(self.reference_dir, exist_ok=True)

        self._left_buf: collections.deque = collections.deque(maxlen=self._buf_size)
        self._right_buf: collections.deque = collections.deque(maxlen=self._buf_size)
        self._window_bufs = {side: collections.deque(maxlen=self._buf_size) for side in SIDES}
        self._map_buttons: collections.deque = collections.deque(
            maxlen=config.CAMERA_DETECTION.agreeing_frames,
        )
        self._buf_lock = threading.Lock()
        self._threat_written_left = False
        self._threat_written_right = False
        self._peak_mse = {'left': 0.0, 'right': 0.0}
        self._last_mse = {'left': 0.0, 'right': 0.0}
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

    @property
    def _layout_path(self) -> str:
        return os.path.join(self.reference_dir, 'layout.txt')

    def _screen_size(self) -> tuple:
        cached = getattr(self, '_screen', None)
        if cached is None:
            try:
                cached = desktop.screen_size()
            except Exception:
                cached = (0, 0)
            self._screen = cached
        return cached

    def _grab_gray(self, sct, x: int, y: int, size: int) -> np.ndarray:
        centre_x, centre_y = anchor.point(x, y)
        size = anchor.size(size)
        offset = size // 2
        return self._grab_box(sct, centre_x - offset, centre_y - offset, size, size)

    def _grab_window(self, sct, side: str) -> np.ndarray:
        left, top, right, bottom = self.windows[side]
        screen_left, screen_top = anchor.point(left, top)
        return self._grab_box(sct, screen_left, screen_top,
                              anchor.size(right - left), anchor.size(bottom - top))

    def _grab_box(self, sct, left: int, top: int, width: int, height: int) -> np.ndarray:
        screen_w, screen_h = self._screen_size()
        if screen_w > 0 and screen_h > 0:
            left = max(0, min(left, screen_w - width))
            top = max(0, min(top, screen_h - height))
        else:
            left = max(0, left)
            top = max(0, top)
        frame = np.array(sct.grab({'top': top, 'left': left, 'width': width, 'height': height}))
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY).astype(np.float32)

    def _capture_loop(self):
        delay = config.VISION_DYNAMICS.capture_delay_sec
        with mss.MSS() as sct:
            while True:
                left_frame = self._grab_gray(sct, self.l_x, self.l_y, self.l_bbox)
                right_frame = self._grab_gray(sct, self.r_x, self.r_y, self.r_bbox)
                windows = {side: self._grab_window(sct, side) for side in SIDES}
                buttons = tablet_map.count_camera_buttons(
                    tablet_map.to_design(np.array(sct.grab(tablet_map.map_box()))),
                )
                with self._buf_lock:
                    self._left_buf.append(left_frame)
                    self._right_buf.append(right_frame)
                    for side, frame in windows.items():
                        self._window_bufs[side].append(frame)
                    self._map_buttons.append(buttons)
                time.sleep(delay)

    def _buffer(self, side: str, door_closed: bool) -> collections.deque:
        if door_closed:
            return self._window_bufs[side]
        return self._left_buf if side == 'left' else self._right_buf

    def capture_bank(self, side: str, door_closed: bool, seconds: float | None = None,
                     brightest_only: bool = False) -> int:
        bank = self.banks[(side, door_closed)]
        buf = self._buffer(side, door_closed)
        deadline = time.perf_counter() + (self._sweep_sec if seconds is None else seconds)
        added, last, brightest = 0, None, None
        while time.perf_counter() < deadline:
            with self._buf_lock:
                frame = buf[-1] if buf else None
            if frame is not None and frame is not last:
                last = frame
                if not brightest_only:
                    added += hallway_bank.add_if_new(bank, frame, self._bank_tolerance)
                elif brightest is None or frame.mean() > brightest.mean():
                    brightest = frame
            time.sleep(self._capture_delay)
        if brightest is not None:
            added += hallway_bank.add_if_new(bank, brightest, self._bank_tolerance)
        self._distance_cache.clear()
        return added

    def _layout_fingerprint(self) -> str:
        return '|'.join(str(getattr(self, name, None)) for name in (
            'l_x', 'l_y', 'l_bbox', 'r_x', 'r_y', 'r_bbox', 'windows',
        )) + '|' + str(anchor.game_rect())

    def _cached_layout_matches(self) -> bool:
        if not os.path.isfile(self._layout_path):
            return True
        with open(self._layout_path, 'r', encoding='utf-8') as handle:
            stored = handle.read().strip()
        if stored == self._layout_fingerprint():
            return True
        _log.info('the cached eye references were taken on a different layout, recapturing')
        return False

    @property
    def _bank_index_path(self) -> str:
        return os.path.join(self.reference_dir, 'banks.json')

    def load_reference_from_disk(self) -> bool:
        if not self._cached_layout_matches() or not os.path.isfile(self._bank_index_path):
            return False
        with open(self._bank_index_path, 'r', encoding='utf-8') as handle:
            counts = json.load(handle)
        loaded = {}
        for side, closed in self.banks:
            name = _bank_name(side, closed)
            shape = self._bank_shape(side, closed)
            frames = [self._load_reference_image(f'{name}_{i:02d}.png', shape)
                      for i in range(counts.get(name, 0))]
            if not frames or any(frame is None for frame in frames):
                return False
            loaded[(side, closed)] = frames
        self.banks = loaded
        self._distance_cache.clear()
        return True

    def _bank_shape(self, side: str, door_closed: bool) -> tuple:
        if door_closed:
            left, top, right, bottom = self.windows[side]
            return (anchor.size(bottom - top), anchor.size(right - left))
        size = anchor.size(self.l_bbox if side == 'left' else self.r_bbox)
        return (size, size)

    def _load_reference_image(self, filename: str, expected_shape: tuple):
        path = os.path.join(self.reference_dir, filename)
        if not os.path.isfile(path):
            return None
        frame = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if frame is None or frame.shape != expected_shape:
            return None
        return frame.astype(np.float32)

    def save_reference_to_disk(self):
        counts = {}
        for (side, closed), frames in self.banks.items():
            name = _bank_name(side, closed)
            counts[name] = len(frames)
            for i, frame in enumerate(frames):
                cv2.imwrite(os.path.join(self.reference_dir, f'{name}_{i:02d}.png'), frame.astype(np.uint8))
        with open(self._bank_index_path, 'w', encoding='utf-8') as handle:
            json.dump(counts, handle)
        with open(self._layout_path, 'w', encoding='utf-8') as handle:
            handle.write(self._layout_fingerprint())

    def clear_buffers(self):
        with self._buf_lock:
            self._left_buf.clear()
            self._right_buf.clear()
            for buf in self._window_bufs.values():
                buf.clear()
            self._map_buttons.clear()

    def light_on(self, side: str) -> bool | None:
        if not anchor.anchored():
            return None
        motor = config.MOTOR_CALIBRATION
        x, y = getattr(motor, f'{side}_light_button_x'), getattr(motor, f'{side}_light_button_y')
        half = config.VISION_DYNAMICS.light_button_half_size
        left, top = anchor.point(x - half, y - half)
        right, bottom = anchor.point(x + half, y + half)
        with mss.MSS() as screen:
            patch = np.array(screen.grab({'left': left, 'top': top,
                                          'width': max(1, right - left), 'height': max(1, bottom - top)}))
        gray = cv2.cvtColor(patch, cv2.COLOR_BGRA2GRAY)
        return float(gray.mean()) > config.VISION_DYNAMICS.light_button_lit_level

    def map_buttons(self) -> list:
        with self._buf_lock:
            return list(self._map_buttons)

    def is_camera_up(self) -> bool:
        seen = self.map_buttons()
        return len(seen) == self._map_buttons.maxlen and all(n >= self._min_buttons for n in seen)

    def is_camera_down(self) -> bool:
        seen = self.map_buttons()
        return len(seen) == self._map_buttons.maxlen and all(n < self._min_buttons for n in seen)

    def _write_threat_evidence(self, side: str, current, reference, mse: float):
        stamp = f'{side}_{time.strftime("%H%M%S")}_{int(mse)}'
        cv2.imwrite(os.path.join(self.debug_dir, f'seen_{stamp}.png'), current.astype(np.uint8))
        cv2.imwrite(os.path.join(self.debug_dir, f'ref_{stamp}.png'), reference.astype(np.uint8))

    def reset_peak_mse(self, side: str):
        self._peak_mse[side] = 0.0

    def peak_mse(self, side: str) -> float:
        return self._peak_mse[side]

    def last_mse(self, side: str) -> float:
        return self._last_mse[side]

    def latest_patches(self) -> dict:
        with self._buf_lock:
            return {
                'left': self._left_buf[-1] if self._left_buf else None,
                'right': self._right_buf[-1] if self._right_buf else None,
            }

    def get_left_sensory_rate(self, door_closed: bool = False) -> float:
        return self._sensory_rate('left', door_closed)

    def get_right_sensory_rate(self, door_closed: bool = False) -> float:
        return self._sensory_rate('right', door_closed)

    def evidence(self, side: str, door_closed: bool) -> tuple:
        bank = self.banks[(side, door_closed)]
        with self._buf_lock:
            frames = list(self._buffer(side, door_closed))
        if not bank or not frames:
            return None
        nearest = [self._nearest(frame, bank, door_closed) for frame in frames]
        middle = hallway_bank.median_index([distance for distance, _ in nearest])
        distance, reference = nearest[middle]
        return distance, frames[middle], reference

    def _nearest(self, frame, bank: list, door_closed: bool) -> tuple:
        key = (id(frame), door_closed)
        cached = self._distance_cache.get(key)
        if cached is None or cached[0] is not frame:
            cached = (frame, hallway_bank.nearest(frame, bank))
            if len(self._distance_cache) > 64:
                self._distance_cache.clear()
            self._distance_cache[key] = cached
        return cached[1]

    def _sensory_rate(self, side: str, door_closed: bool) -> float:
        seen = self.evidence(side, door_closed)
        if seen is None:
            return 0.0
        distance, current, reference = seen
        self._peak_mse[side] = max(self._peak_mse[side], distance)
        self._last_mse[side] = distance
        written = f'_threat_written_{side}'
        threshold = self.closed_mse_threshold if door_closed else self.mse_threshold
        if distance > threshold:
            if not getattr(self, written):
                label = f'{side}_closed' if door_closed else side
                self._write_threat_evidence(label, current, reference, distance)
                setattr(self, written, True)
            return 1.0
        setattr(self, written, False)
        return 0.0


def _bank_name(side: str, door_closed: bool) -> str:
    return f'{side}_closed' if door_closed else f'{side}_open'
