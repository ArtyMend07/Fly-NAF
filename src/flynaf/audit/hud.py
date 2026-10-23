import cv2
import numpy as np

from flynaf import config
from flynaf.env import anchor, tablet_map


def to_design(frame: np.ndarray) -> np.ndarray:
    if frame.shape[:2] == (anchor.DESIGN_HEIGHT, anchor.DESIGN_WIDTH):
        return frame
    return cv2.resize(frame, (anchor.DESIGN_WIDTH, anchor.DESIGN_HEIGHT), interpolation=cv2.INTER_AREA)


def usage_bars(frame: np.ndarray, params=None) -> int:
    params = params or config.NIGHT_AUDIT
    top, bottom = params.usage_bar_rows
    half = params.usage_bar_half_width
    lit = 0
    for centre in params.usage_bar_centres:
        pixels = frame[top:bottom, centre - half:centre + half].reshape(-1, 3).astype(np.float32)
        blue, green, red = pixels.mean(axis=0)
        flat = pixels.std(axis=0).max() < params.usage_bar_flatness
        coloured = max(green, red) > params.usage_bar_lit_level and blue < params.usage_bar_blue_ceiling
        if not (flat and coloured):
            break
        lit += 1
    return lit


def door_closed(frame: np.ndarray, side: str, params=None) -> bool | None:
    params = params or config.NIGHT_AUDIT
    motor = config.MOTOR_CALIBRATION
    x = getattr(motor, f'{side}_door_button_x')
    y = getattr(motor, f'{side}_door_button_y')
    half = params.button_half_size
    _blue, green, red = frame[y - half:y + half, x - half:x + half].reshape(-1, 3).mean(axis=0)
    if green > red + params.button_colour_margin:
        return True
    if red > green + params.button_colour_margin:
        return False
    return None


def light_on(frame: np.ndarray, side: str) -> bool:
    motor = config.MOTOR_CALIBRATION
    x = getattr(motor, f'{side}_light_button_x')
    y = getattr(motor, f'{side}_light_button_y')
    half = config.VISION_DYNAMICS.light_button_half_size
    button = cv2.cvtColor(frame[y - half:y + half, x - half:x + half], cv2.COLOR_BGR2GRAY)
    return float(button.mean()) > config.VISION_DYNAMICS.light_button_lit_level


def tablet_up(frame: np.ndarray) -> bool:
    detection = config.CAMERA_DETECTION
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    crop = gray[detection.map_top:detection.map_bottom, detection.map_left:detection.map_right]
    return tablet_map.count_camera_buttons(crop) >= detection.min_buttons
