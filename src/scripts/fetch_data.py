import argparse
import gzip
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config

PARENT = os.path.dirname(config.PROJECT_ROOT)
FLY_BRAIN = os.path.join(PARENT, 'fly-brain')
ANNOTATIONS = os.path.join(PARENT, 'flywire_annotations')
SOMA_CSV = os.path.join(config.DATA_DIR, 'soma_coordinates_783.csv')
SOMA_URL = 'https://storage.googleapis.com/flywire-data/codex/data/fafb/783/coordinates.csv.gz'
SOMA_HEADER = 'root_id,position'
BRAIN_MESH = os.path.join(config.DATA_DIR, 'brain_mesh_flywire.ply')
BRAIN_MESH_URL = (
    'https://raw.githubusercontent.com/navis-org/navis-flybrains/'
    '273333c8d8bf5adeebebd274e554621462e388bd/flybrains/meshes/FLYWIRE.ply'
)
BRAIN_MESH_SHA256 = '2f345b8c66305d51cfb0f78489742fdc31a06d74d231a9e207d511c9789d516e'

LICENCE_NOTICE = """
This downloads roughly 140 MB of third party data that is deliberately not part
of this repository.

  fly-brain                 GPL v2 or later, from eonsystemspbc
  FlyWire 783 connectome    CC BY-NC 4.0, non commercial, attribution required
  flywire_annotations       no licence file at all
  FlyWire brain mesh        GPL v3, from navis-flybrains

The FlyWire terms are not the same as this project's GPL v3, which is why the
data cannot ship here and why you fetch it yourself. Using it commercially is
not permitted, and FlyWire asks to be cited.
"""


def _have(path: str) -> bool:
    return os.path.isfile(path)


def _clone(url: str, target: str) -> bool:
    if os.path.isdir(os.path.join(target, '.git')):
        print('already cloned: %s' % target)
        return True
    print('cloning %s into %s' % (url, target))
    result = subprocess.run(['git', 'clone', '--depth', '1', url, target])
    return result.returncode == 0


def soma_file_is_current(path: str = SOMA_CSV) -> bool:
    if not _have(path):
        return False
    with open(path, encoding='utf-8', errors='replace') as handle:
        return handle.readline().strip().startswith(SOMA_HEADER)


def _download_soma() -> bool:
    if soma_file_is_current():
        print('already present: %s' % SOMA_CSV)
        return True
    if _have(SOMA_CSV):
        print('%s is not the FlyWire Codex file, replacing it' % SOMA_CSV)
    if not os.path.isdir(config.DATA_DIR):
        print('the fly-brain clone is missing, so there is nowhere to put the soma file')
        return False
    archive = SOMA_CSV + '.gz'
    print('downloading %s' % SOMA_URL)
    try:
        urllib.request.urlretrieve(SOMA_URL, archive)
    except OSError as exc:
        print('download failed: %s' % exc)
        return False
    with gzip.open(archive, 'rb') as source, open(SOMA_CSV, 'wb') as target:
        shutil.copyfileobj(source, target)
    os.remove(archive)
    return True


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _download_brain_mesh() -> bool:
    if _have(BRAIN_MESH) and _sha256(BRAIN_MESH) == BRAIN_MESH_SHA256:
        print('already present: %s' % BRAIN_MESH)
        return True
    if not os.path.isdir(config.DATA_DIR):
        print('the fly-brain clone is missing, so there is nowhere to put the brain mesh')
        return False
    print('downloading %s' % BRAIN_MESH_URL)
    partial = BRAIN_MESH + '.part'
    try:
        urllib.request.urlretrieve(BRAIN_MESH_URL, partial)
    except OSError as exc:
        print('download failed: %s' % exc)
        return False
    if _sha256(partial) != BRAIN_MESH_SHA256:
        os.remove(partial)
        print('the brain mesh did not match its checksum, nothing kept')
        return False
    os.replace(partial, BRAIN_MESH)
    return True


def status() -> list:
    return [
        ('connectivity parquet', config.CONNECTIVITY_PARQUET, _have(config.CONNECTIVITY_PARQUET)),
        ('completeness csv', config.COMPLETENESS_CSV, _have(config.COMPLETENESS_CSV)),
        ('soma coordinates', SOMA_CSV, soma_file_is_current()),
        ('flywire annotations', os.path.join(
            ANNOTATIONS, 'supplemental_files', 'Supplemental_file1_neuron_annotations.tsv',
        ), _have(os.path.join(
            ANNOTATIONS, 'supplemental_files', 'Supplemental_file1_neuron_annotations.tsv',
        ))),
    ]


def ready() -> bool:
    return all(present for _label, _path, present in status())


def print_status():
    print('--- Connectome data ---')
    for label, path, present in status():
        print('%-22s %s  %s' % (label, 'present' if present else 'MISSING', path))


def main():
    parser = argparse.ArgumentParser(
        description='Fetch the FlyWire data this simulation needs. Nothing is redistributed.',
    )
    parser.add_argument('--check', action='store_true', help='only report what is present')
    parser.add_argument('--yes', action='store_true', help='skip the licence prompt')
    args = parser.parse_args()

    if args.check:
        print_status()
        return 0 if ready() else 1

    print(LICENCE_NOTICE)
    if not args.yes:
        answer = input('Continue and download it? [y/N] ').strip().lower()
        if answer not in ('y', 'yes'):
            print('nothing downloaded')
            return 1

    ok = _clone('https://github.com/eonsystemspbc/fly-brain.git', FLY_BRAIN)
    ok = _clone('https://github.com/flyconnectome/flywire_annotations.git', ANNOTATIONS) and ok
    ok = _download_soma() and ok
    if not _download_brain_mesh():
        print('the panel will draw the neurons without the brain outline')

    print()
    print_status()
    if ready():
        print('\nall the required files are in place')
        return 0
    print('\nsomething is still missing, see the list above')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
