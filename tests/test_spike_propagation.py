import pytest
import torch

from flynaf.neural.propagation import (
    OutgoingSynapses,
    leave_idle_cores_to_the_game,
    propagation_for,
)


def _connectome(neurons: int, synapses: int, seed: int) -> torch.Tensor:
    generator = torch.Generator().manual_seed(seed)
    post = torch.randint(0, neurons, (synapses,), generator=generator)
    pre = torch.randint(0, neurons, (synapses,), generator=generator)
    counts = torch.randint(-40, 41, (synapses,), generator=generator).float() * 3.0
    return torch.sparse_coo_tensor(
        torch.stack([post, pre]), counts, (neurons, neurons),
    ).coalesce().to_sparse_csr()


def _spikes(neurons: int, firing: float, seed: int, batch: int = 1) -> torch.Tensor:
    generator = torch.Generator().manual_seed(seed)
    return (torch.rand(batch, neurons, generator=generator) < firing).float()


def _every_synapse(weights: torch.Tensor, spikes: torch.Tensor) -> torch.Tensor:
    return torch.matmul(spikes, weights.transpose(0, 1))


@pytest.mark.parametrize('neurons, synapses, firing', [
    (60, 400, 0.05),
    (60, 400, 0.5),
    (500, 9000, 0.01),
    (500, 9000, 1.0),
    (500, 40, 0.3),
])
def test_summing_the_synapses_of_the_neurons_that_fired_equals_the_full_product(neurons, synapses, firing):
    weights = _connectome(neurons, synapses, seed=neurons + synapses)
    spikes = _spikes(neurons, firing, seed=7)
    reached = OutgoingSynapses(weights).reached_by(spikes)
    assert reached.dtype == torch.float32
    assert torch.equal(reached, _every_synapse(weights, spikes))


def test_a_silent_network_reaches_nobody():
    weights = _connectome(80, 600, seed=3)
    reached = OutgoingSynapses(weights).reached_by(torch.zeros(1, 80))
    assert reached.shape == (1, 80)
    assert not reached.any()


def test_a_neuron_with_no_outgoing_synapse_adds_nothing():
    weights = torch.sparse_coo_tensor(
        torch.tensor([[1, 2], [0, 0]]), torch.tensor([6.0, -9.0]), (4, 4),
    ).to_sparse_csr()
    spikes = torch.tensor([[1.0, 1.0, 0.0, 1.0]])
    assert OutgoingSynapses(weights).reached_by(spikes).tolist() == [[0.0, 6.0, -9.0, 0.0]]


def test_each_row_of_a_batch_is_propagated_on_its_own():
    weights = _connectome(120, 1500, seed=11)
    spikes = _spikes(120, 0.2, seed=5, batch=3)
    assert torch.equal(OutgoingSynapses(weights).reached_by(spikes), _every_synapse(weights, spikes))


@pytest.mark.parametrize('device', ['cpu', 'cuda', 'cuda:0'])
def test_every_device_gets_a_propagation_that_matches_the_full_product(device):
    weights = _connectome(90, 1200, seed=2)
    spikes = _spikes(90, 0.1, seed=9)
    assert torch.equal(propagation_for(weights, device)(spikes), _every_synapse(weights, spikes))


@pytest.mark.parametrize('device, threads_after', [('cuda', 3), ('cpu', 1)])
def test_only_a_brain_on_the_cpu_gives_up_its_spare_threads(device, threads_after):
    before = torch.get_num_threads()
    torch.set_num_threads(3)
    try:
        leave_idle_cores_to_the_game(device)
        assert torch.get_num_threads() == threads_after
    finally:
        torch.set_num_threads(before)


@pytest.mark.connectome
def test_the_connectome_propagates_the_same_spikes_either_way():
    from flynaf.night.engine import ConnectomeEngine
    from flynaf.night.state import SensoryState

    engine = ConnectomeEngine('cpu')
    model = engine._adapter.model
    watching = SensoryState(left_rate=1.0)
    for frame in range(12):
        engine.step(watching, frame * engine.frame_dt)
        spikes = model.spikes.clone()
        assert spikes.any()
        assert torch.equal(model.propagate(spikes), _every_synapse(model.weights, spikes))
