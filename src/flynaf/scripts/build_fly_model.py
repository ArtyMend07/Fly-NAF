import gzip
import json
import os
import struct
import urllib.request

import numpy as np

from flynaf import config

REVISION = '38c8ec61034cd59bc5ba0de20688d4a3c0000d60'
BASE = (
    f'https://raw.githubusercontent.com/NeLy-EPFL/flygym/{REVISION}'
    '/src/flygym/assets/model/neuromechfly/'
)
LICENSE_URL = f'https://raw.githubusercontent.com/NeLy-EPFL/flygym/{REVISION}/LICENSE'
ASSETS = os.path.join(config.PROJECT_ROOT, 'src', 'flynaf', 'env', 'assets')
OUTPUT = os.path.join(ASSETS, 'neuromechfly.bin.gz')
SCALE = 1000.0

SIDES = ('l', 'r')
LEGS = [f'{side}{pos}' for side in SIDES for pos in 'fmh']
LEG_LINKS = ['coxa', 'trochanterfemur', 'tibia', 'tarsus1', 'tarsus2', 'tarsus3', 'tarsus4', 'tarsus5']
AXES = {'pitch': (0.0, 1.0, 0.0), 'roll': (0.0, 0.0, 1.0), 'yaw': (1.0, 0.0, 0.0)}


def _chain(*names):
    return [(names[i], names[i + 1]) for i in range(len(names) - 1)]


PAIRS = [
    ('c_thorax', 'c_head'),
    *_chain('c_head', 'c_rostrum', 'c_haustellum'),
    *_chain('c_thorax', 'c_abdomen12', 'c_abdomen3', 'c_abdomen4', 'c_abdomen5', 'c_abdomen6'),
    *(('c_head', f'{s}_eye') for s in SIDES),
    *(pair for s in SIDES for pair in _chain('c_head', f'{s}_pedicel', f'{s}_funiculus', f'{s}_arista')),
    *(('c_thorax', f'{s}_wing') for s in SIDES),
    *(('c_thorax', f'{s}_haltere') for s in SIDES),
    *(pair for leg in LEGS for pair in _chain('c_thorax', *(f'{leg}_{link}' for link in LEG_LINKS))),
]
PARENT = {child: parent for parent, child in PAIRS}


def material_of(name: str) -> str:
    if name.endswith('_eye'):
        return 'eye_' + name[0]
    if name.endswith('_wing'):
        return 'wing'
    if 'abdomen' in name:
        return 'abdomen'
    if name in ('c_thorax', 'c_head'):
        return 'body'
    if any(part in name for part in ('pedicel', 'funiculus', 'arista', 'haltere', 'rostrum', 'haustellum')):
        return 'detail'
    return 'leg'


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def _parse_rigging(text: str) -> dict:
    rigging, current = {}, None
    for line in text.splitlines():
        if line and not line.startswith(' ') and line.endswith(':'):
            current = line[:-1]
            rigging[current] = {}
        elif current and line.strip().startswith(('pos:', 'quat:')):
            key, _, value = line.strip().partition(':')
            rigging[current][key] = [float(v) for v in value.strip(' []').split(',')]
    return rigging


def _parse_pose(text: str) -> tuple:
    order, angles = [], {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('axis_order:'):
            order = [a.strip() for a in stripped.split(':', 1)[1].strip(' []').split(',')]
        elif line.startswith('  ') and ':' in stripped:
            key, _, value = stripped.partition(':')
            angles[key] = np.radians(float(value))
    for key, value in list(angles.items()):
        parent, child, axis = key.split('-')
        if child[0] != 'l':
            continue
        mirrored_parent = 'r' + parent[1:] if parent[0] == 'l' else parent
        angles.setdefault(f'{mirrored_parent}-r{child[1:]}-{axis}', value)
    return order, angles


def _quat_matrix(q) -> np.ndarray:
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def _axis_matrix(axis, angle: float) -> np.ndarray:
    x, y, z = axis
    c, s, t = np.cos(angle), np.sin(angle), 1 - np.cos(angle)
    return np.array([
        [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
    ])


def _read_stl(data: bytes) -> np.ndarray:
    count = struct.unpack_from('<I', data, 80)[0]
    record = np.dtype([('normal', '<f4', 3), ('v', '<f4', (3, 3)), ('attr', '<u2')])
    return np.frombuffer(data, dtype=record, count=count, offset=84)['v'].astype(np.float64)


def _world_transforms(rigging: dict, order: list, angles: dict) -> dict:
    world = {'c_thorax': (np.eye(3), np.zeros(3))}

    def resolve(name):
        if name in world:
            return world[name]
        parent_rotation, parent_origin = resolve(PARENT[name])
        spec = rigging[name]
        rotation = parent_rotation @ _quat_matrix(np.array(spec['quat']))
        origin = parent_origin + parent_rotation @ np.array(spec['pos'])
        for axis_name in order:
            angle = angles.get(f'{PARENT[name]}-{name}-{axis_name}', 0.0)
            vector = np.array(AXES[axis_name])
            if name[0] == 'r' and axis_name != 'pitch':
                vector = -vector
            rotation = rotation @ _axis_matrix(vector, angle)
        world[name] = (rotation, origin)
        return world[name]

    for name in rigging:
        resolve(name)
    return world


def build() -> str:
    rigging = _parse_rigging(_fetch(BASE + 'rigging.yaml').decode())
    order, angles = _parse_pose(_fetch(BASE + 'pose/neutral/roll_pitch_yaw.yaml').decode())
    world = _world_transforms(rigging, order, angles)
    meshes = {}
    groups = {}
    for name in rigging:
        source = 'l' + name[1:] if name[0] == 'r' else name
        if source not in meshes:
            url = BASE + f'meshes/simplified_max2000faces/{source}.stl'
            meshes[source] = _read_stl(_fetch(url)) * SCALE
            print('fetched', source)
        triangles = meshes[source].copy()
        if name[0] == 'r':
            triangles[:, :, 1] *= -1.0
            triangles = triangles[:, ::-1, :]
        rotation, origin = world[name]
        placed = triangles.reshape(-1, 3) @ rotation.T + origin
        groups.setdefault(material_of(name), []).append(placed)

    everything = np.concatenate([np.concatenate(parts) for parts in groups.values()])
    low, high = everything.min(axis=0), everything.max(axis=0)
    header = {'bounds': [low.tolist(), high.tolist()], 'groups': []}
    blobs = []
    for material, parts in groups.items():
        soup = np.concatenate(parts)
        keys = np.round(soup, 5)
        unique, index = np.unique(keys, axis=0, return_inverse=True)
        quantised = np.round((unique - low) / (high - low) * 65535).astype('<u2')
        header['groups'].append({
            'material': material, 'vertices': int(len(unique)), 'indices': int(index.size),
        })
        blobs.append(quantised.tobytes() + index.astype('<u4').ravel().tobytes())
    meta = json.dumps(header).encode()
    payload = struct.pack('<I', len(meta)) + meta + b''.join(blobs)

    os.makedirs(ASSETS, exist_ok=True)
    with gzip.open(OUTPUT, 'wb', compresslevel=9) as handle:
        handle.write(payload)
    with open(os.path.join(ASSETS, 'LICENSE-neuromechfly.txt'), 'wb') as handle:
        handle.write(_fetch(LICENSE_URL))
    return OUTPUT


if __name__ == '__main__':
    path = build()
    print('wrote %s, %.0f KB' % (path, os.path.getsize(path) / 1024))
