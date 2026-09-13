import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import mss
import numpy as np
import cv2
import config


def run_debug():
    target_x = config.VISION_CALIBRATION.left_target_x
    target_y = config.VISION_CALIBRATION.left_target_y
    bbox_size = config.VISION_CALIBRATION.left_bbox_size
    offset = bbox_size // 2
    bbox = {
        'top': target_y - offset,
        'left': target_x - offset,
        'width': bbox_size,
        'height': bbox_size,
    }

    cv2.namedWindow('left eye view', cv2.WINDOW_NORMAL)
    cv2.moveWindow('left eye view', 1000, 50)

    with mss.MSS() as sct:
        try:
            while True:
                img = sct.grab(bbox)
                frame = np.array(img)
                cv2.imshow('left eye view', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except KeyboardInterrupt:
            pass
        finally:
            cv2.destroyAllWindows()


if __name__ == '__main__':
    run_debug()