import cv2
import numpy as np

from flynaf import config
from flynaf.env import anchor


def design_size(params=None) -> tuple:
    params = params or config.CAMERA_DETECTION
    return (params.map_right - params.map_left, params.map_bottom - params.map_top)


def map_box() -> dict:
    params = config.CAMERA_DETECTION
    left, top = anchor.point(params.map_left, params.map_top)
    right, bottom = anchor.point(params.map_right, params.map_bottom)
    return {'left': left, 'top': top, 'width': max(1, right - left), 'height': max(1, bottom - top)}


def to_design(frame: np.ndarray, params=None) -> np.ndarray:
    gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    return cv2.resize(gray, design_size(params), interpolation=cv2.INTER_AREA)


def count_camera_buttons(gray: np.ndarray, params=None) -> int:
    params = params or config.CAMERA_DETECTION
    white = (gray > params.white_level).astype(np.uint8)
    contours, _ = cv2.findContours(white, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    low_w, high_w = params.button_width
    low_h, high_h = params.button_height
    shaped = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if not (low_w <= width <= high_w and low_h <= height <= high_h):
            continue
        if cv2.contourArea(contour) > params.button_fill * width * height:
            shaped.append((x, y, width, height))
    return len(distinct_buttons(shaped))


def distinct_buttons(rects: list) -> list:
    kept = []
    for x, y, width, height in sorted(rects, key=lambda rect: rect[2] * rect[3], reverse=True):
        centre_x, centre_y = x + width / 2, y + height / 2
        if any(kx <= centre_x <= kx + kw and ky <= centre_y <= ky + kh for kx, ky, kw, kh in kept):
            continue
        kept.append((x, y, width, height))
    return kept
