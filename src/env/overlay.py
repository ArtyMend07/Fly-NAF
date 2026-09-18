import ctypes
import ctypes.wintypes
import os
import time
import winreg

import config

_APP_PATHS = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'


def find_browser() -> str | None:
    for exe in ('msedge.exe', 'chrome.exe'):
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, _APP_PATHS + '\\' + exe) as key:
                    path = winreg.QueryValue(key, None)
            except OSError:
                continue
            if path and os.path.isfile(path):
                return path

    for path in (
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    ):
        if os.path.isfile(path):
            return path
    return None


def centered_rect(x: int, y: int, size: int) -> tuple:
    offset = size // 2
    return (x - offset, y - offset, x + offset, y + offset)


def capture_regions() -> list:
    vision = config.VISION_CALIBRATION
    camera = config.CAMERA_DETECTION
    return [
        centered_rect(vision.left_target_x, vision.left_target_y, vision.left_bbox_size),
        centered_rect(vision.right_target_x, vision.right_target_y, vision.right_bbox_size),
        centered_rect(camera.patch_x, camera.patch_y, camera.patch_size),
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
    return [centered_rect(x, y, pad * 2) for x, y in targets]


def rects_overlap(a: tuple, b: tuple) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def screen_size() -> tuple:
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))


def game_bounds() -> tuple:
    regions = capture_regions() + motor_regions()
    return (
        max(0, min(r[0] for r in regions)),
        max(0, min(r[1] for r in regions)),
        max(r[2] for r in regions),
        max(r[3] for r in regions),
    )


def ingame_overlay_rect(panel_w: int, panel_h: int, margin: int, step: int = 4) -> tuple | None:
    left, _top, right, bottom = game_bounds()
    forbidden = capture_regions() + motor_regions()
    centre = (left + right) // 2

    first_x = left + margin
    last_x = right - panel_w - margin
    if last_x < first_x:
        return None

    y = margin
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


_GWL_STYLE = -16
_GWL_EXSTYLE = -20
_WS_CAPTION = 0x00C00000
_WS_THICKFRAME = 0x00040000
_WS_MINIMIZEBOX = 0x00020000
_WS_MAXIMIZEBOX = 0x00010000
_WS_SYSMENU = 0x00080000
_WS_EX_TOPMOST = 0x00000008
_WS_EX_LAYERED = 0x00080000
_WS_EX_TRANSPARENT = 0x00000020
_WS_EX_NOACTIVATE = 0x08000000
_WS_EX_TOOLWINDOW = 0x00000080
_SWP_NOACTIVATE = 0x0010
_SWP_FRAMECHANGED = 0x0020
_SW_RESTORE = 9
_GA_ROOT = 2


