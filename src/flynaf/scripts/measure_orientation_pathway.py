import argparse
import statistics

from flynaf import config
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState

SIDES = ('left', 'right')
SETTLE_FRAMES = 30
SIGHTING_MAX_FRAMES = 12
WINDOW_FRAMES = 16


def ring_counts(engine: ConnectomeEngine, spikes) -> dict:
    frame = spikes[0]
    return {side: float(frame[engine.neurons.outputs[f'orientation_{side}']].sum().item())
            for side in SIDES}


def resting(engine: ConnectomeEngine, state: SensoryState, frames: int) -> dict:
    engine.reset()
    for _ in range(SETTLE_FRAMES):
        engine.step(state, 0.0)
    counts = {side: [] for side in SIDES}
    for _ in range(frames):
        for side, count in ring_counts(engine, engine.step(state, 0.0)).items():
            counts[side].append(count)
    return counts


def sighting(engine: ConnectomeEngine, side: str) -> tuple:
    engine.reset()
    quiet = SensoryState()
    for _ in range(SETTLE_FRAMES):
        engine.step(quiet, 0.0)
    seen = SensoryState(**{f'{side}_rate': 1.0})
    giant_fiber = engine.neurons.outputs[f'giant_fiber_{side}']
    totals, answered_at = dict.fromkeys(SIDES, 0.0), None
    for frame in range(1, WINDOW_FRAMES + 1):
        driving = answered_at is None and frame <= SIGHTING_MAX_FRAMES
        spikes = engine.step(seen if driving else quiet, 0.0)
        if driving and spikes[0][giant_fiber].any():
            answered_at = frame
        for ring, count in ring_counts(engine, spikes).items():
            totals[ring] += count
    return totals, answered_at


def describe(values: list) -> str:
    return f'{statistics.mean(values):.3f} (variance {statistics.pvariance(values):.3f})'


def report_resting(engine: ConnectomeEngine, frames: int):
    rate = config.SIMULATION_PARAMS.base_sensory_rate_hz
    for label, state in (('tablet down', SensoryState()), ('tablet up', SensoryState(cam_inhib=rate))):
        counts = resting(engine, state, frames)
        cells = ', '.join(f'{side} {describe(counts[side])}' for side in SIDES)
        print(f'ring spikes per frame at rest, {label}: {cells}', flush=True)


def report_sightings(engine: ConnectomeEngine, trials: int):
    for side in SIDES:
        runs = [sighting(engine, side) for _ in range(trials)]
        same = [totals[side] for totals, _ in runs]
        other = [totals[ring] for totals, _ in runs for ring in SIDES if ring != side]
        latencies = [at for _, at in runs if at is not None]
        print(f'{side} sighting: {statistics.mean(same):.1f} +- {statistics.pstdev(same):.1f} ring spikes '
              f'on that side (min {min(same):.0f}), {statistics.mean(other):.1f} on the other, '
              f'giant fiber answered {len(latencies)}/{trials} at frame '
              f'{statistics.median(latencies) if latencies else "-"}', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='How the ER3d and ER3p ring neurons answer a hallway sighting through MeTu4, '
                    'measured on the running engine.',
    )
    parser.add_argument('--rest-frames', type=int, default=800)
    parser.add_argument('--trials', type=int, default=16)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    args = parser.parse_args()

    engine = ConnectomeEngine(args.device)
    sizes = engine.neurons.sizes()
    print('populations:', ', '.join(
        f'{name} {sizes[name]}' for name in sorted(sizes) if name.startswith(('wide_field', 'orientation'))
    ))
    print(f'a sighting drives the eye and MeTu4 of one side until the giant fiber answers, '
          f'at most {SIGHTING_MAX_FRAMES} frames, and counts ring spikes over {WINDOW_FRAMES} frames\n')
    report_resting(engine, args.rest_frames)
    report_sightings(engine, args.trials)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
