import ctypes
import queue
import threading
import time
import logging
import config

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

_CMD_QUEUE: queue.Queue = queue.Queue()
_log = logging.getLogger(__name__)


def _worker():
    user32 = ctypes.windll.user32

    def _move(x: int, y: int):
        user32.SetCursorPos(x, y)
        time.sleep(config.MOTOR_CALIBRATION.click_delay_sec)

    def _click():
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(config.MOTOR_CALIBRATION.click_delay_sec)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    light_state = {'left': False, 'right': False}

    while True:
        cmd = _CMD_QUEUE.get()
        action = cmd.get('action')

        if action == 'close_left_door':
            _move(config.MOTOR_CALIBRATION.left_door_button_x, config.MOTOR_CALIBRATION.left_door_button_y)
            _click()

        elif action == 'close_right_door':
            _move(config.MOTOR_CALIBRATION.right_door_button_x, config.MOTOR_CALIBRATION.right_door_button_y)
            _click()

        elif action == 'set_left_light':
            state = cmd.get('state', False)
            if light_state['left'] != state:
                _move(config.MOTOR_CALIBRATION.left_light_button_x, config.MOTOR_CALIBRATION.left_light_button_y)
                if state:
                    time.sleep(config.MOTOR_CALIBRATION.pan_delay_sec)
                _click()
                light_state['left'] = state

        elif action == 'set_right_light':
            state = cmd.get('state', False)
            if light_state['right'] != state:
                _move(config.MOTOR_CALIBRATION.right_light_button_x, config.MOTOR_CALIBRATION.right_light_button_y)
                if state:
                    time.sleep(config.MOTOR_CALIBRATION.pan_delay_sec)
                _click()
                light_state['right'] = state

        elif action == 'toggle_camera':
            _move(config.MOTOR_CALIBRATION.camera_hover_x, config.MOTOR_CALIBRATION.camera_hover_y)
            _move(config.MOTOR_CALIBRATION.camera_hover_x, config.MOTOR_CALIBRATION.screen_center_y)

        else:
            _log.warning('unknown command action: %s', action)

        _CMD_QUEUE.task_done()


def start_worker():
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


class FNAFController:
    def trigger_left_door(self):
        _CMD_QUEUE.put({'action': 'close_left_door'})

    def trigger_right_door(self):
        _CMD_QUEUE.put({'action': 'close_right_door'})

    def set_left_light(self, state: bool):
        _CMD_QUEUE.put({'action': 'set_left_light', 'state': state})

    def set_right_light(self, state: bool):
        _CMD_QUEUE.put({'action': 'set_right_light', 'state': state})

    def toggle_camera(self):
        _CMD_QUEUE.put({'action': 'toggle_camera'})