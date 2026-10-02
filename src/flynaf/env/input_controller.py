import logging
import queue
import threading
import time

from flynaf import config
from flynaf.env import anchor, desktop

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
    def _reach(x: int, y: int):
        side = _pan_side(x)
        moved = side != office_facing()
        if moved:
            _set_facing('panning')
        desktop.move_cursor(*anchor.point(x, y))
        if moved:
            time.sleep(config.MOTOR_CALIBRATION.pan_delay_sec)
            _set_facing(side)
        else:
            time.sleep(config.MOTOR_CALIBRATION.click_delay_sec)

    def _click():
        desktop.mouse_down()
        time.sleep(config.MOTOR_CALIBRATION.click_delay_sec)
        desktop.mouse_up()

    def _flip(x: int, y_from: int, y_to: int, steps: int = 20, delay: float = 0.008):
        desktop.move_cursor(*anchor.point(x, y_from))
        for i in range(1, steps + 1):
            y = y_from + int((y_to - y_from) * i / steps)
            desktop.move_cursor(*anchor.point(x, y))
            time.sleep(delay)
        for offset in (8, 16, 8, 0):
            time.sleep(0.04)
            desktop.move_cursor(*anchor.point(x + offset, y_to))
        _set_facing(_pan_side(x))

    light_state = {'left': False, 'right': False}
    door_state = {'left': False, 'right': False}

    while True:
        cmd = _CMD_QUEUE.get()
        action = cmd.get('action')
        done = cmd.get('done')
        try:
            _dispatch(cmd, action, _reach, _click, _flip, light_state, door_state)
        finally:
            if done is not None:
                done.set()
            _CMD_QUEUE.task_done()


def _dispatch(cmd, action, _reach, _click, _flip, light_state, door_state):
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

    elif action in ('press_left_light', 'press_right_light'):
        side = action.split('_')[1]
        _reach(getattr(motor, f'{side}_light_button_x'), getattr(motor, f'{side}_light_button_y'))
        _click()
        light_state[side] = cmd.get('state', not light_state[side])

    elif action == 'flip_tablet':
        _flip(motor.camera_hover_x, motor.camera_bar_approach_y, motor.camera_hover_y)

    elif action == 'select_camera':
        button = _camera_button(cmd.get('camera'))
        if button is not None:
            time.sleep(cmd.get('settle_sec', 0.0))
            desktop.move_cursor(*anchor.point(button.x, button.y))
            time.sleep(motor.click_delay_sec)
            _click()

    else:
        _log.warning('unknown command action: %s', action)


def _camera_button(name):
    for button in config.TABLET_VISION.cameras:
        if button.name == name:
            return button
    _log.warning('no map button is calibrated for camera %s', name)
    return None


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

    def press_left_light(self, state: bool) -> threading.Event:
        return _submit(action='press_left_light', state=state)

    def press_right_light(self, state: bool) -> threading.Event:
        return _submit(action='press_right_light', state=state)

    def flip_tablet(self) -> threading.Event:
        return _submit(action='flip_tablet')

    def select_camera(self, camera: str, settle_sec: float = 0.0) -> threading.Event:
        return _submit(action='select_camera', camera=camera, settle_sec=settle_sec)
