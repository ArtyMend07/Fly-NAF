import json
import logging
import os
import threading
from datetime import datetime

import config

_log = logging.getLogger(__name__)

TRACE_VERSION = 1


def default_path() -> str:
    folder = os.path.join(config.PROJECT_ROOT, 'logs', 'traces')
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return os.path.join(folder, 'trace_%s.jsonl' % stamp)


def _settings() -> dict:
    simulation = config.SIMULATION_PARAMS
    foraging = config.FORAGING_PARAMS
    search = config.SEARCH_DYNAMICS
    return {
        'arousal_multiplier': simulation.arousal_multiplier,
        'base_sensory_rate_hz': simulation.base_sensory_rate_hz,
        'steps_per_frame': simulation.steps_per_frame,
        'target_fps': simulation.target_fps,
        'subliminal_noise_hz': foraging.subliminal_noise_hz,
        'mse_threshold': foraging.mse_threshold,
        'starvation_sec': search.starvation_sec,
    }


class SessionRecorder:
    def __init__(self, path: str | None = None, enabled: bool = True):
        self.enabled = enabled
        self.path = path or default_path()
        self.frames = 0
        self._lock = threading.Lock()
        self._handle = None
        if not self.enabled:
            return
        self._handle = open(self.path, 'w', encoding='utf-8')
        self._write({
            'kind': 'header',
            'trace_version': TRACE_VERSION,
            'recorded_at': datetime.now().isoformat(timespec='seconds'),
            'connectome': os.path.basename(config.CONNECTIVITY_PARQUET),
            'settings': _settings(),
        })

    def _write(self, payload: dict):
        if self._handle is None:
            return
        self._handle.write(json.dumps(payload, separators=(',', ':')) + '\n')

    def frame(self, elapsed: float, state, engine, spikes_left: bool, spikes_right: bool,
              left_mse: float, right_mse: float, camera_open: bool):
        if not self.enabled:
            return
        with self._lock:
            self.frames += 1
            self._write({
                'kind': 'frame',
                't': round(elapsed, 4),
                'left_rate': round(float(state.left_rate), 4),
                'right_rate': round(float(state.right_rate), 4),
                'cam_inhib': round(float(state.cam_inhib), 2),
                'left_mse': round(float(left_mse), 1),
                'right_mse': round(float(right_mse), 1),
                'camera_open': bool(camera_open),
                'gf_left': bool(spikes_left),
                'gf_right': bool(spikes_right),
                'eye_membrane_diff': round(float(engine.eye_membrane_diff), 4),
                'explore_membrane': round(float(engine.explore_membrane), 4),
            })

    def event(self, elapsed: float, label: str, detail: str = ''):
        if not self.enabled:
            return
        with self._lock:
            self._write({
                'kind': 'event',
                't': round(elapsed, 4),
                'label': label,
                'detail': detail,
            })

    def close(self):
        if self._handle is None:
            return
        with self._lock:
            self._handle.close()
            self._handle = None
        _log.info('trace written to %s (%d frames)', self.path, self.frames)


def load_trace(path: str) -> tuple:
    header, frames, events = {}, [], []
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            kind = payload.get('kind')
            if kind == 'header':
                header = payload
            elif kind == 'frame':
                frames.append(payload)
            elif kind == 'event':
                events.append(payload)
    return header, frames, events
