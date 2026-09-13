import logging
import torch
from typing import List

import config
from neural.models import FlyBrainModel
from neural.data_loader import get_hash_tables, load_connectome_weights

_log = logging.getLogger(__name__)


class BrainAdapter:
    def __init__(self, comp_path: str, conn_path: str, wt_dir: str, device: str = 'cpu'):
        self.device = device
        _log.info('loading anatomical indices')
        self.flyid2i, self.i2flyid = get_hash_tables(comp_path)
        _log.info('loading sparse connectome weights')
        self.weights = load_connectome_weights(
            conn_path, comp_path, wt_dir, csr=True, device=self.device
        )
        self.weights = self.weights * config.SIMULATION_PARAMS.arousal_multiplier
        self.num_neurons = self.weights.shape[0]
        _log.info('brain loaded, neurons=%d', self.num_neurons)
        self.model = None

    def map_neuron_ids_to_indices(self, root_ids: List[int]) -> List[int]:
        return [self.flyid2i[n] for n in root_ids if n in self.flyid2i]

    def initialize_model(self, exc_indices: List[int]):
        _log.info('instantiating neural engine')
        self.model = FlyBrainModel(
            self.num_neurons,
            self.weights,
            exc_indices=exc_indices,
            device=self.device,
        )

    def step(self, rates: torch.Tensor, steps: int = 1) -> torch.Tensor:
        accumulated_spikes = torch.zeros_like(rates)
        for _ in range(steps):
            accumulated_spikes += self.model.step(rates)
        return accumulated_spikes