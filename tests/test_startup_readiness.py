import asyncio
from unittest.mock import MagicMock, patch

from flynaf import config
from flynaf.env import overlay
from flynaf.night import calibration, monitor

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
         patch.object(overlay, 'window_title', return_value=''), \
         patch.object(overlay, 'foreground_window', return_value=EDITOR), \
         patch.object(overlay, 'window_rect', return_value=None):
        assert overlay.find_game_window() == GAME


def test_a_minimised_game_is_still_found():
    with patch.object(overlay, '_top_level_windows', return_value=[GAME]), \
         patch.object(overlay, 'window_process', return_value='FiveNightsatFreddys.exe'), \
         patch.object(overlay, 'window_title', return_value=''), \
         patch.object(overlay, 'foreground_window', return_value=0), \
         patch.object(overlay, 'window_rect', return_value=None):
        assert overlay.find_game_window() == GAME


def test_the_game_window_in_front_beats_its_minimised_frame():
    frame, fullscreen = 919132, 919200
    titles = {frame: "Five Nights at Freddy's", fullscreen: ''}
    with patch.object(overlay, '_top_level_windows', return_value=[frame, fullscreen]), \
         patch.object(overlay, 'window_process', return_value='FiveNightsatFreddys.exe'), \
         patch.object(overlay, 'window_title', side_effect=titles.get), \
         patch.object(overlay, 'foreground_window', return_value=fullscreen):
        assert overlay.find_game_window() == fullscreen
        assert overlay.game_in_front() == fullscreen


def test_a_showing_game_window_beats_a_minimised_one_when_neither_is_in_front():
    frame, fullscreen = 919132, 919200
    rects = {frame: None, fullscreen: (0, 0, 1280, 720)}
    processes = {frame: 'FiveNightsatFreddys.exe', fullscreen: 'FiveNightsatFreddys.exe',
                 EDITOR: 'Code.exe'}
    with patch.object(overlay, '_top_level_windows', return_value=[frame, fullscreen]), \
         patch.object(overlay, 'window_process', side_effect=processes.get), \
         patch.object(overlay, 'window_title', return_value=''), \
         patch.object(overlay, 'foreground_window', return_value=EDITOR), \
         patch.object(overlay, 'window_rect', side_effect=rects.get):
        assert overlay.find_game_window() == fullscreen
        assert overlay.game_in_front() == 0


def test_the_title_is_only_a_fallback():
    with patch.object(overlay, '_top_level_windows', return_value=[EDITOR]), \
         patch.object(overlay, 'window_process', return_value='Code.exe'), \
         patch.object(overlay, 'window_title', return_value="Five Nights at Freddy's"), \
         patch.object(overlay, 'foreground_window', return_value=0), \
         patch.object(overlay, 'window_rect', return_value=None):
        assert overlay.find_game_window() == EDITOR

    with patch.object(overlay, '_top_level_windows', return_value=[EDITOR]), \
         patch.object(overlay, 'window_process', return_value='Code.exe'), \
         patch.object(overlay, 'window_title', return_value='something else'), \
         patch.object(overlay, 'foreground_window', return_value=0), \
         patch.object(overlay, 'window_rect', return_value=None):
        assert overlay.find_game_window() == 0


def test_a_browser_tab_named_after_the_game_is_not_the_game():
    tab = "ArtyMend07/Fly-NAF: an agent that plays Five Nights at Freddy's 1 - Opera"
    with patch.object(overlay, '_top_level_windows', return_value=[EDITOR]),          patch.object(overlay, 'window_process', return_value='opera.exe'),          patch.object(overlay, 'window_title', return_value=tab),          patch.object(overlay, 'foreground_window', return_value=0),          patch.object(overlay, 'window_rect', return_value=None):
        assert overlay.find_game_window() == 0


def test_the_countdown_gives_the_operator_time_to_reach_the_game():
    with patch.object(calibration.asyncio, 'sleep', new=_no_wait):
        asyncio.run(calibration.countdown_to_the_night(3.0))

    assert _slept == [1.0, 1.0, 1.0]


def test_the_night_starts_even_with_the_wrong_window_in_front():
    with patch.object(calibration, 'game_in_front', return_value=0), \
         patch.object(calibration, 'anchor_to_game') as anchor:
        calibration.confirm_game_in_front()
    anchor.assert_not_called()


def test_the_anchor_is_taken_once_the_game_is_in_front():
    with patch.object(calibration, 'game_in_front', return_value=GAME), \
         patch.object(calibration, 'window_title', return_value="Five Nights at Freddy's"), \
         patch.object(calibration, 'anchor_to_game') as anchor:
        calibration.confirm_game_in_front()
    anchor.assert_called_once()


def test_a_launcher_hook_replaces_the_countdown():
    started = []
    vision = MagicMock()
    vision.load_reference_from_disk.return_value = True
    controller = MagicMock()

    with patch.object(calibration, 'countdown_to_the_night', new=_refuse), \
         patch.object(calibration, 'game_in_front', return_value=0):
        asyncio.run(calibration.calibrate(
            vision, controller, begin_night=lambda: started.append('hook'),
        ))

    assert started == ['hook']


async def _refuse(_seconds):
    raise AssertionError('the countdown ran although the launcher starts the night')


def test_the_night_starts_by_putting_away_a_tablet_already_on_screen():
    screen = {'up': True}
    vision = MagicMock()
    vision.load_reference_from_disk.return_value = True
    vision.is_camera_up.side_effect = lambda: screen['up']
    vision.is_camera_down.side_effect = lambda: not screen['up']

    def flip():
        screen['up'] = not screen['up']
        event = MagicMock()
        event.wait.return_value = True
        return event

    controller = MagicMock()
    controller.flip_tablet.side_effect = flip

    with patch.object(calibration, 'countdown_to_the_night', new=_ready),          patch.object(calibration, 'game_in_front', return_value=0),          patch.object(monitor, 'ALREADY_THERE_SEC', 0.0):
        asyncio.run(calibration.calibrate(vision, controller))

    assert controller.flip_tablet.call_count == 1
    assert screen['up'] is False


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
