import logging
import os
import threading
import time

import cv2
import numpy as np

from flynaf import clock, config
from flynaf.env import anchor, capture

_log = logging.getLogger(__name__)

FRAME_SUFFIX = '.jpg'


def frames_folder(trace_path: str) -> str:
    stamp = os.path.splitext(os.path.basename(trace_path))[0].removeprefix('trace_')
    return os.path.join(config.PROJECT_ROOT, 'logs', 'frames', stamp)


def frame_name(elapsed: float) -> str:
    return f'{elapsed:010.3f}{FRAME_SUFFIX}'


def frame_time(name: str) -> float:
    return float(name.removesuffix(FRAME_SUFFIX))


class FrameRecorder:
    def __init__(self, folder: str, origin: float, params=None):
        self._p = params or config.FRAME_RECORDING
        self._origin = origin
        self.folder = folder

    def start(self):
        os.makedirs(self.folder, exist_ok=True)
        threading.Thread(target=self._record, daemon=True).start()
        _log.info('recording the game window into %s', self.folder)

    def _record(self):
        capture.keep_capturing(self._grab_once, 'frame recording', config.VISION_DYNAMICS.capture_retry_sec)

    def _grab_once(self, screen):
        rect = anchor.game_rect()
        if rect is not None:
            left, top, width, height = rect
            shot = np.asarray(screen.grab({'left': left, 'top': top, 'width': width, 'height': height}))
            path = os.path.join(self.folder, frame_name(clock.now() - self._origin))
            cv2.imwrite(path, shot[..., :3], [cv2.IMWRITE_JPEG_QUALITY, self._p.jpeg_quality])
        time.sleep(self._p.period_sec)
