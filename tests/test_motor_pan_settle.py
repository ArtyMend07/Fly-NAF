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
    input_controller._FACING['side'] = 'centre'
    threading.Thread(target=input_controller._worker, daemon=True).start()
    return input_controller._CMD_QUEUE


def test_pan_side_classifies_every_real_button():
    motor = config.MOTOR_CALIBRATION

    assert input_controller._pan_side(motor.left_door_button_x) == 'left'
    assert input_controller._pan_side(motor.left_light_button_x) == 'left'
    assert input_controller._pan_side(motor.right_door_button_x) == 'right'
    assert input_controller._pan_side(motor.right_light_button_x) == 'right'
    assert input_controller._pan_side(motor.camera_hover_x) == 'centre'


def test_the_office_reports_which_way_it_faces():
    """The camera-up detector reads a fixed patch of the office, so a pan the
    fly caused itself looks exactly like a raised tablet unless it knows it is
    mid-turn."""
    mock_user32 = MagicMock()

    with patch.object(input_controller.ctypes, 'windll', MagicMock(user32=mock_user32)),          patch.object(input_controller.time, 'sleep'):
        cmd_queue = _start_isolated_worker()
        controller = input_controller.FNAFController()

        assert controller.facing() == 'centre'

        controller.set_left_light(True)
        cmd_queue.join()
        assert controller.facing() == 'left'

        controller.set_right_light(True)
        cmd_queue.join()
        assert controller.facing() == 'right'

        controller.open_camera()
        cmd_queue.join()
        assert controller.facing() == 'centre'


def test_light_waits_for_the_office_to_swing_before_clicking():
    """The click used to fire the instant the cursor moved, so it landed while
    the office was still panning and hit whatever happened to be under it."""
    mock_user32 = MagicMock()
    sleeps = []

    with patch.object(input_controller.ctypes, 'windll', MagicMock(user32=mock_user32)), \
         patch.object(input_controller.time, 'sleep', side_effect=sleeps.append):
        cmd_queue = _start_isolated_worker()
        controller = input_controller.FNAFController()

        controller.set_left_light(True)
        cmd_queue.join()

    assert config.MOTOR_CALIBRATION.pan_delay_sec in sleeps


def test_second_action_on_the_same_side_does_not_wait_again():
    """Once the office already faces that way there is nothing to wait for, so
    turning the light back off must not cost another full pan."""
    mock_user32 = MagicMock()
    sleeps = []

    with patch.object(input_controller.ctypes, 'windll', MagicMock(user32=mock_user32)), \
         patch.object(input_controller.time, 'sleep', side_effect=sleeps.append):
        cmd_queue = _start_isolated_worker()
        controller = input_controller.FNAFController()

        controller.set_left_light(True)
        cmd_queue.join()
        pans_after_first = sleeps.count(config.MOTOR_CALIBRATION.pan_delay_sec)

        controller.set_left_light(False)
        cmd_queue.join()
        pans_after_second = sleeps.count(config.MOTOR_CALIBRATION.pan_delay_sec)

    assert pans_after_first == 1
    assert pans_after_second == 1


def test_command_reports_completion_so_the_caller_can_stop_guessing():
    mock_user32 = MagicMock()

    with patch.object(input_controller.ctypes, 'windll', MagicMock(user32=mock_user32)), \
         patch.object(input_controller.time, 'sleep'):
        _start_isolated_worker()
        controller = input_controller.FNAFController()

        done = controller.set_right_light(True)
        assert done.wait(timeout=5.0), 'worker never acknowledged the command'


def test_completion_is_reported_even_for_a_command_that_changes_nothing():
    """A no-op must still raise the flag, or a caller awaiting it hangs until
    its timeout every time the light is already in the state it asked for."""
    mock_user32 = MagicMock()

    with patch.object(input_controller.ctypes, 'windll', MagicMock(user32=mock_user32)), \
         patch.object(input_controller.time, 'sleep'):
        _start_isolated_worker()
        controller = input_controller.FNAFController()

        controller.set_left_light(False).wait(timeout=5.0)
        done = controller.set_left_light(False)
        assert done.wait(timeout=5.0), 'a redundant command never acknowledged'


if __name__ == '__main__':
    test_pan_side_classifies_every_real_button()
    test_light_waits_for_the_office_to_swing_before_clicking()
    test_second_action_on_the_same_side_does_not_wait_again()
    test_command_reports_completion_so_the_caller_can_stop_guessing()
    test_completion_is_reported_even_for_a_command_that_changes_nothing()
    print('ok')
