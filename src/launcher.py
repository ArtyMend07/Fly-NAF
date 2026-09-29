import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
from env import anchor, desktop, profiles
from env.overlay import anchor_to_game, find_game_window, hold_foreground
from scripts import fetch_data

_log = logging.getLogger(__name__)

NEW = 'new'
CONTINUE = 'continue'
MANUAL = 'manual'
MODES = (NEW, CONTINUE, MANUAL)

_PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env', 'launcher.html')
_FLY_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env', 'assets', 'neuromechfly.bin.gz')


def save_file_path() -> str | None:
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return None
    return os.path.join(appdata, 'MMFApplications', 'freddy')


def saved_night(path: str | None = None) -> int | None:
    path = path or save_file_path()
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding='latin-1') as handle:
            for line in handle:
                key, _sep, value = line.partition('=')
                if key.strip().lower() == 'level':
                    return int(value.strip())
    except (OSError, ValueError):
        return None
    return None


def menu_point(mode: str) -> tuple | None:
    params = config.GAME_LAUNCHER
    points = {
        NEW: (params.new_game_x, params.new_game_y),
        CONTINUE: (params.continue_x, params.continue_y),
    }
    x, y = points.get(mode, (None, None))
    if x is None or y is None:
        return None
    return (x, y)


def game_target() -> str:
    return config.GAME_LAUNCHER.executable or config.GAME_LAUNCHER.steam_uri


class LauncherSession:
    def __init__(self):
        self._lock = threading.Lock()
        self.chosen = threading.Event()
        self.mode = None
        self.phase = 'choosing'
        self.message = ''
        self.opened_game = False

    def choose(self, mode: str) -> bool:
        with self._lock:
            if self.mode is not None or mode not in MODES:
                return False
            self.mode = mode
        self.chosen.set()
        return True

    def report(self, phase: str, message: str):
        with self._lock:
            self.phase, self.message = phase, message
        if phase == 'error':
            _log.error(message)
        else:
            _log.info(message)

    def status(self) -> dict:
        with self._lock:
            mode, phase, message = self.mode, self.phase, self.message
        target = game_target()
        return {
            'platform': desktop.name,
            'data_ready': fetch_data.ready(),
            'game_running': bool(find_game_window()),
            'opens_with': 'Steam' if '://' in target else os.path.basename(target),
            'night': saved_night(),
            'menu': {NEW: menu_point(NEW) is not None, CONTINUE: menu_point(CONTINUE) is not None},
            'mode': mode,
            'phase': phase,
            'message': message,
        }


def open_game(session: LauncherSession) -> int:
    handle = find_game_window()
    if handle:
        session.report('found', 'the game is already running, the menu is left to you')
        return handle

    target = game_target()
    session.report('opening', f'opening the game through {target}')
    if not desktop.open_target(target):
        session.report('error', f'could not open {target}')
        return 0
    session.opened_game = True

    deadline = time.monotonic() + config.GAME_LAUNCHER.window_wait_sec
    while time.monotonic() < deadline:
        handle = find_game_window()
        if handle:
            session.report('open', 'the game is open, loading the brain')
            return handle
        time.sleep(0.5)
    session.report('error', 'the game window never appeared')
    return 0


def _fills_screen(rect) -> bool:
    screen_w, screen_h = desktop.screen_size()
    return rect[2] >= screen_w and rect[3] >= screen_h


def leave_fullscreen(session: LauncherSession) -> bool:
    params = config.GAME_LAUNCHER
    if not params.windowed:
        return True
    deadline = time.monotonic() + params.windowed_wait_sec
    windowed_since = None
    while time.monotonic() < deadline:
        handle = find_game_window()
        rect = desktop.window_rect(handle) if handle else None
        if rect is not None and not _fills_screen(rect):
            windowed_since = windowed_since or time.monotonic()
            if time.monotonic() - windowed_since >= params.windowed_stable_sec:
                session.report('windowed', f'the game runs in a {rect[2]}x{rect[3]} window')
                return True
            time.sleep(0.25)
            continue
        windowed_since = None
        if not handle:
            time.sleep(0.5)
            continue
        hold_foreground(handle, timeout_sec=3.0, settle_sec=0.5)
        if rect is not None and desktop.toggle_fullscreen():
            _log.info('the game is fullscreen, sending Alt+Enter to put it in a window')
        time.sleep(3.0)
    session.report(
        'fullscreen',
        'the game stayed fullscreen, press Alt+Enter in it or the panel will black it out',
    )
    return False


