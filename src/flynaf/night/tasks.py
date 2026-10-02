import asyncio
import logging

from flynaf import clock, config
from flynaf.env.brain_view import PanelFrame, SpikeFeed
from flynaf.env.input_controller import FNAFController
from flynaf.env.vision import FNAFVision
from flynaf.night.calibration import calibrate
from flynaf.night.doors import DoorControl
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.lights import set_light
from flynaf.night.monitor import MonitorControl
from flynaf.night.motor import await_motor
from flynaf.night.state import SaccadeRequest, SensoryState
from flynaf.night.tablet.senses import BlindSenses
from flynaf.night.tablet.watch import IdleTablet
from flynaf.recorder import SessionRecorder
from flynaf.search_drive import ExploreDrive, SearchDrive
from flynaf.telemetry import ConnectomeTelemetry

_log = logging.getLogger(__name__)


async def vision_task(
    vision: FNAFVision, controller: FNAFController, state: SensoryState, shutdown: asyncio.Event,
    senses=None,
):
    delay = config.VISION_DYNAMICS.capture_delay_sec
    senses = senses or BlindSenses()
    while not shutdown.is_set():
        state.tablet_seen = vision.is_camera_up()
        now = clock.now()
        looking_left = state.check_left and now >= state.blind_until['left']
        looking_right = state.check_right and now >= state.blind_until['right']
        closed = state.door_closed
        state.left_rate = vision.get_left_sensory_rate(closed['left']) if looking_left else 0.0
        state.right_rate = vision.get_right_sensory_rate(closed['right']) if looking_right else 0.0
        state.cam_inhib = config.SIMULATION_PARAMS.base_sensory_rate_hz if state.tablet_seen else 0.0
        state.tablet_drive = senses.read(state, now)
        await asyncio.sleep(delay)


async def observe_hallway(
    engine: ConnectomeEngine, vision: FNAFVision, state: SensoryState, side: str
) -> tuple:
    foraging = config.FORAGING_PARAMS
    vision.reset_peak_mse(side)
    state.look_started[side] = clock.now()
    opened_at_frame = engine.frames
    opened_at_driven = engine.driven_frames[side]
    deadline = clock.now() + foraging.light_inspection_max_sec

    if side == 'left':
        state.check_left = True
    else:
        state.check_right = True

    fired = False
    while engine.frames - opened_at_frame < foraging.light_inspection_frames:
        if state.l_spike if side == 'left' else state.r_spike:
            fired = True
            break
        if clock.now() >= deadline:
            break
        await asyncio.sleep(engine.frame_dt / 2)

    state.check_left = False
    state.check_right = False
    return (vision.peak_mse(side), engine.frames - opened_at_frame,
            engine.driven_frames[side] - opened_at_driven, fired)


async def saccade_task(
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
    tablet_feed=None,
):
    await view_ready.wait()
    await calibrate(vision, controller, begin_night, tablet_feed)
    calibration_done.set()

    while not shutdown.is_set():
        if saccade.side is None:
            await asyncio.sleep(engine.frame_dt)
            continue

        side = saccade.side
        saccade.busy = True

        while (state.camera_open or state.tablet_seen) and not shutdown.is_set():
            await asyncio.sleep(engine.frame_dt)
        if shutdown.is_set():
            break

        _log.info('%s light check, %s (search drive %+.2f)',
                  side, saccade.reason, saccade.drive)
        telemetry.record_light_saccade(side, saccade.drive, saccade.reason)
        lit = await set_light(vision, controller, side, True)
        if not lit:
            _log.warning('the %s light would not come on, the hallway is read in the dark', side)
        await asyncio.sleep(config.FORAGING_PARAMS.light_activation_settle_sec)

        contrast, frames, driven, fired = await observe_hallway(engine, vision, state, side)
        await set_light(vision, controller, side, False)

        threshold = config.FORAGING_PARAMS.mse_threshold
        _log.info('%s hallway read %.0f against a %.0f threshold, eye driven %d of %d frames%s',
                  side, contrast, threshold, driven, frames,
                  ', giant fiber answered' if fired else '')
        telemetry.record_look_contrast(side, contrast, frames, driven)
        remember_a_clear_look(state, side, fired, driven, lit)

        saccade.ready_at = clock.now() + config.FORAGING_PARAMS.saccade_refractory_sec
        saccade.side = None
        saccade.busy = False


async def engine_task(
    engine: ConnectomeEngine,
    vision: FNAFVision,
    controller: FNAFController,
    state: SensoryState,
    shutdown: asyncio.Event,
    telemetry: ConnectomeTelemetry,
    calibration_done: asyncio.Event,
    feed: SpikeFeed,
    saccade: SaccadeRequest,
    trace: SessionRecorder | None = None,
    tablet=None,
):
    await warm_up(engine, telemetry)
    await calibration_done.wait()
    trace = trace or SessionRecorder(enabled=False)
    tablet = tablet or IdleTablet()

    search = SearchDrive(engine.sensory_span)
    explore = ExploreDrive()
    monitor = MonitorControl(vision, controller, telemetry, state, tablet)
    doors = DoorControl(controller, telemetry, state)
    last_frame_at = clock.now()

    while not shutdown.is_set():
        now = clock.now()
        frame_elapsed = now - last_frame_at
        last_frame_at = now

        inputs = (state.left_rate > 0.0, state.right_rate > 0.0)
        spikes = await asyncio.to_thread(engine.step, state, now)
        read_spikes(engine, spikes, state)

        explore.update(engine.explore_membrane, state.explore_spike, frame_elapsed)
        look_pending = saccade.side is not None or saccade.busy
        telemetry.record_frame(state.cam_inhib > 0, look_pending)
        monitor.update(now, explore, state.forage_bias, look_pending)
        watch_the_tablet(tablet, monitor, doors, telemetry, state, now)
        request_saccade(search, saccade, monitor, engine, state, frame_elapsed, now, look_pending)

        feed.publish(
            spikes[0].nonzero().flatten().cpu().numpy(),
            panel_frame(state, vision, doors, monitor, inputs),
        )
        trace.frame(
            now - telemetry.start_time, state, engine,
            state.l_spike, state.r_spike,
            vision.peak_mse('left'), vision.peak_mse('right'), monitor.is_open,
        )
        doors.update(now, frame_elapsed)
        answer_giant_fibers(engine, doors, feed, state, now)

        remaining = engine.frame_dt - (clock.now() - now)
        await asyncio.sleep(max(remaining, 0.0))


