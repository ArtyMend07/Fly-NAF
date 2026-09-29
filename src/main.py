import asyncio
import logging
import os
import subprocess
import threading
import time

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
from night.calibration import calibrate
from night.engine import ConnectomeEngine
from night.motor import await_motor
from night.state import MotorRefrac, SaccadeRequest, SensoryState
from search_drive import ExploreDrive, SearchDrive
from telemetry import ConnectomeTelemetry
from recorder import SessionRecorder
import tuning

TRACE = SessionRecorder(enabled=False)

_log = logging.getLogger(__name__)

_BRAIN_VIEW_PIN: dict = {}


async def _vision_task(
    vision: FNAFVision, controller: FNAFController, state: SensoryState, shutdown: asyncio.Event
):
    delay = config.VISION_DYNAMICS.capture_delay_sec
    while not shutdown.is_set():
        state.office_centred = controller.facing() == 'centre'
        cam_up = state.office_centred and vision.is_camera_up()
        now = time.time()
        looking_left = state.check_left and now >= state.blind_until['left']
        looking_right = state.check_right and now >= state.blind_until['right']
        state.left_rate = vision.get_left_sensory_rate() if looking_left else 0.0
        state.right_rate = vision.get_right_sensory_rate() if looking_right else 0.0
        state.cam_inhib = config.SIMULATION_PARAMS.base_sensory_rate_hz if cam_up else 0.0
        await asyncio.sleep(delay)


async def _office_comes_back(
    vision: FNAFVision, controller, settle_sec: float, confirm_sec: float
) -> bool:
    vision.clear_buffers()
    deadline = time.time() + confirm_sec
    agreed = 0
    while time.time() < deadline:
        await asyncio.sleep(settle_sec / 2.0)
        if controller is not None and controller.facing() != 'centre':
            agreed = 0
            continue
        if vision.is_camera_up():
            agreed = 0
            continue
        agreed += 1
        if agreed >= 2:
            return True
    return False


async def _reanchor_office_reference(
    vision: FNAFVision, settle_sec: float, confirm_sec: float = 0.0, controller=None
) -> bool:
    if not await _office_comes_back(vision, controller, settle_sec, max(confirm_sec, settle_sec)):
        return False
    vision.capture_camera_closed_reference()
    return True


async def _lower_monitor(
    vision: FNAFVision, controller: FNAFController, settle_sec: float,
    confirm_sec: float, attempt: int, gesture_budget: int,
) -> bool:
    gesture = None
    if attempt < gesture_budget:
        if attempt % 2 == 0:
            gesture = 'sliding off the tablet bar'
            await await_motor(controller.close_camera(force=True))
        else:
            gesture = 'tapping the tablet bar'
            await await_motor(controller.nudge_camera_bar())

    if await _reanchor_office_reference(vision, settle_sec, confirm_sec, controller):
        return True

    if gesture is None:
        return False

    _log.warning(
        'the monitor is still up after %s, attempt %d of %d, office patch %.0f mse from '
        'its reference', gesture, attempt + 1, gesture_budget, vision.camera_mse(),
    )
    return False


def _release_reason(explore, bored: bool) -> str:
    if not bored:
        return 'cap'
    return 'drive' if explore.spent else 'search'


