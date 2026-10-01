import argparse
import json
import logging
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import recorder

_log = logging.getLogger(__name__)


class FrameInput:
    def __init__(self, payload: dict):
        self.left_rate = float(payload.get('left_rate', 0.0))
        self.right_rate = float(payload.get('right_rate', 0.0))
        self.cam_inhib = float(payload.get('cam_inhib', 0.0))
        self.tablet_drive = dict(payload.get('tablet_drive') or {})
        self.recorded_gf_left = bool(payload.get('gf_left', False))
        self.recorded_gf_right = bool(payload.get('gf_right', False))
        self.t = float(payload.get('t', 0.0))


def _reflex_latencies(driven: list) -> list:
    latencies, run, answered = [], 0, False
    for is_driven, fired in driven:
        if is_driven:
            run += 1
            if fired and not answered:
                latencies.append(run)
                answered = True
        else:
            run, answered = 0, False
    return latencies


def replay(trace_path: str, device: str = 'cpu') -> dict:
    from brain_adapter import BrainAdapter
    from night.engine import ConnectomeEngine
    from night.state import SensoryState

    header, frames, _events = recorder.load_trace(trace_path)
    if not frames:
        raise SystemExit('the trace has no frames in it: %s' % trace_path)

    _log.info('replaying %d frames from %s', len(frames), os.path.basename(trace_path))
    engine = ConnectomeEngine(device)
    state = SensoryState()

    left_driven, right_driven = [], []
    gf_left_total = gf_right_total = 0
    idle_frames = idle_spikes = 0
    tablet_frames = tablet_escapes = tablet_pursuits = 0

    for payload in frames:
        recorded = FrameInput(payload)
        state.left_rate = recorded.left_rate
        state.right_rate = recorded.right_rate
        state.cam_inhib = recorded.cam_inhib
        state.tablet_drive = recorded.tablet_drive

        spikes = engine.step(state, recorded.t)
        fired_left = bool(spikes[0, engine.l_motor_idx].any())
        fired_right = bool(spikes[0, engine.r_motor_idx].any())
        if recorded.tablet_drive:
            tablet_frames += 1
            tablet_escapes += int(bool(spikes[0, engine.l_escape_idx].any() or spikes[0, engine.r_escape_idx].any()))
            tablet_pursuits += int(bool(spikes[0, engine.explore_idx].any()))

        gf_left_total += int(fired_left)
        gf_right_total += int(fired_right)
        left_driven.append((recorded.left_rate > 0.0, fired_left))
        right_driven.append((recorded.right_rate > 0.0, fired_right))

        if recorded.left_rate == 0.0 and recorded.right_rate == 0.0:
            idle_frames += 1
            idle_spikes += int(fired_left or fired_right)

    latencies = _reflex_latencies(left_driven) + _reflex_latencies(right_driven)
    return {
        'trace': os.path.basename(trace_path),
        'recorded_at': header.get('recorded_at', 'unknown'),
        'settings': header.get('settings', {}),
        'frames': len(frames),
        'left_driven_frames': sum(1 for driven, _ in left_driven if driven),
        'right_driven_frames': sum(1 for driven, _ in right_driven if driven),
        'gf_left_spikes': gf_left_total,
        'gf_right_spikes': gf_right_total,
        'reflex_answers': len(latencies),
        'reflex_latency_frames': sorted(latencies),
        'idle_frames': idle_frames,
        'idle_false_alarms': idle_spikes,
        'tablet_frames': tablet_frames,
        'tablet_escape_frames': tablet_escapes,
        'tablet_explore_frames': tablet_pursuits,
    }


def report(result: dict) -> str:
    lines = [
        '=== Connectome Replay Report ===',
        'Trace                        : %s' % result['trace'],
        'Recorded at                  : %s' % result['recorded_at'],
        'Frames replayed              : %d' % result['frames'],
        '',
        '--- Input as recorded ---',
        'Frames driving the left eye  : %d' % result['left_driven_frames'],
        'Frames driving the right eye : %d' % result['right_driven_frames'],
        '',
        '--- What the giant fibers did this time ---',
        'DNp01 left spikes            : %d' % result['gf_left_spikes'],
        'DNp01 right spikes           : %d' % result['gf_right_spikes'],
        'Threats answered             : %d' % result['reflex_answers'],
    ]
    latencies = result['reflex_latency_frames']
    if latencies:
        lines.append(
            'Reflex latency (frames)      : median %.0f, min %d, max %d'
            % (statistics.median(latencies), latencies[0], latencies[-1])
        )
    lines += [
        'Idle frames                  : %d' % result['idle_frames'],
        'Spikes with nothing on screen: %d' % result['idle_false_alarms'],
        '',
        '--- What the tablet feed drove ---',
        'Frames with the feed driving : %d' % result.get('tablet_frames', 0),
        'Frames DNp04 answered        : %d' % result.get('tablet_escape_frames', 0),
        'Frames DNp09 answered        : %d' % result.get('tablet_explore_frames', 0),
        '',
        '--- How to read this ---',
        'The simulation is driven stochastically on purpose, so this run does not match the',
        'recorded one number for number and is not supposed to. What holds across runs is',
        'the shape: the giant fiber answers while its own eye is driven, it stays quiet on',
        'idle frames, and the latency lands in the seven to nine frame band ADR 0013',
        'measured. A run that breaks those is a real failure. A run that differs by a few',
        'spikes is the fly being a fly.',
    ]
    settings = result.get('settings') or {}
    if settings:
        lines.append('')
        lines.append('--- Settings the trace was recorded with ---')
        for name in sorted(settings):
            lines.append('%-29s: %s' % (name, settings[name]))
    return '\n'.join(lines)


def export_for_panel(trace_path: str, out_path: str) -> str:
    header, frames, events = recorder.load_trace(trace_path)
    payload = {
        'header': header,
        'frames': frames,
        'events': events,
    }
    with open(out_path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, separators=(',', ':'))
    return out_path


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    parser = argparse.ArgumentParser(
        description='Replay a recorded night through the real connectome, without the game.',
    )
    parser.add_argument('trace', help='path to a trace written by a run')
    parser.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    parser.add_argument('--export', metavar='PATH', help='write the trace as JSON for the panel')
    args = parser.parse_args()

    if args.export:
        path = export_for_panel(args.trace, args.export)
        print('panel data written to %s' % path)
        return

    result = replay(args.trace, args.device)
    text = report(result)
    print(text)

    folder = os.path.join(config.PROJECT_ROOT, 'logs')
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, 'replay_report.txt')
    with open(out, 'w', encoding='utf-8') as handle:
        handle.write(text + '\n')
    print('\nsaved to %s' % out)


if __name__ == '__main__':
    main()
