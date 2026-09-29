import gzip
import json
import os
import struct
import sys
import tempfile
from unittest.mock import patch

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
from env import brain_view

ASSET = os.path.join(config.PROJECT_ROOT, 'src', 'env', 'assets', 'neuromechfly.bin.gz')


def _codex_file(folder: str, rows: list):
    with open(os.path.join(folder, 'soma_coordinates_783.csv'), 'w', encoding='utf-8') as handle:
        handle.write('root_id,position,supervoxel_id\n')
        for root_id, x, y, z in rows:
            handle.write(f'{root_id},[{x} {y} {z}],1\n')


def test_positions_follow_the_root_id_and_not_the_row_order():
    with tempfile.TemporaryDirectory() as folder:
        _codex_file(folder, [(30, 3, 3, 3), (10, 1, 1, 1), (10, 9, 9, 9), (20, 2, 2, 2)])
        with patch.object(config, 'DATA_DIR', folder):
            coords = brain_view._read_soma_positions(['10', '20', '30', '40'])
    assert coords[:3].tolist() == [[1, 1, 1], [2, 2, 2], [3, 3, 3]]
    assert np.isnan(coords[3]).all()


def test_the_brain_outline_and_the_neurons_share_one_placement():
    positions = np.array([[0, 0, 0], [10, 20, 30]], dtype=np.float32)
    mesh = (np.array([[-10, -10, -10], [10, 10, 10]], dtype=np.float32), np.zeros((0, 3), np.uint32))
    place = brain_view._normalizer(positions, mesh)
    placed = place(np.array([[0, 0, 0], [10, 10, 10]], dtype=np.float32))
    assert np.allclose(placed[0], [0, 0, 0], atol=0.02)
    assert np.allclose(placed[1], [1, -1, -1], atol=0.02)


def test_a_missing_brain_mesh_leaves_an_empty_outline():
    with tempfile.TemporaryDirectory() as folder:
        with patch.object(config, 'DATA_DIR', folder):
            assert brain_view._read_brain_mesh() is None


def test_the_fly_model_carries_both_eyes_as_separate_groups():
    with gzip.open(ASSET) as handle:
        payload = handle.read()
    length = struct.unpack_from('<I', payload)[0]
    header = json.loads(payload[4:4 + length])
    materials = {group['material'] for group in header['groups']}
    assert {'eye_l', 'eye_r', 'body', 'leg', 'wing'} <= materials
    body = sum(g['vertices'] * 6 + g['indices'] * 4 for g in header['groups'])
    assert len(payload) == 4 + length + body


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
