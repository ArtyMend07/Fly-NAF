# ADR 0028: A Night Reads One High Resolution Clock

## Status
Accepted.

## Context
The time of a night came from `time.time()`. The engine loop read it once per
frame, the vision loop read it before every capture, and every door, saccade and
tablet deadline was written against it. The frame budget alone was measured with
`time.perf_counter()`.

`time.time()` is the wall clock. It can be adjusted while a night runs, and on
Windows its resolution is that of the system timer, not of the processor. On the
project's Python 3.11 the three clocks resolve very different intervals.

| Clock | Implementation on Windows | Resolution |
|---|---|---|
| `time.time` | GetSystemTimeAsFileTime | 15.6 ms nominal |
| `time.monotonic` | GetTickCount64 | 15.6 ms |
| `time.perf_counter` | QueryPerformanceCounter | 0.1 us |

The wall clock ticked every millisecond while the measurement ran, because
another process had raised the timer resolution, and it ticks every 15.6 ms when
nothing has. The fly's behaviour therefore depended on what else was open.

Every leak in the loop is scaled by the measured time between frames. The door
hold decays as `hold_leak ** (frame_elapsed * fps)`, and DNp09 and the search
drive integrate over the same interval. At ten frames a second a quantum of
15.6 ms is a sixth of a frame. The tablet is worse. `LoomChannel` derives the
speed it feeds LC4 from the change in contrast over the time between two reads
taken 30 ms apart, so an interval read as one or two quanta, or as zero and
clamped to a millisecond, scales the drive by the same factor.

`time.monotonic` is the usual answer to an adjustable clock, but on this Python
it has the same 15.6 ms resolution and would not help. Python 3.13 moves it to
QueryPerformanceCounter.

## Decision
`flynaf/clock.py` exposes `now`, bound to `time.perf_counter`, and every reading
of time that a night acts on goes through it. That covers the vision and engine
loops, the hallway observation and the saccade refractory period, the office
recovery in the monitor, the tablet reference capture, the session telemetry
and the live tablet debug script. The engine loop measures its frame budget from
the same reading it hands to the engine, so the loop no longer reads two clocks.

Wall clock time stays where a person reads it, the timestamps in file names and
in the session report.

## Consequences
The intervals the leaks and the loom speed are computed from are exact to well
under a microsecond whatever the system timer is doing, and a clock adjustment
during a night no longer moves a deadline.

All of a night's times have to come from the same clock, because a door sets
`blind_until` from the engine's reading and the vision loop compares it with its
own. A new loop that reads `time.time()` directly would compare times taken on
two different clocks without any error to show for it.

The deadlines outside a night, the launcher, the overlay placement and the
Linux window settling, stay on `time.monotonic`. They only compare a reading
with another reading of the same clock, at a resolution far finer than the
seconds they wait.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the move of every time step in a night to one perf_counter clock | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
