import math

from flynaf.night.tablet.memory import ObjectMemory

DECAY = 4.0
BASE_RATE = 1000.0


def _memory() -> ObjectMemory:
    return ObjectMemory(DECAY, BASE_RATE)


def test_a_remembered_figure_fades_with_the_memory_time_constant():
    memory = _memory()
    memory.remember('left', 0.6, now=10.0)
    assert memory.level(10.0) == 0.6
    assert abs(memory.level(14.0) - 0.6 * math.exp(-1.0)) < 1e-9
    assert memory.level(14.0, 'right') == 0.0


def test_the_memory_is_gone_once_it_would_feed_less_than_one_spike_a_second():
    memory = _memory()
    memory.remember('left', 0.6, now=0.0)
    vanishes_at = DECAY * math.log(0.6 * BASE_RATE)
    assert memory.level(vanishes_at - 0.1) > 0.0
    assert memory.level(vanishes_at + 0.1) == 0.0
    assert memory.drive(vanishes_at + 0.1) == {}


def test_a_stronger_sighting_refreshes_the_memory_and_a_weaker_one_does_not():
    memory = _memory()
    assert memory.remember('left', 0.4, now=0.0)
    assert not memory.remember('left', 0.3, now=0.5)
    assert memory.remember('left', 0.7, now=1.0)
    assert memory.level(1.0) == 0.7
    assert not memory.remember('left', 0.0, now=2.0)


def test_a_faded_memory_is_refreshed_by_any_new_sighting():
    memory = _memory()
    memory.remember('left', 0.6, now=0.0)
    assert memory.remember('left', 0.2, now=16.0)
    assert memory.level(16.0) == 0.2


def test_the_memory_drives_the_looming_populations_on_its_side():
    memory = _memory()
    assert memory.drive(0.0) == {}
    memory.remember('left', 0.5, now=0.0)
    assert memory.drive(0.0) == {'loom_size_left': 0.5, 'loom_speed_left': 0.5}
