import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
import main

FRAMES = config.FORAGING_PARAMS.light_inspection_frames


class TickingEngine:
    def __init__(self, frame_dt=0.005, stalled=False, driving=False):
        self.frame_dt = frame_dt
        self.frames = 0
        self.driven_frames = {'left': 0, 'right': 0}
        self._stalled = stalled
        self._driving = driving

    async def run(self, state, slam_at=None, side='left'):
        while True:
            await asyncio.sleep(self.frame_dt)
            if self._stalled:
                continue
            self.frames += 1
            if self._driving:
                self.driven_frames[side] += 1
            if slam_at is not None and self.frames >= slam_at:
                if side == 'left':
                    state.l_spike = True
                else:
                    state.r_spike = True


class PeakVision:
    def __init__(self, peak=0.0):
        self.peaks = {'left': 0.0, 'right': 0.0}
        self._peak = peak
        self.resets = []

    def reset_peak_mse(self, side):
        self.resets.append(side)
        self.peaks[side] = 0.0

    def peak_mse(self, side):
        return self.peaks[side] or self._peak


def _watch(engine, vision, state, side, slam_at=None):
    async def scenario():
        ticker = asyncio.create_task(engine.run(state, slam_at, side))
        try:
            return await main._observe_hallway(engine, vision, state, side)
        finally:
            ticker.cancel()

    return asyncio.run(scenario())


def test_the_eye_stays_open_for_the_configured_number_of_engine_frames():
    engine = TickingEngine()
    state = main.SensoryState()

    _contrast, frames, _driven, fired = _watch(engine, PeakVision(), state, 'left')

    assert frames >= FRAMES, f'the look lasted {frames} frames, needed {FRAMES}'
    assert fired is False


def test_the_look_is_long_enough_for_the_measured_reflex_latency():
    """DNp01 answers a saturated eye after 7 to 9 engine frames at the calmed
    gain. A window shorter than that can never produce a door slam however
    clearly the fly sees the threat."""
    assert FRAMES >= 9


def test_the_eye_closes_early_once_the_giant_fiber_answers():
    engine = TickingEngine()
    state = main.SensoryState()

    _contrast, frames, _driven, fired = _watch(engine, PeakVision(), state, 'left', slam_at=3)

    assert fired is True
    assert frames < FRAMES


def test_a_stalled_engine_cannot_hold_the_light_forever():
    engine = TickingEngine(stalled=True)
    state = main.SensoryState()
    original = config.FORAGING_PARAMS.light_inspection_max_sec
    assert original <= 10.0, 'the safety cap has to stay short enough to test'

    _contrast, frames, _driven, fired = _watch(engine, PeakVision(), state, 'left')

    assert frames == 0
    assert fired is False


def test_the_gaze_flag_is_cleared_on_both_sides_afterwards():
    engine = TickingEngine()
    state = main.SensoryState()

    _watch(engine, PeakVision(), state, 'right')

    assert state.check_left is False
    assert state.check_right is False


def test_the_peak_is_reset_at_the_start_and_reported_at_the_end():
    engine = TickingEngine()
    state = main.SensoryState()
    vision = PeakVision(peak=2400.0)

    contrast, _frames, _driven, _fired = _watch(engine, vision, state, 'left')

    assert vision.resets == ['left']
    assert contrast == 2400.0


def test_the_report_can_tell_a_look_apart_from_a_look_that_saw_something():
    """A peak contrast says the eye crossed the threshold once. Only the frame
    count says whether it held long enough for DNp01 to answer."""
    engine = TickingEngine(driving=True)
    state = main.SensoryState()

    _contrast, frames, driven, _fired = _watch(engine, PeakVision(), state, 'left')

    assert driven == frames

    quiet = TickingEngine(driving=False)
    _contrast, _frames, driven, _fired = _watch(quiet, PeakVision(), main.SensoryState(), 'left')

    assert driven == 0


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
