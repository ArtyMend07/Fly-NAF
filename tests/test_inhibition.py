import sys
import os
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import config
from neural.models import FlyBrainModel
from neural.data_loader import get_hash_tables, load_connectome_weights


def test_biological_inhibition():
    device = 'cpu'
    flyid2i, _ = get_hash_tables(config.COMPLETENESS_CSV)
    weights = load_connectome_weights(
        config.CONNECTIVITY_PARQUET, config.COMPLETENESS_CSV, config.DATA_DIR,
        csr=True, device=device,
    )
    num_neurons = weights.shape[0]
    weights = weights * config.SIMULATION_PARAMS.arousal_multiplier

    exc_indices = [flyid2i[n] for n in config.SENSORY_NEURONS.left_eye_cluster if n in flyid2i]
    inhib_indices = [flyid2i[n] for n in config.SENSORY_NEURONS.camera_inhibitor_left if n in flyid2i]
    motor_idx = flyid2i[config.MOTOR_NEURONS.dnp01_giant_fiber[0]]

    model = FlyBrainModel(num_neurons, weights, exc_indices=exc_indices + inhib_indices, device=device)

    rates = torch.zeros(1, num_neurons, device=device)
    rates[:, exc_indices] = config.SIMULATION_PARAMS.base_sensory_rate_hz
    total_spikes = sum(
        model.step(rates)[0, motor_idx].item()
        for _ in range(5000)
    )
    assert total_spikes > 0, f'expected startle reflex, got {total_spikes} spikes'

    model.reset_state()

    rates[:, inhib_indices] = config.SIMULATION_PARAMS.base_sensory_rate_hz
    total_inhibited = sum(
        model.step(rates)[0, motor_idx].item()
        for _ in range(5000)
    )
    assert total_inhibited == 0, (
        f'inhibition failed, giant fiber spiked {total_inhibited} times with camera open'
    )


if __name__ == '__main__':
    test_biological_inhibition()
    print('ok')