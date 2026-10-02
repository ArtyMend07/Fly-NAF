import argparse
import time

from flynaf import config
from flynaf.env.input_controller import FNAFController, start_worker
from flynaf.env.overlay import anchor_to_game
from flynaf.env.vision import FNAFVision


def sample_window(vision: FNAFVision, side: str, seconds: float) -> list:
    readings = []
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        seen = vision.evidence(side, door_closed=True)
        if seen is not None:
            readings.append(seen[0])
        time.sleep(0.1)
    return readings


def measure(side: str, seconds: float) -> list:
    controller = FNAFController()
    settle = config.FORAGING_PARAMS.light_activation_settle_sec + config.DOOR_DYNAMICS.motion_settle_sec
    light = getattr(controller, f'set_{side}_light')
    vision = FNAFVision()
    if not vision.load_reference_from_disk():
        return []

    getattr(controller, f'trigger_{side}_door')().wait(6.0)
    time.sleep(settle)
    light(True).wait(6.0)
    time.sleep(settle)
    readings = sample_window(vision, side, seconds)
    light(False).wait(6.0)
    getattr(controller, f'open_{side}_door')().wait(6.0)
    return readings


def summary(readings: list) -> str:
    ordered = sorted(readings)
    return (f'{len(ordered)} readings, min {ordered[0]:.0f}, '
            f'median {ordered[len(ordered) // 2]:.0f}, peak {ordered[-1]:.0f}')


def main():
    parser = argparse.ArgumentParser(
        description='Close one door, light its window and report how far the window strays from '
                    'the nearest closed-door view calibrated at midnight. Run it once with the hallway empty and once with '
                    'Bonnie or Chica outside, then set closed_door_mse_threshold between the two.',
    )
    parser.add_argument('side', choices=('left', 'right'))
    parser.add_argument('--seconds', type=float, default=5.0)
    args = parser.parse_args()

    anchor_to_game()
    start_worker()
    print(f'measuring the {args.side} window in 3s, leave the game in front')
    time.sleep(3.0)
    readings = measure(args.side, args.seconds)
    if not readings:
        print('no closed-door references in logs/vision_reference, run one night first so the '
              'live calibration captures them')
        return

    threshold = config.FORAGING_PARAMS.closed_door_mse_threshold
    print(f'{args.side} window behind the closed door: {summary(readings)}')
    print(f'closed_door_mse_threshold is {threshold:.0f}, '
          f'{sum(1 for mse in readings if mse > threshold)} readings above it')


if __name__ == '__main__':
    main()
