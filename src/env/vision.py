import mss
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
        
        self.ref_left = None
        self.ref_right = None
        
    def _grab_gray(self, x: int, y: int, size: int) -> np.ndarray:
        offset = size // 2
        bbox = {"top": y - offset, "left": x - offset, "width": size, "height": size}
        img = self.sct.grab(bbox)
        frame = np.array(img)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY).astype(np.float32)
        
    def capture_left_reference(self):
        self.ref_left = self._grab_gray(self.l_x, self.l_y, self.l_bbox)
        
    def capture_right_reference(self):
        self.ref_right = self._grab_gray(self.r_x, self.r_y, self.r_bbox)
        
    def get_left_sensory_rate(self) -> float:
        if self.ref_left is None:
            return 0.0
        current = self._grab_gray(self.l_x, self.l_y, self.l_bbox)
        mse = np.mean((current - self.ref_left) ** 2)
        if mse > self.mse_threshold:
            print(f"\n[VISION] LEFT THREAT DETECTED! MSE: {mse:.1f} > {self.mse_threshold}")
            return 1.0
        return 0.0

    def get_right_sensory_rate(self) -> float:
        if self.ref_right is None:
            return 0.0
        current = self._grab_gray(self.r_x, self.r_y, self.r_bbox)
        mse = np.mean((current - self.ref_right) ** 2)
        if mse > self.mse_threshold:
            print(f"\n[VISION] RIGHT THREAT DETECTED! MSE: {mse:.1f} > {self.mse_threshold}")
            return 1.0
        return 0.0

