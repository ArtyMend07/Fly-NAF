import ctypes
import time
import mss
import cv2
import numpy as np
import os
import sys

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_position() -> tuple[int, int]:
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def compute_edge_density(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    total_pixels = edges.shape[0] * edges.shape[1]
    if total_pixels == 0:
        return 0.0
        
    edge_pixels = np.count_nonzero(edges)
    return float(edge_pixels) / float(total_pixels)

def run_vision_calibration(bbox_size: int = 100):
    print(f"[SYSTEM] Structural Vision Calibrator Running (BBox: {bbox_size}x{bbox_size})")
    print("[SYSTEM] Hover over target. Console shows live Edge Density.")
    print("[SYSTEM] Press SPACEBAR to save data to logs/vision_calibration.txt.")
    print("[SYSTEM] Press Ctrl+C to exit.\n")
    
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "vision_calibration.txt")
    
    with open(log_path, "w") as f:
        f.write("--- FNAF STRUCTURAL VISION CALIBRATION ---\n")
    
    offset = bbox_size // 2
    space_was_down = False
    
    with mss.MSS() as sct:
        try:
            while True:
                x, y = get_mouse_position()
                
                bbox = {
                    "top": y - offset,
                    "left": x - offset,
                    "width": bbox_size,
                    "height": bbox_size
                }
                
                try:
                    img = sct.grab(bbox)
                    frame = np.array(img)
                    density = compute_edge_density(frame)
                    
                    sys.stdout.write(f"\r[LIVE] X={x:<4} Y={y:<4} | Edge Density: {density:.4f}")
                    sys.stdout.flush()
                    
                    space_is_down = (ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000) != 0
                    if space_is_down and not space_was_down:
                        data = f"Pos: {x},{y} | BBox: {bbox_size} | Density: {density:.4f}\n"
                        with open(log_path, "a") as f:
                            f.write(data)
                        print(f"\n[SAVED] {data.strip()}")
                        
                    space_was_down = space_is_down
                    
                except mss.exception.ScreenShotError:
                    pass
                    
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n[SYSTEM] Calibration halted.")

if __name__ == "__main__":
    run_vision_calibration()

