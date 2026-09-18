import ctypes
import queue
import threading
import time
import logging
import config

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

_CMD_QUEUE: queue.Queue = queue.Queue()
_FACING = {'side': 'centre'}
_FACING_LOCK = threading.Lock()
_log = logging.getLogger(__name__)


def office_facing() -> str:
    with _FACING_LOCK:
        return _FACING['side']


def _set_facing(side: str):
    with _FACING_LOCK:
        _FACING['side'] = side


def _pan_side(x: int) -> str:
    centre = config.MOTOR_CALIBRATION.camera_hover_x
    if x < centre - 200:
        return 'left'
    if x > centre + 200:
        return 'right'
    return 'centre'


def _worker():
    user32 = ctypes.windll.user32

    def _reach(x: int, y: int):
        side = _pan_side(x)
        moved = side != office_facing()
        if moved:
            _set_facing('panning')
        user32.SetCursorPos(x, y)
        if moved:
            time.sleep(config.MOTOR_CALIBRATION.pan_delay_sec)
            _set_facing(side)
        else:
            time.sleep(config.MOTOR_CALIBRATION.click_delay_sec)

    def _click():
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(config.MOTOR_CALIBRATION.click_delay_sec)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def _slide(x: int, y_from: int, y_to: int, steps: int = 20, delay: float = 0.008):
        side = _pan_side(x)
        swinging = side != office_facing()
        _set_facing('panning')
        for i in range(1, steps + 1):
            y = y_from + int((y_to - y_from) * i / steps)
            user32.SetCursorPos(x, y)
            time.sleep(delay)
        if swinging:
            time.sleep(config.MOTOR_CALIBRATION.pan_delay_sec)
        _set_facing(side)


    light_state = {'left': False, 'right': False}
    camera_state = {'open': False}
    door_state = {'left': False, 'right': False}

    while True:
        cmd = _CMD_QUEUE.get()
        action = cmd.get('action')
        done = cmd.get('done')
        try:
            _dispatch(cmd, action, _reach, _click, _slide, light_state, camera_state, door_state)
        finally:
            if done is not None:
                done.set()
            _CMD_QUEUE.task_done()


def _dispatch(cmd, action, _reach, _click, _slide, light_state, camera_state, door_state):
    motor = config.MOTOR_CALIBRATION

    if action in ('close_left_door', 'open_left_door'):
        wanted = action.startswith('close')
        if door_state['left'] != wanted:
            _reach(motor.left_door_button_x, motor.left_door_button_y)
            _click()
            door_state['left'] = wanted

    elif action in ('close_right_door', 'open_right_door'):
        wanted = action.startswith('close')
        if door_state['right'] != wanted:
            _reach(motor.right_door_button_x, motor.right_door_button_y)
            _click()
            door_state['right'] = wanted

    elif action == 'set_left_light':
        state = cmd.get('state', False)
        if light_state['left'] != state:
            _reach(motor.left_light_button_x, motor.left_light_button_y)
            _click()
            light_state['left'] = state

    elif action == 'set_right_light':
        state = cmd.get('state', False)
        if light_state['right'] != state:
            _reach(motor.right_light_button_x, motor.right_light_button_y)
            _click()
            light_state['right'] = state

    elif action == 'centre_view':
        _reach(motor.camera_hover_x, motor.screen_center_y)

    elif action == 'open_camera':
        if not camera_state['open']:
            _slide(motor.camera_hover_x, motor.screen_center_y, motor.camera_hover_y)
            camera_state['open'] = True

    elif action == 'close_camera':
        if camera_state['open'] or cmd.get('force'):
            _slide(motor.camera_hover_x, motor.camera_hover_y, motor.screen_center_y)
            camera_state['open'] = False

    elif action == 'nudge_camera_bar':
        _slide(motor.camera_hover_x, motor.screen_center_y, motor.camera_hover_y)
        time.sleep(motor.camera_bar_dwell_sec)
        _slide(motor.camera_hover_x, motor.camera_hover_y, motor.screen_center_y)
        camera_state['open'] = False

    else:
        _log.warning('unknown command action: %s', action)


def start_worker():
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _submit(**cmd) -> threading.Event:
    done = threading.Event()
    cmd['done'] = done
    _CMD_QUEUE.put(cmd)
    return done


class FNAFController:
    def facing(self) -> str:
        return office_facing()

    def trigger_left_door(self) -> threading.Event:
        return _submit(action='close_left_door')

    def trigger_right_door(self) -> threading.Event:
        return _submit(action='close_right_door')

    def open_left_door(self) -> threading.Event:
        return _submit(action='open_left_door')

    def open_right_door(self) -> threading.Event:
        return _submit(action='open_right_door')

    def set_left_light(self, state: bool) -> threading.Event:
        return _submit(action='set_left_light', state=state)

    def set_right_light(self, state: bool) -> threading.Event:
        return _submit(action='set_right_light', state=state)

    def centre_view(self) -> threading.Event:
        return _submit(action='centre_view')

    def open_camera(self) -> threading.Event:
        return _submit(action='open_camera')

    def close_camera(self, force: bool = False) -> threading.Event:
        return _submit(action='close_camera', force=force)

    def nudge_camera_bar(self) -> threading.Event:
        return _submit(action='nudge_camera_bar')