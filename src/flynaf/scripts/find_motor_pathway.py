import argparse

from flynaf import config
from flynaf.graph_search import dijkstra, load_excitatory_graph
from flynaf.neural.cell_types import CellTypeIndex
from flynaf.neural.data_loader import get_hash_tables


def _indices(cell_index: CellTypeIndex, flyid2i: dict, cell_type: str, side: str) -> list:
    return [flyid2i[root] for root in cell_index.root_ids([cell_type], side) if root in flyid2i]


def run(source_type: str, target_type: str, side: str, max_hops: int) -> int:
    cell_index = CellTypeIndex.load()
    flyid2i, i2flyid = get_hash_tables(config.COMPLETENESS_CSV)
    sources = _indices(cell_index, flyid2i, source_type, side)
    targets = _indices(cell_index, flyid2i, target_type, side)
    if not sources or not targets:
        print(f'{source_type} or {target_type} has no {side} neurons in this release')
        return 1

    print(f'{len(sources)} {source_type} and {len(targets)} {target_type} on the {side}, building the graph')
    found = dijkstra(load_excitatory_graph(config.CONNECTIVITY_PARQUET), sources, targets, max_hops)
    if found is None:
        print(f'no excitatory path within {max_hops} hops')
        return 1

    cost, path = found
    print(f'cheapest excitatory path, cost {cost:.4f} over {len(path) - 1} synapses')
    for hop, index in enumerate(path):
        print(f'  {hop}: {cell_index.describe(i2flyid[index])}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Cheapest excitatory path between two FlyWire cell types, weights as cost.',
    )
    parser.add_argument('--source', default='LPLC2')
    parser.add_argument('--target', default='DNp01')
    parser.add_argument('--side', default='left', choices=('left', 'right'))
    parser.add_argument('--max-hops', type=int, default=10)
    args = parser.parse_args()
    return run(args.source, args.target, args.side, args.max_hops)


if __name__ == '__main__':
    raise SystemExit(main())
