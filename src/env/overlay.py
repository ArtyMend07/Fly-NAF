import time

import config
from env import anchor
from env import desktop

find_browser = desktop.find_browser
screen_size = desktop.screen_size
is_window = desktop.is_window
window_title = desktop.window_title
window_process = desktop.window_process
foreground_window = desktop.foreground_window
apply_overlay_style = desktop.apply_overlay_style
give_focus_back = desktop.give_focus_back
window_rect = desktop.window_rect
_top_level_windows = desktop.top_level_windows


def centered_rect(x: int, y: int, size: int) -> tuple:
    offset = size // 2
    return (x - offset, y - offset, x + offset, y + offset)


def capture_regions() -> list:
    vision = config.VISION_CALIBRATION
    camera = config.CAMERA_DETECTION
    left = anchor.point(vision.left_target_x, vision.left_target_y)
    right = anchor.point(vision.right_target_x, vision.right_target_y)
    patch = anchor.point(camera.patch_x, camera.patch_y)
    return [
        centered_rect(left[0], left[1], anchor.size(vision.left_bbox_size)),
        centered_rect(right[0], right[1], anchor.size(vision.right_bbox_size)),
        centered_rect(patch[0], patch[1], anchor.size(camera.patch_size)),
    ]


def motor_regions(pad: int = 40) -> list:
    motor = config.MOTOR_CALIBRATION
    targets = [
        (motor.left_door_button_x, motor.left_door_button_y),
        (motor.left_light_button_x, motor.left_light_button_y),
        (motor.right_door_button_x, motor.right_door_button_y),
        (motor.right_light_button_x, motor.right_light_button_y),
        (motor.camera_hover_x, motor.camera_hover_y),
        (motor.camera_hover_x, motor.screen_center_y),
    ]
    reach = anchor.size(pad * 2)
    return [centered_rect(*anchor.point(x, y), reach) for x, y in targets]


def rects_overlap(a: tuple, b: tuple) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def game_bounds() -> tuple:
    rect = anchor.game_rect()
    if rect is not None:
        return (rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])
    regions = capture_regions() + motor_regions()
    return (
        max(0, min(r[0] for r in regions)),
        max(0, min(r[1] for r in regions)),
        max(r[2] for r in regions),
        max(r[3] for r in regions),
    )


_TASKBAR_RESERVE = 48


def beside_game_rect(
    screen_w: int, screen_h: int, min_width: int, max_width: int, margin: int,
) -> tuple | None:
    rect = anchor.game_rect()
    if rect is None:
        return None
    game_x, game_y, game_w, game_h = rect
    top = max(0, game_y)
    height = max(game_h, screen_h - top - _TASKBAR_RESERVE)
    right_space = screen_w - (game_x + game_w) - 2 * margin
    if right_space >= min_width:
        width = min(max_width, right_space)
        return (game_x + game_w + margin, top, width, height)
    left_space = game_x - 2 * margin
    if left_space >= min_width:
        width = min(max_width, left_space)
        return (game_x - margin - width, top, width, height)
    return None


