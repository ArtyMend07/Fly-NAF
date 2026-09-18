# Experiment 09: The Rates Buffer That Never Forgot

## The Problem

The fly used to go catatonic. After a variable amount of time in a real night,
session_telemetry would show a normal spread of door panics and light
checks for the first 30-60 seconds, then just... stop. For the rest of the
run, the only thing left firing was the CPG, pulling the camera up every
15 or 20 seconds like clockwork, while Bonnie and Chica could have walked right
up to the glass and nothing would have happened. She was acting extremely dumb, even for her standards.

I chased that one down to `vision.py`'s `_ref_camera_closed`, and it was captured
exactly once, at boot, and never touched again. The very first time the real
camera got used, the closed office reference stopped matching the actual
screen (residual pan drift, compression noise, whatever), the MSE against it
never dropped back under `mse_trigger` again, and `is_camera_up()` got stuck
reporting `True` for the rest of the session. Per ADR 0006, a stuck-open
camera reading pins the GABAergic `camera_inhibitor` clusters at full drive,
which `test_inhibition.py` already proves is enough to completely zero the
Giant Fiber. Then I recapture `_ref_camera_closed` as a
side effect of the engine's own `close_camera()` call, with `clear_buffers()`
first so the recapture can't read a frame still mid-animation.

That fix worked. And then, surprisingly, the fly did something far worse.

## The Problem, Take Two

With the camera reference self-healing, the next test run reacted to
everything, and then never stopped reacting. Giant fiber firings every ~2
seconds, alternating left/right, for 80+ seconds straight. The fly was literally having a seizure in the middle of the gameplay. My first guess was
that the camera was somehow blowing up the door-hallway MSE too, same family
of bug as before, just on `ref_left`/`ref_right` instead of
`_ref_camera_closed`.

It wasn't that. `get_left_sensory_rate()`/`get_right_sensory_rate()` only
ever write `panic_left.png`/`ref_left.png` to `logs/vision_debug/` the moment
the MSE actually crosses threshold. Those files were still timestamped from
the *previous day's* session. The vision system never once reported a real
threat during the entire panic storm. Whatever was making the Giant Fiber
fire, it wasn't the eyes.

## Chasing the Wrong Neuron

I was tired, but before giving up, I tested two more hypotheses directly against the real connectome:

- **Pure background noise alone**, 90 seconds, nothing else driving the
  network: 0 Giant Fiber spikes in the quiet phase.
- **A CPG explore burst followed by 90 seconds of background noise**, to see if a camera-pull event was somehow tipping the
  recurrent network into a self-sustaining hyperexcitable state: also 0
  Giant Fiber spikes afterward.

Both dead ends. The isolated model, driven exactly like production, refused
to reproduce the storm. Which meant the bug wasn't in the connectome or the
weights at all. It was in how `main.py` was feeding it.

## What Was Actually Happening

`ConnectomeEngine._rates` is a tensor allocated once in `__init__` and
reused every frame. `step()` only ever *overwrites* the ~200 indices that
belong to the eye clusters, the camera inhibitors, and the explore neurons.
Every other neuron in the 138,639-neuron graph is touched by exactly one
line:

```python
self._rates += torch.rand_like(self._rates) * noise_hz
```

Additive. Every frame. Onto a buffer that's never zeroed. I checked the
growth with a bare tensor.

```
t=0s   mean_fire_prob=0.004
t=10s  mean_fire_prob=0.808
t=20s  mean_fire_prob=1.000   <- saturated, stays there forever
```

