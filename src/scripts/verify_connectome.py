import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import config
from brain_adapter import BrainAdapter

FLYWIRE_ANNOTATIONS = os.path.join(
    os.path.dirname(config.PROJECT_ROOT),
    'flywire_annotations', 'supplemental_files', 'Supplemental_file1_neuron_annotations.tsv'
)

PROOFREAD_783 = 139255


def report_graph():
    comp = pd.read_csv(config.COMPLETENESS_CSV, index_col=0)
    conn = pd.read_parquet(config.CONNECTIVITY_PARQUET)

    neurons = comp.shape[0]
    edges = conn.shape[0]
    max_index = int(max(conn['Presynaptic_Index'].max(), conn['Postsynaptic_Index'].max()))
    weights = conn['Excitatory x Connectivity']

    print('--- Graph as loaded ---')
    print(f'Neurons in the completeness index   : {neurons:,}')
    print(f'Proofread neurons in FlyWire 783    : {PROOFREAD_783:,}')
    print(f'Coverage                            : {neurons / PROOFREAD_783 * 100:.2f}%')
    print(f'Edges in the connectivity table     : {edges:,}')
    print(f'Highest index referenced by an edge : {max_index:,}')
    print(f'Every edge fits the matrix          : {max_index < neurons}')
    print(f'Excitatory edges                    : {int((weights > 0).sum()):,}')
    print(f'Inhibitory edges                    : {int((weights < 0).sum()):,}')
    return comp, edges


def report_exclusions(comp):
    if not os.path.exists(FLYWIRE_ANNOTATIONS):
        print('\n--- Neurons left out ---')
        print('Annotation file not found, skipping.')
        return

    anno = pd.read_csv(FLYWIRE_ANNOTATIONS, sep='\t', low_memory=False)
    simulated = set(int(i) for i in comp.index)
    annotated = anno[anno['root_id'].notna()].copy()
    annotated['root_id'] = annotated['root_id'].astype('int64')
    missing = annotated[~annotated['root_id'].isin(simulated)]

    print('\n--- Neurons left out ---')
    print(f'Annotated neurons                   : {len(annotated):,}')
    print(f'Annotated but not simulated         : {len(missing):,}')
    for super_class, count in missing['super_class'].value_counts(dropna=False).items():
        print(f'  {str(super_class):<34}: {count:,}')


def report_matrix():
    adapter = BrainAdapter(
        config.COMPLETENESS_CSV,
        config.CONNECTIVITY_PARQUET,
        config.DATA_DIR,
        device='cpu',
    )
    rows, cols = adapter.weights.shape

    print('\n--- Matrix handed to the engine ---')
    print(f'Shape                               : {rows:,} x {cols:,}')
    print(f'Non-zero entries                    : {adapter.weights.values().numel():,}')
    print(f'Neurons the engine will simulate    : {adapter.num_neurons:,}')
    print(f'Rows dropped before the engine      : {rows - adapter.num_neurons}')
    print(f'Global gain applied to every weight : {config.SIMULATION_PARAMS.arousal_multiplier}x')
    print('Sign and topology are FlyWire measurements, magnitude is scaled by that gain.')


def main():
    comp, _ = report_graph()
    report_exclusions(comp)
    report_matrix()


if __name__ == '__main__':
    main()
