
import pytest
import torch

from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState

pytestmark = pytest.mark.connectome

FRAMES = 2500


def test_sensory_to_motor_pathway():
    engine = ConnectomeEngine('cpu')
    state = SensoryState(left_rate=1.0)
    eye = set(engine.l_sensory_idx)

    total_spikes_per_neuron = torch.zeros(engine.num_neurons)
    for frame in range(FRAMES):
        total_spikes_per_neuron += engine.step(state, frame * engine.frame_dt)[0]

    active_neurons = (total_spikes_per_neuron > 0).nonzero(as_tuple=True)[0]
    downstream_active = [idx.item() for idx in active_neurons if idx.item() not in eye]

    assert len(downstream_active) > 0, 'no interneurons recruited from sensory input'
    assert total_spikes_per_neuron[engine.l_motor_idx].sum().item() > 0, (
        'signal did not reach the left giant fiber'
    )


if __name__ == '__main__':
    test_sensory_to_motor_pathway()
    print('ok')
