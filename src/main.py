import asyncio
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field

import torch

import config
from brain_adapter import BrainAdapter
from env.vision import FNAFVision
from env.input_controller import FNAFController, start_worker
from env.brain_view import BrainViewServer, SpikeFeed
from env.overlay import (
    capture_regions,
    find_browser,
    find_game_window,
    hold_foreground,
    ingame_overlay_rect,
    motor_regions,
    pick_overlay_position,
    keep_pinned,
    pin_as_overlay,
    screen_size,
    window_title,
)
from search_drive import ExploreDrive, SearchDrive
from telemetry import ConnectomeTelemetry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
_log = logging.getLogger(__name__)

_WARMUP_COUNTDOWN = 10
_BRAIN_VIEW_PIN: dict = {}


@dataclass
class SensoryState:
    left_rate: float = 0.0
    right_rate: float = 0.0
    cam_inhib: float = 0.0
    check_left: bool = False
    check_right: bool = False
    camera_open: bool = False
    l_spike: bool = False
    r_spike: bool = False
    l_sensory_count: int = 0
    r_sensory_count: int = 0
    forage_bias: float = 0.0
    blind_until: dict = field(default_factory=lambda: {'left': 0.0, 'right': 0.0})


@dataclass
class MotorRefrac:
    left: float = 0.0
    right: float = 0.0


@dataclass
class SaccadeRequest:
    side: str | None = None
    reason: str = ''
    drive: float = 0.0
    busy: bool = False
    ready_at: float = 0.0


class ConnectomeEngine:
    def __init__(self, device: str):
        self._device = device
        self._adapter = BrainAdapter(
            config.COMPLETENESS_CSV,
            config.CONNECTIVITY_PARQUET,
            config.DATA_DIR,
            device,
        )
        sensory = config.SENSORY_NEURONS
        motor = config.MOTOR_NEURONS

        self._l_sensory_idx = self._adapter.map_neuron_ids_to_indices(sensory.left_eye_cluster)
        self._r_sensory_idx = self._adapter.map_neuron_ids_to_indices(sensory.right_eye_cluster)
        all_sensory = self._l_sensory_idx + self._r_sensory_idx

        self._l_motor_idx = self._adapter.map_neuron_ids_to_indices([motor.dnp01_giant_fiber[0]])
        self._r_motor_idx = self._adapter.map_neuron_ids_to_indices([motor.dnp01_giant_fiber[1]])
        self._explore_idx = self._adapter.map_neuron_ids_to_indices(motor.dnp09_explore)
        self._l_inhib_idx = self._adapter.map_neuron_ids_to_indices(sensory.camera_inhibitor_left)
        self._r_inhib_idx = self._adapter.map_neuron_ids_to_indices(sensory.camera_inhibitor_right)

        self._adapter.initialize_model(exc_indices=all_sensory)

        self._rates = torch.zeros(1, self._adapter.num_neurons, device=device)
        self._base_rate = config.SIMULATION_PARAMS.base_sensory_rate_hz
        self._steps = config.SIMULATION_PARAMS.steps_per_frame
        self.frame_dt = 1.0 / config.SIMULATION_PARAMS.target_fps
        self.eye_membrane_diff = 0.0
        self.explore_membrane = 0.0

    @property
    def sensory_span(self) -> int:
        return len(self._l_sensory_idx) * self._steps

    def step(self, state: SensoryState, current_time: float) -> torch.Tensor:
        self._rates.zero_()

        self._rates[:, self._l_sensory_idx] = self._base_rate * state.left_rate
        self._rates[:, self._r_sensory_idx] = self._base_rate * state.right_rate
        self._rates[:, self._l_inhib_idx] = state.cam_inhib
        self._rates[:, self._r_inhib_idx] = state.cam_inhib

        noise_hz = config.FORAGING_PARAMS.subliminal_noise_hz
        self._rates += torch.rand_like(self._rates) * noise_hz

        spikes = self._adapter.step(self._rates, steps=self._steps)

        v = self._adapter.membrane_potential()
        self.eye_membrane_diff = float(
            v[0, self._l_sensory_idx].mean() - v[0, self._r_sensory_idx].mean()
        )
        self.explore_membrane = float(v[0, self._explore_idx].mean())
        return spikes

    @property
    def l_motor_idx(self):
        return self._l_motor_idx

    @property
    def r_motor_idx(self):
        return self._r_motor_idx

    @property
    def explore_idx(self):
        return self._explore_idx

    @property
    def l_sensory_idx(self):
        return self._l_sensory_idx

    @property
    def r_sensory_idx(self):
        return self._r_sensory_idx


