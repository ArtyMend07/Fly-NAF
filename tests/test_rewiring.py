import torch

from flynaf.neural.rewiring import shuffled_targets, without_outgoing


def _wiring(seed: int = 0, size: int = 60, edges: int = 400) -> torch.Tensor:
    rng = torch.Generator().manual_seed(seed)
    pairs = torch.randint(0, size, (2, edges), generator=rng)
    values = torch.randn(edges, generator=rng)
    return torch.sparse_coo_tensor(pairs, values, (size, size)).coalesce().to_sparse_csr()


def _degrees(weights: torch.Tensor) -> tuple:
    dense = weights.to_dense()
    return (dense != 0).sum(1), (dense != 0).sum(0)


def test_every_source_keeps_its_outgoing_weights():
    weights = _wiring()
    rewired = shuffled_targets(weights, seed=3)
    assert torch.allclose(weights.to_dense().sum(0), rewired.to_dense().sum(0), atol=1e-5)


def test_degrees_survive_apart_from_merged_duplicates():
    weights = _wiring()
    rewired = shuffled_targets(weights, seed=3)
    incoming, outgoing = _degrees(weights)
    rewired_in, rewired_out = _degrees(rewired)
    assert rewired_in.sum() <= incoming.sum()
    assert (rewired_out <= outgoing).all()
    assert rewired.values().numel() >= 0.95 * weights.values().numel()


def test_the_targets_actually_move_and_the_seed_repeats():
    weights = _wiring()
    first, again, other = (shuffled_targets(weights, seed=s) for s in (1, 1, 2))
    assert not torch.equal(first.to_dense(), weights.to_dense())
    assert torch.equal(first.to_dense(), again.to_dense())
    assert not torch.equal(first.to_dense(), other.to_dense())


def test_a_cut_neuron_reaches_nothing_and_every_other_synapse_is_kept():
    weights = _wiring()
    cut = without_outgoing(weights, [4, 9])
    dense, kept = weights.to_dense(), cut.to_dense()
    assert not kept[:, [4, 9]].any()
    others = [column for column in range(dense.shape[1]) if column not in (4, 9)]
    assert torch.equal(kept[:, others], dense[:, others])
