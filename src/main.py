import asyncio
import logging
import math
import time
from dataclasses import dataclass, field

import torch

import config
from brain_adapter import BrainAdapter
from env.vision import FNAFVision
from env.input_controller import FNAFController, start_worker
from telemetry import ConnectomeTelemetry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
_log = logging.getLogger(__name__)

_WARMUP_COUNTDOWN = 10


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


@dataclass
class MotorRefrac:
    left: float = 0.0
    right: float = 0.0
    camera: float = 0.0


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
        self.explore_drive = 0.0

    def step(self, state: SensoryState, current_time: float) -> torch.Tensor:
        self._rates[:, self._l_sensory_idx] = self._base_rate * state.left_rate
        self._rates[:, self._r_sensory_idx] = self._base_rate * state.right_rate
        self._rates[:, self._l_inhib_idx] = state.cam_inhib
        self._rates[:, self._r_inhib_idx] = state.cam_inhib

        noise_hz = config.FORAGING_PARAMS.subliminal_noise_hz
        self._rates += torch.rand_like(self._rates) * noise_hz

        cpg = config.CPG_DYNAMICS
        cpg_wave = (math.sin(current_time * cpg.frequency_hz * 2 * math.pi) + 1) / 2
        cpg_current = cpg.peak_current if cpg_wave > cpg.spike_threshold else cpg.base_current
        self._rates[:, self._explore_idx] = cpg_current
        self.explore_drive = cpg_wave

        return self._adapter.step(self._rates, steps=self._steps)

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

    def membrane_bias(self, indices: list) -> float:
        v = self._adapter.membrane_potential()
        return float(v[0, indices].mean().item())


async def _vision_task(vision: FNAFVision, state: SensoryState, shutdown: asyncio.Event):
    delay = config.VISION_DYNAMICS.capture_delay_sec
    while not shutdown.is_set():
        cam_up = vision.is_camera_up()
        state.left_rate = vision.get_left_sensory_rate() if state.check_left else 0.0
        state.right_rate = vision.get_right_sensory_rate() if state.check_right else 0.0
        state.cam_inhib = config.SIMULATION_PARAMS.base_sensory_rate_hz if cam_up else 0.0
        await asyncio.sleep(delay)


async def _calibrate(vision: FNAFVision, controller: FNAFController):
    settle = config.FORAGING_PARAMS.light_activation_settle_sec
    full_settle = config.MOTOR_CALIBRATION.pan_delay_sec + config.MOTOR_CALIBRATION.click_delay_sec + settle

    _log.info('calibrating in %d seconds', _WARMUP_COUNTDOWN)
    for i in range(_WARMUP_COUNTDOWN, 0, -1):
        _log.info('T-%d', i)
        await asyncio.sleep(1.0)

    controller.set_left_light(True)
    await asyncio.sleep(full_settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_left_reference)
    _log.info('left reference captured')
    controller.set_left_light(False)
    await asyncio.sleep(full_settle + 0.1)

    controller.set_right_light(True)
    await asyncio.sleep(full_settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_right_reference)
    _log.info('right reference captured')
    controller.set_right_light(False)

    await asyncio.sleep(full_settle)
    vision.capture_camera_closed_reference()
    _log.info('camera-closed reference captured')


async def _saccade_task(
    engine: ConnectomeEngine,
    vision: FNAFVision,
    controller: FNAFController,
    state: SensoryState,
    shutdown: asyncio.Event,
    telemetry: ConnectomeTelemetry,
    calibration_done: asyncio.Event
):
    await _calibrate(vision, controller)
    calibration_done.set()

    full_settle = (
        config.MOTOR_CALIBRATION.pan_delay_sec
        + config.MOTOR_CALIBRATION.click_delay_sec
        + config.FORAGING_PARAMS.light_activation_settle_sec
    )
    saccade_refrac = 0.0
    leak = config.FORAGING_PARAMS.saccade_leak_per_frame
    trigger = config.FORAGING_PARAMS.subliminal_bias_threshold
    integral_l = 0.0
    integral_r = 0.0

    while not shutdown.is_set():
        await asyncio.sleep(engine.frame_dt)

        now = time.time()

        e_left = float(state.l_sensory_count)
        e_right = float(state.r_sensory_count)

        integral_l += e_left
        integral_r += e_right
        integral_l *= leak
        integral_r *= leak

        bias = (integral_l - integral_r) / (integral_l + integral_r + 1e-5)
        state.forage_bias = abs(bias)

        if state.camera_open or now < saccade_refrac or abs(bias) < trigger:
            continue

        saccade_refrac = now + config.FORAGING_PARAMS.saccade_refractory_sec
        integral_l = 0.0
        integral_r = 0.0

        if bias > 0:
            telemetry.record_light_saccade('left', bias)
            controller.set_left_light(True)
            await asyncio.sleep(full_settle)
            state.check_left = True
            await asyncio.sleep(config.FORAGING_PARAMS.light_inspection_time)
            state.check_left = False
            controller.set_left_light(False)
        else:
            telemetry.record_light_saccade('right', bias)
            controller.set_right_light(True)
            await asyncio.sleep(full_settle)
            state.check_right = True
            await asyncio.sleep(config.FORAGING_PARAMS.light_inspection_time)
            state.check_right = False
            controller.set_right_light(False)


