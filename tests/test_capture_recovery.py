import logging
from unittest.mock import MagicMock, patch

import pytest
from mss.exception import ScreenShotError

from flynaf.env import capture


class EndOfTest(Exception):
    pass


def _grabs(outcomes: list):
    seen = []

    def grab_once(screen):
        seen.append(screen)
        if not outcomes:
            raise EndOfTest
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome

    return grab_once, seen


def _capture(outcomes: list, caplog):
    grab_once, seen = _grabs(outcomes)
    with patch.object(capture.mss, 'MSS', MagicMock()), patch.object(capture.time, 'sleep'), \
            caplog.at_level(logging.INFO, logger='flynaf.env.capture'), pytest.raises(EndOfTest):
        capture.keep_capturing(grab_once, 'eye', retry_sec=1.0)
    return seen


def test_a_failed_grab_does_not_end_the_capture(caplog):
    """The capture used to run in a thread with nothing to catch a failed
    grab, so one failure left the fly reading its last frame for the rest of
    the night."""
    seen = _capture([None, ScreenShotError('locked'), None, None], caplog)
    assert len(seen) == 5


def test_an_outage_is_reported_once_and_so_is_its_end(caplog):
    _capture([None, ScreenShotError('locked'), ScreenShotError('locked'), ScreenShotError('locked'), None],
             caplog)
    assert caplog.text.count('eye capture failed') == 1
    assert caplog.text.count('eye capture is back') == 1
