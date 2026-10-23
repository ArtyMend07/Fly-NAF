# ADR 0019: Recorded Nights Replace The Missing Demo

## Status
Accepted.

## Context
Every public listing of this project carries the same two words, no demo. The curated indexes that rate connectome projects hold this one as unrated on the grounds that nobody has read it closely enough to attach evidence, and that what they have is a description taken from a secondary source rather than an independent reproduction. That is a fair assessment of the situation. Until this change there was no way to see the fly behave, or to check that it behaves the way the README claims, without owning the game.

The cost of reproducing a night is the obstacle, not the willingness. A reviewer needs Windows, a purchased copy of the game, 140 MB of third party data and a calibration pass before the first frame runs.

## Decision
A run writes a trace, and the trace can be replayed through the brain without the game.

`src/recorder.py` appends one JSON line per engine frame holding the three fields of `SensoryState`, the raw hallway readings, the tablet state, whether each giant fiber fired, and the two membrane potentials the decision layers read. The header line records the connectome file and every setting in force, so a trace carries the conditions it was made under.

`src/replay.py` feeds a trace back into a real `ConnectomeEngine` and writes a report. It drives the engine directly rather than impersonating the vision and motor layers, because the question a reviewer is asking is narrow. Given this input, does DNp01 answer, how long does it take, and does it stay quiet when nothing is on screen.

Replay does not reproduce the recorded night frame for frame, and the report says so in the report itself rather than in a footnote. The Poisson generator and the subliminal noise are unseeded on purpose, because the fly is meant to behave stochastically. What is checked across runs is the shape. The fiber answers while its own eye is driven, it is quiet on idle frames, and the latency lands in the seven to nine frame band ADR 0013 measured.

### Amendment, 2026-10-21: the screen is recorded too, and a night can be audited

A trace holds what the fly read and what it decided, and nothing of what the game did with it. The night 3 of 2026-10-21 was the first the fly passed, with the power gone about fifty seconds before 6 AM, and neither the log nor the trace could say where the battery went, or that the right door had stood open for three minutes while the fly held it shut. A release click had not landed, and the next close opened the door instead.

`run.py --frames` starts `flynaf/env/frame_recorder.py`, which saves the game window about three times a second into `logs/frames/`, under the stamp of the trace. Each frame is named by the clock the trace uses, so a frame and the trace line of the same moment carry the same time.

`python -m flynaf.scripts.audit_night <night>` reads those frames with `flynaf.audit`:

- From each frame, the usage bars of the power HUD, the colour of the two door buttons, green when the door is shut and red when it is open, and whether the camera map is up.
- The power split between the office, the passive drain of the night, the tablet, each door and the lights. The rules are the ones the [Technical FNAF wiki](https://technicalfnaf.fandom.com/wiki/Power_Mechanics_(Fnaf_1)) gives: 0.1 percent a second for each usage bar, and from night 2 on another 0.1 percent every 6, 5, 4 or 3 seconds. A door is held in the state it was last seen in while the office faces the other way, and the lights are what is left of the bars once the tablet and the doors are counted.
- For each shut door, the seconds in which its lit window showed someone, showed nobody, or had not been looked at since the door shut. The window is read against the closed-door references and the threshold the eye itself uses, and a reading counts only once two lit frames in a row agree, because the frame in which the light goes off still shows the button lit over a dark window.
- Every stretch of at least two seconds in which a door on screen disagreed with what the fly believed, split where the screen changed.
- The spending minute by minute, with the watches begun in each.
- Whether the night ended with the power out, which shows as the HUD giving way to a dark office before 6 AM. The battery is full at midnight, so whatever the bars leave unexplained went where they do not show, such as Foxy hitting a shut door, which the same wiki puts at 1, 6, 11 and 16 percent for each hit in turn.
- What each look at CAM 1C read, from the trace.

The audit is printed and saved to `logs/audits/` under the same stamp. It stops at the first absence of the HUD longer than twenty seconds, because after 6 AM the game goes straight into the next night and the fly does not stop.

## Consequences
A reviewer with the data and no game can now confirm the central claim on any operating system, which is what ADR 0017 made possible and what this decision makes worth doing. Recording is on by default and can be turned off with `FLYNAF_RECORD=0`.

The trace is the evidence the project was missing, and it is small. A ten minute night is a few thousand lines of JSON. Traces are kept out of the repository along with the rest of `logs/`, but a representative one can be committed deliberately when it is worth citing.

Replay is not a regression test and must not be read as one. A run that differs by a few spikes is the fly being a fly. A run where the fiber never answers, or answers with nothing on screen, is a real failure, and those are the only two conditions worth alarming on.

Frames are recorded only when asked for. A night at three frames a second is about 150 MB of JPEG, and they stay out of the repository with the rest of `logs/`, since every one of them is a picture of a commercial game. The tests draw their own HUD instead.

On the night 3 of 2026-10-21 the audit summed to 99.4 percent of the battery: 49.8 for the office, 10.0 of passive drain, 14.2 for the tablet over 34 watches, 14.1 for the left door, 7.2 for the lights and 4.3 for the right door. Of the 141 seconds of left door, 111 had Bonnie's shadow in the lit window and 29 had nobody, the half minute in which the door was held for a Foxy still inside the cove. The split is only as fine as the HUD, since the game draws a whole bar for whatever is on and charges by the second.

The night 4 that followed lost its power at about 4 AM, and the bars explained 82.1 percent of the battery. Between two looks at the cove Foxy left three times, found the left door shut and went back to peeking, and the three hits, 1, 6 and 11 percent, are the 18 percent the bars do not show. The left door was shut for 259 seconds, 214 of them with nobody at its window, held against a Foxy who was out of the curtain, and that shut door is also why none of his three runs reached the office.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the trace format and what replay does and does not prove | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 |
| 1.1 | Added the frame recording and the night audit, and joined the lines broken at eighty columns | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-21 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-21 |
