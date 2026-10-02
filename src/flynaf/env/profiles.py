import glob
import os
import shutil
import tempfile

_PREFIX = 'flynaf_'


def _held_by_live_browser(path: str) -> bool:
    lock = os.path.join(path, 'lockfile')
    if os.path.exists(lock):
        try:
            os.remove(lock)
        except OSError:
            return True
    singleton = os.path.join(path, 'SingletonLock')
    if os.path.islink(singleton):
        owner = os.readlink(singleton).rpartition('-')[2]
        try:
            os.kill(int(owner), 0)
        except (OSError, ValueError):
            return False
        return True
    return False


def sweep() -> int:
    removed = 0
    for path in glob.glob(os.path.join(tempfile.gettempdir(), _PREFIX + '*')):
        if os.path.isdir(path) and not _held_by_live_browser(path):
            shutil.rmtree(path, ignore_errors=True)
            removed += not os.path.exists(path)
    return removed


def fresh(kind: str) -> str:
    sweep()
    return tempfile.mkdtemp(prefix=f'{_PREFIX}{kind}_')
