import heapq
import pandas as pd
import numpy as np
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

def load_excitatory_graph(conn_path: str) -> Dict[int, List[Tuple[float, int]]]:
    df = pd.read_parquet(conn_path, columns=[
        'Presynaptic_Index', 'Postsynaptic_Index', 'Excitatory x Connectivity'
    ])

    excitatory_edges = df[df['Excitatory x Connectivity'] > 0]

    graph = defaultdict(list)
    for _, row in excitatory_edges.iterrows():
        src = int(row['Presynaptic_Index'])
        dst = int(row['Postsynaptic_Index'])
        weight = float(row['Excitatory x Connectivity'])
        cost = 1.0 / weight
        graph[src].append((cost, dst))

    return graph

def dijkstra(
    graph: Dict[int, List[Tuple[float, int]]],
    source_indices: List[int],
    target_indices: List[int],
    max_hops: int = 10
) -> Optional[Tuple[float, List[int]]]:
    target_set = set(target_indices)

    dist = {}
    prev = {}
    heap = []

    for src in source_indices:
        dist[src] = 0.0
        prev[src] = None
        heapq.heappush(heap, (0.0, 0, src))

    while heap:
        current_cost, hops, node = heapq.heappop(heap)

        if node in target_set:
            path = _reconstruct_path(prev, node)
            return current_cost, path

        if hops >= max_hops:
            continue

        if current_cost > dist.get(node, float('inf')):
            continue

        for edge_cost, neighbor in graph.get(node, []):
            new_cost = current_cost + edge_cost
            if new_cost < dist.get(neighbor, float('inf')):
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, hops + 1, neighbor))

    return None

def _reconstruct_path(prev: Dict[int, Optional[int]], target: int) -> List[int]:
    path = []
    node = target
    while node is not None:
        path.append(node)
        node = prev[node]
    return list(reversed(path))