class MonitorControl:
    def __init__(self, vision, controller, telemetry, state: SensoryState):
        foraging = config.FORAGING_PARAMS
        self._vision = vision
        self._controller = controller
        self._telemetry = telemetry
        self._state = state
        self._watch_max_sec = foraging.camera_watch_max_sec
        self._watch_min_sec = foraging.camera_watch_min_sec
        self._release_bias = foraging.camera_release_forage_bias
        self._refractory_sec = foraging.camera_refractory_sec
        self._settle_sec = config.CAMERA_DETECTION.close_settle_sec
        self._retry_sec = config.CAMERA_DETECTION.lower_retry_sec
        self._confirm_sec = config.CAMERA_DETECTION.lower_confirm_sec
        self._gesture_budget = config.CAMERA_DETECTION.lower_gesture_attempts
        self._attempts = 0
        self.is_open = False
        self.ready_at = 0.0
        self._releasing = False
        self._lowering = None
        self._retry_at = 0.0
        self._opened_at = 0.0
        self._cap_at = 0.0

    def update(self, now: float, explore, forage_bias: float, look_pending: bool):
        self._collect_lowering(now)
        if self._lowering is not None:
            return
        if self.is_open:
            self._release(now, explore, forage_bias)
            return
        if explore.wants_monitor and now > self.ready_at and not look_pending:
            self._raise(now, explore)

    def _raise(self, now: float, explore):
        _log.info(
            'DNp09 %s, camera pull triggered',
            'fired' if explore.commanded
            else f'drive reached the bound ({explore.drive:.2f})',
        )
        self._telemetry.record_camera_pull(explore.commanded, explore.drive)
        self._controller.open_camera()
        self.is_open = True
        self._state.camera_open = True
        self._opened_at = now
        self._cap_at = now + self._watch_max_sec

    def _release(self, now: float, explore, forage_bias: float):
        watched_for = now - self._opened_at
        if not self._releasing:
            bored = watched_for >= self._watch_min_sec and (
                explore.spent or forage_bias >= self._release_bias
            )
            if now < self._cap_at and not bored:
                return
            self._releasing = True
            self._telemetry.record_camera_release(watched_for, _release_reason(explore, bored))
        if now < self._retry_at:
            return
        if self._attempts == self._gesture_budget:
            _log.warning(
                'neither gesture brought the monitor down in %d tries, so the fly has stopped '
                'reaching for it and is just watching the screen. Lower the tablet by hand and '
                'it picks up from there.', self._gesture_budget,
            )
        self._lowering = asyncio.create_task(
            _lower_monitor(
                self._vision, self._controller, self._settle_sec, self._confirm_sec,
                self._attempts, self._gesture_budget,
            )
        )
        self._attempts += 1

    def _collect_lowering(self, now: float):
        if self._lowering is None or not self._lowering.done():
            return
        lowered = self._lowering.result()
        self._lowering = None
        if not lowered:
            self._telemetry.record_monitor_stuck()
            self._retry_at = now + self._retry_sec
            return
        if self._attempts > 1:
            _log.info('the office is back after %d lowering attempts', self._attempts)
        self.is_open = False
        self._releasing = False
        self._attempts = 0
        self._state.camera_open = False
        self.ready_at = now + self._refractory_sec


async def _observe_hallway(
    engine: ConnectomeEngine, vision: FNAFVision, state: SensoryState, side: str
) -> tuple:
    foraging = config.FORAGING_PARAMS
    vision.reset_peak_mse(side)
    opened_at_frame = engine.frames
    opened_at_driven = engine.driven_frames[side]
    deadline = time.time() + foraging.light_inspection_max_sec

    if side == 'left':
        state.check_left = True
    else:
        state.check_right = True

    fired = False
    while engine.frames - opened_at_frame < foraging.light_inspection_frames:
        if state.l_spike if side == 'left' else state.r_spike:
            fired = True
            break
        if time.time() >= deadline:
            break
        await asyncio.sleep(engine.frame_dt / 2)

    state.check_left = False
    state.check_right = False
    return (vision.peak_mse(side), engine.frames - opened_at_frame,
            engine.driven_frames[side] - opened_at_driven, fired)


