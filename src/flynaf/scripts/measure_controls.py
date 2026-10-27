import argparse
import json
import os
import statistics
import time

from flynaf import config, recorder
from flynaf.controls import (
    CONDITIONS,
    SIDES,
    eyes_swapped,
    inhibitors_cut,
    readouts,
    shuffled,
)
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState
from flynaf.replay import replay
from flynaf.search_drive import ExploreDrive


def first_spikes(engine: ConnectomeEngine, fields: dict, frames: int) -> dict:
    engine.reset()
    state = SensoryState(**fields)
    watched = readouts(engine)
    first = dict.fromkeys(watched)
    for frame in range(1, frames + 1):
        spikes = engine.step(state, frame * engine.frame_dt)[0]
        for name, indices in watched.items():
            if first[name] is None and spikes[indices].any():
                first[name] = frame
    return first


def stimulus_table(engine: ConnectomeEngine, frames: int, trials: int) -> dict:
    table = {}
    for label, fields in CONDITIONS:
        runs = [first_spikes(engine, fields, frames) for _ in range(trials)]
        table[label] = {}
        for name in runs[0]:
            hits = [run[name] for run in runs if run[name] is not None]
            table[label][name] = [len(hits), statistics.median(hits) if hits else None]
    return table


class NightWatch:
    def __init__(self):
        self.drive = ExploreDrive()
        self.raises = 0
        self.answers = {'own side first': 0, 'other side first': 0, 'both at once': 0, 'unanswered': 0}
        self._wanted = False
        self._runs = {side: None for side in SIDES}

    def __call__(self, engine, recorded, spikes):
        fired = {'left': bool(spikes[0, engine.l_motor_idx].any()),
                 'right': bool(spikes[0, engine.r_motor_idx].any())}
        for side, other in (('left', 'right'), ('right', 'left')):
            self._follow_the_run(side, other, getattr(recorded, f'{side}_rate') > 0.0, fired)
        self._count_raises(engine, recorded, spikes)

    def _follow_the_run(self, side: str, other: str, driven: bool, fired: dict):
        run = self._runs[side]
        if not driven:
            if run == 'open':
                self.answers['unanswered'] += 1
            self._runs[side] = None
            return
        if run not in (None, 'open'):
            return
        if fired[side] and fired[other]:
            self.answers['both at once'] += 1
        elif fired[side]:
            self.answers['own side first'] += 1
        elif fired[other]:
            self.answers['other side first'] += 1
        else:
            self._runs[side] = 'open'
            return
        self._runs[side] = 'answered'

    def _count_raises(self, engine, recorded, spikes):
        if recorded.camera_open:
            self._wanted = False
            return
        self.drive.update(engine.explore_membrane, bool(spikes[0, engine.explore_idx].any()), recorded.arousal)
        wanted = self.drive.wants_monitor
        self.raises += wanted and not self._wanted
        self._wanted = wanted


def night_replay(engine: ConnectomeEngine, trace: str) -> dict:
    watch = NightWatch()
    result = replay(trace, watch=watch, engine=engine)
    latencies = result['reflex_latency_frames']
    return {
        **{f'hallway threats, {name}': count for name, count in watch.answers.items()},
        'median reflex latency (frames)': statistics.median(latencies) if latencies else None,
        'frames with a DNp01 spike': result['gf_left_spikes'] + result['gf_right_spikes'],
        'idle frames with a DNp01 spike': result['idle_false_alarms'],
        'tablet-feed frames DNp04 answered': result['tablet_escape_frames'],
        'tablet-feed frames DNp09 answered': result['tablet_explore_frames'],
        'tablet raises the DNp09 drive asked for': watch.raises,
        'idle frames': result['idle_frames'],
        'tablet-feed frames': result['tablet_frames'],
    }


def measure(label: str, rewire, swapped: bool, args) -> dict:
    started = time.perf_counter()
    engine = ConnectomeEngine(args.device, rewire=rewire)
    if swapped:
        engine.neurons = eyes_swapped(engine.neurons)
    table = stimulus_table(engine, args.frames, args.trials)
    night = night_replay(engine, args.trace)
    print(f'{label}: measured in {time.perf_counter() - started:.0f}s', flush=True)
    return {'brain': label, 'stimuli': table, 'night': night}


def cell(hits: int, latency) -> str:
    return f'{hits} @ {"-" if latency is None else f"{latency:g}"}'


def print_tables(results: list, trials: int):
    names = list(results[0]['stimuli'][CONDITIONS[0][0]])
    for result in results:
        print(f'\n{result["brain"]}, trials out of {trials} in which each readout fired, '
              f'@ the median first-spike frame')
        print(f'{"condition":<26}' + ''.join(f'{name:>10}' for name in names))
        for label, row in result['stimuli'].items():
            print(f'{label:<26}' + ''.join(f'{cell(*row[name]):>10}' for name in names))
    print('\nthe recorded night replayed')
    print(f'{"":<42}' + ''.join(f'{result["brain"]:>16}' for result in results))
    for key in results[0]['night']:
        print(f'{key:<42}' + ''.join(f'{str(result["night"][key]):>16}' for result in results))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='The same stimuli and the same recorded night run through the FlyWire brain and through '
                    'controls: shuffles that keep every neuron\'s in-degree, out-degree and outgoing weights '
                    'but send each connection to a random target, the eyes swapped left for right, and the '
                    'camera inhibitors with their outgoing synapses cut.',
    )
    parser.add_argument('--trace', default=None)
    parser.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2])
    parser.add_argument('--frames', type=int, default=40)
    parser.add_argument('--trials', type=int, default=8)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    parser.add_argument('--out', default=os.path.join(config.PROJECT_ROOT, 'logs', 'controls.json'))
    args = parser.parse_args()
    args.trace = args.trace or recorder.latest_trace()
    print(f'replaying {os.path.basename(args.trace)}', flush=True)

    brains = [('FlyWire', None, False)]
    brains += [(f'shuffle {seed}', shuffled(seed), False) for seed in args.seeds]
    brains += [('eyes swapped', None, True), ('inhibitors cut', inhibitors_cut, False)]
    results = [measure(label, rewire, swapped, args) for label, rewire, swapped in brains]
    print_tables(results, args.trials)
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump({'trace': os.path.basename(args.trace), 'trials': args.trials, 'frames': args.frames,
                   'results': results}, handle, indent=1)
    print(f'\nsaved to {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
