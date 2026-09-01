import mss
import cv2
import numpy as np

class FNAFVision:
    def __init__(self, monitor_index=1, region=None):
        self.sct = mss.mss()
        self.monitor = region if region else self.sct.monitors[monitor_index]
            
    def capture_frame(self):
        sct_img = self.sct.grab(self.monitor)
        return np.array(sct_img)

    def detect_animatronic_at_left_door(self, frame):
        height, width = frame.shape[:2]
        left_door_region = frame[height//3:height//2, width//10:width//4]
        
        gray = cv2.cvtColor(left_door_region, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        
        return brightness > 150

    def get_sensory_rates(self):
        frame = self.capture_frame()
        danger = self.detect_animatronic_at_left_door(frame)
        return 1.0 if danger else 0.0

if __name__ == "__main__":
    vision = FNAFVision()
    frame = vision.capture_frame()
    print(f"Sensory rate: {vision.get_sensory_rates()}")
