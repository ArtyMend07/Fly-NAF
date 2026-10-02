import ctypes
import logging
import os
import shutil
import signal
import subprocess
import time

from Xlib import X, display, error
from Xlib.ext import shape, xtest

_log = logging.getLogger(__name__)

_BROWSERS = (
    'google-chrome',
    'google-chrome-stable',
    'chromium',
    'chromium-browser',
    'microsoft-edge',
    'microsoft-edge-stable',
)

_PR_SET_PDEATHSIG = 1
_UNDECORATED = [2, 0, 0, 0, 0]
_SETTLE_SEC = 1.5
_PAGER_REQUEST = 2

_DISPLAY = None
_SHAPE_CHECKED = False
_HAS_SHAPE = False


def _dpy():
    global _DISPLAY
    if _DISPLAY is None:
        _DISPLAY = display.Display()
    return _DISPLAY


def _root():
    return _dpy().screen().root


def _atom(name: str):
    return _dpy().intern_atom(name)


def _window(handle: int):
    if not handle:
        return None
    try:
        return _dpy().create_resource_object('window', handle)
    except error.XError:
        return None


def _property(window, name: str, kind=X.AnyPropertyType):
    try:
        value = window.get_full_property(_atom(name), kind)
    except error.XError:
        return None
    return value.value if value else None


def _has_shape() -> bool:
    global _SHAPE_CHECKED, _HAS_SHAPE
    if not _SHAPE_CHECKED:
        _SHAPE_CHECKED = True
        try:
            _HAS_SHAPE = _dpy().has_extension('SHAPE')
        except error.XError:
            _HAS_SHAPE = False
    return _HAS_SHAPE


def find_browser():
    for name in _BROWSERS:
        path = shutil.which(name)
        if path:
            return path
    return None


def screen_size() -> tuple:
    screen = _dpy().screen()
    return (screen.width_in_pixels, screen.height_in_pixels)


def is_window(handle: int) -> bool:
    window = _window(handle)
    if window is None:
        return False
    try:
        window.get_attributes()
        return True
    except error.XError:
        return False


def window_title(handle: int) -> str:
    window = _window(handle)
    if window is None:
        return ''
    raw = _property(window, '_NET_WM_NAME')
    if raw is None:
        raw = _property(window, 'WM_NAME')
    if raw is None:
        return ''
    if isinstance(raw, bytes):
        return raw.decode('utf-8', 'replace')
    return str(raw)


def window_pid(handle: int) -> int:
    window = _window(handle)
    if window is None:
        return 0
    raw = _property(window, '_NET_WM_PID')
    if not raw:
        return 0
    try:
        return int(raw[0])
    except (TypeError, ValueError, IndexError):
        return 0


def window_process(handle: int) -> str:
    pid = window_pid(handle)
    if not pid:
        return ''
    try:
        return os.path.basename(os.readlink('/proc/%d/exe' % pid))
    except OSError:
        pass
    try:
        with open('/proc/%d/comm' % pid, 'r', encoding='utf-8') as handle_file:
            return handle_file.read().strip()
    except OSError:
        return ''


def window_rect(handle: int):
    window = _window(handle)
    if window is None:
        return None
    try:
        geometry = window.get_geometry()
        coords = window.translate_coords(_root(), 0, 0)
    except error.XError:
        return None
    if geometry.width <= 0 or geometry.height <= 0:
        return None
    return (-coords.x, -coords.y, geometry.width, geometry.height)


def foreground_window() -> int:
    raw = _property(_root(), '_NET_ACTIVE_WINDOW')
    if not raw:
        return 0
    try:
        return int(raw[0])
    except (TypeError, ValueError, IndexError):
        return 0


def _client_of(window, depth: int = 2):
    if _property(window, 'WM_STATE') is not None:
        return window
    if depth == 0:
        return None
    try:
        children = window.query_tree().children
    except error.XError:
        return None
    for child in children:
        client = _client_of(child, depth - 1)
        if client is not None:
            return client
    return None


