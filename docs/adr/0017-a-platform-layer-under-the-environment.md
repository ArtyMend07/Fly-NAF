# ADR 0017: A Platform Layer Under the Environment

## Status
Accepted.

## Context
Nothing in this project could be inspected by anyone who did not own a Windows
machine, a copy of Five Nights at Freddy's and an hour for calibration. That is
not a licensing problem or a data problem. It was one import.

`src/env/overlay.py` opened with `import ctypes.wintypes` and `import winreg`,
and `src/main.py` imported twelve names from it. Both of those imports fail on
Linux, so `main.py` could not be imported at all, and with it went every test
that touches the engine and every script that reads the connectome. The two
tests that prove the escape pathway, `test_inhibition.py` and
`test_pathways.py`, need nothing but `torch`, `config` and `neural/`, and they
were locked out by a registry lookup used to find a browser.

An audit of the whole source tree found the coupling is smaller than the README
suggested. Eight of the main modules already run anywhere, `mss` is
cross-platform and the code uses its modern `MSS` class, and the motor layer
reduces to five Win32 calls. Two of the four affected files are standalone
calibration tools that never run during a night.

## Decision
The operating system surface moves behind `src/env/desktop/`, which picks a
backend at import time from `sys.platform`, or from `FLYNAF_PLATFORM` when it is
set. Three backends implement the same functions.

`windows.py` receives the existing code unchanged, so a night on Windows behaves
exactly as before. `linux.py` reaches X11 through Xlib, with EWMH for window
enumeration and focus, XTEST for cursor and clicks, and an empty Shape input
region for the click-through panel, since X11 has no equivalent of
`WS_EX_TRANSPARENT`. `headless.py` answers every call without a display and
records the cursor and clicks in memory, which is what the replay path consumes.

`overlay.py` keeps only geometry that was already portable and delegates the
rest. `input_controller.py` keeps its queue, its facing state and its timing and
calls three functions on the layer.

A backend that fails to import falls back to headless with a warning rather than
bringing the process down, because a missing Xlib should cost the panel, not the
run.

## Consequences
The verification script and the connectome tests run on Linux and macOS without
a game, a display or a purchase. That is the point of the change. A reviewer who
wants to check that 138,639 neurons are really in the loop can now do it in a
minute on a machine that will never run the game.

Wayland is not supported and will not be. Screen capture through mss, synthetic
global pointer input and client-side input shaping are all unavailable to a
Wayland client by design. An X11 session is required, and the game itself runs
under Wine or Proton, which changes what the window reports as its process name.

The mocking seam in the motor tests moved from `ctypes.windll` to the platform
module. That is a better seam, because it names the three operations the motor
layer actually performs instead of the Windows API it used to reach for.
`AttachThreadInput` has no analogue on X11 and simply disappears there, since
X11 has no foreground lock to work around.

The first run of the X11 backend against a live server, under WSLg, found that
every request sent to the window manager used event mask names that do not
exist in python-xlib. The exception was caught, so the panel was never asked to
stay above the game and the focus handback never reached the window manager,
while the unit tests, which mock the backend, kept passing. The masks are now
the real ones and the handback identifies itself as a pager, which window
managers with focus stealing prevention honour where they may refuse an
ordinary application. The same run showed that a window manager does not have
to publish `_NET_CLIENT_LIST`, so the window lookup falls back to walking the
tree for the ICCCM `WM_STATE` property that every managed client carries.

WSLg itself is Wayland underneath, with X11 clients served through XWayland.
It refuses focus requests from X11 clients, ignores the always on top and
undecorated hints and draws its own frame, which is the Wayland limit above in
a form that looks like X11. Window lookup, geometry, pointer input and input
shaping all work there. A browser started for the panel receives `SIGKILL`
through `PR_SET_PDEATHSIG` when the process that started it dies, the Linux
counterpart of the Windows job object in ADR 0021.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the platform layer and the Wayland limit | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 |
| 1.1 | Recorded the first live X11 run, its fixes and the WSLg limits | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
