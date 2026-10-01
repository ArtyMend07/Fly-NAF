import ctypes
import ctypes.wintypes
import os
import subprocess
import winreg

_APP_PATHS = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'

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
_SW_SHOWNOACTIVATE = 4
_STARTF_USESHOWWINDOW = 0x00000001

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

_VK_MENU = 0x12
_VK_RETURN = 0x0D
_KEYEVENTF_KEYUP = 0x0002


def _user32():
    user32 = ctypes.windll.user32
    user32.SetWindowPos.argtypes = [
        ctypes.wintypes.HWND, ctypes.wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = ctypes.wintypes.BOOL
    return user32


class _JobBasicLimits(ctypes.Structure):
    _fields_ = [
        ('PerProcessUserTimeLimit', ctypes.c_int64),
        ('PerJobUserTimeLimit', ctypes.c_int64),
        ('LimitFlags', ctypes.wintypes.DWORD),
        ('MinimumWorkingSetSize', ctypes.c_size_t),
        ('MaximumWorkingSetSize', ctypes.c_size_t),
        ('ActiveProcessLimit', ctypes.wintypes.DWORD),
        ('Affinity', ctypes.c_void_p),
        ('PriorityClass', ctypes.wintypes.DWORD),
        ('SchedulingClass', ctypes.wintypes.DWORD),
    ]


class _JobIoCounters(ctypes.Structure):
    _fields_ = [(field, ctypes.c_uint64) for field in (
        'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
        'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount',
    )]


class _JobExtendedLimits(ctypes.Structure):
    _fields_ = [
        ('BasicLimitInformation', _JobBasicLimits),
        ('IoInfo', _JobIoCounters),
        ('ProcessMemoryLimit', ctypes.c_size_t),
        ('JobMemoryLimit', ctypes.c_size_t),
        ('PeakProcessMemoryUsed', ctypes.c_size_t),
        ('PeakJobMemoryUsed', ctypes.c_size_t),
    ]


_open_jobs = []


def _kernel32():
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    return kernel32


def find_browser():
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


def screen_size() -> tuple:
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))


def is_window(handle: int) -> bool:
    return bool(handle) and bool(ctypes.windll.user32.IsWindow(handle))


def window_title(handle: int) -> str:
    if not handle:
        return ''
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(handle)
    if length <= 0:
        return ''
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, buffer, length + 1)
    return buffer.value


def window_process(handle: int) -> str:
    if not handle:
        return ''
    user32 = ctypes.windll.user32
    kernel32 = _kernel32()
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
    if not pid.value:
        return ''
    process = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return ''
    try:
        size = ctypes.wintypes.DWORD(512)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return ''
        return os.path.basename(buffer.value)
    finally:
        kernel32.CloseHandle(process)


def window_rect(handle: int):
    if not handle or not is_window(handle):
        return None
    user32 = ctypes.windll.user32
    if user32.IsIconic(handle):
        return None
    rect = ctypes.wintypes.RECT()
    if not user32.GetClientRect(handle, ctypes.byref(rect)):
        return None
    origin = ctypes.wintypes.POINT(0, 0)
    if not user32.ClientToScreen(handle, ctypes.byref(origin)):
        return None
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    return (origin.x, origin.y, width, height)


def foreground_window() -> int:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
    return user32.GetForegroundWindow() or 0


def top_level_windows() -> list:
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def visit(handle, _lparam):
        if user32.IsWindowVisible(handle):
            found.append(handle)
        return True

    user32.EnumWindows(visit, 0)
    return found


