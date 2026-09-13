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

        self._left_buf: collections.deque = collections.deque(maxlen=self._buf_size)
        self._right_buf: collections.deque = collections.deque(maxlen=self._buf_size)
        self._cam_buf: collections.deque = collections.deque(maxlen=1)
        self._buf_lock = threading.Lock()
        self._threat_written_left = False
        self._threat_written_right = False
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

    def capture_camera_closed_reference(self):
        with self._buf_lock:
            frames = list(self._cam_buf)
        self._ref_camera_closed = frames[0] if frames else None

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

    def is_camera_up(self) -> bool:
        if self._ref_camera_closed is None:
            return False
        with self._buf_lock:
            frames = list(self._cam_buf)
        if not frames:
            return False
        current = frames[-1]
        mse = float(np.mean((current - self._ref_camera_closed) ** 2))
        return mse > self._cam_mse_trigger

    def _get_min_mse_from_buffer(self, ref_frame: np.ndarray, buf: collections.deque):
        with self._buf_lock:
            frames = list(buf)
        if not frames:
            return float('inf'), None
        mses = [(float(np.mean((f - ref_frame) ** 2)), f) for f in frames]
        return min(mses, key=lambda x: x[0])

    def get_left_sensory_rate(self) -> float:
        if self.ref_left is None:
            return 0.0
        mse, current = self._get_min_mse_from_buffer(self.ref_left, self._left_buf)
        if mse > self.mse_threshold:
            if not self._threat_written_left:
                cv2.imwrite(os.path.join(self.debug_dir, 'panic_left.png'), current.astype(np.uint8))
                cv2.imwrite(os.path.join(self.debug_dir, 'ref_left.png'), self.ref_left.astype(np.uint8))
                self._threat_written_left = True
            return 1.0
        self._threat_written_left = False
        return 0.0

    def get_right_sensory_rate(self) -> float:
        if self.ref_right is None:
            return 0.0
        mse, current = self._get_min_mse_from_buffer(self.ref_right, self._right_buf)
        if mse > self.mse_threshold:
            if not self._threat_written_right:
                cv2.imwrite(os.path.join(self.debug_dir, 'panic_right.png'), current.astype(np.uint8))
                cv2.imwrite(os.path.join(self.debug_dir, 'ref_right.png'), self.ref_right.astype(np.uint8))
                self._threat_written_right = True
            return 1.0
        self._threat_written_right = False
        return 0.0