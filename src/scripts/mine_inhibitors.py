import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import config

FLYWIRE_ANNOTATIONS = os.path.join(
    os.path.dirname(config.PROJECT_ROOT),
    'flywire_annotations', 'supplemental_files', 'Supplemental_file1_neuron_annotations.tsv'
)


def mine_top_50():
    conn = pd.read_parquet(config.CONNECTIVITY_PARQUET)
    anno = pd.read_csv(FLYWIRE_ANNOTATIONS, sep='\t', low_memory=False)

    left_gf, right_gf = config.MOTOR_NEURONS.dnp01_giant_fiber

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