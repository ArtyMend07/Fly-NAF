import queue
import threading
from unittest.mock import MagicMock, patch

import flynaf.env.input_controller as input_controller
from flynaf import config


def _start_isolated_worker() -> queue.Queue:
    input_controller._CMD_QUEUE = queue.Queue()
    threading.Thread(target=input_controller._worker, daemon=True).start()
    return input_controller._CMD_QUEUE


def test_repeated_left_door_close_only_clicks_once():
    mock_desktop = MagicMock()
    sleep_calls = []

    with patch.object(input_controller, 'desktop', mock_desktop), \
         patch.object(input_controller.time, 'sleep', side_effect=sleep_calls.append):
        cmd_queue = _start_isolated_worker()
        controller = input_controller.FNAFController()

        controller.trigger_left_door()
        controller.trigger_left_door()
        controller.trigger_left_door()
        cmd_queue.join()

    assert mock_desktop.move_cursor.call_count == 1
    assert mock_desktop.mouse_down.call_count == 1
    assert mock_desktop.mouse_up.call_count == 1
    assert config.MOTOR_CALIBRATION.pan_delay_sec in sleep_calls


def test_left_and_right_doors_track_state_independently():
    mock_desktop = MagicMock()

    with patch.object(input_controller, 'desktop', mock_desktop), \
         patch.object(input_controller.time, 'sleep'):
        cmd_queue = _start_isolated_worker()
        controller = input_controller.FNAFController()

        controller.trigger_left_door()
        controller.trigger_right_door()
        controller.trigger_left_door()
        cmd_queue.join()

    assert mock_desktop.move_cursor.call_count == 2
    assert mock_desktop.mouse_down.call_count == 2
    assert mock_desktop.mouse_up.call_count == 2


if __name__ == '__main__':
    test_repeated_left_door_close_only_clicks_once()
    test_left_and_right_doors_track_state_independently()
    print('ok')