def _user32():
    user32 = ctypes.windll.user32
    user32.SetWindowPos.argtypes = [
        ctypes.wintypes.HWND, ctypes.wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = ctypes.wintypes.BOOL
    return user32


_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _kernel32():
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    return kernel32


def is_window(hwnd: int) -> bool:
    return bool(hwnd) and bool(ctypes.windll.user32.IsWindow(hwnd))


def window_title(hwnd: int) -> str:
    if not hwnd:
        return ''
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ''
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def window_process(hwnd: int) -> str:
    if not hwnd:
        return ''
    user32 = ctypes.windll.user32
    kernel32 = _kernel32()
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ''
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ''
    try:
        size = ctypes.wintypes.DWORD(512)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ''
        return os.path.basename(buffer.value)
    finally:
        kernel32.CloseHandle(handle)


def _squashed(text: str) -> str:
    return ''.join(ch for ch in text.lower() if ch.isalnum())


def foreground_window() -> int:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
    return user32.GetForegroundWindow() or 0


def _top_level_windows() -> list:
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def visit(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return found


def find_game_window() -> int:
    wanted_process = _squashed(config.BRAIN_VIEW.game_process)
    wanted_title = _squashed(config.BRAIN_VIEW.game_title)
    windows = _top_level_windows()

    for hwnd in windows:
        if wanted_process and wanted_process in _squashed(window_process(hwnd)):
            return hwnd
    for hwnd in windows:
        if wanted_title and wanted_title in _squashed(window_title(hwnd)):
            return hwnd
    return 0


def find_window(*title_fragments: str) -> int:
    user32 = ctypes.windll.user32
    wanted = [fragment.lower() for fragment in title_fragments if fragment]
    found = []

    @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.lower()
        if any(fragment in title for fragment in wanted):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else 0


def wait_for_window(*title_fragments: str, timeout_sec: float = 45.0) -> int:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        hwnd = find_window(*title_fragments)
        if hwnd:
            return hwnd
        time.sleep(0.2)
    return 0


def apply_overlay_style(hwnd: int, x: int, y: int, w: int, h: int) -> bool:
    user32 = _user32()
    topmost = ctypes.wintypes.HWND(-1)

    style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
    user32.SetWindowLongW(
        hwnd, _GWL_STYLE,
        style & ~(_WS_CAPTION | _WS_THICKFRAME | _WS_MINIMIZEBOX | _WS_MAXIMIZEBOX | _WS_SYSMENU),
    )
    ex_style = user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd, _GWL_EXSTYLE,
        ex_style | _WS_EX_LAYERED | _WS_EX_TRANSPARENT | _WS_EX_NOACTIVATE | _WS_EX_TOOLWINDOW,
    )
    user32.SetWindowPos(hwnd, topmost, x, y, w, h, _SWP_NOACTIVATE | _SWP_FRAMECHANGED)

    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    placed = (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top) == (x, y, w, h)
    return placed and bool(user32.GetWindowLongW(hwnd, _GWL_EXSTYLE) & _WS_EX_TOPMOST)


def pin_as_overlay(window_titles, x: int, y: int, w: int, h: int,
                   timeout_sec: float = 45.0, settle_sec: float = 8.0) -> int:
    if isinstance(window_titles, str):
        window_titles = (window_titles,)
    hwnd = wait_for_window(*window_titles, timeout_sec=timeout_sec)
    if not hwnd:
        return 0

    deadline = time.monotonic() + settle_sec
    while time.monotonic() < deadline:
        if apply_overlay_style(hwnd, x, y, w, h):
            return hwnd
        time.sleep(0.25)
    return -hwnd


def keep_pinned(hwnd: int, x: int, y: int, w: int, h: int, stop: object,
                interval_sec: float = 2.0):
    user32 = _user32()
    topmost = ctypes.wintypes.HWND(-1)
    while not stop.is_set():
        if not user32.IsWindow(hwnd):
            return
        user32.SetWindowPos(hwnd, topmost, x, y, w, h, _SWP_NOACTIVATE | _SWP_FRAMECHANGED)
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


def give_focus_back(hwnd: int) -> bool:
    if not hwnd:
        return False
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.IsWindow(hwnd):
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, _SW_RESTORE)

    current = kernel32.GetCurrentThreadId()
    holder = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    target = user32.GetWindowThreadProcessId(hwnd, None)
    user32.AttachThreadInput(current, holder, True)
    user32.AttachThreadInput(current, target, True)
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    user32.AttachThreadInput(current, target, False)
    user32.AttachThreadInput(current, holder, False)
    return user32.GetForegroundWindow() == hwnd


def hold_foreground(hwnd: int, timeout_sec: float = 12.0, settle_sec: float = 2.0) -> bool:
    if not hwnd:
        return False
    user32 = ctypes.windll.user32
    deadline = time.monotonic() + timeout_sec
    holding_since = None
    while time.monotonic() < deadline:
        if user32.GetForegroundWindow() == hwnd:
            if holding_since is None:
                holding_since = time.monotonic()
            elif time.monotonic() - holding_since >= settle_sec:
                return True
        else:
            holding_since = None
            give_focus_back(hwnd)
        time.sleep(0.25)
    return user32.GetForegroundWindow() == hwnd
