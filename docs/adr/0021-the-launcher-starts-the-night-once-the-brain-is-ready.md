# ADR 0021: The Launcher Starts The Night Once The Brain Is Ready

## Status
Accepted. Amends ADR 0018 on when the game window is measured.

## Context
Starting a night asked the operator for a sequence with a deadline. Open the
game by hand, run the script from a terminal, wait for the connectome to load,
then reach the game and start a night inside a ten second countdown. Missing
the window left the fly reading whatever was on screen, and nothing in the flow
told a newcomer which of those steps had gone wrong.

A live measurement against the fullscreen game showed that ADR 0018 had two
defects of its own. The window was measured once, when the process started,
which is exactly the moment the operator is in the terminal and a fullscreen
game is minimised. Windows reports a minimised window as a 158 by 26 rectangle
near minus twenty one thousand on both axes, and every click and capture would
have been scaled onto it. Separately, the check that the game was in front
compared window handles, while the lookup only enumerated windows that carry a
title. With the game fullscreen and focused, the check never succeeded during a
three minute observation, and the countdown's own confirmation relies on the
same comparison.

The game makes the rest easy. It is built on Clickteam Fusion, which always
draws at 1280x720 and in fullscreen switches the display to that mode, so every
menu button sits at one fixed point of the reference layout. The save file at
`%APPDATA%\MMFApplications\freddy` holds the night reached as a plain
`level=` line.

## Decision
A minimised window is never measured, and the game is measured again at the
moment the night starts, when it is confirmed to be in front. Being in front
means that the foreground window belongs to the game's process, not that it is
one particular handle, and untitled windows are part of the lookup. When no
game window is in front, the largest one that is showing wins over a minimised
frame.

`run.py` opens a launcher before anything else. It is a local page drawn as the
front of a fly's head, with New Game and Continue inside the two compound eyes,
the saved night shown in the Continue eye, and three ocelli that light for the
connectome data, the game and the menu calibration. The choice opens the game
through its Steam URI, or through a configured executable for other stores, and
hands `main()` a hook that replaces the countdown. The hook runs after the
connectome has loaded, brings the game to the front and clicks the chosen menu
point. `--new`, `--continue` and `--manual` make the same choice without the
page, and a terminal prompt stands in when no Chromium browser is installed.

The launcher page was later redrawn as a scene rather than a diagram. It shows the NeuroMechFly body model, a micro-CT reconstruction of a female fly, standing on a desk under a flickering lamp in front of a tiled wall, seen through a security camera filter. New Game and Continue are still the two compound eyes, now picked by a ray cast against the real eye meshes, and each eye shows the pseudopupil, the dark patch a real compound eye shows in the direction it is viewed from. The model ships as a posed and quantised file built by `build_fly_model.py` from the Apache 2.0 flygym assets, and a page without WebGL falls back to plain buttons.

The two menu points ship unset and are measured once by the operator. Until
they are, the launcher still opens and focuses the game and leaves the click to
the operator. It never clicks a game it did not open in that run, because a
game that was already running may be in the middle of a night, where the same
point can land on the office.

## Consequences
The night no longer starts before the brain can play it. On a first night that
costs nothing, but on a continued night the animatronics are already active
from the first second, and a fly still loading its connectome would have spent
that time blind.

The waits after the menu click are motor durations, the time the newspaper and
the night card take to clear, and they are configured in `GameLauncher` rather
than chosen by the network. They decide nothing about the night.

The launcher launches a copy the operator already owns and distributes nothing.
The game art that the eye references capture is still taken from the
operator's own screen on the first night, as before.

A live run showed that exclusive fullscreen cannot coexist with the panel.
Any new window that takes the foreground makes Windows minimise an exclusive
fullscreen game, and a Clickteam game that loses its Direct3D device this way
often comes back as a black screen, a failure its players report on the Steam
forums as the Alt+Tab bug. The launcher therefore puts the game in a window
with Alt+Enter before the brain loads, and waits until the window has stayed
smaller than the display for a moment before it moves on. A windowed game does
not lose its device when another window appears, and the panel can sit beside
it. `GameLauncher.windowed` turns this off for an operator who accepts the risk.