Twenty seconds of engine time (not wall-clock session time, since the ~20s of
calibration before the engine even starts stepping doesn't count) for the
background noise on every untouched neuron to climb past the Poisson
generator's probability ceiling and pin the entire rest of the connectome at
a 100% fire chance, every step, permanently, since nothing ever subtracts
from it. That is close enough to the real session's ~20-26s delay between
"calibration done" and "first panic" that I'm confident it's the same
number. Once the whole graph is saturated, of course the Giant Fiber fires
constantly, and so does everything else. And it can never recover mid-session,
because the accumulator only grows.

Fix: `self._rates.zero_()` at the top of `step()`, before anything else
touches it. One line. Everything downstream of it, meaning the CPG's actual
intended behavior, the sensory clusters and the inhibitors, was already
correct; they just needed the frame to start from silence instead of from
whatever leftover noise the last thousand frames had piled up.

## Two Bugs That Were Hiding Behind The First One

With the Giant Fiber no longer firing 40 times a minute, two smaller,
unrelated problems in `input_controller.py` became visible:

- `close_left_door`/`close_right_door` are a physical toggle in FNAF, not a
  "set closed" command, and the worker never tracked door state the way it
  already tracks `light_state`/`camera_state`. Every repeated panic click
  was silently re-*opening* the door it had just closed.
- `_move()` teleports the cursor with `SetCursorPos` and clicks ~50ms later.
  The office view has to pan to the door before the button is actually
  under the cursor; the click was landing mid-pan and missing.

Both were real even before the runaway-rates bug, just masked by how rarely
a *legitimate* panic used to fire back when the door reflex worked at all.
Fixed the same way `light_state`/`camera_state` already worked: track
`door_state`, no-op a close that's already closed, and wait
`pan_delay_sec` before the click actually happens.

## What I Decided Not To Do

When I proposed re-adding a `state.camera_open = vision.is_camera_up()`
resync inside `_vision_task` (to catch the case where a `close_camera()`
click silently fails in-game), I vetoed it myself once I thought about who
owns that variable. `_engine_task` is the only place that ever decides to
open or close the camera, and it does so on a hard deadline
(`cam_close_after`), so it can't actually get stuck. Piping a second,
independently-timed writer into the same field from `_vision_task` just
reintroduces the exact class of race condition the earlier bug already
punished us for. `_engine_task` stays the sole owner; only the *reference*
that `is_camera_up()` reads against gets refreshed.

## Consequences

- The fly reacts continuously now instead of degrading into either
  catatonia or a seizure, for the same underlying reason: neurons that
  aren't supposed to be driven this frame need to actually read as
  undriven, not as "whatever the last N frames added up to."
- `arousal_multiplier = 10.0` and the rest of the tuning in `config.py`
  were never actually miscalibrated. I spent real time suspecting the CPG,
  the GABAergic inhibitors, and the vision MSE before finding this, and none
  of them needed to change.
- Persisting `ref_left.png`/`ref_right.png` to `logs/vision_reference/` (not
  the debug dir) after a live calibration means future runs can skip the
  10-second flash-and-capture entirely, as long as the bbox size in
  `config.py` hasn't changed since the cache was written.
- I left one open question at the end of the last session: now that the
  network isn't artificially saturated, does the CPG's
  `peak_current`/`base_current` still cross the `dnp09_explore` firing
  threshold often enough on its own to ever reach `integral_trigger`? See
  below. The answer is no.

## The Camera Stopped Opening, And That Answers The Open Question

Next test run after all of the above: the fly reacted correctly to doors and
lights, and then never pulled the camera up once, all night. Told me
directly not to touch the light logic while I looked at this one, and since it
isn't related, that was easy to honor.

I drove the real `dnp09_explore` cluster the same way `ConnectomeEngine.step`
does, with the actual sine-wave CPG current, `base_current=50` most of the time
and `peak_current=200` for the ~25% of each 33.33s cycle above
`spike_threshold=0.85`, against the real connectome, for 180 simulated
seconds, with the rates buffer correctly zeroed every frame this time
(i.e. the *fixed* behavior, not the bug):

```
t=  9.9s  cpg_wave=0.98  cpg_current=200  explore_integral=0.21  total_spikes=4
t= 39.9s  cpg_wave=0.97  cpg_current=200  explore_integral=0.00  total_spikes=4
t=109.9s  cpg_wave=0.98  cpg_current=200  explore_integral=0.00  total_spikes=4
t=139.9s  cpg_wave=0.97  cpg_current=200  explore_integral=0.00  total_spikes=4
```

Four spikes total, all of them in the very first peak window, none in the
three peak windows after it. `explore_integral` peaked at 0.21, nowhere near
`integral_trigger=25`, and never moved again. So this confirms the
open question: `peak_current=200` was never actually strong enough to drive
`dnp09_explore` past its own LIF threshold on a fair fight. Every camera
pull logged in every session before this one, including the ones I called
"normal" in earlier experiments, was riding on the runaway-saturation bug
providing free recurrent excitation on top of the CPG's own signal. Now that
`self._rates.zero_()` took that crutch away, the CPG's own numbers are
exposed as under-tuned for the network they actually have to drive.
`CPG_DYNAMICS` in `config.py` was calibrated entirely against a broken
baseline and needs to be redone against the honest one.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Documentation of the never-reset rates buffer investigation and the door toggle/timing bugs it hid | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.1 | Closing the open question, where the CPG was never strong enough on its own, it only appeared to work due to the saturation bug | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.2 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
