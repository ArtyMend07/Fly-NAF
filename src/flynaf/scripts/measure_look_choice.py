import argparse
import json
import os
import statistics
import time

from flynaf import config
from flynaf.controls import SIDES, shuffled, unwired
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.memory import OrientationMemory
from flynaf.night.state import SensoryState
from flynaf.night.tasks import read_spikes, recall_the_hallway
from flynaf.search_drive import SearchDrive


class LookLoop:
    def __init__(self, engine: ConnectomeEngine):
        self.engine = engine
        self.search = SearchDrive(engine.sensory_span)
        self.orientation = OrientationMemory()
        self.state = SensoryState()
        self.frame = 0
        self.ready_at = 0.0

    @property
    def now(self) -> float:
        return self.frame * self.engine.frame_dt

    def step(self, can_look: bool):
        engine, state = self.engine, self.state
        spikes = engine.step(state, self.now)
        read_spikes(engine, spikes, state)
        recall_the_hallway(self.orientation, state, self.now)
        wants = self.search.update(
            engine.eye_membrane_diff, state.l_sensory_count, state.r_sensory_count,
            engine.frame_dt, self.now, can_look and self.now >= self.ready_at, state.recalled,
        )
        self.frame += 1
        return wants, spikes

    def look(self, side: str, sighted: bool) -> bool:
        foraging = config.FORAGING_PARAMS
        fps = config.SIMULATION_PARAMS.target_fps
        for _ in range(round(foraging.light_activation_settle_sec * fps)):
            self.step(False)
        motor = self.engine.l_motor_idx if side == 'left' else self.engine.r_motor_idx
        fired = False
        setattr(self.state, f'{side}_rate', 1.0 if sighted else 0.0)
        for _ in range(foraging.light_inspection_frames if sighted else foraging.light_quiet_frames):
            _, spikes = self.step(False)
            if sighted and bool(spikes[0, motor].any()):
                fired = True
                break
        setattr(self.state, f'{side}_rate', 0.0)
        self.ready_at = self.now + foraging.saccade_refractory_sec
        return fired

    def next_look(self, limit_frames: int) -> tuple:
        started = self.now
        for _ in range(limit_frames):
            wants, _ = self.step(True)
            if wants is not None:
                return wants, self.search.reason, self.now - started
        return None, None, self.now - started


def idle_looks(loop: LookLoop, frames: int) -> list:
    looks, end = [], loop.frame + frames
    while loop.frame < end:
        side, reason, waited = loop.next_look(end - loop.frame)
        if side is None:
            break
        looks.append({'side': side, 'reason': reason, 'waited_sec': round(waited, 2)})
        loop.look(side, sighted=False)
    return looks


def looks_after_a_sighting(loop: LookLoop, trials: int, limit_frames: int) -> list:
    answers = []
    for trial in range(trials):
        sighted = SIDES[trial % 2]
        while loop.now < loop.ready_at:
            loop.step(False)
        fired = loop.look(sighted, sighted=True)
        side, reason, waited = loop.next_look(limit_frames)
        answers.append({'sighted': sighted, 'giant_fiber': fired, 'next': side, 'reason': reason,
                        'waited_sec': round(waited, 2)})
        if side is not None:
            loop.look(side, sighted=False)
    return answers


def summary(idle: list, sightings: list) -> dict:
    sides = [look['side'] for look in idle]
    switches = sum(a != b for a, b in zip(sides, sides[1:]))
    reasons = {reason: sum(look['reason'] == reason for look in idle)
               for reason in ('drift', 'evidence', 'memory', 'guard')}
    looked = [answer for answer in sightings if answer['next'] is not None]
    returned = sum(answer['next'] == answer['sighted'] for answer in looked)
    return {
        'idle looks': len(idle),
        'idle looks to the left': sides.count('left'),
        'idle side switches': f'{switches} of {max(0, len(sides) - 1)}',
        'idle median wait (s)': statistics.median([look['waited_sec'] for look in idle]) if idle else None,
        **{f'idle looks by {reason}': count for reason, count in reasons.items()},
        'sightings answered by the giant fiber': sum(answer['giant_fiber'] for answer in sightings),
        'next look back to the sighted side': f'{returned} of {len(looked)}',
        'next look median wait (s)': statistics.median([a['waited_sec'] for a in looked]) if looked else None,
        'next looks by guard': sum(answer['reason'] == 'guard' for answer in looked),
    }


def measure(label: str, rewire, args) -> dict:
    started = time.perf_counter()
    engine = ConnectomeEngine(args.device, rewire=rewire)
    engine.settle()
    loop = LookLoop(engine)
    idle = idle_looks(loop, args.idle_frames)
    sightings = looks_after_a_sighting(loop, args.sightings, args.limit_frames)
    print(f'{label}: measured in {time.perf_counter() - started:.0f}s', flush=True)
    return {'brain': label, 'summary': summary(idle, sightings), 'idle': idle, 'sightings': sightings}


def print_table(results: list):
    print(f'\n{"":<40}' + ''.join(f'{result["brain"]:>14}' for result in results))
    for key in results[0]['summary']:
        print(f'{key:<40}' + ''.join(f'{str(result["summary"][key]):>14}' for result in results))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Where the search drive sends the light when nothing is in either hallway, and where it '
                    'sends it after a sighting, on the FlyWire brain, on shuffled wiring and on a brain with '
                    'every synapse removed, whose only activity is the subliminal noise and the eye input.',
    )
    parser.add_argument('--seeds', type=int, nargs='+', default=[0])
    parser.add_argument('--idle-frames', type=int, default=3000)
    parser.add_argument('--sightings', type=int, default=24)
    parser.add_argument('--limit-frames', type=int, default=600)
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    parser.add_argument('--out', default=os.path.join(config.PROJECT_ROOT, 'logs', 'look_choice.json'))
    args = parser.parse_args()

    brains = [('FlyWire', None)]
    brains += [(f'shuffle {seed}', shuffled(seed)) for seed in args.seeds]
    brains += [('unwired', unwired)]
    results = [measure(label, rewire, args) for label, rewire in brains]
    print_table(results)
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump({'idle_frames': args.idle_frames, 'sightings': args.sightings, 'results': results},
                  handle, indent=1)
    print(f'\nsaved to {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
