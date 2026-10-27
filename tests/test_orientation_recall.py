import math

import pytest
import torch

from flynaf import config
from flynaf.night import tasks
from flynaf.night.memory import OrientationMemory
from flynaf.night.neurons import NeuronMap, stimulus_rates
from flynaf.night.state import SensoryState
from flynaf.search_drive import SearchDrive

SPAN = 100
DT = 1.0 / config.SIMULATION_PARAMS.target_fps
REFRACTORY_FRAMES = int(config.FORAGING_PARAMS.saccade_refractory_sec / DT)
MEMORY_SEC = config.MEMORY_DYNAMICS.orientation_sec


def _after_a_look_at(side: str) -> tuple:
    drive = SearchDrive(SPAN)
    now = 1000.0
    seen = (SPAN, 0) if side == 'left' else (0, SPAN)
    for _ in range(100):
        now += DT
        if drive.update(0.0, *seen, DT, now, True) == side:
            return drive, now
    raise AssertionError(f'the evidence never produced a {side} look')


def _next_look(drive: SearchDrive, now: float, remembered_side: str | None, frames: int = 150):
    sign = {'left': 1.0, 'right': -1.0, None: 0.0}[remembered_side]
    seen_at = now
    for frame in range(frames):
        now += DT
        recalled = sign * math.exp(-(now - seen_at) / MEMORY_SEC)
        side = drive.update(0.0, 0, 0, DT, now, frame >= REFRACTORY_FRAMES, recalled)
        if side is not None:
            return side, drive.reason, now - seen_at
    return None, None, None


@pytest.mark.parametrize('side', ['left', 'right'])
def test_the_fly_looks_back_at_the_side_where_it_just_saw_a_figure(side):
    drive, now = _after_a_look_at(side)
    looked, reason, waited = _next_look(drive, now, side)
    assert (looked, reason) == (side, 'memory')
    assert waited < 2 * config.FORAGING_PARAMS.saccade_refractory_sec


@pytest.mark.parametrize('side, other', [('left', 'right'), ('right', 'left')])
def test_without_a_memory_habituation_sends_the_next_look_to_the_other_side(side, other):
    drive, now = _after_a_look_at(side)
    looked, _reason, _waited = _next_look(drive, now, None)
    assert looked == other


def _looks_at(drive: SearchDrive, now: float, side: str, visible_until: float, seconds: float) -> list:
    sign = 1.0 if side == 'left' else -1.0
    start, seen_at, looks, ready_at = now, now, [], now + config.FORAGING_PARAMS.saccade_refractory_sec
    while now - start < seconds:
        now += DT
        recalled = 0.0 if seen_at is None else sign * math.exp(-(now - seen_at) / MEMORY_SEC)
        looked = drive.update(0.0, 0, 0, DT, now, now >= ready_at, recalled)
        if looked is None:
            continue
        looks.append(looked)
        ready_at = now + config.FORAGING_PARAMS.saccade_refractory_sec
        if looked == side:
            seen_at = now if now - start < visible_until else None
    return looks


@pytest.mark.parametrize('side', ['left', 'right'])
def test_a_figure_that_stays_in_view_keeps_drawing_the_look_back(side):
    drive, now = _after_a_look_at(side)
    looks = _looks_at(drive, now, side, visible_until=12.0, seconds=12.0)
    assert looks.count(side) >= 3, looks


@pytest.mark.parametrize('side, other', [('left', 'right'), ('right', 'left')])
def test_a_look_that_finds_the_figure_gone_ends_the_pull_and_the_other_side_gets_its_turn(side, other):
    drive, now = _after_a_look_at(side)
    assert _looks_at(drive, now, side, visible_until=0.0, seconds=20.0) == [side, other]