The measurement of the menu points is the one step of setup that remains
manual. It happens once per install rather than once per resolution, since the
points are in the reference layout.

The browser that draws the panel is a process the operator did not ask for by
name, and closing `run.py` with Ctrl+C or letting it finish already terminates
it through `LauncherWindow.close` and the brain view shutdown path. What those
paths cannot reach is the operator ending the Python process itself from the
task manager or a forceful `taskkill`, since Windows does not kill a process's
children when the parent dies, so the panel or the launcher window used to
outlive the run that opened them. The browser is now started inside a Windows
job object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, a construct whose whole
purpose is that closing the job's last handle kills every process assigned to
it. Python holds that handle for as long as it runs, and the operating system
closes it on any exit of the Python process, graceful or not, which closes the
browser with it. On Linux the kernel gives the same guarantee through
`PR_SET_PDEATHSIG`, set in the child before it executes the browser. The
headless backend opens no browser and keeps a plain `Popen`.

Each browser gets a fresh profile directory, because Chromium hands a second
launch on a busy profile over to the process already running there and every
window flag of the new launch is lost. A fresh profile weighs about sixty
megabytes and would otherwise stay in the temporary directory forever. Every
launch and every shutdown of the panel removes the profiles that no live
browser holds, which Chromium itself reports through the `lockfile` it keeps
open on Windows and the `SingletonLock` link naming its process on Linux. The
first run of the sweep removed ten stale profiles, 460 megabytes in all. A
fresh profile is also a first run to Edge, which answers it with a sync
consent bubble over the panel, and `--disable-sync` suppresses it.

A window whose title merely contains the name of the game is not the game. A
browser tab open on this repository's page carries the name in its title, and it
made the lookup report a running game, so the launcher skipped opening it and
went straight to the brain. The title fallback now requires the whole title to be
the game's, and the process name stays the primary test.
Being ready also has to mean that the brain has stopped starting up. Almost every recorded night opened with a door slam the eye did not cause. Of course it was weird, in seven of the eight traces long enough to tell, DNp01 fired within the first ten engine frames with both eye populations at zero input. The engine used to take its first step only once calibration had finished, from `reset_state`, which puts all 138,639 neurons at `v0` with no conductance. Stepped from there with only the background noise, the network recruits about 150 active neurons per frame up to about 3,000, excitation outruns the inhibition that later balances it, and over four measured starts the Giant Fiber fired inside that wave three times, always between frames 10 and 17, and never after frame 20. A real fly has no such moment, because its brain was running long before it was put in front of the hallways. The engine now steps without input while calibration runs, until the neurons active in the last ten frames are no more than 1.2 times those in the ten before, with a cap of 200 frames, and nothing in that warm-up reaches a motor path. The measured wave first meets the criterion around frame 30. Over six fresh starts the network settled after 29 to 35 frames and the Giant Fiber stayed silent through the 150 unstimulated frames that followed each one. The session report prints the warm-up, and `replay` settles the engine the same way before it feeds a recorded night.

The window has to be measured in physical pixels too. Windows reports window rectangles scaled down by the display setting to any process that has not declared itself DPI aware, and the declaration used to happen as a side effect of the first `screen_size()` call. On a display at 150 percent, a run started with `--manual` measured the game at 213,131 sized 853x480 instead of 320,197 sized 1280x720 and placed the panel "beside" a game that actually extended under it, over the right eye, the right door and light buttons and part of the camera map. The Windows backend now declares DPI awareness when it is loaded, before anything reads a coordinate.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the launcher and the corrected window measurement | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
| 1.1 | Put the game in a window before the panel opens | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
| 1.2 | Tied the browser's lifetime to the Python process with a job object | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
| 1.3 | Recorded the profile sweep, the sync bubble and the Linux parent death signal | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
| 1.4 | Replaced the drawn head with the NeuroMechFly model in a night office scene | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 |
| 1.5 | Required the whole window title to match the game | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 |
| 1.6 | Warmed the network up before the night and declared DPI awareness before the first window measurement | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