async def _vision_task(vision: FNAFVision, state: SensoryState, shutdown: asyncio.Event):
    delay = config.VISION_DYNAMICS.capture_delay_sec
    while not shutdown.is_set():
        cam_up = vision.is_camera_up()
        now = time.time()
        looking_left = state.check_left and now >= state.blind_until['left']
        looking_right = state.check_right and now >= state.blind_until['right']
        state.left_rate = vision.get_left_sensory_rate() if looking_left else 0.0
        state.right_rate = vision.get_right_sensory_rate() if looking_right else 0.0
        state.cam_inhib = config.SIMULATION_PARAMS.base_sensory_rate_hz if cam_up else 0.0
        await asyncio.sleep(delay)


async def _calibrate_eye_references_live(vision: FNAFVision, controller: FNAFController, settle: float):
    _log.info('calibrating in %d seconds', _WARMUP_COUNTDOWN)
    for i in range(_WARMUP_COUNTDOWN, 0, -1):
        _log.info('T-%d', i)
        await asyncio.sleep(1.0)

    await _await_motor(controller.set_left_light(True))
    await asyncio.sleep(settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_left_reference)
    _log.info('left reference captured')
    await _await_motor(controller.set_left_light(False))

    await _await_motor(controller.set_right_light(True))
    await asyncio.sleep(settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_right_reference)
    _log.info('right reference captured')
    await _await_motor(controller.set_right_light(False))

    vision.save_reference_to_disk()


async def _calibrate(vision: FNAFVision, controller: FNAFController):
    settle = config.FORAGING_PARAMS.light_activation_settle_sec

    if vision.load_reference_from_disk():
        _log.info('loaded left/right eye references from disk, skipping live calibration')
    else:
        await _calibrate_eye_references_live(vision, controller, settle)

    await asyncio.sleep(settle)
    vision.capture_camera_closed_reference()
    _log.info('camera-closed reference captured')


async def _await_motor(done, timeout_sec: float = 6.0):
    finished = await asyncio.get_event_loop().run_in_executor(None, done.wait, timeout_sec)
    if not finished:
        _log.warning('motor command did not complete within %.0fs', timeout_sec)
    return finished


async def _reanchor_office_reference(vision: FNAFVision, settle_sec: float) -> bool:
    vision.clear_buffers()
    await asyncio.sleep(settle_sec)
    if vision.is_camera_up():
        return False
    vision.capture_camera_closed_reference()
    return True


async def _lower_monitor(
    vision: FNAFVision, controller: FNAFController, settle_sec: float
) -> bool:
    await _await_motor(controller.close_camera(force=True))
    if await _reanchor_office_reference(vision, settle_sec):
        return True

    await _await_motor(controller.nudge_camera_bar())
    if await _reanchor_office_reference(vision, settle_sec):
        return True

    _log.warning(
        'the monitor did not come down on either gesture, office patch still %.0f mse '
        'away from its reference; lower the tablet by hand to hand control back',
        vision.camera_mse(),
    )
    return False


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
            self._telemetry.record_camera_release(watched_for, explore.spent)
        if now < self._retry_at:
            return
        self._lowering = asyncio.create_task(
            _lower_monitor(self._vision, self._controller, self._settle_sec)
        )

    def _collect_lowering(self, now: float):
        if self._lowering is None or not self._lowering.done():
            return
        lowered = self._lowering.result()
        self._lowering = None
        if not lowered:
            self._telemetry.record_monitor_stuck()
            self._retry_at = now + self._retry_sec
            return
        self.is_open = False
        self._releasing = False
        self._state.camera_open = False
        self.ready_at = now + self._refractory_sec


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
):
    await view_ready.wait()
    await _calibrate(vision, controller)
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

        await _await_motor(switch(True))
        await asyncio.sleep(config.FORAGING_PARAMS.light_activation_settle_sec)

        if side == 'left':
            state.check_left = True
            await asyncio.sleep(config.FORAGING_PARAMS.light_inspection_time)
            state.check_left = False
        else:
            state.check_right = True
            await asyncio.sleep(config.FORAGING_PARAMS.light_inspection_time)
            state.check_right = False

        switch(False)

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
        if state.check_left:
            highlights['gaze'] = 'LEFT'
        elif state.check_right:
            highlights['gaze'] = 'RIGHT'
        else:
            highlights['gaze'] = '--'

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
            if not state.camera_open:
                door_hold['left'] = 1.0
                if not door_closed['left']:
                    _log.warning('left giant fiber fired')
                    telemetry.record_door_panic('left')
                    controller.trigger_left_door()
                    door_closed['left'] = True
                    door_closed_at['left'] = now
                refrac.left = now + motor_dur
            state.left_rate = 0.0

        if spikes[0, engine.r_motor_idx].any() and now > refrac.right:
            if not state.camera_open:
                door_hold['right'] = 1.0
                if not door_closed['right']:
                    _log.warning('right giant fiber fired')
                    telemetry.record_door_panic('right')
                    controller.trigger_right_door()
                    door_closed['right'] = True
                    door_closed_at['right'] = now
                refrac.right = now + motor_dur
            state.right_rate = 0.0

        elapsed = time.perf_counter() - t_start
        remaining = engine.frame_dt - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        else:
            await asyncio.sleep(0)


