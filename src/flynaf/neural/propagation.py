import numpy as np
import torch


class OutgoingSynapses:
    def __init__(self, weights: torch.Tensor):
        by_source = weights.to('cpu').to_sparse_csc()
        self._first = by_source.ccol_indices().numpy().astype(np.int64)
        self._target = by_source.row_indices().numpy().astype(np.int32)
        self._weight = by_source.values().numpy().copy()
        self._size = weights.shape[0]

    def reached_by(self, spikes: torch.Tensor) -> torch.Tensor:
        rows = [self._reached_by_row(row) for row in spikes.numpy()]
        return torch.from_numpy(np.stack(rows))

    def _reached_by_row(self, spikes: np.ndarray) -> np.ndarray:
        fired = np.flatnonzero(spikes)
        starts = self._first[fired]
        lengths = self._first[fired + 1] - starts
        ends = np.cumsum(lengths)
        total = int(ends[-1]) if fired.size else 0
        synapses = np.repeat(starts - ends + lengths, lengths) + np.arange(total)
        reached = np.bincount(
            self._target[synapses], weights=self._weight[synapses], minlength=self._size,
        )
        return reached.astype(np.float32)


def runs_on_cpu(device: str) -> bool:
    return torch.device(device).type == 'cpu'


def propagation_for(weights: torch.Tensor, device: str):
    if runs_on_cpu(device):
        return OutgoingSynapses(weights).reached_by
    incoming = weights.transpose(0, 1)
    return lambda spikes: torch.matmul(spikes, incoming)


def leave_idle_cores_to_the_game(device: str):
    if runs_on_cpu(device):
        torch.set_num_threads(1)
