import dataclasses
import os
import tempfile
from unittest.mock import patch

from flynaf import config, launcher

GAME = 919200
CALIBRATED = dataclasses.replace(
    config.GAME_LAUNCHER, new_game_x=170, new_game_y=400, continue_x=170, continue_y=480,
    menu_settle_sec=0.0, night_start_new_sec=0.0, night_start_continue_sec=0.0,
)


def _save_file(text: str) -> str:
    handle = tempfile.NamedTemporaryFile('w', delete=False, suffix='freddy', encoding='latin-1')
    handle.write(text)
    handle.close()
    return handle.name


def test_the_saved_night_is_read_from_the_game_save():
    path = _save_file('[freddy]\nlevel=2\nlives=5\n')
    try:
        assert launcher.saved_night(path) == 2
    finally:
        os.remove(path)


def test_a_missing_or_broken_save_gives_no_night():
    assert launcher.saved_night(os.path.join(tempfile.gettempdir(), 'no-such-freddy')) is None
    path = _save_file('[freddy]\nlevel=two\n')
    try:
        assert launcher.saved_night(path) is None
    finally:
        os.remove(path)


def test_menu_points_stay_unset_until_calibrated():
    with patch.object(config, 'GAME_LAUNCHER', CALIBRATED):
        assert launcher.menu_point(launcher.NEW) == (170, 400)
        assert launcher.menu_point(launcher.CONTINUE) == (170, 480)
        assert launcher.menu_point(launcher.MANUAL) is None


def test_a_choice_is_taken_once():
    session = launcher.LauncherSession()
    assert not session.choose('sideways')
    assert session.choose(launcher.CONTINUE)
    assert not session.choose(launcher.NEW)
    assert session.mode == launcher.CONTINUE
    assert session.chosen.is_set()


def _begin(session: launcher.LauncherSession) -> list:
    clicks = []
    with patch.object(config, 'GAME_LAUNCHER', CALIBRATED), \
         patch.object(launcher, 'find_game_window', return_value=GAME), \
         patch.object(launcher, 'hold_foreground', return_value=True), \
         patch.object(launcher, 'anchor_to_game', return_value=True), \
         patch.object(launcher, '_click', side_effect=clicks.append), \
         patch.object(launcher.time, 'sleep'):
        launcher.night_starter(session)()
    return clicks


def test_the_fly_clicks_the_chosen_option_in_a_game_it_opened():
    session = launcher.LauncherSession()
    session.choose(launcher.CONTINUE)
    session.opened_game = True
    assert _begin(session) == [(170, 480)]


def test_a_game_that_was_already_running_is_never_clicked():
    session = launcher.LauncherSession()
    session.choose(launcher.NEW)
    session.opened_game = False
    assert _begin(session) == []


def test_an_already_running_game_is_not_opened_twice():
    session = launcher.LauncherSession()
    with patch.object(launcher, 'find_game_window', return_value=GAME), \
         patch.object(launcher.desktop, 'open_target') as opener:
        assert launcher.open_game(session) == GAME
    opener.assert_not_called()
    assert not session.opened_game



def _windowing(rects: list) -> int:
    presses = []
    params = dataclasses.replace(config.GAME_LAUNCHER, windowed_stable_sec=0.0)

    def toggle():
        presses.append(1)
        return True

    with patch.object(config, 'GAME_LAUNCHER', params),          patch.object(launcher, 'find_game_window', return_value=GAME),          patch.object(launcher, 'hold_foreground', return_value=True),          patch.object(launcher.desktop, 'screen_size', return_value=(1920, 1080)),          patch.object(launcher.desktop, 'window_rect', side_effect=rects),          patch.object(launcher.desktop, 'toggle_fullscreen', side_effect=toggle),          patch.object(launcher.time, 'sleep'):
        assert launcher.leave_fullscreen(launcher.LauncherSession())
    return len(presses)


def test_a_fullscreen_game_is_put_in_a_window_once():
    assert _windowing([(0, 0, 1920, 1080), (320, 180, 1280, 720)]) == 1


def test_a_game_already_in_a_window_is_left_alone():
    assert _windowing([(320, 180, 1280, 720)]) == 0


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')
