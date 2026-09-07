import torch
from typing import List, Tuple

from neural.models import FlyBrainModel
from neural.data_loader import get_hash_tables, load_connectome_weights

class BrainAdapter:
    def __init__(self, comp_path: str, conn_path: str, wt_dir: str, device: str = 'cpu'):
        self.device = device
        print("[SYSTEM] Loading anatomical indices...")
        self.flyid2i, self.i2flyid = get_hash_tables(comp_path)
        print("[SYSTEM] Loading sparse connectome weights...")
        self.weights = load_connectome_weights(
            conn_path, comp_path, wt_dir, csr=True, device=self.device
        )
        arousal_multiplier = 10.0
        self.weights = self.weights * arousal_multiplier
        self.num_neurons = self.weights.shape[0]
        print(f"[SYSTEM] Brain loaded. Total Neurons: {self.num_neurons}")
        self.model = None

    def map_neuron_ids_to_indices(self, root_ids: List[int]) -> List[int]:
        return [self.flyid2i[n] for n in root_ids if n in self.flyid2i]

    def initialize_model(self, exc_indices: List[int]):
        print("[SYSTEM] Instantiating neural engine...")
        self.model = FlyBrainModel(
            self.num_neurons, 
            self.weights, 
            exc_indices=exc_indices, 
            device=self.device
        )
    def step(self, rates: torch.Tensor, steps: int = 1) -> torch.Tensor:
        accumulated_spikes = torch.zeros_like(rates)
        for _ in range(steps):
            spikes = self.model.step(rates)
            if spikes is not None:
                accumulated_spikes += spikes
        return accumulated_spikes