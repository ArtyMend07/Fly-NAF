# ADR 0018: Screen Targets Follow The Game Window

## Status
Accepted. Supersedes the manual calibration step described in ADR 0001.

## Context
Every click target and capture box in `config.py` was an absolute desktop pixel,
measured once against a 1280x720 game window pushed into the top left corner of
the display. Fifteen constants encoded that one layout. Anybody with a different
resolution, a different window position or a second monitor had to re-measure
all of them with `select_roi.py` and `vision_calibrator.py` before the fly could
see or click anything, and a mistake produced a fly that silently read the wrong
pixels for a whole night.

The odd part is that the game window was already being located. `find_game_window`
matched it by process name and then by title, and the handle it returned was used
only to check and restore focus. `GetWindowRect` was never called on it. The
information that would have removed the entire calibration step was being
fetched and thrown away.

Three latent defects came out of the same audit. `_grab_gray` computed
`left = x - size // 2` with no clamp, and with the shipped numbers the left
hallway box already sat exactly on the screen edge at zero, so any adjustment
pushed it negative. The cached eye references were validated only by pixel
shape, so moving a capture point without changing its size loaded a reference
taken from somewhere else on screen, with no warning and no way to notice.
And `_pan_side` compared against a fixed 200 pixel threshold.

## Decision
The constants in `config.py` are reinterpreted as a design space of 1280x720
rather than as desktop pixels. `src/env/anchor.py` holds the measured client
rectangle of the game window and converts a design coordinate to a screen
coordinate at the moment it is used.

`main()` calls `anchor_to_game()` at startup. When the window is found, the fly
follows it at whatever size and position it has. When it is not found, the
anchor stays unset and resolves as the identity, which reproduces the previous
behaviour exactly, so an unanchored run is the old run.

The capture box is clamped against the screen bounds. The reference cache gains
a fingerprint file recording the coordinates and the window rectangle it was
captured with, and a mismatch triggers recapture instead of loading a stale
image. An absent fingerprint is accepted, so caches written before this change
still load.

## Consequences
The calibration step is no longer required for an ordinary setup, and the
1280x720 requirement becomes a recommendation rather than a precondition. The
calibration scripts stay, because a window whose client area is not a 16:9
letterbox of the reference layout will still need them, and because they remain
the way to inspect what each region reads.

The design space is deliberately the game window and not the screen. This is
what makes `screen_center_y = 540` behave sensibly, since it is three quarters
of the way down a 720 tall window rather than half of a 1080 tall monitor, which
is what it happened to coincide with on the machine it was measured on.

Scaling is linear and uniform, so a window whose aspect ratio differs from 16:9
will put the targets slightly off. That is a real limit, and it is the reason
the anchor logs the scale factors it derived when it attaches.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the move from absolute pixels to window-relative targets | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 |
