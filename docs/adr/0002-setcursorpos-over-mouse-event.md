# 0002. Use SetCursorPos over Normalized mouse_event for OS Interaction

## Status
Accepted

## Context
To physically click the door button in FNAF 1, the biological neural network outputs a motor spike that must be translated into a Windows OS mouse click. Initially, `ctypes.windll.user32.mouse_event` was used with the `MOUSEEVENTF_ABSOLUTE` flag, which requires normalizing screen coordinates into a `0-65535` grid divided by the current screen width/height. 
However, modern Windows environments frequently use UI Scaling (something like 125% or 150%). This scaling corrupts the math for `GetSystemMetrics(0/1)`, causing the normalized coordinates to drift and the mouse to click significantly offset from the intended target.

## Decision
I will bypass normalized coordinates and use `ctypes.windll.user32.SetCursorPos(x, y)` to move the mouse using raw absolute pixel coordinates obtained directly from calibration, followed by `mouse_event` strictly for the `LEFTDOWN` and `LEFTUP` actions.

## Consequences
**Positive:**
- Eliminates coordinate drift caused by Windows UI scaling math bugs.
- A 1:1 match with the coordinates obtained during the `calibrator.py` step (which uses `GetCursorPos`).

**Negative:**
- `SetCursorPos` can be overridden or ignored by exclusive full-screen environments that rely on raw mouse deltas (Pointer Lock). If the game client traps the mouse at the OS level, this method may fail to move the cursor visually.
