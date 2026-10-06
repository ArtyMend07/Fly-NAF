
import pytest

from flynaf import config
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState

pytestmark = pytest.mark.connectome

FRAMES = 2500
TABLET_FRAMES = 40
TABLET_UP_HZ = config.SIMULATION_PARAMS.base_sensory_rate_hz

_ENGINE = {}


def _engine() -> ConnectomeEngine:
    if 'engine' not in _ENGINE:
        _ENGINE['engine'] = ConnectomeEngine('cpu')
    return _ENGINE['engine']


def _spike_frames(state: SensoryState, frames: int) -> dict:
    engine = _engine()
    engine.reset()
    readouts = {
        'giant_fiber': engine.l_motor_idx,
        'looming_escape': engine.l_escape_idx,
        'explore': engine.explore_idx,
    }
    counts = dict.fromkeys(readouts, 0)
    for frame in range(frames):
        spikes = engine.step(state, frame * engine.frame_dt)[0]
        for name, indices in readouts.items():
            counts[name] += int(bool(spikes[indices].any()))
    return counts


def test_biological_inhibition():
    startle = _spike_frames(SensoryState(left_rate=1.0), FRAMES)
    assert startle['giant_fiber'] > 0, f'expected startle reflex, got {startle}'

    inhibited = _spike_frames(SensoryState(left_rate=1.0, cam_inhib=TABLET_UP_HZ), FRAMES)
    assert inhibited['giant_fiber'] == 0, (
        f'inhibition failed, giant fiber spiked on {inhibited["giant_fiber"]} frames with camera open'
    )


TABLET_CASES = (
    ('looming on the camera', {'loom_size_left': 0.25, 'loom_speed_left': 0.25},
     'looming_escape', ('giant_fiber', 'explore')),
    ('a figure in the cove', {'figure_left': 0.25},
     'explore', ('giant_fiber', 'looming_escape')),
)


def test_each_tablet_channel_wakes_its_own_descending_neuron():
    for label, drive, answers, silent in TABLET_CASES:
        counts = _spike_frames(SensoryState(cam_inhib=TABLET_UP_HZ, tablet_drive=drive), TABLET_FRAMES)
        assert counts[answers] > 0, f'{label}: {answers} never fired, {counts}'
        assert counts['giant_fiber'] == 0, f'{label}: the giant fiber broke through the inhibitors, {counts}'
        crossed = [name for name in silent if name != 'giant_fiber' and counts[name] > counts[answers] / 4]
        assert not crossed, f'{label}: {crossed} answered a channel that is not theirs, {counts}'


def test_a_remembered_figure_keeps_the_giant_fiber_answering_once_the_tablet_is_down():
    faint = {'loom_size_left': 0.05, 'loom_speed_left': 0.05}
    counts = _spike_frames(SensoryState(tablet_drive=faint), TABLET_FRAMES)
    assert counts['giant_fiber'] > 0, f'the giant fiber ignored the remembered figure, {counts}'


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
