import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mss
import numpy as np
import cv2
import config

def run_debug():
    target_x = config.VISION_CALIBRATION["bonnie_target_x"]
    target_y = config.VISION_CALIBRATION["bonnie_target_y"]
    bbox_size = config.VISION_CALIBRATION["bbox_size"]
    offset = bbox_size // 2
    bbox = {
        "top": target_y - offset, 
        "left": target_x - offset, 
        "width": bbox_size, 
        "height": bbox_size
    }

    print(f"[SYSTEM] Debug Vision Running.")
    print(f"[SYSTEM] The fly is looking at: X={target_x}, Y={target_y}")
    print(f"[SYSTEM] A window will open showing exactly what the fly sees ({bbox_size}x{bbox_size}).")
    print(f"[SYSTEM] Press 'q' in the image window or Ctrl+C here to exit.")

    cv2.namedWindow("Fly's Left Eye (LPLC2 Vision)", cv2.WINDOW_NORMAL)
    cv2.moveWindow("Fly's Left Eye (LPLC2 Vision)", 1000, 50)

    with mss.MSS() as sct:
        try:
            while True:
                img = sct.grab(bbox)
                frame = np.array(img)
                cv2.imshow("Fly's Left Eye (LPLC2 Vision)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        except KeyboardInterrupt:
            pass
        finally:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    run_debug()