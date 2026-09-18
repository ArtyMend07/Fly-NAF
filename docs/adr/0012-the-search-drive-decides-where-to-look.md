# ADR 0012: An Accumulator Decides Where the Fly Looks

## Status
Accepted. Supersedes ADR 0008.

## Context
ADR 0008 added a starvation guard so a hallway could not go unwatched forever, with the connectome's own bias as the normal path and the guard as a backstop. The session report from the 2026-09-16 21:20 run shows the guard was not the backstop; it was the entire mechanism. Twenty-five of twenty-seven light checks logged a membrane bias of exactly `+0.00`, and the checks arrived every 2.1 seconds, alternating left, right, left, right for the whole night. The fly was a metronome again, which is the same defect ADR 0010 removed from the camera.

Two of the four non-zero entries prove the bias was decorative rather than causal: the check at 14.2s logged `+1.00` and went right, the one at 46.5s logged `-1.00` and went left. `decide_saccade_side` reads the sign of the bias as left-positive, so both looks were chosen by the guard and the bias was merely printed beside them.

The bias could not have been anything else, for three compounding reasons.

- **The integrator was inside the effector.** `_saccade_task` both accumulated `l_sensory_count`/`r_sensory_count` and performed the look. A look costs about two seconds of awaited motor time, during which that coroutine is suspended and accumulates nothing. The eye only ever sees during a look, so every scrap of evidence the fly gathered was produced exactly while the only thing that could record it was asleep.
- **What survived was discarded.** The integrals were zeroed at each decision.
- **The baseline is symmetric by construction.** With no look running, both eye clusters receive only `subliminal_noise_hz`, so their spike counts are equal in expectation and the normalised bias sits at zero, far under `subliminal_bias_threshold`. Measured over 300 resting frames: 0.093 spikes per frame on the left, 0.107 on the right.

On top of that the guard was consulted first, at 2.5 seconds, while a look plus its refractory already costs about 2.1. A side was therefore always starved by the time the fly was free, and the bias branch was unreachable in practice.

## Decision
The decision moves out of `_saccade_task` into `SearchDrive` (`src/search_drive.py`), evaluated once per frame from `_engine_task`, which is the only loop in the process that never blocks. `_saccade_task` becomes a pure effector that carries out a requested look and reports when it is free. The accumulator therefore keeps integrating *through* a look, which is the whole point: the evidence arriving during a look is exactly the evidence that should decide the next one.

The decision is an accumulation to a bound, the standard mechanistic account of a two-alternative choice, fed by three signals.

**Drift.** The difference in mean membrane potential between the left and right eye populations. `membrane_bias()` had been written for this and never called. Measured on this connectome at rest it is not white noise: lag-1 autocorrelation is 0.985, its sign holds for 21 frames on average and up to 72, and its magnitude averages 28 mV against a standard deviation of 33. It is a slow spontaneous left/right preference the network generates by itself, and it is what replaces the clock.

The raw difference is used only after two corrections. A slow baseline (500 frames) is subtracted, because a static hemispheric offset would otherwise read as a permanent preference and park the fly on one door for the entire night. The remainder is divided by a running average of its own magnitude (300 frames), because the absolute millivolt spread changes with network state, and raising the monitor alone is enough to shift it, so a threshold in millivolts would silently mean something different in each regime. Both averages are held back by however many frames they have actually seen, or the normaliser spends its first half-minute climbing out of its initial value and a fly that has just woken up reads every ordinary swing as enormous.

**Evidence.** The difference in eye-cluster spike counts, divided by what a saturated cluster produces in a frame. `get_left_sensory_rate()` is binary, so a clear hallway contributes only the resting trickle while a detection contributes roughly a thousand times that. The fly returns to a hallway it just saw something down.

**Habituation.** A per-side trace charged on every look and decaying with a time constant of about 67 frames. Without it the drift, which holds its sign for longer than a look takes, re-selects the same hallway over and over; replay showed one side going 48 seconds unwatched. This is inhibition of return, and it is what makes the *unchecked* side regain salience without consulting a clock.

The accumulator is linear, so it is carried as three separate sums whose total is the drive. That costs nothing and lets the report attribute each look to the signal that actually caused it rather than guessing.

The gain is expressed as a fraction of the bound rather than in absolute units. An accumulator fed a sustained unit signal settles at `gain / (1 - leak)`, so `gain_ratio = 0.70` is exactly the statement that a drift of ordinary size can never reach the bound on its own and only a stronger-than-usual swing earns a look. Setting that ratio above 1 puts the drive over the bound on essentially every free frame, and the fly looks as fast as the motor allows, which is the metronome rebuilt.

Every time constant is applied against the wall clock as `leak ** (elapsed * target_fps)`, using the exact geometric sum for the input term, so the configured numbers keep meaning seconds when the engine falls behind its nominal rate. On CPU it always does: this machine runs the connectome at about 6.5 Hz against a nominal 10. This is the same correction ADR 0011 applied to the door hold after a configured 4.9-second hold measured 7.5 seconds in play.

The starvation guard survives, at 16 seconds instead of 2.5, and is now tested **before** the bound rather than after. Tested after, a fly that keeps seeing something down one hallway holds the drive over the bound indefinitely, the guard never gets a turn, and the worst case on the other door stops being bounded at all. Replay reached 49 seconds that way with a strong evidence gain.

## Consequences
- Constants were fitted by replaying a 1500-frame recording of the connectome at rest through the shipped class, not chosen by taste. Replayed at the rate this machine really manages, a night gives 12 looks per minute, a median interval of 4.3s with quartiles at 3.1 and 5.5 and a range of 3.1 to 12.8, an even left/right split, and 82% of looks decided by the connectome against 17% by the guard. The same replay at the nominal 10 Hz gives 11 looks per minute and 96% brain-driven, confirming the wall-clock anchoring holds the behaviour steady across frame rates.
- With an animatronic standing at one door, 85% of looks are brain-driven and the threatened side takes 7 of the 12 looks taken while it is there. The evidence term is what produces that, and it is visible in the report as a distinct cause.
- The worst-case blind window is `starvation_sec` plus however long the fly happens to be busy when the guard arms, so about 16 to 18 seconds rather than a hard 16. Lowering `starvation_sec` shortens it and pays in looks the clock decided rather than the connectome; the report prints that split every night, so the trade is measured rather than assumed.
- `subliminal_bias_threshold`, `saccade_leak_per_frame` and `saccade_starvation_sec` are gone from `ForagingParams`, replaced by `SearchDynamics`. `subliminal_noise_hz` stays: it is what keeps the drift alive.
- `state.forage_bias` now carries the drive's distance to the bound instead of a normalised spike ratio. The camera release in `_engine_task` reads it to decide the fly has lost interest in the monitor, and it now means something closer to what that check wants: how badly the fly wants to be looking at a door instead. This is a behaviour change, not only a rename. The old quantity sat at zero almost always, so `camera_release_forage_bias` was effectively dead and the tablet stayed up until `camera_watch_max_sec`; the new one passes 0.5 regularly, so the monitor comes down nearer `camera_watch_min_sec` whenever a door is pulling at the fly. Per ADR 0010 a raised tablet is pure cost, so shorter is better, but the knob is live now where it was not before.
- `SearchDrive` has no torch dependency and takes its time from its caller, so the whole decision is unit-testable without the connectome, the game or the event loop. `tests/test_saccade_scheduling.py` covers it against a synthetic drift built from the measured statistics.
- The fly can still be caught mid-look. Nothing here shortens the two seconds a look costs, and both doors are unwatched for that whole window.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Saccade clock replaced by an accumulator fed by membrane drift, visual evidence and habituation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
