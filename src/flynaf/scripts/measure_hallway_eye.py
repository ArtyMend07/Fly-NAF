import argparse
import bisect
import glob
import json
import os
import re
import statistics

import cv2
import numpy as np

from flynaf import config, recorder
from flynaf.env import hallway_bank
from flynaf.env.frame_recorder import frame_time
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.hallway import LoomingEye
from flynaf.night.state import SensoryState

LOGS = os.path.join(config.PROJECT_ROOT, 'logs')
LOOMING_EYE = 'looming eye'
EYE_LEVELS = (0.05, 0.08, 0.12, 0.2, 0.3, 0.5, 1.0)
DETECTION = re.compile(r'seen_(left|right)(_closed)?_\d+_(\d+)\.png$')


def gray(path: str) -> np.ndarray:
    return cv2.imread(path, cv2.IMREAD_GRAYSCALE).astype(np.float32)


def looming_drive(side: str, share: float) -> dict:
    return LoomingEye().transduce(side, share, 0.0)


def outcome(drive: dict) -> str:
    if any(name.startswith('loom_size') for name in drive):
        return 'looming'
    return 'wide field' if drive else 'nothing'


def share_of(frame: np.ndarray, reference: np.ndarray) -> float:
    p = config.HALLWAY_VISION
    return hallway_bank.changed_share(frame, reference, p.view_scale, p.cell_pixels, p.cell_noise_mse)


def saved_detections(folder: str) -> list:
    rows = []
    for seen in sorted(glob.glob(os.path.join(folder, 'seen_*.png'))):
        match = DETECTION.search(os.path.basename(seen))
        reference = seen.replace('seen_', 'ref_')
        if match is None or not os.path.isfile(reference):
            continue
        side, closed, mse = match.group(1), bool(match.group(2)), int(match.group(3))
        share = share_of(gray(seen), gray(reference))
        rows.append({'image': os.path.basename(seen), 'side': side, 'closed': closed, 'mse': mse,
                     'share': round(share, 3), LOOMING_EYE: outcome(looming_drive(side, share))})
    return rows