def _mapped_clients() -> list:
    found = []
    for frame in _root().query_tree().children:
        try:
            if frame.get_attributes().map_state != X.IsViewable:
                continue
        except error.XError:
            continue
        client = _client_of(frame)
        if client is not None:
            found.append(client.id)
    return found


def top_level_windows() -> list:
    raw = _property(_root(), '_NET_CLIENT_LIST')
    if raw:
        return [int(handle) for handle in raw]
    try:
        return _mapped_clients()
    except error.XError:
        return []


def _set_state(window, *names: str):
    state = _atom('_NET_WM_STATE')
    data = [2, 0, 0, 0, 0]
    for name in names:
        data[1] = _atom(name)
        event = display.event.ClientMessage(
            window=window, client_type=state, data=(32, tuple(data)),
        )
        _root().send_event(
            event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
        )


def _make_click_through(window) -> bool:
    if not _has_shape():
        return False
    try:
        window.shape_rectangles(
            shape.SO.Set, shape.SK.Input, X.YXBanded, 0, 0, [],
        )
        return True
    except Exception as exc:
        _log.warning('input shaping failed, the panel will swallow clicks: %s', exc)
        return False


def apply_overlay_style(handle: int, x: int, y: int, w: int, h: int) -> bool:
    window = _window(handle)
    if window is None:
        return False
    try:
        hints = _atom('_MOTIF_WM_HINTS')
        window.change_property(hints, hints, 32, _UNDECORATED)
        window.configure(x=x, y=y, width=w, height=h)
        _set_state(window, '_NET_WM_STATE_ABOVE', '_NET_WM_STATE_SKIP_TASKBAR')
        click_through = _make_click_through(window)
        _dpy().sync()
    except Exception as exc:
        _log.warning('overlay styling failed: %s', exc)
        return False

    deadline = time.monotonic() + _SETTLE_SEC
    while True:
        rect = window_rect(handle)
        placed = rect is not None and rect[2] == w and rect[3] == h
        if placed or time.monotonic() >= deadline:
            return bool(placed and click_through)
        time.sleep(0.05)


def move_window(handle: int, x: int, y: int) -> bool:
    window = _window(handle)
    if window is None:
        return False
    try:
        window.configure(x=x, y=y)
        _dpy().sync()
    except error.XError:
        return False
    return True


def outer_rect(handle: int):
    return None


def clip_window(handle: int, left: int, top: int, right: int, bottom: int, radius: int) -> bool:
    return False


def give_focus_back(handle: int) -> bool:
    window = _window(handle)
    if window is None:
        return False
    try:
        event = display.event.ClientMessage(
            window=window,
            client_type=_atom('_NET_ACTIVE_WINDOW'),
            data=(32, (_PAGER_REQUEST, X.CurrentTime, 0, 0, 0)),
        )
        _root().send_event(
            event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
        )
        window.raise_window()
        _dpy().sync()
    except Exception as exc:
        _log.warning('focus handback failed: %s', exc)
        return False
    return foreground_window() == handle


def popen_kwargs_no_activate() -> dict:
    return {}


def toggle_fullscreen() -> bool:
    return False


def _die_with_parent():
    ctypes.CDLL('libc.so.6', use_errno=True).prctl(_PR_SET_PDEATHSIG, signal.SIGKILL)


def start_child_in_job(args: list, **popen_kwargs) -> subprocess.Popen:
    return subprocess.Popen(args, preexec_fn=_die_with_parent, **popen_kwargs)


def open_target(target: str) -> bool:
    if '://' in target:
        command, folder = ['xdg-open', target], None
    else:
        command, folder = [target], os.path.dirname(target) or None
    try:
        subprocess.Popen(command, cwd=folder)
    except OSError:
        return False
    return True


def move_cursor(x: int, y: int):
    xtest.fake_input(_dpy(), X.MotionNotify, x=int(x), y=int(y))
    _dpy().sync()


def mouse_down():
    xtest.fake_input(_dpy(), X.ButtonPress, 1)
    _dpy().sync()


def mouse_up():
    xtest.fake_input(_dpy(), X.ButtonRelease, 1)
    _dpy().sync()
