import argparse
import functools
import http.server
import json
import os
import shutil
import tempfile
import webbrowser
from datetime import date

from flynaf import config

EXAMPLES_DIR = os.path.join(config.PROJECT_ROOT, 'examples')
EXAMPLE_TRACE = os.path.join(EXAMPLES_DIR, 'night-3.jsonl')
RECORDING_DIR = os.path.join(EXAMPLES_DIR, 'night-3-page')
RECORDING_FILES = ('night.json', 'spikes.bin')
PAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env')
LIVE_TITLE = '<title>Connectome Live Activity</title>'
REPLAY_TITLE = '<title>Fly-NAF Night 3</title>\n<script src="player.js"></script>'
ROW_KEYS = (
    't', 'in_l', 'in_r', 'mse_l', 'mse_r', 'eye_l', 'eye_r', 'gf_l', 'gf_r', 'door_l', 'door_r', 'camera', 'cam',
    'figure', 'loom', 'recall_l', 'recall_r', 'dnp09', 'dnp04_l', 'dnp04_r',
)
OUTCOME = 'replayed from the recorded input, so no door moves here'


def _varint(value: int, out: bytearray):
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)


def encode_spikes(frames: list) -> bytes:
    out = bytearray()
    _varint(len(frames), out)
    for indices in frames:
        _varint(len(indices), out)
        previous = 0
        for index in sorted(int(i) for i in indices):
            _varint(index - previous, out)
            previous = index
    return bytes(out)


def decode_spikes(data: bytes) -> list:
    position = 0

    def read() -> int:
        nonlocal position
        value, shift = 0, 0
        while True:
            byte = data[position]
            position += 1
            value |= (byte & 0x7F) << shift
            shift += 7
            if byte < 0x80:
                return value

    frames = []
    for _ in range(read()):
        indices, previous = [], 0
        for _ in range(read()):
            previous += read()
            indices.append(previous)
        frames.append(indices)
    return frames


def _strongest(drive: dict, prefix: str) -> float:
    return round(max((level for name, level in drive.items() if name.startswith(prefix)), default=0.0), 3)


class NightRecording:
    def __init__(self):
        from flynaf.night.memory import OrientationMemory
        from flynaf.night.state import SensoryState
        self.rows, self.spikes, self.cascades = [], [], []
        self._memory = OrientationMemory()
        self._state = SensoryState()
        self._answered = {'left': False, 'right': False}
        self._feed = None

    def __call__(self, engine, recorded, spikes):
        from flynaf.night.tasks import read_spikes, recall_the_hallway
        if self._feed is None:
            self._feed = self._spike_feed(engine)
        self._feed.publish(spikes[0].nonzero().flatten().cpu().numpy())
        read_spikes(engine, spikes, self._state)
        recall_the_hallway(self._memory, self._state, recorded.t)
        self.spikes.append(self._feed.indices)
        self.rows.append(self._row(recorded))
        self._trace_answers(engine, recorded)

    @staticmethod
    def _spike_feed(engine):
        from flynaf.env.brain_view import SpikeFeed
        from flynaf.env.cascade import CascadeTracer
        return SpikeFeed(engine.num_neurons, CascadeTracer.from_csr(engine.synapses))

    def _row(self, recorded) -> list:
        state = self._state
        drive = {**recorded.tablet_drive, **recorded.memory_drive}
        looking = (recorded.left_rate > 0.0, recorded.right_rate > 0.0)
        return [
            round(recorded.t, 3), int(looking[0]), int(looking[1]),
            round(recorded.left_mse) if looking[0] else None,
            round(recorded.right_mse) if looking[1] else None,
            state.l_sensory_count, state.r_sensory_count, int(state.l_spike), int(state.r_spike),
            *recorded.doors,
            int(recorded.camera_open), recorded.tablet_camera,
            _strongest(drive, 'figure'), _strongest(drive, 'loom'),
            round(max(0.0, state.remembered['left']), 3), round(max(0.0, state.remembered['right']), 3),
            int(state.explore_spike), int(state.l_escape), int(state.r_escape),
        ]

    def _trace_answers(self, engine, recorded):
        for side, fired, driven, motor, sensory in (
            ('left', self._state.l_spike, recorded.left_rate > 0.0, engine.l_motor_idx, engine.l_sensory_idx),
            ('right', self._state.r_spike, recorded.right_rate > 0.0, engine.r_motor_idx, engine.r_sensory_idx),
        ):
            if fired and not self._answered[side]:
                self._feed.trace_escape(side, int(motor[0]), sensory, False)
                self.cascades.append({**self._feed.cascade, 'outcome': OUTCOME})
            self._answered[side] = (self._answered[side] or fired) and driven


