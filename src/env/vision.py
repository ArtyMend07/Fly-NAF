import os
import mss
import time
import numpy as np
import cv2
import config

class FNAFVision:
    def __init__(self):
        self.sct = mss.MSS()
        self.mse_threshold = config.FORAGING_PARAMS["mse_threshold"]

        self.l_x = config.VISION_CALIBRATION["left_target_x"]
        self.l_y = config.VISION_CALIBRATION["left_target_y"]
        self.l_bbox = config.VISION_CALIBRATION["left_bbox_size"]

        self.r_x = config.VISION_CALIBRATION["right_target_x"]
        self.r_y = config.VISION_CALIBRATION["right_target_y"]
        self.r_bbox = config.VISION_CALIBRATION["right_bbox_size"]

        self._calib_frames = config.VISION_DYNAMICS["calibration_peak_frames"]
        self._calib_delay = config.VISION_DYNAMICS["calibration_peak_delay_sec"]
        self._int_frames = config.VISION_DYNAMICS["flicker_integration_frames"]
        self._int_delay = config.VISION_DYNAMICS["flicker_integration_delay_sec"]

        self.ref_left = None
        self.ref_right = None
        
        self.debug_dir = os.path.join(config.PROJECT_ROOT, "logs", "vision_debug")
        os.makedirs(self.debug_dir, exist_ok=True)

    def _grab_gray(self, x: int, y: int, size: int) -> np.ndarray:
        offset = size // 2
        bbox = {"top": y - offset, "left": x - offset, "width": size, "height": size}
        img = self.sct.grab(bbox)
        frame = np.array(img)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY).astype(np.float32)

    def _capture_peak_reference(self, x: int, y: int, size: int) -> np.ndarray:
        best_frame = None
        max_brightness = -1.0
        for _ in range(self._calib_frames):
            frame = self._grab_gray(x, y, size)
            brightness = float(np.mean(frame))
            if brightness > max_brightness:
                max_brightness = brightness
                best_frame = frame
            time.sleep(self._calib_delay)
        return best_frame

    def _get_temporal_mse(self, ref_frame: np.ndarray, x: int, y: int, size: int):
        min_mse = float("inf")
        brightest_current = None
        for _ in range(self._int_frames):
            current = self._grab_gray(x, y, size)
            mse = float(np.mean((current - ref_frame) ** 2))
            if mse < min_mse:
                min_mse = mse
                brightest_current = current
            time.sleep(self._int_delay)
        return min_mse, brightest_current

    def capture_left_reference(self):
        self.ref_left = self._capture_peak_reference(self.l_x, self.l_y, self.l_bbox)

    def capture_right_reference(self):
        self.ref_right = self._capture_peak_reference(self.r_x, self.r_y, self.r_bbox)

    def get_left_sensory_rate(self) -> float:
        if self.ref_left is None:
            return 0.0
        mse, current = self._get_temporal_mse(self.ref_left, self.l_x, self.l_y, self.l_bbox)
        if mse > self.mse_threshold:
            print(f"\n[VISION] LEFT THREAT DETECTED! MSE: {mse:.1f} > {self.mse_threshold}")
            cv2.imwrite(os.path.join(self.debug_dir, "panic_left.png"), current.astype(np.uint8))
            cv2.imwrite(os.path.join(self.debug_dir, "ref_left.png"), self.ref_left.astype(np.uint8))
            return 1.0
        return 0.0

    def get_right_sensory_rate(self) -> float:
        if self.ref_right is None:
            return 0.0
        mse, current = self._get_temporal_mse(self.ref_right, self.r_x, self.r_y, self.r_bbox)
        if mse > self.mse_threshold:
            print(f"\n[VISION] RIGHT THREAT DETECTED! MSE: {mse:.1f} > {self.mse_threshold}")
            cv2.imwrite(os.path.join(self.debug_dir, "panic_right.png"), current.astype(np.uint8))
            cv2.imwrite(os.path.join(self.debug_dir, "ref_right.png"), self.ref_right.astype(np.uint8))
            return 1.0
        return 0.0