def test_the_memory_term_is_bounded_like_the_evidence():
    weak, strong = SearchDrive(SPAN), SearchDrive(SPAN)
    now = 1000.0
    for _ in range(20):
        now += DT
        weak.update(0.0, 0, 0, DT, now, False, 1.0)
        strong.update(0.0, 0, 0, DT, now, False, 50.0)
    assert weak.drive == pytest.approx(strong.drive)
    assert weak.leaning == 'left'


def test_a_look_spends_the_memory_term_with_the_others():
    drive = SearchDrive(SPAN)
    now = 1000.0
    looked = None
    while looked is None:
        now += DT
        looked = drive.update(0.0, 0, 0, DT, now, True, 1.0)
    assert (looked, drive.reason) == ('left', 'memory')
    assert drive.drive == 0.0


class _RingEngine:
    l_motor_idx, r_motor_idx = [0], [1]
    l_escape_idx, r_escape_idx = [2], [3]
    l_explore_idx, r_explore_idx = [4], [11]
    l_sensory_idx, r_sensory_idx = [5], [6]
    l_ring_idx, r_ring_idx = [7, 8], [9, 10]


def _read(firing) -> SensoryState:
    spikes = torch.zeros(1, 12)
    spikes[0, list(firing)] = 1.0
    state = SensoryState()
    tasks.read_spikes(_RingEngine(), spikes, state)
    return state


@pytest.mark.parametrize('firing, counts', [
    ((), (0, 0)),
    ((7, 8), (2, 0)),
    ((9,), (0, 1)),
    ((7, 9, 10), (1, 2)),
])
def test_the_ring_neurons_of_each_side_are_counted_apart(firing, counts):
    state = _read(firing)
    assert (state.l_ring_count, state.r_ring_count) == counts


@pytest.mark.parametrize('firing, left, right', [
    ((), False, False),
    ((4,), True, False),
    ((11,), False, True),
    ((4, 11), True, True),
])
def test_each_dnp09_is_read_on_its_own_side_and_either_one_counts_as_a_spike(firing, left, right):
    state = _read(firing)
    assert (state.l_explore, state.r_explore) == (left, right)
    assert state.explore_spike is (left or right)


@pytest.mark.parametrize('side, recalled', [('left', 1.0), ('right', -1.0)])
def test_a_burst_of_ring_spikes_is_recalled_as_the_side_it_came_from(side, recalled):
    rings = config.MEMORY_DYNAMICS
    sighting = {'left': rings.ring_sighting_left, 'right': rings.ring_sighting_right}
    resting = {'left': rings.ring_resting_left, 'right': rings.ring_resting_right}
    counts = {ring: resting[ring] for ring in resting}
    counts[side] += sighting[side]
    state = SensoryState(l_ring_count=counts['left'], r_ring_count=counts['right'])
    tasks.recall_the_hallway(OrientationMemory(), state, now=10.0)
    assert state.recalled == pytest.approx(recalled)
    assert state.remembered[side] == pytest.approx(1.0)


def test_the_eye_alone_writes_no_memory_until_the_rings_answer():
    state = SensoryState(left_rate=1.0, right_rate=1.0)
    tasks.recall_the_hallway(OrientationMemory(), state, now=10.0)
    assert all(abs(level) < 0.05 for level in state.remembered.values()), state.remembered


def test_a_hallway_figure_drives_the_wide_field_neurons_of_its_side_with_the_eye():
    neurons = NeuronMap(
        inputs={'eye_left': [0], 'eye_right': [1], 'wide_field_left': [2], 'wide_field_right': [3],
                'inhibitors_left': [4], 'inhibitors_right': [5], 'loom_size_right': [6]},
        outputs={},
    )
    state = SensoryState(left_rate=1.0, tablet_drive={'loom_size_right': 0.2})
    rates = {tuple(indices): rate for indices, rate in stimulus_rates(neurons, state, 1000.0)}
    assert rates[(0,)] == rates[(2,)] == 1000.0
    assert rates[(1,)] == rates[(3,)] == 0.0
    assert rates[(6,)] == 200.0
