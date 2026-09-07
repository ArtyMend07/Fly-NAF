import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mss
import numpy as np
import cv2

def run_roi_selector():
    print("[SYSTEM] Switching to countdown. Open your game/video now!")
    for i in range(5, 0, -1):
        print(f"Taking screenshot in {i}...")
        time.sleep(1)
    print("[SYSTEM] Taking a full screenshot...")
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
    frame = np.array(img)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    print("[SYSTEM] An image of your screen will open.")
    print("[SYSTEM] Click and drag a box over the left door.")
    print("[SYSTEM] Press ENTER or SPACE to confirm the box.")
    print("[SYSTEM] Press c to cancel.")
    cv2.namedWindow("Select Door Bounding Box", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Select Door Bounding Box", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    r = cv2.selectROI("Select Door Bounding Box", frame, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()
    x, y, w, h = r
    if w > 0 and h > 0:
        center_x = x + (w // 2)
        center_y = y + (h // 2)
        bbox_size = max(w, h)
        print("\n--- [CALIBRATION RESULTS] ---")
        print("Update your src/config.py with these values:")
        print(f"  bonnie_target_x: {center_x}")
        print(f"  bonnie_target_y: {center_y}")
        print(f"  bbox_size:       {bbox_size}")
        print("-----------------------------\n")
    else:
        print("\n[SYSTEM] No box selected.")

if __name__ == "__main__":
    run_roi_selector()