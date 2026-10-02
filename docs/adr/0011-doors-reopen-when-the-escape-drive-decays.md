# ADR 0011: Doors Reopen When the Escape Drive Decays

## Status
Accepted. Amended on 2026-10-01, when the eye stopped being blind behind a closed door and reopening started to wait for a look.

## Context
Until now a door only ever closed. `close_left_door` set `door_state['left'] = True` and nothing ever set it back, so the first Giant Fiber spike of the night shut that door permanently. In FNAF a closed door draws power continuously, so a fly that slams both doors early has already lost the night at around 3 AM regardless of what the connectome does afterwards. The reflex was complete and the recovery was missing.

The first version of this decision reopened the door on a timer-like trace and kept the eye blind behind it. The argument was that the eye reads the doorway as an MSE deviation from a reference captured on an empty, lit hallway, that a shut door deviates from that reference far more than any animatronic does, and that a closed door blocks the view anyway. Re-referencing against a "door closed" frame looked like it would only invert the problem, because that frame would be captured with the animatronic still standing outside.

The premise about the view was wrong, and nobody had checked it. With the door shut, the light still reaches the window, and that is exactly how a player tells whether the threat has gone. Bonnie, outside the left door, casts a shadow across the window that blocks the light, and the shadow disappears when he leaves. Chica stands in the right window and stays visible there for as long as she waits. It took a night of watching the fly reopen into a hallway it had not looked at to notice that the game had been offering the answer the whole time.

The worry about the reference does not hold either. The live calibration runs at midnight, when all four animatronics are on stage, so a closed-door reference captured then is an empty window behind a shut door.

Two findings from the Drosophila literature shape what replaced the blind reopening. Visual neurons in the fly receive motor-related input that predicts, and cancels, the image change a voluntary turn will cause (Kim, Fitzgerald and Maimon 2015), so comparing the eye against what the fly's own motor act should produce is a biological operation rather than a convenience. A repeated visual threat also leaves a persistent, slowly decaying defensive state whose length grows with the number of threats (Gibson et al. 2015), which is the role the hold trace already plays.

## Decision
The door is held shut by a leaky trace of the Giant Fiber drive, the same shape as `explore_drive` in ADR 0010. A spike charges `door_hold` to 1.0, and the trace decays toward `release_threshold` with a leak of 0.972 per nominal frame, about 4.9 seconds from a full charge. The decay is applied as `leak ** (elapsed * target_fps)` against the clock rather than once per iteration, because the first night run measured a mean hold of 7.5 seconds when the loop was really turning at 6.5 Hz.

The live calibration records each hallway with the door open and with the door closed for a moment, after `motion_settle_sec` for the animation, and keeps the views it sees in a bank per door state (ADR 0001).

The eye compares each hallway against the bank that matches the door's current state, which `DoorControl` publishes in `SensoryState.door_closed`. A shut door therefore reads as the expected closed view and drives nothing, while Bonnie's shadow or Chica in the window reads as a deviation and drives LPLC2 and LC4 exactly as a body in an open doorway does. The closed view has its own threshold, `closed_door_mse_threshold`, because a shadow is a fainter stimulus than a lit animatronic and has to be fitted on its own measurement.

The eye is blind on that side only while a door command is in flight and for `motion_settle_sec` after the motor reports it done, so the moving door is not read as a threat. During a hold the fly looks at that side like any other.

A Giant Fiber spike on a side whose door is already shut renews the hold to 1.0 and is recorded as a renewal. A threat still standing in the window keeps its own door shut, through the same pathway that closed it.

Behind a shut door the eye reads the window and not the doorway. `VisionCalibration.left_window` and `right_window` are rectangles of their own, captured alongside the hallway boxes, and the closed-door bank holds views of that rectangle only. The bank keeps a single view per side, the brightest frame of the lit sweep, which is the empty window with the light falling through it. Dark frames do not enter it, whether they come from the light being off, from the moment before it comes on or from a flicker.

The door reopens when two things are true at once. The hold has decayed under `release_threshold`, which is the defensive state running out, and the most recent look at that side since the last renewal came back clear. A look is clear when the light was confirmed on screen, the Giant Fiber stayed silent, the eye never drove the cluster, and the eye was not blind when the look began. Nothing is pressed while the tablet is up or the camera map is on screen, since the door buttons are not there to be clicked, and pressing anyway would leave the controller believing in a door the game never moved.

## Consequences
- The door opens because the fly saw the hallway empty, not because a trace ran out. A threat that waits keeps the door shut for as long as it is seen, and the session report counts each renewal.
- Nothing forces a look at the closed side, so a door can stay shut past the 4.9 second hold while the search drive looks elsewhere. The report prints that wait as the wait for the clearing look. The starvation guard still reaches every side within thirty seconds, so the wait is bounded, but it is power the night pays for.
- The chatter the first version accepted, reopening blind into a waiting animatronic and slamming again, is replaced by a hold that persists through the window, which also means fewer door actions competing for the motor queue.
- The first night after the change runs a live calibration and closes and opens each door once at midnight. Both hallways have to be empty for it, as they always are at that hour.
- The first live measurement of Bonnie behind the left door, on night 2, showed why the fly reopened into him. The left eye box spans x 0 to 480 of the game and is mostly door and buttons, while his shadow covers x 420 to 517 and y 263 to 541, so 42 percent of it fell outside the box and the rest was diluted into a distance of 16 against the empty window. Worse, the bank held a frame from the lit sweep in which the light had not yet reached the window, and inside the old box that dark window and Bonnie are the same picture. Twenty-five readings with him outside measured 2 against that frame, under a threshold of 40.
- With the light on and the window empty, the closed-door view is the same image every time and reads exactly 0. On the window rectangle, x 340 to 540 and y 200 to 560, Bonnie measures about 77 against it, so `closed_door_mse_threshold` is 30. The right window still uses the right eye box until Chica is measured the same way.
- A flicker behind a shut door now reads as a deviation, since no dark view is in the bank. The cost is a hold renewed for a moment longer, the direction the door can afford to be wrong in.
- A look taken while the light would not come on no longer counts as clear. It used to, because a dark window matched the dark views of the bank.
- The release still depends on a trace that is not part of the connectome. What changed is that the trace no longer decides on its own.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Door reopening driven by the decay of the Giant Fiber trace | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
| 1.2 | Kept the eye open behind a closed door against a closed-door reference and made reopening wait for a clear look | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
| 1.3 | Described the closed-door views as a bank and recorded the first live hold | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
| 1.4 | Read the window rectangle behind a shut door against its lit view only, fitted the threshold on Bonnie's shadow and required a lit look to clear | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
