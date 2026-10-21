import argparse
import statistics

from flynaf import config
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.memory import DefensiveState
from flynaf.night.state import SensoryState
from flynaf.search_drive import SearchDrive

SIDES = ('left', 'right')
FIGURE_LEVELS = (0.05, 0.1, 0.25, 0.5, 1.0)
LOOM_LEVELS = (0.1, 0.25, 0.5, 1.0)
SIGHTINGS = (0.0, 0.25, 0.6, 1.0)


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


def leaning_after_a_sighting(engine: ConnectomeEngine, side: str, strength: float, seconds: float) -> tuple:
    engine.reset()
    defence = DefensiveState()
    if strength > 0.0:
        defence.threat(side, strength, 0.0)
    search = SearchDrive(engine.sensory_span)
    leaning_right, giant_fiber = 0, 0
    frames = int(seconds / engine.frame_dt)
    for frame in range(frames):
        now = frame * engine.frame_dt
        state = SensoryState(memory_drive=defence.drive(now))
        spikes = engine.step(state, now)[0]
        search.update(
            engine.eye_membrane_diff,
            int(spikes[engine.l_sensory_idx].sum()), int(spikes[engine.r_sensory_idx].sum()),
            engine.frame_dt, now, False,
        )
        leaning_right += search.leaning == 'right'
        giant_fiber += bool(spikes[engine.neurons.outputs[f'giant_fiber_{side}']].any())
    return leaning_right / frames, giant_fiber


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


def print_leaning(engine: ConnectomeEngine, seconds: float, trials: int):
    print(f'\ntablet down after a sighting, {trials} trials of {seconds:g}s, '
          f'share of frames the search drive leans right and frames the giant fiber fired')
    for side in SIDES:
        for strength in SIGHTINGS:
            runs = [leaning_after_a_sighting(engine, side, strength, seconds) for _ in range(trials)]
            shares = [share for share, _ in runs]
            fired = [count for _, count in runs]
            print(f'{side:<6} sighting {strength:.2f}   leans right median {statistics.median(shares):.2f} '
                  f'(min {min(shares):.2f}, max {max(shares):.2f})   giant fiber frames median '
                  f'{statistics.median(fired):g}', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='The tablet channels on both sides and where a sighting turns the search drive, '
                    'measured on the running engine.',
    )
    parser.add_argument('--frames', type=int, default=40)
    parser.add_argument('--trials', type=int, default=8)
    parser.add_argument('--seconds', type=float, default=10.0)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    parser.add_argument('--skip-tablet', action='store_true')
    args = parser.parse_args()

    engine = ConnectomeEngine(args.device)
    if not args.skip_tablet:
        print_tablet_tables(engine, args.frames, args.trials)
    print_leaning(engine, args.seconds, args.trials)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
