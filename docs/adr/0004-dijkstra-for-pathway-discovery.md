# 0004. Use Dijkstra's Algorithm for Biological Motor Pathway Discovery

## Status
Accepted

## Context
Phase 1 proved that the direct sensory-to-motor signal propagation (Sugar GRNs to P9 walking neurons) fails entirely within the connectome. The inhibitory network absorbed the stimulus before it could reach the motor cortex.
Two candidate algorithms existed for finding valid excitatory pathways: Reinforcement Learning (trial-and-error training) and Dijkstra's Algorithm (deterministic graph search).
RL was initially listed as a candidate approach for discovering optimal sensory entry points. However, since the full 15-million-edge connectivity matrix is available as structured data with explicit excitatory weights (`Excitatory x Connectivity`), running RL is wasteful. RL is appropriate when the search space has no ground truth. Here, the ground truth is the connectome itself.

## Decision
I will apply Dijkstra's Algorithm over a directed graph constructed exclusively from excitatory synapses (`Excitatory x Connectivity > 0`). Edge cost is defined as the inverse of synaptic weight (`1.0 / weight`), ensuring that stronger biological connections represent shorter graph distances. The algorithm searches from all Sugar GRN indices simultaneously (multi-source) toward the P9 motor neuron indices.

## Consequences
**Positive:**
- Deterministic result. The same connectome always produces the same optimal pathway.
- No training phase, no GPU requirement, no hyperparameter tuning.
- The discovered pathway is anatomically valid: every hop corresponds to a real excitatory synapse in the biological dataset.
- Eliminates the need for the RL-based "Translation Layer" originally planned, simplifying the overall architecture.

**Negative:**
- Dijkstra on a 15M-edge graph with 138k nodes is memory-intensive. Building the adjacency list requires loading and filtering the full parquet file into RAM.
- The algorithm may fail to find a path if the excitatory subgraph is disconnected between the Sugar GRN cluster and the P9 cluster within the configured `max_hops` limit.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---------|-------------|-----------|------|-------------|-------------|
| 1.0 | Initial version | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 |
