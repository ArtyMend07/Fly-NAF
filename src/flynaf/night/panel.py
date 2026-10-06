import asyncio
import logging
import os
import subprocess
import threading

from flynaf import config
from flynaf.env import desktop, profiles
from flynaf.env.brain_view import BrainViewServer, SpikeFeed
from flynaf.env.overlay import (
    anchor_to_game,
    beside_game_rect,
    capture_regions,
    dock_game_for_panel,
    find_browser,
    find_game_window,
    game_in_front,
    hold_foreground,
    ingame_overlay_rect,
    is_window,
    keep_pinned,
    motor_regions,
    pick_overlay_position,
    pin_as_overlay,
    screen_size,
    strip_browser_chrome,
    window_title,
)

_log = logging.getLogger(__name__)

_BRAIN_VIEW_PIN: dict = {}


def restore_game_focus(game: int, panel: int, timeout_sec: float):
    if not game or game == panel or not is_window(game):
        game = find_game_window()
    if not game or game == panel:
        _log.warning(
            'nothing recognisable sits under the office capture patch, so focus cannot be '
            'handed back; click the game yourself or the captures will read the browser'
        )
        return
    if hold_foreground(game, timeout_sec):
        anchor_to_game()
        _log.info('focus handed back to %r', window_title(game) or '<untitled>')
        return
    _log.warning(
        'the window under the office (%r) did not come back to the foreground within %.0fs; '
        'click the game so the captures stop reading whatever is on top of it',
        window_title(game) or '<untitled>', timeout_sec,
    )


def _beside_the_game(screen_w: int):
    params = config.BRAIN_VIEW
    beside = beside_game_rect(
        screen_w, params.beside_min_width, params.width, params.ingame_margin,
    )
    if beside is not None or not params.dock_game:
        return beside
    if not dock_game_for_panel(screen_w, params.beside_min_width, params.ingame_margin):
        return None
    _log.info('game window moved to the left edge to make room for the panel')
    return beside_game_rect(
        screen_w, params.beside_min_width, params.width, params.ingame_margin,
    )


def _choose_panel_placement(url: str):
    params = config.BRAIN_VIEW
    screen_w, screen_h = screen_size()
    beside = _beside_the_game(screen_w)
    if beside is not None:
        _log.info('brain view beside the game, panel %dx%d at %d,%d', beside[2], beside[3], *beside[:2])
        return (*beside, f'{url}?corner={params.corner_radius}', True)

    ingame = ingame_overlay_rect(params.ingame_width, params.ingame_height, params.ingame_margin)
    if ingame is not None:
        _log.info('brain view in-game overlay, panel %dx%d at %d,%d',
                  params.ingame_width, params.ingame_height, *ingame)
        return (*ingame, params.ingame_width, params.ingame_height,
                f'{url}?mini=1&corner={params.corner_radius}', True)

    position = pick_overlay_position(
        screen_w, screen_h, params.width, params.height, capture_regions() + motor_regions(),
    )
    if position is None:
        _log.warning('brain view has no screen area clear of capture and motor targets')
        return None
    _log.info('brain view side panel, panel %dx%d at %d,%d', params.width, params.height, *position)
    return (*position, params.width, params.height, url, False)


def _launch_brain_view_window(port: int, page_height) -> bool:
    params = config.BRAIN_VIEW
    url = f'http://127.0.0.1:{port}/'

    placement = _choose_panel_placement(url)
    if placement is None:
        return False
    x, y, width, height, page, topmost = placement

    browser = find_browser()
    if browser is None:
        _log.warning('no Edge or Chrome install found, open %s manually', url)
        return False

    game = game_in_front() if topmost else 0
    playing = bool(game)

    profile = profiles.fresh('brainview')
    process = desktop.start_child_in_job([
        browser,
        f'--app={page}',
        f'--user-data-dir={profile}',
        f'--window-position={x},{y}',
        f'--window-size={width},{height}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-sync',
        '--disable-features=Translate,MediaRouter,CalculateNativeWinOcclusion',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-background-timer-throttling',
    ], **desktop.popen_kwargs_no_activate())
    _log.info('brain view launched with %s', os.path.basename(browser))
    _BRAIN_VIEW_PIN['process'] = process

    if not topmost:
        return True

    hwnd = pin_as_overlay(
        ('Connectome Live Activity', f'127.0.0.1:{port}'), x, y, width, height,
    )
    if playing:
        restore_game_focus(game, abs(hwnd), params.focus_handback_sec)
    if hwnd == 0:
        _log.warning(
            'brain view window never appeared within the wait (browser exit code %s), '
            'it will not be on top of the game', process.poll(),
        )
        return False
    if hwnd < 0:
        _log.warning(
            'brain view window found but it would not settle at %d,%d %dx%d without its '
            'frame and on top; it will show as an ordinary window over the game',
            x, y, width, height,
        )
        return False

    clip = None
    stripped = strip_browser_chrome(hwnd, x, y, width, height, page_height, params.corner_radius)
    if stripped is None:
        _log.warning('the browser title bar could not be cut away, the panel keeps it')
    else:
        (x, y, width, height), page = stripped
        clip = (*page, params.corner_radius)

    stop = threading.Event()
    keeper = threading.Thread(
        target=keep_pinned, args=(hwnd, x, y, width, height, stop),
        kwargs={'clip': clip}, daemon=True,
    )
    keeper.start()
    _BRAIN_VIEW_PIN['stop'] = stop
    _log.info('brain view pinned as a borderless overlay at %d,%d', x, y)
    return True


async def brain_view_task(
    feed: SpikeFeed, shutdown: asyncio.Event, view_ready: asyncio.Event,
    eyes=None,
):
    if not config.BRAIN_VIEW.enabled:
        view_ready.set()
        return

    server = BrainViewServer(feed, eyes)
    try:
        port = await server.start()
        _log.info('brain view server listening on %d', port)
        if config.BRAIN_VIEW.launch_browser:
            await asyncio.to_thread(_launch_brain_view_window, port, server.page_height)
        view_ready.set()
        await shutdown.wait()
    except OSError as exc:
        _log.warning('brain view unavailable, the run continues without it: %s', exc)
    finally:
        view_ready.set()
        await server.close()
        _close_brain_view_window()


def _close_brain_view_window():
    stop = _BRAIN_VIEW_PIN.get('stop')
    if stop is not None:
        stop.set()
    process = _BRAIN_VIEW_PIN.get('process')
    if process is not None and process.poll() is None:
        process.terminate()
        _log.info('brain view window closed')
    if process is not None:
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            return
        profiles.sweep()
