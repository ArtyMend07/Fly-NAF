import torch

from flynaf import config
from flynaf.brain_adapter import BrainAdapter
from flynaf.neural.cell_types import CellTypeIndex
from flynaf.night.neurons import build_neuron_map, stimulus_rates
from flynaf.night.state import SensoryState


class ConnectomeEngine:
    def __init__(self, device: str, cell_index: CellTypeIndex | None = None):
        self._device = device
        self._adapter = BrainAdapter(
            config.COMPLETENESS_CSV,
            config.CONNECTIVITY_PARQUET,
            config.DATA_DIR,
            device,
        )
        self.neurons = build_neuron_map(
            cell_index or CellTypeIndex.load(), self._adapter.map_neuron_ids_to_indices,
        )
        self._adapter.initialize_model(exc_indices=self.neurons.stimulus_indices())

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
        return max(len(self.l_sensory_idx), len(self.r_sensory_idx)) * self._steps

    def step(self, state: SensoryState, current_time: float) -> torch.Tensor:
        self.frames += 1
        if state.left_rate > 0.0:
            self.driven_frames['left'] += 1
        if state.right_rate > 0.0:
            self.driven_frames['right'] += 1

        self._load_rates(state)
        spikes = self._adapter.step(self._rates, steps=self._steps)

        v = self._adapter.membrane_potential()
        self.eye_membrane_diff = float(
            v[0, self.l_sensory_idx].mean() - v[0, self.r_sensory_idx].mean()
        )
        self.explore_membrane = float(v[0, self.explore_idx].mean())
        return spikes

    def reset(self):
        self._adapter.model.reset_state()

    def _load_rates(self, state: SensoryState):
        self._rates.zero_()
        for indices, rate_hz in stimulus_rates(self.neurons, state, self._base_rate):
            if rate_hz > 0.0:
                self._rates[:, indices] = torch.clamp(self._rates[:, indices], min=rate_hz)
        noise_hz = config.FORAGING_PARAMS.subliminal_noise_hz
        self._rates += torch.rand_like(self._rates) * noise_hz

    @property
    def num_neurons(self) -> int:
        return self._adapter.num_neurons

    @property
    def synapses(self):
        return self._adapter.weights

    @property
    def l_motor_idx(self):
        return self.neurons.outputs['giant_fiber_left']

    @property
    def r_motor_idx(self):
        return self.neurons.outputs['giant_fiber_right']

    @property
    def l_escape_idx(self):
        return self.neurons.outputs['looming_escape_left']

    @property
    def r_escape_idx(self):
        return self.neurons.outputs['looming_escape_right']

    @property
    def explore_idx(self):
        return self.neurons.outputs['explore']

    @property
    def l_sensory_idx(self):
        return self.neurons.inputs['eye_left']

    @property
    def r_sensory_idx(self):
        return self.neurons.inputs['eye_right']

