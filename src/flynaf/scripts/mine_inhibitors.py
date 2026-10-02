import pandas as pd

from flynaf import config
from flynaf.neural.cell_types import CellTypeIndex


def mine_top_50():
    conn = pd.read_parquet(config.CONNECTIVITY_PARQUET)
    anno = pd.read_csv(config.ANNOTATIONS_TSV, sep='\t', low_memory=False)

    cell_index = CellTypeIndex.load()
    giant_fiber = config.CELL_POPULATIONS.giant_fiber
    left_gf = cell_index.root_ids(giant_fiber, 'left')[0]
    right_gf = cell_index.root_ids(giant_fiber, 'right')[0]

    gaba_ids = set(anno[anno['top_nt'] == 'gaba']['root_id'].unique())

    top_left = (
        conn[conn['Postsynaptic_ID'] == left_gf]
        .pipe(lambda df: df[df['Presynaptic_ID'].isin(gaba_ids)])
        .sort_values('Connectivity', ascending=False)
        .head(50)
    )
    top_right = (
        conn[conn['Postsynaptic_ID'] == right_gf]
        .pipe(lambda df: df[df['Presynaptic_ID'].isin(gaba_ids)])
        .sort_values('Connectivity', ascending=False)
        .head(50)
    )

    print('left gf top 50 gaba:', top_left['Presynaptic_ID'].tolist())
    print('right gf top 50 gaba:', top_right['Presynaptic_ID'].tolist())


if __name__ == '__main__':
    mine_top_50()
