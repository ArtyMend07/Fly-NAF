import json
import os

import cv2
import numpy as np

from flynaf import config
from flynaf.audit import hud
from flynaf.env import anchor, hallway_bank, reference_store

EYE_FOLDER = os.path.join(reference_store.ROOT, f'{anchor.DESIGN_WIDTH}x{anchor.DESIGN_HEIGHT}', 'eye')
SIDES = ('left', 'right')


def closed_door_references(folder: str = EYE_FOLDER) -> dict:
    index = os.path.join(folder, 'banks.json')
    if not os.path.isfile(index):
        return {}
    with open(index, encoding='utf-8') as handle:
        counts = json.load(handle)
    references = {}
    for side in SIDES:
        name = f'{side}_closed'
        frames = [cv2.imread(os.path.join(folder, f'{name}_{i:02d}.png'), cv2.IMREAD_GRAYSCALE)
                  for i in range(counts.get(name, 0))]
        if frames and all(frame is not None for frame in frames):
            references[side] = [frame.astype(np.float32) for frame in frames]
    return references


def someone_at_the_window(frame: np.ndarray, side: str, references: dict) -> bool | None:
    bank = references.get(side)
    if not bank or not hud.light_on(frame, side):
        return None
    left, top, right, bottom = getattr(config.VISION_CALIBRATION, f'{side}_window')
    window = cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2GRAY).astype(np.float32)
    distance, _reference = hallway_bank.nearest(window, bank)
    return distance > config.FORAGING_PARAMS.closed_door_mse_threshold
