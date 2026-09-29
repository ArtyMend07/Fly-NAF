# ADR 0019: Recorded Nights Replace The Missing Demo

## Status
Accepted.

## Context
Every public listing of this project carries the same two words, no demo. The
curated indexes that rate connectome projects hold this one as unrated on the
grounds that nobody has read it closely enough to attach evidence, and that what
they have is a description taken from a secondary source rather than an
independent reproduction. That is a fair assessment of the situation. Until this
change there was no way to see the fly behave, or to check that it behaves the
way the README claims, without owning the game.

The cost of reproducing a night is the obstacle, not the willingness. A reviewer
needs Windows, a purchased copy of the game, 140 MB of third party data and a
calibration pass before the first frame runs.

## Decision
A run writes a trace, and the trace can be replayed through the brain without the
game.

`src/recorder.py` appends one JSON line per engine frame holding the three fields
of `SensoryState`, the raw hallway readings, the tablet state, whether each giant
fiber fired, and the two membrane potentials the decision layers read. The header
line records the connectome file and every setting in force, so a trace carries
the conditions it was made under.

`src/replay.py` feeds a trace back into a real `ConnectomeEngine` and writes a
report. It drives the engine directly rather than impersonating the vision and
motor layers, because the question a reviewer is asking is narrow. Given this
input, does DNp01 answer, how long does it take, and does it stay quiet when
nothing is on screen.

Replay does not reproduce the recorded night frame for frame, and the report says
so in the report itself rather than in a footnote. The Poisson generator and the
subliminal noise are unseeded on purpose, because the fly is meant to behave
stochastically. What is checked across runs is the shape. The fiber answers while
its own eye is driven, it is quiet on idle frames, and the latency lands in the
seven to nine frame band ADR 0013 measured.

## Consequences
A reviewer with the data and no game can now confirm the central claim on any
operating system, which is what ADR 0017 made possible and what this decision
makes worth doing. Recording is on by default and can be turned off with
`FLYNAF_RECORD=0`.

The trace is the evidence the project was missing, and it is small. A ten minute
night is a few thousand lines of JSON. Traces are kept out of the repository
along with the rest of `logs/`, but a representative one can be committed
deliberately when it is worth citing.

Replay is not a regression test and must not be read as one. A run that differs
by a few spikes is the fly being a fly. A run where the fiber never answers, or
answers with nothing on screen, is a real failure, and those are the only two
conditions worth alarming on.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the trace format and what replay does and does not prove | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 |