def _click(point: tuple):
    delay = config.MOTOR_CALIBRATION.click_delay_sec
    desktop.move_cursor(*anchor.point(*point))
    time.sleep(delay)
    desktop.mouse_down()
    time.sleep(delay)
    desktop.mouse_up()


def night_starter(session: LauncherSession):
    params = config.GAME_LAUNCHER

    def begin():
        handle = find_game_window()
        if not handle:
            session.report('error', 'the game window is gone')
            return
        hold_foreground(handle, timeout_sec=config.BRAIN_VIEW.focus_handback_sec, settle_sec=1.0)

        point = menu_point(session.mode)
        if point is None or not session.opened_game:
            wait = config.BRAIN_VIEW.start_countdown_sec
            _log.info('pick %s in the menu yourself, the fly starts in %.0fs', session.mode, wait)
            time.sleep(wait)
            return

        time.sleep(params.menu_settle_sec)
        anchor_to_game()
        _click(point)
        _log.info('clicked %s in the menu', session.mode)
        time.sleep(params.night_start_new_sec if session.mode == NEW
                   else params.night_start_continue_sec)

    return begin


class _Handler(BaseHTTPRequestHandler):
    session: LauncherSession = None
    origin: str = ''

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/status':
            self._send(200, 'application/json', json.dumps(self.session.status()).encode())
            return
        if path == '/fly.bin':
            with open(_FLY_MODEL, 'rb') as handle:
                self._send(200, 'application/octet-stream', handle.read())
            return
        with open(_PAGE, 'rb') as handle:
            self._send(200, 'text/html; charset=utf-8', handle.read())

    def do_POST(self):
        url = urlparse(self.path)
        sender = self.headers.get('Origin')
        if url.path != '/start' or (sender and sender != self.origin):
            self._send(403, 'application/json', b'{"ok":false}')
            return
        mode = parse_qs(url.query).get('mode', [''])[0]
        accepted = self.session.choose(mode)
        self._send(200 if accepted else 409, 'application/json',
                   json.dumps({'ok': accepted}).encode())

    def _send(self, code: int, kind: str, body: bytes):
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


class LauncherWindow:
    def __init__(self, session: LauncherSession):
        self._session = session
        self._server = None
        self._browser = None

    def open(self) -> bool:
        params = config.GAME_LAUNCHER
        handler = type('Handler', (_Handler,), {'session': self._session})
        try:
            self._server = ThreadingHTTPServer(('127.0.0.1', params.port), handler)
        except OSError:
            self._server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        port = self._server.server_address[1]
        handler.origin = f'http://127.0.0.1:{port}'
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

        browser = desktop.find_browser()
        if browser is None:
            _log.warning('no Edge or Chrome install found, open %s/ yourself', handler.origin)
            return False
        screen_w, screen_h = desktop.screen_size()
        x = max(0, (screen_w - params.width) // 2)
        y = max(0, (screen_h - params.height) // 2)
        self._browser = desktop.start_child_in_job([
            browser,
            f'--app={handler.origin}/',
            f'--user-data-dir={profiles.fresh("launcher")}',
            f'--window-position={x},{y}',
            f'--window-size={params.width},{params.height}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-sync',
        ], **desktop.popen_kwargs_no_activate())
        return True

    def close(self, linger_sec: float = 0.0):
        if linger_sec:
            time.sleep(linger_sec)
        if self._browser is not None and self._browser.poll() is None:
            self._browser.terminate()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()


def ask_in_terminal(session: LauncherSession):
    answers = {'n': NEW, 'c': CONTINUE, 'm': MANUAL}
    night = saved_night()
    hint = f' (saved night {night})' if night else ''
    while not session.chosen.is_set():
        reply = input(f'[n]ew game, [c]ontinue{hint}, or [m]anual start? ').strip().lower()[:1]
        if reply in answers:
            session.choose(answers[reply])
