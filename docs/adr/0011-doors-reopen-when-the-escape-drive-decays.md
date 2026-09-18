# ADR 0011: Doors Reopen When the Escape Drive Decays

## Status
Accepted.

## Context
Until now a door only ever closed. `close_left_door` set `door_state['left'] = True` and nothing ever set it back, so the first Giant Fiber spike of the night shut that door permanently. In FNAF a closed door draws power continuously, so a fly that slams both doors early has already lost the night at around 3 AM regardless of what the connectome does afterwards. The reflex was complete and the recovery was missing.

The naive fix, reopening once the hallway looks clear again, does not work here, and the reason is in `_vision_task`: the eye only reads the doorway while a light saccade is running, and it reads it as an MSE deviation from a reference captured on an empty, lit hallway. With the door shut, that same region is a door panel, which deviates from the reference far more than any animatronic does. The fly would read its own closed door as a permanent threat, keep the Giant Fiber charged, and never release. Re-referencing against a "door closed" frame inverts the problem rather than solving it, because the reference would then be captured with the animatronic still standing there, and its departure would register as the change.

## Decision
The door is held shut by a leaky trace of the Giant Fiber drive, the same shape as `explore_drive` in ADR 0010. A spike charges `door_hold` to 1.0; the trace decays toward `release_threshold`, and when it falls under it the descending drive that was holding the door has stopped and the door relaxes open. With a leak of 0.972 per nominal frame and a threshold of 0.25 that is a hold of about 4.9 seconds.

The decay is applied as `leak ** (elapsed * target_fps)` against the wall clock rather than once per iteration. The first night run measured a mean hold of 7.5 seconds against the 4.9 the config asks for, because `engine.step` does not keep up with `target_fps` and the loop was really turning at about 6.5 Hz. Anchoring the decay to elapsed time makes the configured number mean what it says whatever the engine manages that night.

A release is only acted on while the monitor is down. The door buttons are not on screen behind a raised tablet, so a click there does nothing, and firing it anyway would leave the controller believing the door is open while the game still holds it shut, a desync that never heals. The trace keeps decaying while the tablet is up; only the motor act waits.

While a door is shut, that side's visual input is gated to zero, and `state.blind_until[side]` is pushed forward every frame. This is the same corollary-discharge principle ADR 0006 already applies to the camera: the motor act that would saturate a sensory channel also suppresses it. It is also literally true, since a closed door blocks the view of the hallway behind it. The gate outlives the reopen by `reopen_settle_sec`, so the door's own opening animation is not read as motion.

The fly therefore does not verify before reopening. It reopens blind, vision returns half a second later, and if the threat is still standing there LPLC2 drives the Giant Fiber again within one or two frames and the door slams a second time. Verification is not a separate mechanism; it is what the existing 10 Hz loop does as soon as it can see again.

## Consequences
- Power is no longer spent indefinitely on a threat that walked away three hours ago, which is the difference between reaching 6 AM and browning out.
- An animatronic that waits produces a visible chatter: slam, hold ~5s, reopen, re-slam. That is an honest read of the animal, a transient escape reflex re-triggering, and it is the most legible behaviour the panel will show all night.
- The chatter is bounded by cost. Each door action carries `pan_delay_sec` of mouse travel before the click, and the motor queue is shared with lights and camera, so a much shorter hold would starve the other motor paths. `hold_leak_per_frame` is the knob if a night shows the fly toggling too often.
- The hold outlives `motor_refractory_sec`, checked in `tests/test_door_release.py`, so the Giant Fiber is always out of refractory by the time the door it closed comes back up and can immediately close it again.
- The fly is blind on a shut side. Nothing reads the hallway behind a closed door, which is correct, but it means a hold is a commitment: the fly cannot learn during those five seconds.
- `record_door_release` gives the session report the hold durations and the total door-closed time, which is the number that actually predicts whether the power lasts.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Door reopening driven by the decay of the Giant Fiber trace | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
