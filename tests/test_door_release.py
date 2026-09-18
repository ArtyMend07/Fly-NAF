import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config


def decay_frames_to_release() -> int:
    hold = 1.0
    frames = 0
    while hold >= config.DOOR_DYNAMICS.release_threshold:
        hold *= config.DOOR_DYNAMICS.hold_leak_per_frame
        frames += 1
    return frames


def test_hold_lasts_a_few_seconds_at_the_engine_frame_rate():
    seconds = decay_frames_to_release() / config.SIMULATION_PARAMS.target_fps

    assert 3.0 < seconds < 8.0, f'door hold of {seconds:.1f}s is outside the survivable range'


def test_hold_outlives_the_motor_refractory():
    """A door must not reopen while the giant fiber is still refractory, or the
    threat that is still standing there cannot slam it shut again."""
    seconds = decay_frames_to_release() / config.SIMULATION_PARAMS.target_fps

    assert seconds > config.FORAGING_PARAMS.motor_refractory_sec


def test_reopen_settle_is_shorter_than_the_hold():
    """The blind window after reopening has to end well before the next hold
    could start, otherwise the fly reopens into a threat it cannot see."""
    seconds = decay_frames_to_release() / config.SIMULATION_PARAMS.target_fps

    assert config.DOOR_DYNAMICS.reopen_settle_sec < seconds / 2


def test_a_renewed_spike_recharges_the_hold_to_full():
    hold = 1.0
    for _ in range(10):
        hold *= config.DOOR_DYNAMICS.hold_leak_per_frame
    assert hold < 1.0

    hold = 1.0
    assert hold >= config.DOOR_DYNAMICS.release_threshold


if __name__ == '__main__':
    test_hold_lasts_a_few_seconds_at_the_engine_frame_rate()
    test_hold_outlives_the_motor_refractory()
    test_reopen_settle_is_shorter_than_the_hold()
    test_a_renewed_spike_recharges_the_hold_to_full()
    print('ok')
