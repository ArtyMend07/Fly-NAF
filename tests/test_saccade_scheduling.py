import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
from search_drive import SearchDrive

SPAN = 100          # 50 sensory neurons x 2 steps per frame
DT = 1.0 / config.SIMULATION_PARAMS.target_fps
P = config.SEARCH_DYNAMICS

# The real signal, measured over 1500 frames of this connectome at rest: it
# swings either side of its own average with a typical magnitude of about 30 mV
# and holds its sign for roughly 20 frames at a time.
TYPICAL = 30.0
SIGN_RUN = 20


def swing(i: int, amplitude: float = TYPICAL) -> float:
    return amplitude * (1.0 if (i // SIGN_RUN) % 2 == 0 else -1.0)


# The drift as it was actually measured: a first-order autoregressive process
# with a lag-1 autocorrelation of 0.985 and a standard deviation of 33 mV. The
# square wave above is fine for testing which side wins, but not for anything
# about rate: `gain_ratio` under 1 means the accumulator deliberately cannot
# reach the bound on a swing of unchanging size, so a fake with a fixed
# amplitude, or one with amplitude stepped in blocks, manufactures dead
# stretches the real signal does not have and hands the guard work it would
# never do in play. Seeded, so the numbers below do not move between runs.
_AR_RHO = 0.985
_AR_SD = 33.0


def measured_drift(frames: int, seed: int = 7) -> list:
    import random
    rng = random.Random(seed)
    step_sd = _AR_SD * (1.0 - _AR_RHO ** 2) ** 0.5
    x = 0.0
    out = []
    for _ in range(frames):
        x = _AR_RHO * x + rng.gauss(0.0, step_sd)
        out.append(x)
    return out


class Clock:
    def __init__(self, t0: float = 1000.0):
        self.now = t0

    def tick(self, dt: float = DT) -> float:
        self.now += dt
        return self.now


INSPECTION_SEC = (config.FORAGING_PARAMS.light_inspection_frames
                  / config.SIMULATION_PARAMS.target_fps)
BUSY_FRAMES = int((config.FORAGING_PARAMS.light_activation_settle_sec
                   + INSPECTION_SEC
                   + config.MOTOR_CALIBRATION.pan_delay_sec
                   + config.FORAGING_PARAMS.saccade_refractory_sec) / DT)


def feed(drive, clock, frames, membrane_diff=0.0, left=0.0, right=0.0, can_act=True,
         offset=0, busy_frames=0):
    """Advances the accumulator and returns every look it asked for as
    (frame, side, reason)."""
    looks = []
    busy = 0
    for i in range(frames):
        diff = membrane_diff(i + offset) if callable(membrane_diff) else membrane_diff
        free = can_act and busy <= 0
        busy -= 1
        side = drive.update(diff, left, right, DT, clock.tick(), free)
        if side is not None:
            looks.append((i, side, drive.reason))
            busy = busy_frames
    return looks


# Short enough that the starvation guard is nowhere near armed by the time the
# assertions start, which the bias-corrected running averages make possible.
WARMUP_FRAMES = 60


def settled():
    """A drive whose baseline and normaliser have seen enough of the signal to
    know what an ordinary swing looks like."""
    drive = SearchDrive(SPAN)
    clock = Clock()
    feed(drive, clock, WARMUP_FRAMES, membrane_diff=swing, can_act=False)
    return drive, clock


def test_a_stronger_than_usual_swing_wins_a_look():
    """The point of the whole change: a preference the connectome generates on
    its own has to be able to move the head, with no clock involved."""
    drive, clock = settled()
    looks = feed(drive, clock, 60, membrane_diff=2.0 * TYPICAL)
    assert looks, 'a strong hemispheric drift never produced a look'
    assert looks[0][1] == 'left'
    assert looks[0][2] == 'drift'


def test_the_swing_decides_which_hallway():
    left_drive, left_clock = settled()
    right_drive, right_clock = settled()
    left = feed(left_drive, left_clock, 60, membrane_diff=2.0 * TYPICAL)
    right = feed(right_drive, right_clock, 60, membrane_diff=-2.0 * TYPICAL)
    assert left[0][1] == 'left'
    assert right[0][1] == 'right'


def test_an_ordinary_swing_is_not_enough_on_its_own():
    """`gain_ratio` under 1 means the accumulator settles below the bound for a
    drift of ordinary size. Without that the drive is over the bound on
    essentially every free frame and the fly looks as fast as the motor allows,
    which is the metronome this replaces."""
    drive, clock = settled()
    window = int((P.starvation_sec - 1.0) / DT) - WARMUP_FRAMES
    looks = feed(drive, clock, window, membrane_diff=TYPICAL)
    assert looks == [], f'an average-sized drift alone produced {len(looks)} looks'


def test_a_static_offset_is_adapted_away_instead_of_parking_the_fly():
    """A permanent left/right imbalance would otherwise read as a permanent
    preference and leave one door unwatched for the whole night."""
    drive = SearchDrive(SPAN)
    clock = Clock()
    drift = measured_drift(1500)
    biased = lambda i: 25.0 + drift[i]
    looks = feed(drive, clock, 1500, membrane_diff=biased, busy_frames=BUSY_FRAMES)
    sides = [side for _, side, _ in looks]
    assert sides.count('left') > 0 and sides.count('right') > 0
    assert min(sides.count('left'), sides.count('right')) / len(sides) > 0.3


def test_seeing_something_pulls_the_fly_straight_back_to_that_side():
    drive, clock = settled()
    looks = feed(drive, clock, 40, membrane_diff=0.0, left=SPAN, right=0.0)
    assert looks, 'a full detection never triggered a look'
    assert looks[0][1] == 'left'
    assert looks[0][2] == 'evidence'


def test_evidence_beats_an_idle_drift_pulling_the_other_way():
    drive, clock = settled()
    looks = feed(drive, clock, 40, membrane_diff=-2.0 * TYPICAL, left=SPAN, right=0.0)
    assert looks[0][1] == 'left', 'a threat on the left lost to an idle drift'


def test_habituation_stops_one_hallway_from_winning_forever():
    """A swing holds its sign for longer than a look takes, so without
    habituation the same side is re-selected over and over while the other door
    goes unwatched."""
    drive = SearchDrive(SPAN)
    clock = Clock()
    drift = measured_drift(1500)
    looks = feed(drive, clock, 1500, membrane_diff=drift.__getitem__, busy_frames=BUSY_FRAMES)
    sides = [side for _, side, _ in looks]
    longest = max(len(run) for run in _runs(sides))
    assert longest <= 4, f'the same side was chosen {longest} times in a row'


def _runs(seq):
    group = []
    for item in seq:
        if group and item != group[-1]:
            yield group
            group = []
        group.append(item)
    if group:
        yield group


def test_the_accumulator_keeps_integrating_while_the_head_is_busy():
    """If it stopped, the evidence gathered during a look would be discarded,
    which is precisely the bug this replaces."""
    drive, clock = settled()
    before = abs(drive.drive)
    feed(drive, clock, 25, membrane_diff=2.0 * TYPICAL, can_act=False)
    assert abs(drive.drive) > before, 'the drive stood still while the fly was busy'


def test_nothing_fires_while_the_fly_is_not_free_to_act():
    drive, clock = settled()
    looks = feed(drive, clock, 400, membrane_diff=3.0 * TYPICAL, left=SPAN, can_act=False)
    assert looks == []


def test_the_guard_still_bounds_the_blind_window():
    drive = SearchDrive(SPAN)
    clock = Clock()
    looks = feed(drive, clock, int((P.starvation_sec + 2.0) / DT), membrane_diff=0.0)
    assert looks, 'a perfectly balanced brain left both doors unwatched forever'
    assert looks[0][2] == 'guard'


def test_the_guard_is_not_what_normally_drives_the_fly():
    """The old scheduler was a 2.1s metronome because the guard was consulted
    before the bias branch could ever matter. It has to stay a backstop."""
    drive = SearchDrive(SPAN)
    clock = Clock()
    drift = measured_drift(1500)
    looks = feed(drive, clock, 1500, membrane_diff=drift.__getitem__, busy_frames=BUSY_FRAMES)
    guarded = sum(1 for _, _, reason in looks if reason == 'guard')
    assert guarded / len(looks) < 0.35, (
        f'{guarded} of {len(looks)} looks came from the clock, not the brain'
    )


def test_looks_are_not_evenly_spaced():
    """A metronome and a brain produce the same count and a very different
    spread. This is the property the run report is judged on."""
    drive = SearchDrive(SPAN)
    clock = Clock()
    drift = measured_drift(3000)
    looks = feed(drive, clock, 3000, membrane_diff=drift.__getitem__, busy_frames=BUSY_FRAMES)
    gaps = [(b - a) * DT for (a, _, _), (b, _, _) in zip(looks, looks[1:])]
    spread = max(gaps) - min(gaps)
    assert spread > 2.0, f'looks are spaced {min(gaps):.1f}-{max(gaps):.1f}s apart, a metronome'


def test_a_slow_engine_frame_is_worth_more_than_a_fast_one():
    """The constants are in seconds. A frame that took twice as long has to
    integrate twice as much, or they quietly mean something else every time the
    engine falls behind its nominal rate, which on CPU it always does."""
    fast, slow = SearchDrive(SPAN), SearchDrive(SPAN)
    fast_clock, slow_clock = Clock(), Clock()
    # Same simulated duration either side, one at the nominal rate and one at
    # half it, which is roughly what this engine manages on CPU.
    for i in range(WARMUP_FRAMES):
        fast.update(swing(i), 0, 0, DT, fast_clock.tick(), False)
    for i in range(WARMUP_FRAMES // 2):
        slow.update(swing(2 * i), 0, 0, 2 * DT, slow_clock.tick(2 * DT), False)
    for _ in range(40):
        fast.update(TYPICAL, 0, 0, DT, fast_clock.tick(), False)
    for _ in range(20):
        slow.update(TYPICAL, 0, 0, 2 * DT, slow_clock.tick(2 * DT), False)
    # The residual is the running averages being sampled half as often; the
    # accumulator itself uses the exact geometric sum and does not drift.
    assert abs(fast.drive - slow.drive) < 0.03 * abs(fast.drive), (
        f'fast={fast.drive:.4f} slow={slow.drive:.4f}'
    )


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
