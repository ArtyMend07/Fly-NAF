import mss
import numpy as np
import cv2

class FNAFVision:
    def __init__(self, target_x: int, target_y: int, bbox_size: int, threshold: float):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]
        
        self.target_x = target_x
        self.target_y = target_y
        self.bbox_size = bbox_size
        self.threshold = threshold
        
    def get_sensory_rates(self) -> float:
        offset = self.bbox_size // 2
        bbox = {
            'top': self.target_y - offset, 
            'left': self.target_x - offset, 
            'width': self.bbox_size, 
            'height': self.bbox_size
        }
        
        img = self.sct.grab(bbox)
        frame = np.array(img)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        brightness = float(np.mean(gray))
        
        print(f"[VISION DEBUG] Looking at X={self.target_x}, Y={self.target_y} | Current Brightness: {brightness:.1f}", end='\r')
        
        if brightness > self.threshold:
            print("\n[VISION ALERT] BRIGHTNESS THRESHOLD EXCEEDED! Triggering Fly Brain!")
            return 1.0
            
        return 0.0
