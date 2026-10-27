
import pytest

from flynaf import config
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.state import SensoryState

pytestmark = pytest.mark.connectome

FRAMES = 2500
TABLET_FRAMES = 40
TABLET_UP_HZ = config.SIMULATION_PARAMS.base_sensory_rate_hz
OTHER_SIDE = {'left': 'right', 'right': 'left'}

_ENGINE = {}


def _engine() -> ConnectomeEngine:
    if 'engine' not in _ENGINE:
        _ENGINE['engine'] = ConnectomeEngine('cpu')
    return _ENGINE['engine']


def _spike_frames(state: SensoryState, frames: int, side: str = 'left') -> dict:
    engine = _engine()
    engine.reset()
    across = OTHER_SIDE[side]
    readouts = {
        'giant_fiber': engine.neurons.outputs[f'giant_fiber_{side}'],
        'looming_escape': engine.neurons.outputs[f'looming_escape_{side}'],
        'explore': engine.neurons.outputs[f'explore_{side}'],
        'explore_across': engine.neurons.outputs[f'explore_{across}'],
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


SIDES = ('left', 'right')
TABLET_CHANNELS = (
    ('looming', ('loom_size', 'loom_speed'), 'looming_escape', 'explore'),
    ('a figure', ('figure',), 'explore', 'looming_escape'),
)


@pytest.mark.parametrize('side', SIDES)
@pytest.mark.parametrize('label, populations, answers, silent', TABLET_CHANNELS)
def test_each_tablet_channel_wakes_its_own_descending_neuron(side, label, populations, answers, silent):
    drive = {f'{population}_{side}': 0.25 for population in populations}
    counts = _spike_frames(SensoryState(cam_inhib=TABLET_UP_HZ, tablet_drive=drive), TABLET_FRAMES, side)
    assert counts[answers] > 0, f'{label} on the {side}: {answers} never fired, {counts}'
    assert counts['giant_fiber'] == 0, f'{label} on the {side}: the giant fiber broke through, {counts}'
    assert counts[silent] <= counts[answers] / 4, f'{label} on the {side}: {silent} answered too, {counts}'


@pytest.mark.parametrize('side', SIDES)
@pytest.mark.parametrize('level', [0.25, 1.0])
def test_a_figure_on_the_tablet_wakes_only_the_dnp09_on_its_own_side(side, level):
    drive = {f'figure_{side}': level}
    counts = _spike_frames(SensoryState(cam_inhib=TABLET_UP_HZ, tablet_drive=drive), TABLET_FRAMES, side)
    assert counts['explore'] > 0, f'a figure of {level} on the {side} went unanswered, {counts}'
    assert counts['explore_across'] == 0, f'a figure of {level} on the {side} crossed the midline, {counts}'


SIGHTING_FRAMES = 4
AFTER_SIGHTING_FRAMES = 12
SIGHTING_TRIALS = 6


def _sighting(side: str) -> tuple:
    engine = _engine()
    engine.reset()
    seen, quiet = SensoryState(**{f'{side}_rate': 1.0}), SensoryState()
    rings = {'left': 0.0, 'right': 0.0}
    readouts = {'giant_fiber': engine.neurons.outputs[f'giant_fiber_{side}'],
                'looming_escape': engine.neurons.outputs[f'looming_escape_{side}'],
                'explore': engine.explore_idx}
    descending = dict.fromkeys(readouts, 0)
    for frame in range(SIGHTING_FRAMES + AFTER_SIGHTING_FRAMES):
        spikes = engine.step(seen if frame < SIGHTING_FRAMES else quiet, frame * engine.frame_dt)[0]
        rings['left'] += float(spikes[engine.l_ring_idx].sum())
        rings['right'] += float(spikes[engine.r_ring_idx].sum())
        for name, indices in readouts.items():
            descending[name] += int(bool(spikes[indices].any()))
    return rings, descending


def _sightings(side: str, wide_field: bool) -> tuple:
    inputs = _engine().neurons.inputs
    kept = inputs[f'wide_field_{side}']
    inputs[f'wide_field_{side}'] = kept if wide_field else []
    try:
        runs = [_sighting(side) for _ in range(SIGHTING_TRIALS)]
    finally:
        inputs[f'wide_field_{side}'] = kept
    rings = {ring: sum(r[ring] for r, _ in runs) / SIGHTING_TRIALS for ring in SIDES}
    descending = {name: sum(d[name] for _, d in runs) for name in runs[0][1]}
    return rings, descending


@pytest.mark.parametrize('side, other', [('left', 'right'), ('right', 'left')])
def test_a_hallway_sighting_reaches_the_ring_neurons_of_its_own_side_through_metu4(side, other):
    rings, _ = _sightings(side, wide_field=True)
    eye_only, _ = _sightings(side, wide_field=False)
    sighting = getattr(config.MEMORY_DYNAMICS, f'ring_sighting_{side}')
    assert rings[side] >= sighting / 2, rings
    assert rings[side] > 2 * rings[other], rings
    assert eye_only[side] < sighting / 4, eye_only


@pytest.mark.parametrize('side', SIDES)
def test_metu4_adds_nothing_to_what_the_descending_neurons_do_on_a_sighting(side):
    _, with_rings = _sightings(side, wide_field=True)
    _, eye_only = _sightings(side, wide_field=False)
    for name in with_rings:
        assert abs(with_rings[name] - eye_only[name]) <= max(3, eye_only[name] / 4), (with_rings, eye_only)
