import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
from neural.data_loader import get_hash_tables
from graph_search import load_excitatory_graph, find_true_sensory_nodes, find_sensory_cluster

def run():
    print("[PHASE 2] Loading anatomical hash tables...")
    flyid2i, i2flyid = get_hash_tables(config.COMPLETENESS_CSV)

    print("[PHASE 2] Loading 15M synaptic edges into excitatory graph...")
    graph, nodes_with_incoming = load_excitatory_graph(config.CONNECTIVITY_PARQUET)
    print(f"[PHASE 2] Graph built. Unique source nodes: {len(graph)}")

    print("[PHASE 2] Mining true sensory entry nodes (In-Degree=0, Out-Degree>=5)...")
    sensory_candidates = find_true_sensory_nodes(graph, nodes_with_incoming, min_out_degree=5)
    print(f"[PHASE 2] Candidates found: {len(sensory_candidates)}")

    motor_root_id = config.MOTOR_NEURONS['p9_walking'][0]
    motor_index = flyid2i[motor_root_id]

    print(f"[PHASE 2] Running cluster search toward motor neuron {motor_root_id}...")
    print(f"          This will evaluate {len(sensory_candidates)} candidates. May take a few minutes.")
    cluster = find_sensory_cluster(graph, sensory_candidates, motor_index, cluster_size=50, max_hops=15)

    if not cluster:
        print("[PHASE 2] FAILED: No sensory candidate reached the motor neuron within hop limit.")
        return

    print(f"\n[PHASE 2] TOP {len(cluster)} SENSORY CLUSTER FOUND.")
    print(f"[PHASE 2] Paste this array into config.py as 'left_eye_cluster':\n")
    root_ids = [i2flyid[idx] for _, idx in cluster]
    print(f"    {root_ids}\n")

    for rank, (cost, idx) in enumerate(cluster):
        print(f"  Rank {rank+1:02d}: Index={idx} | Root ID={i2flyid[idx]} | Cost={cost:.6f}")

if __name__ == '__main__':
    run()
