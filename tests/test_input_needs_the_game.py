import queue
import threading
from unittest.mock import MagicMock, patch

import pytest

import flynaf.env.input_controller as input_controller
from flynaf.env import overlay

GAME = 4242


def _press_the_left_door(game_in_front):
    mock_desktop = MagicMock()
    with patch.object(input_controller, 'desktop', mock_desktop), \
         patch.object(input_controller.time, 'sleep'), \
         patch.dict(input_controller._FACING, side='centre'):
        input_controller._CMD_QUEUE = queue.Queue()
        threading.Thread(target=input_controller._worker, args=(game_in_front,), daemon=True).start()
        done = input_controller.FNAFController().trigger_left_door()
        assert done.wait(timeout=5.0), 'the worker never acknowledged the command'
    return mock_desktop


def test_nothing_is_clicked_while_the_game_cannot_be_brought_forward():
    """A window brought over the game during a night took the clicks meant
    for the doors and the tablet."""
    mock_desktop = _press_the_left_door(lambda: False)
    assert mock_desktop.move_cursor.call_count == 0
    assert mock_desktop.mouse_down.call_count == 0


def test_the_click_goes_through_with_the_game_in_front():
    mock_desktop = _press_the_left_door(lambda: True)
    assert mock_desktop.mouse_down.call_count == 1


@pytest.mark.parametrize('label, in_front, found, focused, ready', [
    ('already in front', [GAME], GAME, False, True),
    ('handed the focus back', [0, GAME], GAME, True, True),
    ('the focus was refused', [0, 0], GAME, False, False),
    ('no game window at all', [0, 0], 0, False, False),
])
def test_the_game_is_brought_forward_before_the_fly_acts(label, in_front, found, focused, ready):
    handed = []

    def give_focus_back(handle):
        handed.append(handle)
        return focused

    with patch.object(overlay, 'game_in_front', side_effect=in_front), \
         patch.object(overlay, 'find_game_window', return_value=found), \
         patch.object(overlay, 'give_focus_back', side_effect=give_focus_back):
        assert overlay.bring_game_forward() is ready, label
    assert handed == ([] if in_front[0] or not found else [found]), label
