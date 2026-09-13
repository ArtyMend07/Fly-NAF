import ctypes
import time
import mss
import cv2
import numpy as np
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config

_LOG_DIR = os.path.join(config.PROJECT_ROOT, 'logs')
_CANNY_LOW = 50
_CANNY_HIGH = 150
_POLL_DELAY = 0.05


class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


def get_mouse_position() -> tuple[int, int]:
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def compute_edge_density(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    edges = cv2.Canny(gray, _CANNY_LOW, _CANNY_HIGH)
    total_pixels = edges.shape[0] * edges.shape[1]
    if total_pixels == 0:
        return 0.0
    return float(np.count_nonzero(edges)) / float(total_pixels)


def run_vision_calibration(bbox_size: int = 100):
    os.makedirs(_LOG_DIR, exist_ok=True)
    log_path = os.path.join(_LOG_DIR, 'vision_calibration.txt')
    with open(log_path, 'w') as f:
        f.write('vision calibration log\n')

    print(f'bbox={bbox_size}x{bbox_size}, hover over target, SPACE to save, Ctrl+C to exit')

    offset = bbox_size // 2
    space_was_down = False
    with mss.MSS() as sct:
        try:
            while True:
                x, y = get_mouse_position()
                bbox = {'top': y - offset, 'left': x - offset, 'width': bbox_size, 'height': bbox_size}
                try:
                    img = sct.grab(bbox)
                    frame = np.array(img)
                    density = compute_edge_density(frame)
                    sys.stdout.write(f'\r x={x:<4} y={y:<4} density={density:.4f}')
                    sys.stdout.flush()
                    space_is_down = (ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000) != 0
                    if space_is_down and not space_was_down:
                        data = f'pos={x},{y} bbox={bbox_size} density={density:.4f}\n'
                        with open(log_path, 'a') as f:
                            f.write(data)
                        print(f'\nsaved: {data.strip()}')
                    space_was_down = space_is_down
                except mss.exception.ScreenShotError:
                    pass
                time.sleep(_POLL_DELAY)
        except KeyboardInterrupt:
            print('\ncalibration stopped')


if __name__ == '__main__':
    run_vision_calibration()