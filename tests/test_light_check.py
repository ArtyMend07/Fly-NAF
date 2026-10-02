import asyncio

import pytest

from flynaf.night import lights


class Done:
    def wait(self, timeout=None):
        return True


class Lamp:
    def __init__(self, lit=False, stuck=False, blink_reads=0):
        self.lit = lit
        self.stuck = stuck
        self.blink_reads = blink_reads
        self.believed = False
        self.presses = 0

    def set_left_light(self, on):
        if self.believed != on:
            self._toggle()
        self.believed = on
        return Done()

    def press_left_light(self, state):
        self.presses += 1
        self._toggle()
        self.believed = state
        return Done()

    def _toggle(self):
        if not self.stuck:
            self.lit = not self.lit

    def light_on(self, side):
        if self.blink_reads:
            self.blink_reads -= 1
            return not self.lit
        return self.lit


@pytest.fixture(autouse=True)
def quick_reads(monkeypatch):
    async def no_wait(_seconds):
        return None
    monkeypatch.setattr(lights.asyncio, 'sleep', no_wait)


def switch(lamp, on):
    return asyncio.run(lights.set_light(lamp, lamp, 'left', on))


@pytest.mark.parametrize('on', [True, False])
def test_a_light_in_step_with_the_controller_needs_no_correction(on):
    lamp = Lamp(lit=False)
    if not on:
        switch(lamp, True)

    assert switch(lamp, on) is True
    assert lamp.lit is on
    assert lamp.presses == 0


def test_a_light_left_on_before_the_night_is_put_right_by_the_screen():
    lamp = Lamp(lit=True)

    assert switch(lamp, True) is True
    assert lamp.lit is True
    assert lamp.presses == 1

    assert switch(lamp, False) is True
    assert lamp.lit is False
    assert lamp.presses == 1


def test_one_odd_reading_does_not_press_the_button():
    lamp = Lamp(lit=False, blink_reads=1)

    assert switch(lamp, True) is True
    assert lamp.presses == 0


def test_a_dead_button_is_reported_after_the_corrections_run_out():
    lamp = Lamp(lit=False, stuck=True)

    assert switch(lamp, True) is False
    assert lamp.presses == 2
