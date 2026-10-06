import argparse
import statistics

from flynaf import config
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState

READOUTS = ('giant_fiber_left', 'looming_escape_left', 'explore')
LEVELS = (0.1, 0.25, 0.5, 1.0)


def conditions() -> list:
    rate = config.SIMULATION_PARAMS.base_sensory_rate_hz
    rows = [
        ('idle, tablet down', {}, 0.0, 0.0),
        ('idle, tablet up', {}, rate, 0.0),
        ('hallway eye, tablet down', {}, 0.0, 1.0),
    ]
    for level in LEVELS:
        rows.append((f'loom {level:.2f}, tablet up',
                     {'loom_size_left': level, 'loom_speed_left': level}, rate, 0.0))
    for level in LEVELS:
        rows.append((f'loom {level:.2f}, tablet down',
                     {'loom_size_left': level, 'loom_speed_left': level}, 0.0, 0.0))
    for level in LEVELS:
        rows.append((f'figure {level:.2f}, tablet up', {'figure_left': level}, rate, 0.0))
    return rows


def trial(engine: ConnectomeEngine, state: SensoryState, frames: int) -> dict:
    engine.reset()
    first = dict.fromkeys(READOUTS)
    for frame in range(1, frames + 1):
        spikes = engine.step(state, 0.0)[0]
        for name in READOUTS:
            if first[name] is None and spikes[engine.neurons.outputs[name]].any():
                first[name] = frame
    return first


def measure(engine: ConnectomeEngine, drive: dict, inhibitors_hz: float, eye: float,
            frames: int, trials: int) -> dict:
    state = SensoryState(left_rate=eye, cam_inhib=inhibitors_hz, tablet_drive=drive)
    results = [trial(engine, state, frames) for _ in range(trials)]
    summary = {}
    for name in READOUTS:
        hits = [result[name] for result in results if result[name] is not None]
        latency = statistics.median(hits) if hits else None
        summary[name] = (len(hits), latency)
    return summary


def cell(hits: int, latency, trials: int) -> str:
    shown = '-' if latency is None else f'{latency:g}'
    return f'{hits}/{trials} @ {shown}'


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Which descending neuron answers each tablet channel, measured on the running engine.',
    )
    parser.add_argument('--frames', type=int, default=40)
    parser.add_argument('--trials', type=int, default=6)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    args = parser.parse_args()

    engine = ConnectomeEngine(args.device)
    print('populations:', ', '.join(f'{k} {v}' for k, v in engine.neurons.sizes().items()))
    print(f'{args.trials} trials of {args.frames} frames each, cell shows trials answered '
          f'and median first-spike frame\n')
    header = f'{"condition":<28}' + ''.join(f'{name:>24}' for name in READOUTS)
    print(header)
    for label, drive, inhibitors_hz, eye in conditions():
        summary = measure(engine, drive, inhibitors_hz, eye, args.frames, args.trials)
        cells = ''.join(f'{cell(*summary[name], args.trials):>24}' for name in READOUTS)
        print(f'{label:<28}{cells}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