def ingame_overlay_rect(panel_w: int, panel_h: int, margin: int, step: int = 4) -> tuple | None:
    left, _top, right, bottom = game_bounds()
    forbidden = capture_regions() + motor_regions()
    centre = (left + right) // 2
    rect = anchor.game_rect()

    first_x = left + margin
    last_x = right - panel_w - margin
    if last_x < first_x:
        return None

    y = (rect[1] if rect is not None else 0) + margin
    while y + panel_h + margin <= bottom:
        clear = [
            x for x in range(first_x, last_x + 1, step)
            if not any(
                rects_overlap((x, y, x + panel_w, y + panel_h), region)
                for region in forbidden
            )
        ]
        if clear:
            return (min(clear, key=lambda x: abs(x + panel_w // 2 - centre)), y)
        y += step
    return None


def _squashed(text: str) -> str:
    return ''.join(ch for ch in text.lower() if ch.isalnum())


def _belongs_to_game(handle: int) -> bool:
    if not handle:
        return False
    wanted_process = _squashed(config.BRAIN_VIEW.game_process)
    if wanted_process and wanted_process in _squashed(window_process(handle)):
        return True
    wanted_title = _squashed(config.BRAIN_VIEW.game_title)
    return bool(wanted_title) and wanted_title in _squashed(window_title(handle))


def game_in_front() -> int:
    front = foreground_window()
    return front if _belongs_to_game(front) else 0


def find_game_window() -> int:
    front = game_in_front()
    if front:
        return front
    candidates = [handle for handle in _top_level_windows() if _belongs_to_game(handle)]
    showing = [(handle, window_rect(handle)) for handle in candidates]
    showing = [(handle, rect) for handle, rect in showing if rect is not None]
    if showing:
        return max(showing, key=lambda item: item[1][2] * item[1][3])[0]
    return candidates[0] if candidates else 0


def anchor_to_game() -> bool:
    handle = find_game_window()
    if not handle:
        return False
    rect = desktop.window_rect(handle)
    if rect is None:
        return False
    anchor.set_game_rect(rect)
    return True


def find_window(*title_fragments: str) -> int:
    wanted = [fragment.lower() for fragment in title_fragments if fragment]
    for handle in _top_level_windows():
        title = window_title(handle).lower()
        if title and any(fragment in title for fragment in wanted):
            return handle
    return 0


def wait_for_window(*title_fragments: str, timeout_sec: float = 45.0) -> int:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        handle = find_window(*title_fragments)
        if handle:
            return handle
        time.sleep(0.2)
    return 0


def pin_as_overlay(window_titles, x: int, y: int, w: int, h: int,
                   timeout_sec: float = 45.0, settle_sec: float = 8.0) -> int:
    if isinstance(window_titles, str):
        window_titles = (window_titles,)
    handle = wait_for_window(*window_titles, timeout_sec=timeout_sec)
    if not handle:
        return 0

    deadline = time.monotonic() + settle_sec
    while time.monotonic() < deadline:
        if desktop.apply_overlay_style(handle, x, y, w, h):
            return handle
        time.sleep(0.25)
    return -handle


def keep_pinned(handle: int, x: int, y: int, w: int, h: int, stop: object,
                interval_sec: float = 2.0):
    while not stop.is_set():
        if not desktop.is_window(handle):
            return
        desktop.apply_overlay_style(handle, x, y, w, h)
        stop.wait(interval_sec)


def pick_overlay_position(
    screen_w: int,
    screen_h: int,
    panel_w: int,
    panel_h: int,
    forbidden: list,
    margin: int = 8,
) -> tuple | None:
    right = screen_w - panel_w - margin
    bottom = screen_h - panel_h - margin
    candidates = [
        (right, (screen_h - panel_h) // 2),
        (right, margin),
        (right, bottom),
        (margin, bottom),
        (margin, margin),
    ]
    for x, y in candidates:
        if x < 0 or y < 0 or x + panel_w > screen_w or y + panel_h > screen_h:
            continue
        panel = (x, y, x + panel_w, y + panel_h)
        if not any(rects_overlap(panel, region) for region in forbidden):
            return (x, y)
    return None


def _holds_front(handle: int) -> bool:
    front = desktop.foreground_window()
    return front == handle or (_belongs_to_game(handle) and _belongs_to_game(front))


def hold_foreground(handle: int, timeout_sec: float = 12.0, settle_sec: float = 2.0) -> bool:
    if not handle:
        return False
    deadline = time.monotonic() + timeout_sec
    holding_since = None
    while time.monotonic() < deadline:
        if _holds_front(handle):
            if holding_since is None:
                holding_since = time.monotonic()
            elif time.monotonic() - holding_since >= settle_sec:
                return True
        else:
            holding_since = None
            desktop.give_focus_back(handle)
        time.sleep(0.25)
    return _holds_front(handle)
