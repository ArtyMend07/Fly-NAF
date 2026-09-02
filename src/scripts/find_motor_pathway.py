import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
from neural.data_loader import get_hash_tables
from graph_search import load_excitatory_graph, dijkstra

def run():
    print("[PHASE 2] Loading anatomical hash tables...")
    flyid2i, i2flyid = get_hash_tables(config.COMPLETENESS_CSV)

    print("[PHASE 2] Loading 15M synaptic edges into excitatory graph...")
    graph = load_excitatory_graph(config.CONNECTIVITY_PARQUET)
    print(f"[PHASE 2] Graph built. Unique source nodes: {len(graph)}")

    sensory_indices = [flyid2i[n] for n in config.SENSORY_NEURONS['sugar_grns'] if n in flyid2i]
    motor_indices = [flyid2i[n] for n in config.MOTOR_NEURONS['p9_walking'] if n in flyid2i]

    print(f"[PHASE 2] Running Dijkstra from {len(sensory_indices)} sensory nodes to {len(motor_indices)} motor nodes...")
    result = dijkstra(graph, sensory_indices, motor_indices, max_hops=15)

    if result is None:
        print("[PHASE 2] FAILED: No excitatory path found within hop limit.")
        print("          Consider relaxing max_hops or expanding sensory neuron candidates.")
        return

    total_cost, path = result
    print(f"\n[PHASE 2] PATH FOUND. Total synaptic cost: {total_cost:.6f}")
    print(f"[PHASE 2] Biological hops: {len(path) - 1}")
    print(f"\n[PHASE 2] Full pathway (Index -> Root ID):")
    for step, idx in enumerate(path):
        label = "[SENSORY]" if idx in sensory_indices else "[MOTOR]" if idx in motor_indices else "      "
        print(f"  Step {step:02d}: Index={idx} | Root ID={i2flyid[idx]} {label}")

    gateway_index = path[0]
    gateway_root_id = i2flyid[gateway_index]
    print(f"\n[PHASE 2] Optimal Sensory Gateway: Index={gateway_index} | Root ID={gateway_root_id}")
    print(f"          Update config.SENSORY_NEURONS to use this node as the stimulus entry point.")

if __name__ == '__main__':
    run()
