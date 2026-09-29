import torch

import config
from brain_adapter import BrainAdapter
from night.state import SensoryState


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

        resolve = self._adapter.map_neuron_ids_to_indices
        self._l_sensory_idx = resolve(sensory.left_eye_cluster, 'left eye cluster')
        self._r_sensory_idx = resolve(sensory.right_eye_cluster, 'right eye cluster')
        all_sensory = self._l_sensory_idx + self._r_sensory_idx

        self._l_motor_idx = resolve([motor.dnp01_giant_fiber[0]], 'DNp01 left giant fiber')
        self._r_motor_idx = resolve([motor.dnp01_giant_fiber[1]], 'DNp01 right giant fiber')
        self._explore_idx = resolve(motor.dnp09_explore, 'DNp09 explore')
        self._l_inhib_idx = resolve(sensory.camera_inhibitor_left, 'left camera inhibitors')
        self._r_inhib_idx = resolve(sensory.camera_inhibitor_right, 'right camera inhibitors')

        self._adapter.initialize_model(exc_indices=all_sensory)

        self._rates = torch.zeros(1, self._adapter.num_neurons, device=device)
        self._base_rate = config.SIMULATION_PARAMS.base_sensory_rate_hz
        self._steps = config.SIMULATION_PARAMS.steps_per_frame
        self.frame_dt = 1.0 / config.SIMULATION_PARAMS.target_fps
        self.eye_membrane_diff = 0.0
        self.explore_membrane = 0.0
        self.frames = 0
        self.driven_frames = {'left': 0, 'right': 0}

    @property
    def sensory_span(self) -> int:
        return len(self._l_sensory_idx) * self._steps

    def step(self, state: SensoryState, current_time: float) -> torch.Tensor:
        self.frames += 1
        if state.left_rate > 0.0:
            self.driven_frames['left'] += 1
        if state.right_rate > 0.0:
            self.driven_frames['right'] += 1
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
    def num_neurons(self) -> int:
        return self._adapter.num_neurons

    @property
    def synapses(self):
        return self._adapter.weights

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