async def warm_up(engine: ConnectomeEngine, telemetry: ConnectomeTelemetry):
    settled = await asyncio.to_thread(engine.settle)
    frames = len(engine.warmup_activity)
    if settled:
        _log.info('the network settled after %d warm-up frames, %d neurons active per frame',
                  frames, engine.warmup_activity[-1])
    else:
        _log.warning('the network was still growing after %d warm-up frames, starting anyway', frames)
    telemetry.record_warmup(frames, settled, engine.warmup_activity)


def remember_a_clear_look(state: SensoryState, side: str, fired: bool, driven: int, lit: bool = True):
    if fired or driven > 0 or not lit:
        return
    if state.blind_until[side] > state.look_started[side]:
        return
    state.cleared_at[side] = clock.now()


def read_spikes(engine, spikes, state: SensoryState):
    frame = spikes[0]
    state.l_spike = bool(frame[engine.l_motor_idx].any())
    state.r_spike = bool(frame[engine.r_motor_idx].any())
    state.l_escape = bool(frame[engine.l_escape_idx].any())
    state.r_escape = bool(frame[engine.r_escape_idx].any())
    state.explore_spike = bool(frame[engine.explore_idx].any())
    state.l_sensory_count = int(frame[engine.l_sensory_idx].sum().item())
    state.r_sensory_count = int(frame[engine.r_sensory_idx].sum().item())


def watch_the_tablet(tablet, monitor: MonitorControl, doors: DoorControl, telemetry,
                     state: SensoryState, now: float):
    if not monitor.is_open:
        return
    camera = tablet.camera
    side = tablet.update(now, state.explore_spike, {'left': state.l_escape, 'right': state.r_escape})
    if side is None:
        return

    async def close_the_door():
        pressed = doors.slam(side, now, 'DNp04 looming escape')
        if pressed is not None:
            await await_motor(pressed)

    if monitor.escape(now, close_the_door):
        _log.warning('%s DNp04 fired while watching camera %s, dropping the tablet for the door',
                     side, camera)
        telemetry.record_tablet_escape(side, camera)


def request_saccade(search: SearchDrive, saccade: SaccadeRequest, monitor: MonitorControl,
                    engine, state: SensoryState, frame_elapsed: float, now: float,
                    look_pending: bool):
    can_look = (not look_pending and not monitor.engaged and not state.tablet_seen
                and now >= saccade.ready_at)
    wants = search.update(
        engine.eye_membrane_diff, state.l_sensory_count, state.r_sensory_count,
        frame_elapsed, now, can_look,
    )
    state.forage_bias = search.tension
    if wants is None:
        return
    saccade.reason = search.reason
    saccade.drive = search.last_drive
    saccade.side = wants


def answer_giant_fibers(engine, doors: DoorControl, feed: SpikeFeed, state: SensoryState, now: float):
    for side, fired, motor_idx, sensory_idx in (
        ('left', state.l_spike, engine.l_motor_idx, engine.l_sensory_idx),
        ('right', state.r_spike, engine.r_motor_idx, engine.r_sensory_idx),
    ):
        if not fired or doors.refractory(side, now):
            continue
        moved = doors.on_giant_fiber(side, now)
        feed.trace_escape(side, motor_idx[0], sensory_idx, moved)
        setattr(state, f'{side}_rate', 0.0)


def _strongest(drive: dict, prefix: str) -> float:
    return max((level for name, level in drive.items() if name.startswith(prefix)), default=0.0)


def panel_frame(state: SensoryState, vision: FNAFVision, doors: DoorControl,
                monitor: MonitorControl, inputs: tuple) -> PanelFrame:
    return PanelFrame(
        gaze='LEFT' if state.check_left else 'RIGHT' if state.check_right else '--',
        camera=monitor.is_open,
        cam=state.tablet_camera,
        gf_l=state.l_spike,
        gf_r=state.r_spike,
        in_l=inputs[0],
        in_r=inputs[1],
        look_l=state.check_left,
        look_r=state.check_right,
        mse_l=vision.last_mse('left') if state.check_left else None,
        mse_r=vision.last_mse('right') if state.check_right else None,
        mse_th=vision.mse_threshold,
        eye_l=state.l_sensory_count,
        eye_r=state.r_sensory_count,
        door_l=doors.closed['left'],
        door_r=doors.closed['right'],
        figure=_strongest(state.tablet_drive, 'figure'),
        loom=_strongest(state.tablet_drive, 'loom'),
        dnp09=state.explore_spike,
        dnp04_l=state.l_escape,
        dnp04_r=state.r_escape,
    )