def _restore_game_focus(panel: int, timeout_sec: float):
    game = find_game_window()
    if not game or game == panel:
        _log.warning(
            'nothing recognisable sits under the office capture patch, so focus cannot be '
            'handed back; click the game yourself or the captures will read the browser'
        )
        return
    if hold_foreground(game, timeout_sec):
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

    ingame = ingame_overlay_rect(params.ingame_width, params.ingame_height, params.ingame_margin)
    if ingame is not None:
        x, y = ingame
        width, height = params.ingame_width, params.ingame_height
        page = f'{url}?mini=1'
        topmost = True
        _log.info('brain view in-game overlay, panel %dx%d at %d,%d', width, height, x, y)
    else:
        screen_w, screen_h = screen_size()
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

    profile = os.path.join(config.PROJECT_ROOT, 'logs', 'brain_view_profile')
    process = subprocess.Popen([
        browser,
        f'--app={page}',
        f'--user-data-dir={profile}',
        f'--window-position={x},{y}',
        f'--window-size={width},{height}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-features=Translate,MediaRouter',
    ])
    _log.info('brain view launched with %s', os.path.basename(browser))

    if not topmost:
        return True

    hwnd = pin_as_overlay(
        ('Connectome Live Activity', f'127.0.0.1:{port}'), x, y, width, height,
    )
    _restore_game_focus(abs(hwnd), params.focus_handback_sec)
    if hwnd == 0:
        _log.warning(
            'brain view window never appeared within the wait (browser exit code %s), '
            'it will not be on top of the game', process.poll(),
        )
        return False
    if hwnd < 0:
        _log.warning(
            'brain view window found but it would not stay at %d,%d %dx%d, '
            'it will not be on top of the game', x, y, width, height,
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
    feed: SpikeFeed, highlights: dict, shutdown: asyncio.Event, view_ready: asyncio.Event
):
    if not config.BRAIN_VIEW.enabled:
        view_ready.set()
        return

    server = BrainViewServer(feed, highlights)
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


async def _run(telemetry: ConnectomeTelemetry):
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
    feed = SpikeFeed(engine._adapter.num_neurons)
    highlights = {'gaze': '--', 'gf_l': False, 'gf_r': False, 'camera': False}
    saccade = SaccadeRequest()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(_vision_task(vision, state, shutdown))
        tg.create_task(_saccade_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            saccade, view_ready,
        ))
        tg.create_task(_engine_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            feed, highlights, saccade,
        ))
        tg.create_task(_brain_view_task(feed, highlights, shutdown, view_ready))


def main():
    telemetry = ConnectomeTelemetry()
    try:
        asyncio.run(_run(telemetry))
    except KeyboardInterrupt:
        _log.info('shutdown')
    finally:
        path = telemetry.dump_report()
        _log.info('Telemetry report saved to %s', path)


if __name__ == '__main__':
    main()
