import argparse
import statistics

from flynaf import config
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState

SIDES = ('left', 'right')
FIGURE_LEVELS = (0.05, 0.1, 0.25, 0.5, 1.0)
LOOM_LEVELS = (0.1, 0.25, 0.5, 1.0)


def readouts(engine: ConnectomeEngine) -> dict:
    outputs = engine.neurons.outputs
    return {
        f'{name} {side[0].upper()}': outputs[f'{role}_{side}']
        for side in SIDES
        for name, role in (('DNp01', 'giant_fiber'), ('DNp04', 'looming_escape'), ('DNp09', 'explore'))
    }


def tablet_conditions(side: str) -> list:
    rows = [('nothing on screen', {})]
    rows += [(f'figure {side} {level:.2f}', {f'figure_{side}': level}) for level in FIGURE_LEVELS]
    rows += [(f'loom {side} {level:.2f}', {f'loom_size_{side}': level, f'loom_speed_{side}': level})
             for level in LOOM_LEVELS]
    return rows


def first_spikes(engine: ConnectomeEngine, state: SensoryState, frames: int, watched: dict) -> dict:
    engine.reset()
    first = dict.fromkeys(watched)
    for frame in range(1, frames + 1):
        spikes = engine.step(state, 0.0)[0]
        for name, indices in watched.items():
            if first[name] is None and spikes[indices].any():
                first[name] = frame
    return first


def tablet_row(engine: ConnectomeEngine, drive: dict, frames: int, trials: int) -> dict:
    watched = readouts(engine)
    state = SensoryState(cam_inhib=config.SIMULATION_PARAMS.base_sensory_rate_hz, tablet_drive=drive)
    runs = [first_spikes(engine, state, frames, watched) for _ in range(trials)]
    summary = {}
    for name in watched:
        hits = [run[name] for run in runs if run[name] is not None]
        summary[name] = (len(hits), statistics.median(hits) if hits else None)
    return summary


def cell(hits: int, latency, trials: int) -> str:
    shown = '-' if latency is None else f'{latency:g}'
    return f'{hits}/{trials} @ {shown}'


def print_tablet_tables(engine: ConnectomeEngine, frames: int, trials: int):
    names = list(readouts(engine))
    for side in SIDES:
        print(f'\ntablet up, {side} channels, {trials} trials of {frames} frames, '
              f'trials answered and median first-spike frame')
        print(f'{"condition":<22}' + ''.join(f'{name:>12}' for name in names))
        for label, drive in tablet_conditions(side):
            summary = tablet_row(engine, drive, frames, trials)
            print(f'{label:<22}' + ''.join(f'{cell(*summary[name], trials):>12}' for name in names),
                  flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='The tablet channels on both sides, measured on the running engine.',
    )
    parser.add_argument('--frames', type=int, default=40)
    parser.add_argument('--trials', type=int, default=8)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    args = parser.parse_args()

    engine = ConnectomeEngine(args.device)
    print_tablet_tables(engine, args.frames, args.trials)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
