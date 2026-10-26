import argparse
import dataclasses
import os
import statistics

import cv2
import numpy as np

from flynaf import config, recorder
from flynaf.env import reference_store
from flynaf.env.frame_recorder import frame_time, frames_folder
from flynaf.env.tablet_feed import (
    bank_noise,
    bank_reading,
    feed_size,
    prepare,
    spread_sample,
    view_mask,
)
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState
from flynaf.night.tablet.senses import transduce

CAMERA = '1C'
DESIGN_SIZE = (1280, 720)
NEVER = float('inf')
TABLET_UP = config.SIMULATION_PARAMS.base_sensory_rate_hz
SETTLE_FRAMES = 11


@dataclasses.dataclass
class Look:
    start: float
    door_shut: bool
    readings: list


def camera_spec(params):
    return next(camera for camera in params.cameras if camera.name == CAMERA)


def load_bank(folder: str, params) -> list:
    width, height = feed_size(params)
    paths = sorted(p for p in os.listdir(folder) if p.startswith(f'{CAMERA}_') and p.endswith('.png'))
    bank = [cv2.imread(os.path.join(folder, path), cv2.IMREAD_GRAYSCALE) for path in paths]
    if not bank or any(frame is None or frame.shape != (height, width) for frame in bank):
        raise SystemExit(f'no CAM {CAMERA} reference of {width}x{height} in {folder}')
    return [frame.astype(np.float32) for frame in bank]


def views_of_the_camera(frames: list) -> list:
    views, current = [], None
    for frame in frames:
        if frame.get('tablet_camera') != CAMERA:
            current = None
        elif frame.get('tablet_drive'):
            if current is None:
                current = []
                views.append(current)
            current.append(frame)
    return views


class RecordedScreen:
    def __init__(self, folder: str, params):
        self._folder = folder
        self._names = sorted(os.listdir(folder), key=frame_time)
        self._times = np.array([frame_time(name) for name in self._names])
        self._size = feed_size(params)
        self._view = params.view

    def at(self, t: float) -> np.ndarray:
        name = self._names[int(np.argmin(abs(self._times - t)))]
        gray = cv2.cvtColor(cv2.resize(cv2.imread(os.path.join(self._folder, name)), DESIGN_SIZE),
                            cv2.COLOR_BGR2GRAY)
        left, top, right, bottom = self._view
        return prepare(gray[top:bottom, left:right], self._size)


def read_the_looks(trace: str, bank: list, params) -> tuple:
    _header, frames, _events = recorder.load_trace(trace)
    screen = RecordedScreen(frames_folder(trace), params)
    mask = view_mask(params)
    noise = bank_noise(bank, mask, params) * params.noise_margin
    looks, last_look = [], None
    for view in views_of_the_camera(frames):
        seen, readings = [], []
        for frame in view:
            image = screen.at(frame['t'])
            reading = bank_reading(image, bank, mask, noise, params)
            if last_look:
                last_frames, closed_at = last_look
                since = bank_reading(image, last_frames, mask, noise, params).share
                reading = dataclasses.replace(reading, share_since_last_look=since,
                                              since_last_look_sec=frame['t'] - closed_at)
            seen.append(image)
            readings.append(reading)
        last_look = (spread_sample(seen, params.reference_frames), view[-1]['t'])
        looks.append(Look(view[0]['t'], bool(view[0]['door_left']), readings))
    return looks, noise


def drives_at(look: Look, recovery_sec: float, noise: float, params) -> list:
    adapted = dataclasses.replace(params, look_recovery_sec=recovery_sec)
    return [transduce(camera_spec(params), reading, noise, adapted) for reading in look.readings]


def escapes(engine: ConnectomeEngine, drives: list, frames: int) -> bool:
    escape = engine.neurons.outputs['looming_escape_left']
    engine.reset()
    for _ in range(SETTLE_FRAMES):
        engine.step(SensoryState(cam_inhib=TABLET_UP), 0.0)
    for index in range(frames):
        state = SensoryState(cam_inhib=TABLET_UP, tablet_drive=drives[index % len(drives)])
        if engine.step(state, 0.0)[0][escape].any():
            return True
    return False


def measure_look(engine, look: Look, recoveries: list, noise: float, args, params) -> list:
    cells = []
    for recovery in recoveries:
        drives = drives_at(look, recovery, noise, params)
        looms = [drive.get('loom_size_left', 0.0) for drive in drives]
        fired = sum(escapes(engine, drives, args.frames) for _ in range(args.trials))
        cells.append(f'{statistics.median(looms):.2f}/{max(looms):.2f} {fired}/{args.trials}')
    return cells


def recovery_label(recovery: float) -> str:
    return 'never' if recovery == NEVER else f'{recovery:g} s'


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Every look at CAM 1C of the recorded nights read again from the saved frames, with the '
                    'last look fading over each recovery time, and run through the engine with the tablet up '
                    'to count how often DNp04 fires. Needs nights played with run.py --frames.',
    )
    parser.add_argument('stamps', nargs='+', help='night stamps, as in logs/traces/trace_<stamp>.jsonl')
    parser.add_argument('--recovery', type=float, nargs='+', default=[NEVER, 20.0, 30.0])
    parser.add_argument('--frames', type=int, default=20)
    parser.add_argument('--trials', type=int, default=6)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    args = parser.parse_args()
    params = config.TABLET_VISION
    bank = load_bank(os.path.join(reference_store.ROOT, f'{DESIGN_SIZE[0]}x{DESIGN_SIZE[1]}', 'camera'), params)
    engine = ConnectomeEngine(args.device)
    engine.settle()

    print('loom median/max and DNp04 trials fired, last look fading over '
          + ', '.join(recovery_label(r) for r in args.recovery))
    for stamp in args.stamps:
        trace = os.path.join(recorder.TRACES_FOLDER, f'trace_{stamp}.jsonl')
        looks, noise = read_the_looks(trace, bank, params)
        for look in looks:
            cells = measure_look(engine, look, args.recovery, noise, args, params)
            door = 'shut' if look.door_shut else 'open'
            print(f'{stamp} {look.start:6.1f} s, door {door}   ' + ' | '.join(cells), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
