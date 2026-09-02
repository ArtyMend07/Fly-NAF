import ctypes
import time

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class FNAFController:
    def __init__(self, left_door_x: int, left_door_y: int):
        self.user32 = ctypes.windll.user32
        self.left_door_x = left_door_x
        self.left_door_y = left_door_y
        
    def _move_mouse(self, x: int, y: int):
        self.user32.SetCursorPos(x, y)
        time.sleep(0.05)
        
    def _click(self):
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def trigger_left_door(self):
        self._move_mouse(self.left_door_x, self.left_door_y)
        self._click()
