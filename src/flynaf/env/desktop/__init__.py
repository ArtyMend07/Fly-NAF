import logging
import os
import sys

_log = logging.getLogger(__name__)

WINDOWS = 'windows'
LINUX = 'linux'
HEADLESS = 'headless'


def _detect() -> str:
    forced = os.environ.get('FLYNAF_PLATFORM', '').strip().lower()
    if forced in (WINDOWS, LINUX, HEADLESS):
        return forced
    if sys.platform.startswith('win'):
        return WINDOWS
    if sys.platform.startswith('linux') and os.environ.get('DISPLAY'):
        return LINUX
    return HEADLESS


def _import(name: str):
    if name == WINDOWS:
        from . import windows
        return windows
    if name == LINUX:
        from . import linux
        return linux
    from . import headless
    return headless


def _load():
    wanted = _detect()
    try:
        return wanted, _import(wanted)
    except Exception as exc:
        _log.warning('%s backend unavailable (%s), falling back to headless', wanted, exc)
        return HEADLESS, _import(HEADLESS)


name, _backend = _load()


def use_backend(backend, backend_name: str = 'injected'):
    global name, _backend
    name, _backend = backend_name, backend


def interactive() -> bool:
    return name != HEADLESS


def find_browser():
    return _backend.find_browser()


def screen_size() -> tuple:
    return _backend.screen_size()


def is_window(handle: int) -> bool:
    return _backend.is_window(handle)


def window_title(handle: int) -> str:
    return _backend.window_title(handle)


def window_process(handle: int) -> str:
    return _backend.window_process(handle)


def window_rect(handle: int):
    return _backend.window_rect(handle)


def foreground_window() -> int:
    return _backend.foreground_window()


def top_level_windows() -> list:
    return _backend.top_level_windows()


def apply_overlay_style(handle: int, x: int, y: int, w: int, h: int) -> bool:
    return _backend.apply_overlay_style(handle, x, y, w, h)


def move_window(handle: int, x: int, y: int) -> bool:
    return _backend.move_window(handle, x, y)


def outer_rect(handle: int):
    return _backend.outer_rect(handle)


def clip_window(handle: int, left: int, top: int, right: int, bottom: int, radius: int) -> bool:
    return _backend.clip_window(handle, left, top, right, bottom, radius)


def give_focus_back(handle: int) -> bool:
    return _backend.give_focus_back(handle)


def toggle_fullscreen() -> bool:
    return _backend.toggle_fullscreen()


def start_child_in_job(args: list, **popen_kwargs):
    return _backend.start_child_in_job(args, **popen_kwargs)


def open_target(target: str) -> bool:
    return _backend.open_target(target)


def popen_kwargs_no_activate() -> dict:
    return _backend.popen_kwargs_no_activate()


def move_cursor(x: int, y: int):
    _backend.move_cursor(x, y)


def mouse_down():
    _backend.mouse_down()


def mouse_up():
    _backend.mouse_up()
