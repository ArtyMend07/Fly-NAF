import math
from dataclasses import dataclass

import pytest

from flynaf.night.memory import DefensiveState, FadingTrace, OrientationMemory

DECAY = 4.0
BASE_RATE = 1000.0


@dataclass(frozen=True)
class _Rings:
    orientation_sec: float = DECAY
    ring_resting_left: float = 0.1
    ring_resting_right: float = 0.5
    ring_sighting_left: float = 10.0
    ring_sighting_right: float = 20.0


def _trace() -> FadingTrace:
    return FadingTrace(DECAY, BASE_RATE)


def _orientation() -> OrientationMemory:
    return OrientationMemory(_Rings())


@pytest.mark.parametrize('elapsed, kept', [
    (0.0, 1.0),
    (DECAY, math.exp(-1.0)),
    (2 * DECAY, math.exp(-2.0)),
])
def test_a_trace_fades_with_its_time_constant(elapsed, kept):
    trace = _trace()
    trace.add('left', 0.6, now=10.0)
    assert trace.level(10.0 + elapsed, 'left') == pytest.approx(0.6 * kept)
    assert trace.level(10.0 + elapsed, 'right') == 0.0


def test_a_trace_is_gone_once_it_would_feed_less_than_one_spike_a_second():
    trace = _trace()
    trace.add('left', 0.6, now=0.0)
    vanishes_at = DECAY * math.log(0.6 * BASE_RATE)
    assert trace.level(vanishes_at - 0.1, 'left') > 0.0
    assert trace.level(vanishes_at + 0.1, 'left') == 0.0
    assert trace.present(vanishes_at + 0.1) == {}


@pytest.mark.parametrize('amounts, kept', [
    ((0.3, 0.3), 0.6),
    ((0.8, 0.8), 1.0),
    ((0.3, -0.1), 0.3),
])
def test_a_trace_only_adds_up_and_saturates_at_one(amounts, kept):
    trace = _trace()
    for amount in amounts:
        trace.add('left', amount, now=0.0)
    assert trace.level(0.0, 'left') == pytest.approx(kept)


@pytest.mark.parametrize('side, spikes', [('left', 10.1), ('right', 20.5)])
def test_a_sighting_worth_of_ring_spikes_fills_the_memory_of_that_side(side, spikes):
    memory = _orientation()
    other = 'right' if side == 'left' else 'left'
    resting = {'left': 0.1, 'right': 0.5}
    memory.imprint({side: spikes, other: resting[other]}, now=0.0)
    assert memory.level(0.0, side) == pytest.approx(1.0)
    assert memory.level(0.0, other) == 0.0


def test_ring_neurons_firing_at_their_resting_rate_write_nothing():
    memory = _orientation()
    for frame in range(50):
        memory.imprint({'left': 0.1, 'right': 0.5}, now=frame * 0.1)
    assert memory.level(5.0, 'left') == 0.0
    assert memory.level(5.0, 'right') == 0.0


def test_a_quiet_ring_drains_what_a_burst_left_faster_than_the_decay_alone():
    memory = _orientation()
    memory.imprint({'left': 5.1, 'right': 0.5}, now=0.0)
    memory.imprint({'left': 0.0, 'right': 0.5}, now=0.1)
    assert memory.level(0.1, 'left') == pytest.approx(0.5 * math.exp(-0.1 / DECAY) - 0.01)


def test_a_ring_quieter_than_its_rest_sinks_below_rest_down_to_a_floor():
    memory = _orientation()
    memory.imprint({'left': 0.0, 'right': 0.5}, now=0.0)
    assert memory.level(0.0, 'left') == pytest.approx(-0.01)
    for frame in range(1, 400):
        memory.imprint({'left': 0.0, 'right': 0.5}, now=frame * 0.01)
    assert memory.level(3.99, 'left') == -1.0
    assert memory.level(3.99, 'right') == 0.0


def test_each_threat_adds_to_what_is_left_of_the_defensive_state():
    state = DefensiveState(DECAY, BASE_RATE)
    assert state.threat('left', 0.4, now=0.0) == 0.4
    left_over = 0.4 * math.exp(-1.0)
    assert state.threat('left', 0.4, now=DECAY) == pytest.approx(left_over + 0.4)


def test_the_defensive_state_saturates_and_ignores_a_threat_of_nothing():
    state = DefensiveState(DECAY, BASE_RATE)
    state.threat('left', 0.9, now=0.0)
    assert state.threat('left', 0.9, now=0.0) == 1.0
    assert state.threat('right', 0.0, now=0.0) == 0.0
    assert state.threat('right', -0.5, now=0.0) == 0.0


def test_the_defensive_state_drives_the_looming_populations_on_its_side():
    state = DefensiveState(DECAY, BASE_RATE)
    assert state.drive(0.0) == {}
    state.threat('right', 0.5, now=0.0)
    assert state.drive(0.0) == {'loom_size_right': 0.5, 'loom_speed_right': 0.5}
