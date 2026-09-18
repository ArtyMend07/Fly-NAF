"""Shows, live, what the fly's eye is reporting and whether it would slam a door.

A night that logs zero door panics has two very different explanations: nothing
ever came to a door, or the eye never registered what did. The session report
cannot tell them apart. This can.

Run it with the game in the office, then hold a light on. The doorway is only
read while its light is on, exactly as in a real night, so a reading taken with
the light off means nothing.

    python src/scripts/debug_reflex.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

import config
from env.vision import FNAFVision


def main():
    vision = FNAFVision()
    threshold = config.FORAGING_PARAMS.mse_threshold

    if not vision.load_reference_from_disk():
        print('No saved eye references in logs/vision_reference.')
        print('Run a night once so calibration writes them, then come back.')
        return

    print(f'threat threshold (MSE): {threshold:.0f}')
    print(f'camera-up threshold   : {config.CAMERA_DETECTION.mse_trigger:.0f}')
    print('Capturing the camera-closed reference in 3s, stay in the office.')
    time.sleep(3.0)
    vision.capture_camera_closed_reference()
    print('Ready. Hold a light on and watch the side that is lit. Ctrl+C to stop.\n')
    print(f"{'left MSE':>10} {'right MSE':>10}  {'tablet':>8}   verdict")

    try:
        while True:
            left, _ = vision._get_peak_mse_from_buffer(vision.ref_left, vision._left_buf)
            right, _ = vision._get_peak_mse_from_buffer(vision.ref_right, vision._right_buf)
            up = vision.is_camera_up()

            verdict = []
            if left > threshold:
                verdict.append('LEFT would slam')
            if right > threshold:
                verdict.append('RIGHT would slam')
            if up:
                # This is the state that silences the giant fiber entirely.
                verdict.append('tablet reads UP: descending neurons inhibited')
            line = ', '.join(verdict) or 'clear'

            print(f'{left:>10.0f} {right:>10.0f}  {str(up):>8}   {line}')
            time.sleep(0.25)
    except KeyboardInterrupt:
        print('\nstopped')


if __name__ == '__main__':
    main()
