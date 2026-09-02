import ctypes
import time
import mss
import sys

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_position():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def run_calibration():
    print("[SYSTEM] FNAF Vision Calibrator Running...")
    print("[SYSTEM] Hover over the target and press SPACEBAR to save coordinates.")
    print("[SYSTEM] The data will be saved to 'logs/calibration.txt'.")
    print("[SYSTEM] Press Ctrl+C in this terminal to exit.\n")
    
    import os
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "calibration.txt")
    
    with open(log_path, "w") as f:
        f.write("--- FNAF CALIBRATION DATA ---\n")
    
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        space_was_down = False
        
        try:
            while True:
                x, y = get_mouse_position()
                space_is_down = (ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000) != 0
                
                if monitor["left"] <= x < monitor["left"] + monitor["width"] and \
                   monitor["top"] <= y < monitor["top"] + monitor["height"]:
                    
                    bbox = {'top': y, 'left': x, 'width': 1, 'height': 1}
                    img = sct.grab(bbox)
                    b, g, r = img.pixel(0, 0)
                    
                    if space_is_down and not space_was_down:
                        data_line = f"Position: X={x:<4} Y={y:<4} | Color: R={r:<3} G={g:<3} B={b:<3}\n"
                        with open(log_path, "a") as f:
                            f.write(data_line)
                        ctypes.windll.user32.MessageBeep(0) # Toca o som de alerta do Windows
                
                space_was_down = space_is_down
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n[SYSTEM] Calibration stopped.")

if __name__ == "__main__":
    run_calibration()
