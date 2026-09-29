# ADR 0024: The Night Is A Package And Main Only Wires It

## Status
Accepted.

## Context
`src/main.py` had grown to 871 lines and held five unrelated things. It carried
the sensory state and the connectome engine, the calibration flow, the tablet
control, the three asynchronous loops that run a night, and the lifecycle of the
browser window that draws the panel. Every one of them was reached through
`main`, so the tests patched names inside it, and two pieces of process wide
state lived there as module globals, the hook that starts the night and the
session recorder. Reading the file to change one behaviour meant reading all of
them, and a change to the panel window could not be reviewed apart from a change
to the fly's decisions.

## Decision
The parts move into a package, `src/night/`, one module for each responsibility,
and `main.py` keeps only the wiring of a run and its entry function.

| Module | Holds |
|---|---|
| `night/state.py` | `SensoryState`, `MotorRefrac`, `SaccadeRequest` |
| `night/engine.py` | `ConnectomeEngine` |
| `night/motor.py` | `await_motor`, the wait on a motor command |
| `night/calibration.py` | the countdown, the game in front check, the eye reference capture and `calibrate` |
| `night/monitor.py` | `MonitorControl` and the recovery of the office reference |
| `night/tasks.py` | the vision, saccade and engine loops and `observe_hallway` |
| `night/panel.py` | the browser window of the panel, its pinning, its focus handback and its shutdown |

The code moved unchanged. Names that other modules now import lost their leading
underscore, since an underscore promises that nothing outside the module uses
the name.

The two globals became arguments. `calibrate` and `saccade_task` receive the
hook that starts the night, and `engine_task` receives the session recorder, so
a test states what it feeds a loop instead of patching a variable in another
module. Both default to nothing, which keeps the loops usable without a
launcher and without a recording.

`ConnectomeEngine.num_neurons` replaces a reach into the engine's private
adapter.

## Consequences
`main.py` is 74 lines. A change to the fly's decisions touches `tasks.py` or
`monitor.py`, and a change to the window touches `panel.py`, so a reviewer sees
the one that matters.

The earlier records name the old places. `_engine_task`, `_saccade_task` and the
observation of a hallway are now in `night/tasks.py`, `MonitorControl` and its
recovery are in `night/monitor.py`, `_calibrate` is `calibrate` in
`night/calibration.py`, and `_launch_brain_view_window` and its shutdown are in
`night/panel.py`. ADR 0012, ADR 0015 and experiments 08 and 09 keep the names
they were written with.

`engine_task` is still a single long function. Splitting it needs its own
decision, because the door state it keeps in local variables is shared by the
release and the panic paths, and moving it without changing behaviour was the
constraint of this change.

The logger name of each message changed with its module. The log format does not
print it, so nothing visible changed.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the split of main into the night package | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 |
