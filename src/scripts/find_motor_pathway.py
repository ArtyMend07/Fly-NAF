import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
from neural.data_loader import get_hash_tables
from graph_search import load_excitatory_graph, find_true_sensory_nodes, find_sensory_cluster


def run():
    flyid2i, i2flyid = get_hash_tables(config.COMPLETENESS_CSV)
    graph, nodes_with_incoming = load_excitatory_graph(config.CONNECTIVITY_PARQUET)
    print(f'graph built, unique source nodes: {len(graph)}')

    sensory_candidates = find_true_sensory_nodes(graph, nodes_with_incoming, min_out_degree=5)
    print(f'sensory candidates: {len(sensory_candidates)}')

    motor_root_id = config.MOTOR_NEURONS.dnp01_giant_fiber[0]
    motor_index = flyid2i[motor_root_id]

    cluster = find_sensory_cluster(graph, sensory_candidates, motor_index, cluster_size=50, max_hops=15)

    if not cluster:
        print('no sensory candidate reached the motor neuron within hop limit')
        return

    root_ids = [i2flyid[idx] for _, idx in cluster]
    print(f'top {len(cluster)} sensory cluster: {root_ids}')

    for rank, (cost, idx) in enumerate(cluster):
        print(f'rank {rank+1:02d}: index={idx} root_id={i2flyid[idx]} cost={cost:.6f}')


if __name__ == '__main__':
    run()