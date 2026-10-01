import logging
import subprocess
import threading

_log = logging.getLogger(__name__)

_LOCK = threading.Lock()
_CURSOR = {'x': 0, 'y': 0}
_CLICKS: list = []


def cursor_position() -> tuple:
    with _LOCK:
        return (_CURSOR['x'], _CURSOR['y'])


def drain_clicks() -> list:
    with _LOCK:
        clicks = list(_CLICKS)
        _CLICKS.clear()
        return clicks


def find_browser():
    return None


def screen_size() -> tuple:
    return (1920, 1080)


def is_window(handle: int) -> bool:
    return bool(handle)


def window_title(handle: int) -> str:
    return ''


def window_process(handle: int) -> str:
    return ''


def window_rect(handle: int):
    return None


def foreground_window() -> int:
    return 0


def top_level_windows() -> list:
    return []


def apply_overlay_style(handle: int, x: int, y: int, w: int, h: int) -> bool:
    return False


def outer_rect(handle: int):
    return None


def clip_window(handle: int, left: int, top: int, right: int, bottom: int, radius: int) -> bool:
    return False


def give_focus_back(handle: int) -> bool:
    return False


def popen_kwargs_no_activate() -> dict:
    return {}


def toggle_fullscreen() -> bool:
    return False


def start_child_in_job(args: list, **popen_kwargs) -> subprocess.Popen:
    return subprocess.Popen(args, **popen_kwargs)


def open_target(target: str) -> bool:
    return False


def move_cursor(x: int, y: int):
    with _LOCK:
        _CURSOR['x'], _CURSOR['y'] = x, y


def mouse_down():
    with _LOCK:
        _CLICKS.append((_CURSOR['x'], _CURSOR['y']))


def mouse_up():
    return None
