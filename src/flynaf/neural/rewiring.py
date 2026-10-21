import torch


def shuffled_targets(weights: torch.Tensor, seed: int) -> torch.Tensor:
    synapses = weights.to('cpu').to_sparse_coo().coalesce()
    targets, sources = synapses.indices()
    order = torch.randperm(targets.numel(), generator=torch.Generator().manual_seed(seed))
    rewired = torch.sparse_coo_tensor(
        torch.stack([targets[order], sources]), synapses.values(), synapses.shape,
    ).coalesce()
    return rewired.to_sparse_csr().to(weights.device)


def without_outgoing(weights: torch.Tensor, silenced: list) -> torch.Tensor:
    synapses = weights.to('cpu').to_sparse_coo().coalesce()
    targets, sources = synapses.indices()
    kept = ~torch.isin(sources, torch.as_tensor(silenced, dtype=sources.dtype))
    cut = torch.sparse_coo_tensor(
        torch.stack([targets[kept], sources[kept]]), synapses.values()[kept], synapses.shape,
    ).coalesce()
    return cut.to_sparse_csr().to(weights.device)
