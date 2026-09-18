import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
import main
from env import overlay

GAME = 789498
EDITOR = 66778
IME = 196778


def test_the_game_is_found_by_its_process_not_by_what_covers_the_screen():
    """WindowFromPoint at the office patch returned a child of TextInputHost,
    whose window spans the whole desktop, so the game was never identified and
    focus was handed to the editor while the night stayed minimised."""
    windows = [IME, EDITOR, GAME]
    processes = {
        IME: 'TextInputHost.exe',
        EDITOR: 'Code.exe',
        GAME: 'FiveNightsatFreddys.exe',
    }

    with patch.object(overlay, '_top_level_windows', return_value=windows), \
         patch.object(overlay, 'window_process', side_effect=processes.get), \
         patch.object(overlay, 'window_title', return_value=''):
        assert overlay.find_game_window() == GAME


def test_a_minimised_game_is_still_found():
    with patch.object(overlay, '_top_level_windows', return_value=[GAME]), \
         patch.object(overlay, 'window_process', return_value='FiveNightsatFreddys.exe'), \
         patch.object(overlay, 'window_title', return_value=''):
        assert overlay.find_game_window() == GAME


def test_the_title_is_only_a_fallback():
    with patch.object(overlay, '_top_level_windows', return_value=[EDITOR]), \
         patch.object(overlay, 'window_process', return_value='Code.exe'), \
         patch.object(overlay, 'window_title', return_value="Five Nights at Freddy's"):
        assert overlay.find_game_window() == EDITOR

    with patch.object(overlay, '_top_level_windows', return_value=[EDITOR]), \
         patch.object(overlay, 'window_process', return_value='Code.exe'), \
         patch.object(overlay, 'window_title', return_value='something else'):
        assert overlay.find_game_window() == 0


def test_the_countdown_gives_the_operator_time_to_reach_the_game():
    with patch.object(main, 'find_game_window', return_value=GAME),          patch.object(main, 'foreground_window', return_value=GAME),          patch.object(main, 'window_title', return_value="Five Nights at Freddy's"),          patch.object(main.asyncio, 'sleep', new=_no_wait) as _:
        asyncio.run(main._countdown_to_the_night(3.0))

    assert _slept == [1.0, 1.0, 1.0]


def test_the_countdown_starts_the_night_even_with_the_wrong_window_in_front():
    del _slept[:]
    with patch.object(main, 'find_game_window', return_value=GAME),          patch.object(main, 'foreground_window', return_value=EDITOR),          patch.object(main, 'window_title', return_value="Five Nights at Freddy's"),          patch.object(main.asyncio, 'sleep', new=_no_wait):
        asyncio.run(main._countdown_to_the_night(2.0))

    assert len(_slept) == 2


def test_the_office_reference_is_taken_with_the_view_centred():
    order = []
    vision = MagicMock()
    vision.load_reference_from_disk.return_value = True
    vision.capture_camera_closed_reference.side_effect = lambda: order.append('capture')

    controller = MagicMock()

    def centre():
        order.append('centre')
        event = MagicMock()
        event.wait.return_value = True
        return event

    controller.centre_view.side_effect = centre

    with patch.object(main, '_countdown_to_the_night', new=_ready):
        asyncio.run(main._calibrate(vision, controller))

    assert order == ['centre', 'capture']


async def _ready(_seconds):
    return None


_slept = []


async def _no_wait(seconds):
    _slept.append(seconds)


def test_the_countdown_is_long_enough_to_switch_windows():
    assert 5.0 <= config.BRAIN_VIEW.start_countdown_sec <= 30.0


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
