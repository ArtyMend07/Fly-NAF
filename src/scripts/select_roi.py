import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import mss
import numpy as np
import cv2


def run_roi_selector():
    print('open the game, screenshot in 5 seconds')
    for i in range(5, 0, -1):
        print(f'  {i}...')
        time.sleep(1)

    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
    frame = np.array(img)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    print('drag a box over the target area, press ENTER to confirm, c to cancel')
    cv2.namedWindow('Select ROI', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Select ROI', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    r = cv2.selectROI('Select ROI', frame, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, w, h = r
    if w > 0 and h > 0:
        center_x = x + (w // 2)
        center_y = y + (h // 2)
        bbox_size = max(w, h)
        print(f'left_target_x: {center_x}')
        print(f'left_target_y: {center_y}')
        print(f'left_bbox_size: {bbox_size}')
    else:
        print('no region selected')


if __name__ == '__main__':
    run_roi_selector()