import os
import threading
import time
import collections

import mss
import numpy as np
import cv2
import config


class FNAFVision:
    def __init__(self):
        self.mse_threshold = config.FORAGING_PARAMS.mse_threshold

        self.l_x = config.VISION_CALIBRATION.left_target_x
        self.l_y = config.VISION_CALIBRATION.left_target_y
        self.l_bbox = config.VISION_CALIBRATION.left_bbox_size

        self.r_x = config.VISION_CALIBRATION.right_target_x
        self.r_y = config.VISION_CALIBRATION.right_target_y
        self.r_bbox = config.VISION_CALIBRATION.right_bbox_size

        self._cam_x = config.CAMERA_DETECTION.patch_x
        self._cam_y = config.CAMERA_DETECTION.patch_y
        self._cam_size = config.CAMERA_DETECTION.patch_size
        self._cam_mse_trigger = config.CAMERA_DETECTION.mse_trigger

        self._calib_frames = config.VISION_DYNAMICS.calibration_peak_frames
        self._calib_delay = config.VISION_DYNAMICS.calibration_peak_delay_sec
        self._buf_size = config.VISION_DYNAMICS.frame_buffer_size

        self.ref_left = None
        self.ref_right = None
        self._ref_camera_closed = None

        self.debug_dir = os.path.join(config.PROJECT_ROOT, 'logs', 'vision_debug')
        os.makedirs(self.debug_dir, exist_ok=True)

        self.reference_dir = os.path.join(config.PROJECT_ROOT, 'logs', 'vision_reference')
        os.makedirs(self.reference_dir, exist_ok=True)

        self._left_buf: collections.deque = collections.deque(maxlen=self._buf_size)
        self._right_buf: collections.deque = collections.deque(maxlen=self._buf_size)
        self._cam_buf: collections.deque = collections.deque(maxlen=1)
        self._buf_lock = threading.Lock()
        self._threat_written_left = False
        self._threat_written_right = False
        self._peak_mse = {'left': 0.0, 'right': 0.0}
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

    def _grab_gray(self, sct, x: int, y: int, size: int) -> np.ndarray:
        offset = size // 2
        bbox = {'top': y - offset, 'left': x - offset, 'width': size, 'height': size}
        img = sct.grab(bbox)
        frame = np.array(img)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY).astype(np.float32)

    def _capture_loop(self):
        delay = config.VISION_DYNAMICS.capture_delay_sec
        with mss.MSS() as sct:
            while True:
                left_frame = self._grab_gray(sct, self.l_x, self.l_y, self.l_bbox)
                right_frame = self._grab_gray(sct, self.r_x, self.r_y, self.r_bbox)
                cam_frame = self._grab_gray(sct, self._cam_x, self._cam_y, self._cam_size)
                with self._buf_lock:
                    self._left_buf.append(left_frame)
                    self._right_buf.append(right_frame)
                    self._cam_buf.append(cam_frame)
                time.sleep(delay)

    def capture_left_reference(self):
        self.ref_left = self._capture_peak_reference(self._left_buf)

    def capture_right_reference(self):
        self.ref_right = self._capture_peak_reference(self._right_buf)

    def load_reference_from_disk(self) -> bool:
        left = self._load_reference_image('ref_left.png', self.l_bbox)
        right = self._load_reference_image('ref_right.png', self.r_bbox)
        if left is None or right is None:
            return False
        self.ref_left = left
        self.ref_right = right
        return True

    def _load_reference_image(self, filename: str, expected_size: int):
        path = os.path.join(self.reference_dir, filename)
        if not os.path.isfile(path):
            return None
        frame = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if frame is None or frame.shape != (expected_size, expected_size):
            return None
        return frame.astype(np.float32)

    def save_reference_to_disk(self):
        if self.ref_left is not None:
            cv2.imwrite(os.path.join(self.reference_dir, 'ref_left.png'), self.ref_left.astype(np.uint8))
        if self.ref_right is not None:
            cv2.imwrite(os.path.join(self.reference_dir, 'ref_right.png'), self.ref_right.astype(np.uint8))

    def clear_buffers(self):
        with self._buf_lock:
            self._left_buf.clear()
            self._right_buf.clear()
            self._cam_buf.clear()

    def capture_camera_closed_reference(self):
        frames = self._wait_for_frames(self._cam_buf)
        self._ref_camera_closed = frames[0] if frames else None

    def _wait_for_frames(self, buf: collections.deque) -> list:
        for _ in range(self._calib_frames):
            with self._buf_lock:
                frames = list(buf)
            if frames:
                return frames
            time.sleep(self._calib_delay)
        return []

    def _capture_peak_reference(self, buf: collections.deque) -> np.ndarray:
        best_frame = None
        max_brightness = -1.0
        for _ in range(self._calib_frames):
            with self._buf_lock:
                frames = list(buf)
            if not frames:
                time.sleep(self._calib_delay)
                continue
            frame = frames[-1]
            brightness = float(np.mean(frame))
            if brightness > max_brightness:
                max_brightness = brightness
                best_frame = frame
            time.sleep(self._calib_delay)
        return best_frame

    def camera_mse(self) -> float:
        if self._ref_camera_closed is None:
            return 0.0
        mse, current = self._get_min_mse_from_buffer(self._ref_camera_closed, self._cam_buf)
        if current is None:
            return 0.0
        return mse

    def is_camera_up(self) -> bool:
        if self._ref_camera_closed is None:
            return False
        mse, current = self._get_min_mse_from_buffer(self._ref_camera_closed, self._cam_buf)
        if current is None:
            return False
        return mse > self._cam_mse_trigger

    def _mses_against(self, ref_frame: np.ndarray, buf: collections.deque):
        with self._buf_lock:
            frames = list(buf)
        if not frames:
            return []
        return [(float(np.mean((f - ref_frame) ** 2)), f) for f in frames]

    def _get_min_mse_from_buffer(self, ref_frame: np.ndarray, buf: collections.deque):
        mses = self._mses_against(ref_frame, buf)
        if not mses:
            return float('inf'), None
        return min(mses, key=lambda x: x[0])

    def _get_peak_mse_from_buffer(self, ref_frame: np.ndarray, buf: collections.deque):
        mses = self._mses_against(ref_frame, buf)
        if not mses:
            return 0.0, None
        return max(mses, key=lambda x: x[0])

    def _write_threat_evidence(self, side: str, current, reference, mse: float):
        stamp = f'{side}_{time.strftime("%H%M%S")}_{int(mse)}'
        cv2.imwrite(os.path.join(self.debug_dir, f'seen_{stamp}.png'), current.astype(np.uint8))
        cv2.imwrite(os.path.join(self.debug_dir, f'ref_{stamp}.png'), reference.astype(np.uint8))

    def reset_peak_mse(self, side: str):
        self._peak_mse[side] = 0.0

    def peak_mse(self, side: str) -> float:
        return self._peak_mse[side]

    def get_left_sensory_rate(self) -> float:
        if self.ref_left is None:
            return 0.0
        mse, current = self._get_peak_mse_from_buffer(self.ref_left, self._left_buf)
        if current is None:
            return 0.0
        self._peak_mse['left'] = max(self._peak_mse['left'], mse)
        if mse > self.mse_threshold:
            if not self._threat_written_left:
                self._write_threat_evidence('left', current, self.ref_left, mse)
                self._threat_written_left = True
            return 1.0
        self._threat_written_left = False
        return 0.0

    def get_right_sensory_rate(self) -> float:
        if self.ref_right is None:
            return 0.0
        mse, current = self._get_peak_mse_from_buffer(self.ref_right, self._right_buf)
        if current is None:
            return 0.0
        self._peak_mse['right'] = max(self._peak_mse['right'], mse)
        if mse > self.mse_threshold:
            if not self._threat_written_right:
                self._write_threat_evidence('right', current, self.ref_right, mse)
                self._threat_written_right = True
            return 1.0
        self._threat_written_right = False
        return 0.0