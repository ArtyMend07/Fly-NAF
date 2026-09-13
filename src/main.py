import asyncio
import logging
import math
import random
import time
from dataclasses import dataclass, field

import torch

import config
from brain_adapter import BrainAdapter
from env.vision import FNAFVision
from env.input_controller import FNAFController, start_worker

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

    def step(self, state: SensoryState, current_time: float) -> torch.Tensor:
        self._rates[:, self._l_sensory_idx] = self._base_rate * state.left_rate
        self._rates[:, self._r_sensory_idx] = self._base_rate * state.right_rate
        self._rates[:, self._l_inhib_idx] = state.cam_inhib
        self._rates[:, self._r_inhib_idx] = state.cam_inhib

        cpg = config.CPG_DYNAMICS
        cpg_wave = (math.sin(current_time * cpg.frequency_hz * 2 * math.pi) + 1) / 2
        cpg_current = cpg.peak_current if cpg_wave > cpg.spike_threshold else cpg.base_current
        self._rates[:, self._explore_idx] = cpg_current

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


async def _vision_task(vision: FNAFVision, state: SensoryState, shutdown: asyncio.Event):
    delay = config.VISION_DYNAMICS.capture_delay_sec
    while not shutdown.is_set():
        cam_up = vision.is_camera_up()
        state.camera_open = cam_up
        state.left_rate = vision.get_left_sensory_rate() if state.check_left else 0.0
        state.right_rate = vision.get_right_sensory_rate() if state.check_right else 0.0
        state.cam_inhib = config.SIMULATION_PARAMS.base_sensory_rate_hz if cam_up else 0.0
        await asyncio.sleep(delay)


async def _calibrate(vision: FNAFVision, controller: FNAFController):
    settle = config.FORAGING_PARAMS.light_activation_settle_sec

    _log.info('calibrating in %d seconds', _WARMUP_COUNTDOWN)
    for i in range(_WARMUP_COUNTDOWN, 0, -1):
        _log.info('T-%d', i)
        await asyncio.sleep(1.0)

    controller.set_left_light(True)
    await asyncio.sleep(settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_left_reference)
    _log.info('left reference captured')
    controller.set_left_light(False)
    await asyncio.sleep(settle + 0.1)

    controller.set_right_light(True)
    await asyncio.sleep(settle)
    await asyncio.get_event_loop().run_in_executor(None, vision.capture_right_reference)
    _log.info('right reference captured')
    controller.set_right_light(False)

    await asyncio.sleep(settle)
    vision.capture_camera_closed_reference()
    _log.info('camera-closed reference captured')


async def _foraging_task(
    vision: FNAFVision,
    controller: FNAFController,
    state: SensoryState,
    shutdown: asyncio.Event,
):
    await _calibrate(vision, controller)

    settle = config.FORAGING_PARAMS.light_activation_settle_sec
    sides = ['left', 'right']

    while not shutdown.is_set():
        interval = random.uniform(
            config.FORAGING_PARAMS.min_interval_sec,
            config.FORAGING_PARAMS.max_interval_sec,
        )
        await asyncio.sleep(interval)

        target = random.choice(sides)
        if state.camera_open:
            continue  # Impede a apropriação do mouse para acender luzes quando o player está nas câmeras

        if target == 'left':
            controller.set_left_light(True)
            await asyncio.sleep(settle)
            state.check_left = True
            await asyncio.sleep(config.FORAGING_PARAMS.light_inspection_time)
            state.check_left = False
            controller.set_left_light(False)
        else:
            controller.set_right_light(True)
            await asyncio.sleep(settle)
            state.check_right = True
            await asyncio.sleep(config.FORAGING_PARAMS.light_inspection_time)
            state.check_right = False
            controller.set_right_light(False)


async def _engine_task(
    engine: ConnectomeEngine,
    controller: FNAFController,
    state: SensoryState,
    shutdown: asyncio.Event,
):
    refrac = MotorRefrac()
    motor_dur = config.FORAGING_PARAMS.motor_refractory_sec
    cam_dur = config.FORAGING_PARAMS.camera_refractory_sec

    while not shutdown.is_set():
        t_start = time.perf_counter()
        now = time.time()

        loop = asyncio.get_event_loop()
        spikes = await loop.run_in_executor(None, engine.step, state, now)

        if spikes[0, engine.explore_idx].any() and now > refrac.camera:
            controller.toggle_camera()
            refrac.camera = now + cam_dur

        if spikes[0, engine.l_motor_idx].any() and now > refrac.left:
            if not state.camera_open:
                _log.warning('left giant fiber fired')
                controller.trigger_left_door()
                refrac.left = now + motor_dur
            state.left_rate = 0.0

        if spikes[0, engine.r_motor_idx].any() and now > refrac.right:
            if not state.camera_open:
                _log.warning('right giant fiber fired')
                controller.trigger_right_door()
                refrac.right = now + motor_dur
            state.right_rate = 0.0

        elapsed = time.perf_counter() - t_start
        remaining = engine.frame_dt - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        else:
            await asyncio.sleep(0)


async def _run():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    _log.info('brain core online, device=%s', device)

    start_worker()
    engine = ConnectomeEngine(device)
    vision = FNAFVision()
    controller = FNAFController()
    state = SensoryState()
    shutdown = asyncio.Event()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(_vision_task(vision, state, shutdown))
        tg.create_task(_foraging_task(vision, controller, state, shutdown))
        tg.create_task(_engine_task(engine, controller, state, shutdown))


def main():
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        _log.info('shutdown')


if __name__ == '__main__':
    main()