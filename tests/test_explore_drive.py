import math

import pytest

from flynaf import config
from flynaf.search_drive import ExploreDrive, membrane_leak_per_step

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


def feed(drive, values, fired_at=()):
    for i, v in enumerate(values):
        drive.update(v, i in fired_at)
    return drive


def test_a_spike_is_the_command_and_needs_no_accumulation():
    """A descending command neuron firing needs no interpretation. ADR 0010 was
    right about that; it was only wrong that the spike would ever arrive."""
    drive = ExploreDrive()
    drive.update(RESTING, True)
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
        drive.update(v, False)
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
    drive.update(RESTING, True)
    assert drive.wants_monitor and not drive.spent
    # the cluster falls back to rest and the drive decays with it
    feed(drive, [RESTING] * 200)
    assert drive.spent


def test_release_is_hysteretic_so_the_tablet_does_not_chatter():
    """Raising at the bound and lowering at the same bound would flap. The
    release sits well under it."""
    assert P.release_ratio < 1.0
    drive = ExploreDrive()
    drive.update(RESTING, True)
    steps = 0
    while not drive.spent and steps < 1000:
        drive.update(RESTING, False)
        steps += 1
    assert steps > 5, 'the tablet was released almost immediately after going up'


def test_the_drive_counts_steps_of_the_brain_whatever_the_wall_clock_did():
    """The same membrane trace gives the same drive however fast the engine ran,
    because the accumulator leaks in the brain's time."""
    values = wander(400)
    first, second = ExploreDrive(), ExploreDrive()
    feed(first, values)
    feed(second, values)
    assert first.drive == second.drive


def test_the_accumulator_leaks_with_the_membrane_time_constant():
    steps = config.SIMULATION_PARAMS.steps_per_frame * config.NEURAL_PARAMS.dt
    assert membrane_leak_per_step() == pytest.approx(math.exp(-steps / config.NEURAL_PARAMS.tau_mem))
    drive = ExploreDrive()
    drive.update(RESTING, True)
    feed(drive, [RESTING] * 10)
    assert drive.drive == pytest.approx(membrane_leak_per_step() ** 10, rel=1e-6)


@pytest.mark.parametrize('arousal, scale', [(0.0, 1.0), (0.5, 1.5), (1.0, 2.0), (-1.0, 1.0)])
def test_arousal_scales_how_fast_the_same_membrane_fills_the_accumulator(arousal, scale):
    calm, alert = ExploreDrive(), ExploreDrive()
    calm.update(RESTING, False)
    alert.update(RESTING, False, arousal)
    for value in (RESTING + TYPICAL, RESTING + TYPICAL):
        calm.update(value, False)
        alert.update(value, False, arousal)
    assert alert.drive == pytest.approx(calm.drive * scale)


def test_tension_reports_progress_towards_the_bound():
    drive = ExploreDrive()
    assert drive.tension == 0.0
    drive.update(RESTING, True)
    assert drive.tension == 1.0


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
