import time

from flynaf import config
from flynaf.env import anchor, desktop

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
    map_corner = anchor.point(camera.map_left, camera.map_top)
    map_far_corner = anchor.point(camera.map_right, camera.map_bottom)
    view = config.TABLET_VISION.view
    return [
        centered_rect(left[0], left[1], anchor.size(vision.left_bbox_size)),
        centered_rect(right[0], right[1], anchor.size(vision.right_bbox_size)),
        (*map_corner, *map_far_corner),
        (*anchor.point(view[0], view[1]), *anchor.point(view[2], view[3])),
    ]


def motor_regions(pad: int = 40) -> list:
    motor = config.MOTOR_CALIBRATION
    targets = [
        (motor.left_door_button_x, motor.left_door_button_y),
        (motor.left_light_button_x, motor.left_light_button_y),
        (motor.right_door_button_x, motor.right_door_button_y),
        (motor.right_light_button_x, motor.right_light_button_y),
        (motor.camera_hover_x, motor.camera_hover_y),
        (motor.camera_hover_x, motor.camera_bar_approach_y),
    ] + [(button.x, button.y) for button in config.TABLET_VISION.cameras]
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


def dock_game_for_panel(screen_w: int, min_width: int, margin: int) -> bool:
    handle = find_game_window()
    client = desktop.window_rect(handle) if handle else None
    outer = desktop.outer_rect(handle) if handle else None
    if client is None or outer is None:
        return False
    if margin + client[2] + 2 * margin + min_width > screen_w:
        return False
    border = client[0] - outer[0]
    if not desktop.move_window(handle, margin - border, outer[1]):
        return False
    return anchor_to_game()


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
    return bool(wanted_title) and wanted_title == _squashed(window_title(handle))


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


_PAGE_ROUNDING_PX = 2


def frame_around_page(handle: int, x: int, y: int, w: int, h: int, page_height: int):
    client = desktop.window_rect(handle)
    outer = desktop.outer_rect(handle)
    if client is None or outer is None or page_height <= 0:
        return None
    left = client[0] - outer[0]
    right = outer[0] + outer[2] - (client[0] + client[2])
    bottom = outer[1] + outer[3] - (client[1] + client[3])
    top = outer[3] - bottom - page_height + _PAGE_ROUNDING_PX
    if top < 0 or left < 0 or right < 0:
        return None
    window = (x - left, y - top, w + left + right, h + top + bottom)
    page = (left, top, left + w, top + h)
    return window, page


def strip_browser_chrome(handle: int, x: int, y: int, w: int, h: int, page_height,
                         radius: int, timeout_sec: float = 20.0):
    deadline = time.monotonic() + timeout_sec
    frame = previous = None
    while frame is None or frame != previous:
        if time.monotonic() >= deadline:
            return None
        previous = frame
        time.sleep(0.3)
        frame = frame_around_page(handle, x, y, w, h, page_height())
    window, page = frame
    if not desktop.apply_overlay_style(handle, *window):
        return None
    if not desktop.clip_window(handle, *page, radius):
        return None
    return window, page


def keep_pinned(handle: int, x: int, y: int, w: int, h: int, stop: object,
                interval_sec: float = 2.0, clip: tuple | None = None):
    while not stop.is_set():
        if not desktop.is_window(handle):
            return
        desktop.apply_overlay_style(handle, x, y, w, h)
        if clip is not None:
            desktop.clip_window(handle, *clip)
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
