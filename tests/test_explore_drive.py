import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
from search_drive import ExploreDrive

DT = 1.0 / config.SIMULATION_PARAMS.target_fps
P = config.EXPLORE_DYNAMICS

# DNp09's membrane at the calmed gain, measured over 2500 frames: it sits near
# -232 mV, its deviation averages 17 mV, and its lag-1 autocorrelation is 0.963.
RESTING = -232.0
TYPICAL = 17.0
RHO = 0.963


def wander(frames: int, seed: int = 3, amplitude: float = TYPICAL) -> list:
    import random
    rng = random.Random(seed)
    step_sd = amplitude * (1.0 - RHO ** 2) ** 0.5
    x, out = 0.0, []
    for _ in range(frames):
        x = RHO * x + rng.gauss(0.0, step_sd)
        out.append(RESTING + x)
    return out


def feed(drive, values, fired_at=(), dt=DT):
    for i, v in enumerate(values):
        drive.update(v, i in fired_at, dt)
    return drive


def test_a_spike_is_the_command_and_needs_no_accumulation():
    """A descending command neuron firing needs no interpretation. ADR 0010 was
    right about that; it was only wrong that the spike would ever arrive."""
    drive = ExploreDrive()
    drive.update(RESTING, True, DT)
    assert drive.wants_monitor
    assert drive.commanded


def test_the_tablet_still_comes_up_when_the_cluster_never_spikes():
    """The whole reason this class exists: at the calmed gain DNp09 fired once
    in 2500 frames, so a monitor that waits for a spike never comes up."""
    drive = ExploreDrive()
    feed(drive, wander(2000))
    assert drive.wants_monitor or _ever_wanted(wander(2000)), (
        'the drive never reached the bound across 2000 frames of real drift'
    )


def _ever_wanted(values) -> bool:
    drive = ExploreDrive()
    for i, v in enumerate(values):
        drive.update(v, False, DT)
        if drive.wants_monitor:
            return True
    return False


def test_a_flat_cluster_never_raises_the_tablet():
    """Nothing happening is not a reason to burn power on the monitor."""
    drive = ExploreDrive()
    feed(drive, [RESTING] * 1500)
    assert not drive.wants_monitor
    assert drive.drive == 0.0


def test_the_drive_never_runs_negative():
    """A cluster quieter than usual is not evidence against exploring later, so
    the accumulator reflects at zero instead of digging a hole it has to climb
    out of before the next excursion counts."""
    drive = ExploreDrive()
    feed(drive, [RESTING - 5 * TYPICAL] * 300)
    assert drive.drive >= 0.0


def test_watching_ends_because_the_drive_faded_not_because_time_passed():
    drive = ExploreDrive()
    drive.update(RESTING, True, DT)
    assert drive.wants_monitor and not drive.spent
    # the cluster falls back to rest and the drive decays with it
    feed(drive, [RESTING] * 200)
    assert drive.spent


def test_release_is_hysteretic_so_the_tablet_does_not_chatter():
    """Raising at the bound and lowering at the same bound would flap. The
    release sits well under it."""
    assert P.release_ratio < 1.0
    drive = ExploreDrive()
    drive.update(RESTING, True, DT)
    steps = 0
    while not drive.spent and steps < 1000:
        drive.update(RESTING, False, DT)
        steps += 1
    assert steps > 5, 'the tablet was released almost immediately after going up'


def test_a_slow_engine_frame_is_worth_more_than_a_fast_one():
    """Same seconds either side, one at the nominal rate and one at half it."""
    values = wander(400)
    fast, slow = ExploreDrive(), ExploreDrive()
    for v in values:
        fast.update(v, False, DT)
    for v in values[::2]:
        slow.update(v, False, 2 * DT)
    assert abs(fast.drive - slow.drive) < 0.35 * max(fast.drive, 0.1), (
        f'fast={fast.drive:.3f} slow={slow.drive:.3f}'
    )


def test_tension_reports_progress_towards_the_bound():
    drive = ExploreDrive()
    assert drive.tension == 0.0
    drive.update(RESTING, True, DT)
    assert drive.tension == 1.0


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