async def _saccade_task(
    engine: ConnectomeEngine,
    vision: FNAFVision,
    controller: FNAFController,
    state: SensoryState,
    shutdown: asyncio.Event,
    telemetry: ConnectomeTelemetry,
    calibration_done: asyncio.Event,
    saccade: SaccadeRequest,
    view_ready: asyncio.Event,
    begin_night=None,
):
    await view_ready.wait()
    await calibrate(vision, controller, begin_night)
    calibration_done.set()

    while not shutdown.is_set():
        if saccade.side is None:
            await asyncio.sleep(engine.frame_dt)
            continue

        side = saccade.side
        saccade.busy = True

        while state.camera_open and not shutdown.is_set():
            await asyncio.sleep(engine.frame_dt)
        if shutdown.is_set():
            break

        _log.info('%s light check, %s (search drive %+.2f)',
                  side, saccade.reason, saccade.drive)
        telemetry.record_light_saccade(side, saccade.drive, saccade.reason)
        switch = controller.set_left_light if side == 'left' else controller.set_right_light

        await await_motor(switch(True))
        await asyncio.sleep(config.FORAGING_PARAMS.light_activation_settle_sec)

        contrast, frames, driven, fired = await _observe_hallway(engine, vision, state, side)
        switch(False)

        threshold = config.FORAGING_PARAMS.mse_threshold
        _log.info('%s hallway read %.0f against a %.0f threshold, eye driven %d of %d frames%s',
                  side, contrast, threshold, driven, frames,
                  ', giant fiber answered' if fired else '')
        telemetry.record_look_contrast(side, contrast, frames, driven)

        saccade.ready_at = time.time() + config.FORAGING_PARAMS.saccade_refractory_sec
        saccade.side = None
        saccade.busy = False


