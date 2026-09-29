import asyncio
import logging
import time

import config
from env.brain_view import SpikeFeed
from env.input_controller import FNAFController
from env.vision import FNAFVision
from night.calibration import calibrate
from night.engine import ConnectomeEngine
from night.monitor import MonitorControl
from night.motor import await_motor
from night.state import MotorRefrac, SaccadeRequest, SensoryState
from recorder import SessionRecorder
from search_drive import ExploreDrive, SearchDrive
from telemetry import ConnectomeTelemetry

_log = logging.getLogger(__name__)


async def vision_task(
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


async def observe_hallway(
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

        contrast, frames, driven, fired = await observe_hallway(engine, vision, state, side)
        switch(False)

        threshold = config.FORAGING_PARAMS.mse_threshold
        _log.info('%s hallway read %.0f against a %.0f threshold, eye driven %d of %d frames%s',
                  side, contrast, threshold, driven, frames,
                  ', giant fiber answered' if fired else '')
        telemetry.record_look_contrast(side, contrast, frames, driven)

        saccade.ready_at = time.time() + config.FORAGING_PARAMS.saccade_refractory_sec
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
    highlights: dict,
    saccade: SaccadeRequest,
    trace: SessionRecorder | None = None,
):
    await calibration_done.wait()
    trace = trace or SessionRecorder(enabled=False)

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

        trace.frame(
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