async def _engine_task(
    engine: ConnectomeEngine,
    controller: FNAFController,
    state: SensoryState,
    shutdown: asyncio.Event,
    telemetry: ConnectomeTelemetry,
    calibration_done: asyncio.Event
):
    await calibration_done.wait()

    refrac = MotorRefrac()
    motor_dur = config.FORAGING_PARAMS.motor_refractory_sec
    cam_dur = config.FORAGING_PARAMS.camera_refractory_sec
    cam_watch_max_sec = config.FORAGING_PARAMS.camera_watch_max_sec
    cam_watch_min_sec = config.FORAGING_PARAMS.camera_watch_min_sec
    cam_release_bias = config.FORAGING_PARAMS.camera_release_forage_bias
    cam_release_drive = config.CPG_DYNAMICS.release_drive_threshold
    cam_opened_at = 0.0
    cam_close_after = 0.0
    cam_is_open = False

    explore_integral = 0.0
    leak = config.CPG_DYNAMICS.leak_per_frame
    trigger = config.CPG_DYNAMICS.integral_trigger

    while not shutdown.is_set():
        t_start = time.perf_counter()
        now = time.time()

        loop = asyncio.get_event_loop()
        spikes = await loop.run_in_executor(None, engine.step, state, now)

        state.l_spike = bool(spikes[0, engine.l_motor_idx].any())
        state.r_spike = bool(spikes[0, engine.r_motor_idx].any())
        state.l_sensory_count = int(spikes[0, engine.l_sensory_idx].sum().item())
        state.r_sensory_count = int(spikes[0, engine.r_sensory_idx].sum().item())

        if cam_is_open:
            watched_for = now - cam_opened_at
            lost_interest = watched_for >= cam_watch_min_sec and (
                engine.explore_drive < cam_release_drive
                or state.forage_bias >= cam_release_bias
            )
            if now >= cam_close_after or lost_interest:
                controller.close_camera()
                cam_is_open = False
                state.camera_open = False
                refrac.camera = now + cam_dur
                explore_integral = 0.0

        if spikes[0, engine.explore_idx].any():
            explore_integral += 1.0
        explore_integral *= leak

        if not cam_is_open and explore_integral >= trigger and now > refrac.camera:
            telemetry.record_camera_pull()
            controller.open_camera()
            cam_is_open = True
            state.camera_open = True
            cam_opened_at = now
            cam_close_after = now + cam_watch_max_sec
            explore_integral = 0.0

        if spikes[0, engine.l_motor_idx].any() and now > refrac.left:
            if not state.camera_open:
                _log.warning('left giant fiber fired')
                telemetry.record_door_panic('left')
                controller.trigger_left_door()
                refrac.left = now + motor_dur
            state.left_rate = 0.0

        if spikes[0, engine.r_motor_idx].any() and now > refrac.right:
            if not state.camera_open:
                _log.warning('right giant fiber fired')
                telemetry.record_door_panic('right')
                controller.trigger_right_door()
                refrac.right = now + motor_dur
            state.right_rate = 0.0

        elapsed = time.perf_counter() - t_start
        remaining = engine.frame_dt - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        else:
            await asyncio.sleep(0)


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

    async with asyncio.TaskGroup() as tg:
        tg.create_task(_vision_task(vision, state, shutdown))
        tg.create_task(_saccade_task(engine, vision, controller, state, shutdown, telemetry, calibration_done))
        tg.create_task(_engine_task(engine, controller, state, shutdown, telemetry, calibration_done))


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