async def _engine_task(
    engine: ConnectomeEngine,
    vision: FNAFVision,
    controller: FNAFController,
    state: SensoryState,
    shutdown: asyncio.Event,
    telemetry: ConnectomeTelemetry,
    calibration_done: asyncio.Event,
    feed: SpikeFeed,
    highlights: dict,
    saccade: SaccadeRequest,
):
    await calibration_done.wait()

    search = SearchDrive(engine.sensory_span)
    explore = ExploreDrive()
    monitor = MonitorControl(vision, controller, telemetry, state)
    refrac = MotorRefrac()
    motor_dur = config.FORAGING_PARAMS.motor_refractory_sec
    cam_stuck_warn_sec = config.CAMERA_DETECTION.stuck_warn_sec
    inhib_since = 0.0
    inhib_warned_at = 0.0

    doors = (('left', controller.open_left_door), ('right', controller.open_right_door))
    door_closed = {'left': False, 'right': False}
    door_closed_at = {'left': 0.0, 'right': 0.0}
    door_hold = {'left': 0.0, 'right': 0.0}
    hold_leak = config.DOOR_DYNAMICS.hold_leak_per_frame
    hold_release = config.DOOR_DYNAMICS.release_threshold
    reopen_settle = config.DOOR_DYNAMICS.reopen_settle_sec
    nominal_fps = config.SIMULATION_PARAMS.target_fps
    last_frame_at = time.time()

    while not shutdown.is_set():
        t_start = time.perf_counter()
        now = time.time()
        frame_elapsed = now - last_frame_at
        last_frame_at = now

        inputs = (state.left_rate > 0.0, state.right_rate > 0.0)
        loop = asyncio.get_event_loop()
        spikes = await loop.run_in_executor(None, engine.step, state, now)

        state.l_spike = bool(spikes[0, engine.l_motor_idx].any())
        state.r_spike = bool(spikes[0, engine.r_motor_idx].any())
        state.l_sensory_count = int(spikes[0, engine.l_sensory_idx].sum().item())
        state.r_sensory_count = int(spikes[0, engine.r_sensory_idx].sum().item())

        explore.update(
            engine.explore_membrane,
            bool(spikes[0, engine.explore_idx].any()),
            frame_elapsed,
        )
        look_pending = saccade.side is not None or saccade.busy
        telemetry.record_frame(state.cam_inhib > 0, look_pending)
        monitor.update(now, explore, state.forage_bias, look_pending)

        can_look = not look_pending and not monitor.is_open and now >= saccade.ready_at
        wants = search.update(
            engine.eye_membrane_diff,
            state.l_sensory_count,
            state.r_sensory_count,
            frame_elapsed,
            now,
            can_look,
        )
        state.forage_bias = search.tension
        if wants is not None:
            saccade.reason = search.reason
            saccade.drive = search.last_drive
            saccade.side = wants

        feed.publish(spikes[0].nonzero().flatten().cpu().numpy())
        highlights['gf_l'] = state.l_spike
        highlights['gf_r'] = state.r_spike
        highlights['camera'] = monitor.is_open
        highlights['in_l'], highlights['in_r'] = inputs
        highlights['look_l'] = state.check_left
        highlights['look_r'] = state.check_right
        highlights['mse_l'] = vision.last_mse('left') if state.check_left else None
        highlights['mse_r'] = vision.last_mse('right') if state.check_right else None
        highlights['mse_th'] = vision.mse_threshold
        highlights['eye_l'] = state.l_sensory_count
        highlights['eye_r'] = state.r_sensory_count
        highlights['door_l'] = door_closed['left']
        highlights['door_r'] = door_closed['right']
        if state.check_left:
            highlights['gaze'] = 'LEFT'
        elif state.check_right:
            highlights['gaze'] = 'RIGHT'
        else:
            highlights['gaze'] = '--'

        TRACE.frame(
            now - telemetry.start_time, state, engine,
            state.l_spike, state.r_spike,
            vision.peak_mse('left'), vision.peak_mse('right'), monitor.is_open,
        )

        if state.cam_inhib > 0 and not monitor.is_open:
            if inhib_since == 0.0:
                inhib_since = now
            elif now - inhib_since > cam_stuck_warn_sec and now - inhib_warned_at > 30.0:
                _log.warning(
                    'the office reference has disagreed with the screen for %.0fs at %.0f mse; '
                    'the inhibitors are being driven with the tablet down, which silences '
                    'the giant fiber and DNp09. Recapture it with the office on screen.',
                    now - inhib_since, vision.camera_mse(),
                )
                inhib_warned_at = now
        else:
            inhib_since = 0.0

        decay = hold_leak ** (frame_elapsed * nominal_fps)

        for side, open_door in doors:
            if not door_closed[side]:
                continue
            state.blind_until[side] = now + reopen_settle
            door_hold[side] *= decay
            if door_hold[side] >= hold_release or state.camera_open:
                continue
            held = now - door_closed_at[side]
            _log.info('%s escape drive decayed after %.1fs, door released', side, held)
            telemetry.record_door_release(side, held)
            open_door()
            door_closed[side] = False

        if spikes[0, engine.l_motor_idx].any() and now > refrac.left:
            moved = False
            if not state.camera_open:
                door_hold['left'] = 1.0
                if not door_closed['left']:
                    _log.warning('left giant fiber fired')
                    telemetry.record_door_panic('left')
                    controller.trigger_left_door()
                    door_closed['left'] = True
                    door_closed_at['left'] = now
                    moved = True
                refrac.left = now + motor_dur
            feed.trace_escape('left', engine.l_motor_idx[0], engine.l_sensory_idx, moved)
            state.left_rate = 0.0

        if spikes[0, engine.r_motor_idx].any() and now > refrac.right:
            moved = False
            if not state.camera_open:
                door_hold['right'] = 1.0
                if not door_closed['right']:
                    _log.warning('right giant fiber fired')
                    telemetry.record_door_panic('right')
                    controller.trigger_right_door()
                    door_closed['right'] = True
                    door_closed_at['right'] = now
                    moved = True
                refrac.right = now + motor_dur
            feed.trace_escape('right', engine.r_motor_idx[0], engine.r_sensory_idx, moved)
            state.right_rate = 0.0

        elapsed = time.perf_counter() - t_start
        remaining = engine.frame_dt - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        else:
            await asyncio.sleep(0)


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


async def _run(telemetry: ConnectomeTelemetry, begin_night=None):
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
        tg.create_task(_vision_task(vision, controller, state, shutdown))
        tg.create_task(_saccade_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            saccade, view_ready, begin_night,
        ))
        tg.create_task(_engine_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            feed, highlights, saccade,
        ))
        tg.create_task(_brain_view_task(
            feed, highlights, shutdown, view_ready, vision.latest_patches,
        ))


def main(begin_night=None):
    global TRACE
    if os.environ.get('FLYNAF_RECORD', '1') != '0':
        TRACE = SessionRecorder()
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
        asyncio.run(_run(telemetry, begin_night))
    except KeyboardInterrupt:
        _log.info('shutdown')
    finally:
        TRACE.close()
        path = telemetry.dump_report()
        _log.info('Telemetry report saved to %s', path)
