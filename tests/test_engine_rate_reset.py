from unittest.mock import MagicMock

import torch

from flynaf import config
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.neurons import NeuronMap
from flynaf.night.state import SensoryState

NEURONS = 12
TOUCHED = set(range(8))


def _neuron_map() -> NeuronMap:
    return NeuronMap(
        inputs={
            'eye_left': [0, 5], 'eye_right': [1],
            'inhibitors_left': [2], 'inhibitors_right': [3],
            'figure_left': [6], 'figure_right': [],
            'loom_size_left': [0], 'loom_size_right': [],
            'loom_speed_left': [5], 'loom_speed_right': [],
        },
        outputs={
            'giant_fiber_left': [7], 'giant_fiber_right': [8],
            'looming_escape_left': [9], 'looming_escape_right': [10],
            'explore': [4],
        },
    )


def _make_bare_engine() -> ConnectomeEngine:
    engine = ConnectomeEngine.__new__(ConnectomeEngine)
    engine.neurons = _neuron_map()
    engine._rates = torch.zeros(1, NEURONS)
    engine._base_rate = 1000.0
    engine._steps = 2
    engine.frames = 0
    engine.driven_frames = {'left': 0, 'right': 0}
    engine._adapter = MagicMock()
    engine._adapter.step.side_effect = lambda rates, steps: rates.clone()
    engine._adapter.membrane_potential.return_value = torch.zeros(1, NEURONS)
    return engine


def test_untouched_neurons_do_not_accumulate_noise_across_frames():
    engine = _make_bare_engine()
    state = SensoryState()

    for frame in range(500):
        engine.step(state, current_time=frame * 0.1)

    untouched = [i for i in range(NEURONS) if i not in TOUCHED]
    max_untouched_rate = engine._rates[:, untouched].max().item()

    subliminal_noise_hz = config.FORAGING_PARAMS.subliminal_noise_hz
    assert max_untouched_rate < subliminal_noise_hz, (
        f'background noise leaked across frames instead of resetting each '
        f'step: rate reached {max_untouched_rate}'
    )


def test_assigned_clusters_reflect_only_the_current_frame_state():
    engine = _make_bare_engine()

    engine.step(SensoryState(left_rate=1.0, right_rate=0.0), current_time=0.0)
    high_left = engine._rates[0, 0].item()

    engine.step(SensoryState(left_rate=0.0, right_rate=0.0), current_time=0.1)
    low_left = engine._rates[0, 0].item()

    assert high_left >= engine._base_rate
    assert low_left < engine._base_rate


TABLET_CASES = (
    ('figure_left', 6, 0.25),
    ('loom_size_left', 0, 0.5),
    ('loom_speed_left', 5, 1.0),
)


def test_tablet_drive_reaches_only_its_population_for_one_frame():
    for population, index, level in TABLET_CASES:
        engine = _make_bare_engine()

        engine.step(SensoryState(tablet_drive={population: level}), current_time=0.0)
        driven = engine._rates[0, index].item()
        engine.step(SensoryState(), current_time=0.1)

        assert driven >= engine._base_rate * level, population
        assert engine._rates[0, index].item() < config.FORAGING_PARAMS.subliminal_noise_hz, population


def test_overlapping_populations_keep_the_stronger_drive():
    engine = _make_bare_engine()

    state = SensoryState(left_rate=1.0, tablet_drive={'loom_size_left': 0.2})
    engine.step(state, current_time=0.0)

    assert engine._rates[0, 0].item() >= engine._base_rate


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
