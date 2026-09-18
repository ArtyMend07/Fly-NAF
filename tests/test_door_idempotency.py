import os
import sys
import queue
import threading
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
import env.input_controller as input_controller


def _start_isolated_worker() -> queue.Queue:
    input_controller._CMD_QUEUE = queue.Queue()
    threading.Thread(target=input_controller._worker, daemon=True).start()
    return input_controller._CMD_QUEUE


def test_repeated_left_door_close_only_clicks_once():
    mock_user32 = MagicMock()
    sleep_calls = []

    with patch.object(input_controller.ctypes, 'windll', MagicMock(user32=mock_user32)), \
         patch.object(input_controller.time, 'sleep', side_effect=sleep_calls.append):
        cmd_queue = _start_isolated_worker()
        controller = input_controller.FNAFController()

        controller.trigger_left_door()
        controller.trigger_left_door()
        controller.trigger_left_door()
        cmd_queue.join()

    assert mock_user32.SetCursorPos.call_count == 1
    assert mock_user32.mouse_event.call_count == 2
    assert config.MOTOR_CALIBRATION.pan_delay_sec in sleep_calls


def test_left_and_right_doors_track_state_independently():
    mock_user32 = MagicMock()

    with patch.object(input_controller.ctypes, 'windll', MagicMock(user32=mock_user32)), \
         patch.object(input_controller.time, 'sleep'):
        cmd_queue = _start_isolated_worker()
        controller = input_controller.FNAFController()

        controller.trigger_left_door()
        controller.trigger_right_door()
        controller.trigger_left_door()
        cmd_queue.join()

    assert mock_user32.SetCursorPos.call_count == 2
    assert mock_user32.mouse_event.call_count == 4


if __name__ == '__main__':
    test_repeated_left_door_close_only_clicks_once()
    test_left_and_right_doors_track_state_independently()
    print('ok')
