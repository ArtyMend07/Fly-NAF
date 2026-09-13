import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import config
from neural.models import FlyBrainModel
from neural.data_loader import get_hash_tables, load_connectome_weights


def test_sensory_to_motor_pathway():
    device = 'cpu'
    flyid2i, i2flyid = get_hash_tables(config.COMPLETENESS_CSV)
    weights = load_connectome_weights(
        config.CONNECTIVITY_PARQUET, config.COMPLETENESS_CSV, config.DATA_DIR,
        csr=True, device=device,
    )
    num_neurons = weights.shape[0]
    weights = weights * config.SIMULATION_PARAMS.arousal_multiplier

    exc_indices = [flyid2i[n] for n in config.SENSORY_NEURONS.left_eye_cluster if n in flyid2i]
    motor_idx = flyid2i[config.MOTOR_NEURONS.dnp01_giant_fiber[0]]

    model = FlyBrainModel(num_neurons, weights, exc_indices=exc_indices, device=device)

    rates = torch.zeros(1, num_neurons, device=device)
    rates[:, exc_indices] = config.SIMULATION_PARAMS.base_sensory_rate_hz

    total_spikes_per_neuron = torch.zeros(num_neurons, device=device)
    for _ in range(5000):
        total_spikes_per_neuron += model.step(rates)[0]

    active_neurons = (total_spikes_per_neuron > 0).nonzero(as_tuple=True)[0]
    downstream_active = [idx.item() for idx in active_neurons if idx.item() not in exc_indices]

    assert len(downstream_active) > 0, 'no interneurons recruited from sensory input'
    assert total_spikes_per_neuron[motor_idx].item() > 0, (
        f'signal did not reach motor neuron {i2flyid[motor_idx]}'
    )


if __name__ == '__main__':
    test_sensory_to_motor_pathway()
    print('ok')