def apply_overlay_style(handle: int, x: int, y: int, w: int, h: int) -> bool:
    user32 = _user32()
    topmost = ctypes.wintypes.HWND(-1)

    style = user32.GetWindowLongW(handle, _GWL_STYLE)
    user32.SetWindowLongW(
        handle, _GWL_STYLE,
        style & ~(_WS_CAPTION | _WS_THICKFRAME | _WS_MINIMIZEBOX | _WS_MAXIMIZEBOX | _WS_SYSMENU),
    )
    ex_style = user32.GetWindowLongW(handle, _GWL_EXSTYLE)
    user32.SetWindowLongW(
        handle, _GWL_EXSTYLE,
        ex_style | _WS_EX_LAYERED | _WS_EX_TRANSPARENT | _WS_EX_NOACTIVATE | _WS_EX_TOOLWINDOW,
    )
    user32.SetWindowPos(handle, topmost, x, y, w, h, _SWP_NOACTIVATE | _SWP_FRAMECHANGED)

    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(handle, ctypes.byref(rect))
    placed = (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top) == (x, y, w, h)
    still_framed = bool(user32.GetWindowLongW(handle, _GWL_STYLE) & (_WS_CAPTION | _WS_THICKFRAME))
    on_top = bool(user32.GetWindowLongW(handle, _GWL_EXSTYLE) & _WS_EX_TOPMOST)
    return placed and on_top and not still_framed


def outer_rect(handle: int):
    rect = ctypes.wintypes.RECT()
    if not handle or not ctypes.windll.user32.GetWindowRect(handle, ctypes.byref(rect)):
        return None
    return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)


def clip_window(handle: int, left: int, top: int, right: int, bottom: int, radius: int) -> bool:
    gdi32 = ctypes.windll.gdi32
    region = gdi32.CreateRoundRectRgn(left, top, right + 1, bottom + 1, 2 * radius, 2 * radius)
    if not region:
        return False
    if ctypes.windll.user32.SetWindowRgn(handle, region, True):
        return True
    gdi32.DeleteObject(region)
    return False


def give_focus_back(handle: int) -> bool:
    if not handle:
        return False
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.IsWindow(handle):
        return False
    if user32.IsIconic(handle):
        user32.ShowWindow(handle, _SW_RESTORE)

    current = kernel32.GetCurrentThreadId()
    holder = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    target = user32.GetWindowThreadProcessId(handle, None)
    user32.AttachThreadInput(current, holder, True)
    user32.AttachThreadInput(current, target, True)
    user32.SetForegroundWindow(handle)
    user32.BringWindowToTop(handle)
    user32.AttachThreadInput(current, target, False)
    user32.AttachThreadInput(current, holder, False)
    return user32.GetForegroundWindow() == handle


def popen_kwargs_no_activate() -> dict:
    info = subprocess.STARTUPINFO()
    info.dwFlags |= _STARTF_USESHOWWINDOW
    info.wShowWindow = _SW_SHOWNOACTIVATE
    return {'startupinfo': info}


def toggle_fullscreen() -> bool:
    user32 = ctypes.windll.user32
    user32.keybd_event(_VK_MENU, 0, 0, 0)
    user32.keybd_event(_VK_RETURN, 0, 0, 0)
    user32.keybd_event(_VK_RETURN, 0, _KEYEVENTF_KEYUP, 0)
    user32.keybd_event(_VK_MENU, 0, _KEYEVENTF_KEYUP, 0)
    return True


def _job_kernel32():
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    kernel32.CreateJobObjectW.restype = ctypes.wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        ctypes.wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, ctypes.wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = ctypes.wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = ctypes.wintypes.BOOL
    return kernel32


def start_child_in_job(args: list, **popen_kwargs) -> subprocess.Popen:
    process = subprocess.Popen(args, **popen_kwargs)
    kernel32 = _job_kernel32()
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return process
    limits = _JobExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits),
    ):
        kernel32.CloseHandle(job)
        return process
    handle = _kernel32().OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, process.pid)
    if handle:
        kernel32.AssignProcessToJobObject(job, handle)
        kernel32.CloseHandle(handle)
    _open_jobs.append(job)
    return process


def open_target(target: str) -> bool:
    try:
        if '://' in target:
            os.startfile(target)
        else:
            subprocess.Popen([target], cwd=os.path.dirname(target) or None)
    except OSError:
        return False
    return True


def move_cursor(x: int, y: int):
    ctypes.windll.user32.SetCursorPos(x, y)


def mouse_down():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)


def mouse_up():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
