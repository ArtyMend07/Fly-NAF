import ctypes
import time
import config

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class FNAFController:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        
        self.l_door_x = config.MOTOR_CALIBRATION["left_door_button_x"]
        self.l_door_y = config.MOTOR_CALIBRATION["left_door_button_y"]
        self.l_light_x = config.MOTOR_CALIBRATION["left_light_button_x"]
        self.l_light_y = config.MOTOR_CALIBRATION["left_light_button_y"]
        
        self.r_door_x = config.MOTOR_CALIBRATION["right_door_button_x"]
        self.r_door_y = config.MOTOR_CALIBRATION["right_door_button_y"]
        self.r_light_x = config.MOTOR_CALIBRATION["right_light_button_x"]
        self.r_light_y = config.MOTOR_CALIBRATION["right_light_button_y"]
        
        self.is_left_light_on = False
        self.is_right_light_on = False
        
    def _move_mouse(self, x: int, y: int):
        self.user32.SetCursorPos(x, y)
        time.sleep(0.02)
        
    def _click(self):
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.02)
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def trigger_left_door(self):
        self._move_mouse(self.l_door_x, self.l_door_y)
        self._click()
        
    def trigger_right_door(self):
        self._move_mouse(self.r_door_x, self.r_door_y)
        self._click()
        
    def set_left_light(self, state: bool):
        if self.is_left_light_on != state:
            self._move_mouse(self.l_light_x, self.l_light_y)
            self._click()
            self.is_left_light_on = state
            
    def set_right_light(self, state: bool):
        if self.is_right_light_on != state:
            self._move_mouse(self.r_light_x, self.r_light_y)
            self._click()
            self.is_right_light_on = state

