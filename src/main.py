import asyncio
import logging
import os
import subprocess
import threading

import torch

import config
from env import desktop, profiles
from env.vision import FNAFVision
from env.input_controller import FNAFController, start_worker
from env.brain_view import BrainViewServer, SpikeFeed
from env.cascade import CascadeTracer
from env.overlay import (
    anchor_to_game,
    beside_game_rect,
    capture_regions,
    find_browser,
    find_game_window,
    game_in_front,
    hold_foreground,
    is_window,
    ingame_overlay_rect,
    motor_regions,
    pick_overlay_position,
    keep_pinned,
    pin_as_overlay,
    screen_size,
    window_title,
)
from night.engine import ConnectomeEngine
from night.state import SaccadeRequest, SensoryState
from night.tasks import engine_task, saccade_task, vision_task
from telemetry import ConnectomeTelemetry
from recorder import SessionRecorder
import tuning

_log = logging.getLogger(__name__)

_BRAIN_VIEW_PIN: dict = {}


def _restore_game_focus(game: int, panel: int, timeout_sec: float):
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


def _launch_brain_view_window(port: int) -> bool:
    params = config.BRAIN_VIEW
    url = f'http://127.0.0.1:{port}/'

    screen_w, screen_h = screen_size()
    beside = beside_game_rect(
        screen_w, screen_h, params.beside_min_width, params.width, params.ingame_margin,
    )
    ingame = None if beside else ingame_overlay_rect(
        params.ingame_width, params.ingame_height, params.ingame_margin,
    )
    if beside is not None:
        x, y, width, height = beside
        page = url
        topmost = True
        _log.info('brain view beside the game, panel %dx%d at %d,%d', width, height, x, y)
    elif ingame is not None:
        x, y = ingame
        width, height = params.ingame_width, params.ingame_height
        page = f'{url}?mini=1'
        topmost = True
        _log.info('brain view in-game overlay, panel %dx%d at %d,%d', width, height, x, y)
    else:
        position = pick_overlay_position(
            screen_w, screen_h, params.width, params.height,
            capture_regions() + motor_regions(),
        )
        if position is None:
            _log.warning('brain view has no screen area clear of capture and motor targets')
            return False
        x, y = position
        width, height = params.width, params.height
        page = url
        topmost = False
        _log.info('brain view side panel, panel %dx%d at %d,%d', width, height, x, y)

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
        _restore_game_focus(game, abs(hwnd), params.focus_handback_sec)
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

    stop = threading.Event()
    keeper = threading.Thread(
        target=keep_pinned, args=(hwnd, x, y, width, height, stop), daemon=True,
    )
    keeper.start()
    _BRAIN_VIEW_PIN['stop'] = stop
    _log.info('brain view pinned as a borderless overlay at %d,%d', x, y)
    return True


async def _brain_view_task(
    feed: SpikeFeed, highlights: dict, shutdown: asyncio.Event, view_ready: asyncio.Event,
    eyes=None,
):
    if not config.BRAIN_VIEW.enabled:
        view_ready.set()
        return

    server = BrainViewServer(feed, highlights, eyes)
    try:
        port = await server.start()
        _log.info('brain view server listening on %d', port)
        if config.BRAIN_VIEW.launch_browser:
            await asyncio.get_event_loop().run_in_executor(
                None, _launch_brain_view_window, port
            )
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


async def _run(telemetry: ConnectomeTelemetry, trace: SessionRecorder, begin_night=None):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    _log.info('brain core online, device=%s', device)

    start_worker()
    engine = ConnectomeEngine(device)
    vision = FNAFVision()
    controller = FNAFController()
    state = SensoryState()
    shutdown = asyncio.Event()
    calibration_done = asyncio.Event()
    view_ready = asyncio.Event()
    tracer = CascadeTracer.from_csr(engine.synapses) if config.BRAIN_VIEW.enabled else None
    feed = SpikeFeed(engine._adapter.num_neurons, tracer)
    highlights = {'gaze': '--', 'gf_l': False, 'gf_r': False, 'camera': False}
    saccade = SaccadeRequest()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(vision_task(vision, controller, state, shutdown))
        tg.create_task(saccade_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            saccade, view_ready, begin_night,
        ))
        tg.create_task(engine_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            feed, highlights, saccade, trace,
        ))
        tg.create_task(_brain_view_task(
            feed, highlights, shutdown, view_ready, vision.latest_patches,
        ))


def main(begin_night=None):
    trace = SessionRecorder(enabled=os.environ.get('FLYNAF_RECORD', '1') != '0')
    tuning.load()
    if anchor_to_game():
        _log.info('screen targets follow the game window, no calibration needed')
    else:
        _log.warning(
            'the game window was not found, so the screen targets in config.py are used as '
            'measured, which assumes a 1280x720 window at the top left of the display'
        )
    telemetry = ConnectomeTelemetry()
    try:
        asyncio.run(_run(telemetry, trace, begin_night))
    except KeyboardInterrupt:
        _log.info('shutdown')
    finally:
        trace.close()
        path = telemetry.dump_report()
        _log.info('Telemetry report saved to %s', path)
