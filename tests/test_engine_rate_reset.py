import os
import sys
from unittest.mock import MagicMock

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
from main import ConnectomeEngine, SensoryState


def _make_bare_engine(num_neurons: int = 10) -> ConnectomeEngine:
    engine = ConnectomeEngine.__new__(ConnectomeEngine)
    engine._l_sensory_idx = [0]
    engine._r_sensory_idx = [1]
    engine._l_inhib_idx = [2]
    engine._r_inhib_idx = [3]
    engine._explore_idx = [4]
    engine._rates = torch.zeros(1, num_neurons)
    engine._base_rate = 1000.0
    engine._steps = 2
    engine.frames = 0
    engine.driven_frames = {'left': 0, 'right': 0}
    engine._adapter = MagicMock()
    engine._adapter.step.side_effect = lambda rates, steps: rates.clone()
    return engine


def test_untouched_neurons_do_not_accumulate_noise_across_frames():
    engine = _make_bare_engine()
    state = SensoryState()

    for frame in range(500):
        engine.step(state, current_time=frame * 0.1)

    untouched = [i for i in range(10) if i not in (0, 1, 2, 3, 4)]
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


if __name__ == '__main__':
    test_untouched_neurons_do_not_accumulate_noise_across_frames()
    test_assigned_clusters_reflect_only_the_current_frame_state()
    print('ok')
