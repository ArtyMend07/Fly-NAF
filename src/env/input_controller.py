import ctypes
import time

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2
KEYEVENTF_KEYUP = 0x0002

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort)
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", INPUT_I)
    ]

class FNAFController:
    def __init__(self):
        self.SendInput = ctypes.windll.user32.SendInput

    def press_key(self, hexKeyCode):
        extra = ctypes.c_ulong(0)
        ii_ = INPUT_I()
        ii_.ki = KEYBDINPUT(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
        x = INPUT(ctypes.c_ulong(1), ii_)
        self.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

    def release_key(self, hexKeyCode):
        extra = ctypes.c_ulong(0)
        ii_ = INPUT_I()
        ii_.ki = KEYBDINPUT(0, hexKeyCode, 0x0008 | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
        x = INPUT(ctypes.c_ulong(1), ii_)
        self.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
        
    def tap_key(self, hexKeyCode, duration=0.05):
        self.press_key(hexKeyCode)
        time.sleep(duration)
        self.release_key(hexKeyCode)

    def click_left_door(self):
        self.tap_key(0x1E)

if __name__ == "__main__":
    controller = FNAFController()
    time.sleep(3)
    controller.click_left_door()
