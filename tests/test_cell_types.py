import os
import tempfile

import pandas as pd

from flynaf import config
from flynaf.neural.cell_types import CellTypeIndex
from flynaf.night.neurons import NeuronMap, build_neuron_map, stimulus_rates
from flynaf.night.state import SensoryState

TABLE = pd.DataFrame({
    'root_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    'cell_type': ['LPLC2', 'LPLC2', 'LC4', 'LC4', 'LC9', 'LC31a', 'DNp01', 'DNp01',
                  'DNp04', 'DNp04', 'DNp09', 'DNp09', None],
    'side': ['left', 'right', 'left', 'right', 'left', 'left', 'left', 'right',
             'left', 'right', 'left', 'right', 'left'],
})

LOOKUP_CASES = (
    (('LPLC2',), 'left', [1]),
    (('LPLC2', 'LC4'), 'right', [2, 4]),
    (('DNp09',), None, [11, 12]),
    (('LC9', 'LC31a'), 'right', []),
    (('NOPE',), 'left', []),
)


def test_root_ids_select_by_type_and_side():
    index = CellTypeIndex(TABLE)
    for types, side, expected in LOOKUP_CASES:
        assert index.root_ids(types, side) == expected, (types, side)


def test_describe_names_the_type_and_side():
    index = CellTypeIndex(TABLE)
    assert index.describe(7) == 'DNp01 (left) 7'
    assert index.describe(999) == 'untyped 999'


def test_the_cache_is_reused_until_the_annotations_change():
    with tempfile.TemporaryDirectory() as folder:
        tsv = os.path.join(folder, 'annotations.tsv')
        cache = os.path.join(folder, 'cache.parquet')
        TABLE.assign(extra='x').to_csv(tsv, sep='\t', index=False)

        first = CellTypeIndex.load(tsv, cache)
        assert os.path.isfile(cache)
        os.remove(tsv)
        second = CellTypeIndex.load(tsv, cache)
        assert first.root_ids(['LC4'], 'left') == second.root_ids(['LC4'], 'left') == [3]


def _identity(root_ids, label):
    return list(root_ids)


def test_the_neuron_map_resolves_every_role_from_cell_types():
    neurons = build_neuron_map(CellTypeIndex(TABLE), _identity)
    assert neurons.inputs['eye_left'] == [1, 3]
    assert neurons.inputs['figure_left'] == [5, 6]
    assert neurons.inputs['loom_size_left'] == [1]
    assert neurons.inputs['loom_speed_right'] == [4]
    assert neurons.outputs['giant_fiber_right'] == [8]
    assert neurons.outputs['looming_escape_left'] == [9]
    assert neurons.outputs['explore'] == [11, 12]
    assert neurons.inputs['inhibitors_left'] == list(config.SENSORY_NEURONS.camera_inhibitor_left)


def test_inhibitors_keep_their_refractory_period():
    neurons = build_neuron_map(CellTypeIndex(TABLE), _identity)
    stimulated = set(neurons.stimulus_indices())
    assert {1, 2, 3, 4, 5, 6} <= stimulated
    assert not stimulated & set(config.SENSORY_NEURONS.camera_inhibitor_left)


def test_stimulus_rates_scale_levels_and_pass_the_inhibitor_rate_through():
    neurons = NeuronMap(
        inputs={'eye_left': [0], 'eye_right': [1], 'inhibitors_left': [2],
                'inhibitors_right': [3], 'figure_left': [4]},
        outputs={},
    )
    state = SensoryState(left_rate=1.0, cam_inhib=250.0, tablet_drive={'figure_left': 0.5})
    rates = [(tuple(indices), rate) for indices, rate in stimulus_rates(neurons, state, 1000.0)]
    assert rates == [((0,), 1000.0), ((1,), 0.0), ((2,), 250.0), ((3,), 250.0), ((4,), 500.0)]


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