def eye_box(side: str, closed: bool) -> tuple:
    calibration = config.VISION_CALIBRATION
    if closed:
        return getattr(calibration, f'{side}_window')
    x, y = getattr(calibration, f'{side}_target_x'), getattr(calibration, f'{side}_target_y')
    size = getattr(calibration, f'{side}_bbox_size')
    left, top = max(0, x - size // 2), max(0, y - size // 2)
    return left, top, left + size, top + size


def light_is_on(frame: np.ndarray, side: str) -> bool:
    motor, vision = config.MOTOR_CALIBRATION, config.VISION_DYNAMICS
    x, y = getattr(motor, f'{side}_light_button_x'), getattr(motor, f'{side}_light_button_y')
    half = vision.light_button_half_size
    return float(frame[y - half:y + half, x - half:x + half].mean()) > vision.light_button_lit_level


def load_banks(folder: str) -> dict:
    with open(os.path.join(folder, 'banks.json'), encoding='utf-8') as handle:
        counts = json.load(handle)
    return {name: [gray(os.path.join(folder, f'{name}_{i:02d}.png')) for i in range(count)]
            for name, count in counts.items()}


def office_frames(folder: str):
    trace = os.path.join(LOGS, 'traces', f'trace_{os.path.basename(folder)}.jsonl')
    if not os.path.isfile(trace):
        return
    _header, frames, _events = recorder.load_trace(trace)
    times = [frame['t'] for frame in frames]
    for path in sorted(glob.glob(os.path.join(folder, '*.jpg'))):
        t = frame_time(os.path.basename(path))
        recorded = frames[min(bisect.bisect_left(times, t), len(frames) - 1)]
        if recorded.get('camera_open') or recorded.get('tablet_camera') or abs(recorded['t'] - t) > 0.2:
            continue
        yield t, recorded, gray(path)


def lit_hallway(picture: np.ndarray, recorded: dict, side: str, banks: dict):
    if not light_is_on(picture, side):
        return None
    closed = bool(recorded.get(f'door_{side}'))
    left, top, right, bottom = eye_box(side, closed)
    patch = picture[top:bottom, left:right]
    bank = banks[f'{side}_closed' if closed else f'{side}_open']
    if patch.shape != bank[0].shape:
        return None
    mse, reference = hallway_bank.nearest(patch, bank)
    share = share_of(patch, reference)
    return {'side': side, 'closed': closed, 'mse': round(mse, 1), 'share': round(share, 3),
            LOOMING_EYE: outcome(looming_drive(side, share))}


def recorded_looks(frames_root: str, banks: dict) -> list:
    rows = []
    for folder in sorted(glob.glob(os.path.join(frames_root, '*'))):
        for t, recorded, picture in office_frames(folder):
            for side in ('left', 'right'):
                row = lit_hallway(picture, recorded, side, banks)
                if row is not None:
                    rows.append({'night': os.path.basename(folder), 't': t, **row})
    return rows


def first_left_answer(engine: ConnectomeEngine, drives: list, frames: int) -> tuple:
    first, crossed = None, 0
    for frame in range(1, frames + 1):
        drive = drives[min(frame - 1, len(drives) - 1)]
        spikes = engine.step(SensoryState(hallway_drive=drive), 0.0)[0]
        crossed += bool(spikes[engine.r_motor_idx].any())
        if first is None and spikes[engine.l_motor_idx].any():
            first = frame
    return first, crossed


def giant_fiber_answers(engine: ConnectomeEngine, cases: dict, frames: int, rest: int, trials: int) -> dict:
    quiet = SensoryState()
    answers = {}
    for label, drives in cases.items():
        latencies, crossed = [], 0
        for _ in range(trials):
            for _ in range(rest):
                engine.step(quiet, 0.0)
            first, wrong_side = first_left_answer(engine, drives, frames)
            crossed += wrong_side
            if first is not None:
                latencies.append(first)
        answers[label] = {'answered': f'{len(latencies)} of {trials}',
                          'median frame': statistics.median(latencies) if latencies else None,
                          'frames with the right DNp01': crossed}
    return answers


def sighting(share: float) -> list:
    eye = LoomingEye()
    step = 1.0 / config.SIMULATION_PARAMS.target_fps
    return [eye.transduce('left', share, i * step) for i in range(2)]


def print_rows(title: str, rows: list, keys: tuple):
    print(f'\n{title}')
    for row in rows:
        print('  ' + '  '.join(f'{key} {row[key]}' for key in keys))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='What the looming eye makes of every hallway the fly saw: the detections the threshold eye '
                    'saved in logs/vision_debug, the lit hallways of the nights recorded in logs/frames, and the '
                    'Giant Fiber answer to the levels Bonnie, Chica and a shadow produce.',
    )
    parser.add_argument('--trials', type=int, default=10)
    parser.add_argument('--frames', type=int, default=12)
    parser.add_argument('--rest', type=int, default=60)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    parser.add_argument('--out', default=os.path.join(LOGS, 'hallway_eye.json'))
    args = parser.parse_args()

    detections = saved_detections(os.path.join(LOGS, 'vision_debug'))
    print_rows('saved detections', detections, ('image', 'mse', 'share', LOOMING_EYE))
    banks = load_banks(os.path.join(LOGS, 'vision_reference', '1280x720', 'eye'))
    looks = recorded_looks(os.path.join(LOGS, 'frames'), banks)
    groups = {}
    for row in looks:
        key = (row['side'], row['closed'], row['mse'], row['share'], row[LOOMING_EYE])
        groups[key] = groups.get(key, 0) + 1
    print('\nlit hallways in the recorded nights, side, door shut, mse, share, looming eye: frames')
    for key, count in sorted(groups.items()):
        print(f'  {key}: {count}')

    engine = ConnectomeEngine(args.device)
    engine.settle()
    cases = {f'left eye cluster at {level}': [{'eye_left': level}] for level in EYE_LEVELS}
    cases |= {
        'threshold eye, any figure': [{'eye_left': 1.0, 'wide_field_left': 1.0}],
        'looming eye, Bonnie (0.22)': sighting(0.22),
        'looming eye, Chica (0.31)': sighting(0.31),
        'looming eye, shadow (0.13)': sighting(0.13),
        'looming eye, static (1.0)': sighting(1.0),
    }
    answers = giant_fiber_answers(engine, cases, args.frames, args.rest, args.trials)
    print('\nthe left Giant Fiber, settled network')
    for label, answer in answers.items():
        print(f'  {label:<30} {answer}')
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump({'detections': detections, 'recorded looks': looks, 'giant fiber': answers}, handle, indent=1)
    print(f'\nsaved to {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
