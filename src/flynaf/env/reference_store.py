import logging
import os
import shutil
from datetime import datetime

from flynaf import config
from flynaf.env import anchor

_log = logging.getLogger(__name__)

ROOT = os.path.join(config.PROJECT_ROOT, 'logs', 'vision_reference')
ARCHIVE = 'archive'


def layout_folder(kind: str, root: str = ROOT) -> str:
    rect = anchor.game_rect()
    width, height = (rect[2], rect[3]) if rect else (anchor.DESIGN_WIDTH, anchor.DESIGN_HEIGHT)
    folder = os.path.join(root, f'{width}x{height}', kind)
    os.makedirs(folder, exist_ok=True)
    return folder


def keep_aside(folder: str) -> str | None:
    if not os.path.isdir(folder) or not os.listdir(folder):
        return None
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    archive = os.path.join(os.path.dirname(folder), ARCHIVE, f'{os.path.basename(folder)}_{stamp}')
    shutil.move(folder, archive)
    os.makedirs(folder, exist_ok=True)
    _log.info('the previous references in %s were kept in %s', folder, archive)
    return archive
