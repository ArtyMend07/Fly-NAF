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

    def _slide(x: int, y_from: int, y_to: int, steps: int = 20, delay: float = 0.008):
        for i in range(1, steps + 1):
            y = y_from + int((y_to - y_from) * i / steps)
            user32.SetCursorPos(x, y)
            time.sleep(delay)


    light_state = {'left': False, 'right': False}
    camera_state = {'open': False}

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
                _click()
                light_state['left'] = state

        elif action == 'set_right_light':
            state = cmd.get('state', False)
            if light_state['right'] != state:
                _move(config.MOTOR_CALIBRATION.right_light_button_x, config.MOTOR_CALIBRATION.right_light_button_y)
                _click()
                light_state['right'] = state

        elif action == 'open_camera':
            cx = config.MOTOR_CALIBRATION.camera_hover_x
            top = config.MOTOR_CALIBRATION.screen_center_y
            bot = config.MOTOR_CALIBRATION.camera_hover_y
            if not camera_state['open']:
                _slide(cx, top, bot)
                camera_state['open'] = True

        elif action == 'close_camera':
            cx = config.MOTOR_CALIBRATION.camera_hover_x
            top = config.MOTOR_CALIBRATION.screen_center_y
            bot = config.MOTOR_CALIBRATION.camera_hover_y
            if camera_state['open']:
                _slide(cx, bot, top)
                camera_state['open'] = False

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

    def open_camera(self):
        _CMD_QUEUE.put({'action': 'open_camera'})

    def close_camera(self):
        _CMD_QUEUE.put({'action': 'close_camera'})