def record(trace_path: str = EXAMPLE_TRACE, out_dir: str = RECORDING_DIR, device: str = 'cpu') -> dict:
    from flynaf import replay
    recording = NightRecording()
    result = replay.replay(trace_path, device, watch=recording)
    os.makedirs(out_dir, exist_ok=True)
    night = {
        'trace': result['trace'],
        'recorded_at': result['recorded_at'],
        'replayed_on': date.today().isoformat(),
        'settings': result['settings'],
        'ms_per_frame': config.SIMULATION_PARAMS.steps_per_frame * config.NEURAL_PARAMS.dt,
        'keys': ROW_KEYS,
        'rows': recording.rows,
        'cascades': recording.cascades,
    }
    with open(os.path.join(out_dir, 'night.json'), 'w', encoding='utf-8') as handle:
        json.dump(night, handle, separators=(',', ':'))
    with open(os.path.join(out_dir, 'spikes.bin'), 'wb') as handle:
        handle.write(encode_spikes(recording.spikes))
    return result


def replay_page() -> str:
    with open(os.path.join(PAGE_DIR, 'brain_view.html'), encoding='utf-8') as handle:
        page = handle.read()
    if LIVE_TITLE not in page:
        raise ValueError('the panel page no longer carries the title the replay page replaces')
    return page.replace(LIVE_TITLE, REPLAY_TITLE, 1)


def build(out_dir: str, recording_dir: str = RECORDING_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as handle:
        handle.write(replay_page())
    shutil.copyfile(os.path.join(PAGE_DIR, 'replay_player.js'), os.path.join(out_dir, 'player.js'))
    for name in RECORDING_FILES:
        shutil.copyfile(os.path.join(recording_dir, name), os.path.join(out_dir, name))
    open(os.path.join(out_dir, '.nojekyll'), 'w').close()
    return out_dir


def serve(port: int):
    folder = build(tempfile.mkdtemp(prefix='flynaf-page-'))
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=folder)
    with http.server.ThreadingHTTPServer(('127.0.0.1', port), handler) as server:
        url = f'http://127.0.0.1:{server.server_address[1]}/'
        print(f'night 3 replay at {url}, Ctrl+C to stop')
        webbrowser.open(url)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description='The night 3 replay page, recorded, built or served.')
    commands = parser.add_subparsers(dest='command', required=True)
    recording = commands.add_parser('record', help='replay a trace through the brain and keep every spike')
    recording.add_argument('trace', nargs='?', default=EXAMPLE_TRACE)
    recording.add_argument('--out', default=RECORDING_DIR)
    recording.add_argument('--device', default='cpu', choices=('cpu', 'cuda'))
    building = commands.add_parser('build', help='write the static page into a folder')
    building.add_argument('out')
    serving = commands.add_parser('serve', help='build the page and open it on this machine')
    serving.add_argument('--port', type=int, default=0)
    args = parser.parse_args()

    if args.command == 'record':
        record(args.trace, args.out, args.device)
        print(f'recording written to {args.out}')
    elif args.command == 'build':
        print(f'page written to {build(args.out)}')
    else:
        serve(args.port)


if __name__ == '__main__':
    main()
