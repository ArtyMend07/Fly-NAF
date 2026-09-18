# ADR 0015: The Monitor Comes Down Only When the Office Is Back on Screen

## Status
Accepted. Extends ADR 0014, which decided when the tablet rises but said nothing about how it is put away.

## Context
The 2026-09-17 night ended with the operator lowering the tablet by hand. The log explains why, and it is worth reading in order.

At 17:50:47 DNp09 reached the bound and `open_camera` was issued. In the same second a right light check fired. Those two are mutually exclusive in the game, because the office buttons sit behind the tablet, so one of them was always going to be wasted. The engine loop evaluated `can_look` before it evaluated the camera, so a frame could queue a look and then raise the tablet underneath it, and the effector would run the look regardless.

Six seconds later `camera_watch_max_sec` expired, `close_camera` was issued, and the loop set `cam_is_open = False` without ever checking the screen. The gesture slides the cursor away from the tablet bar, which is not what FNAF listens for, so the tablet stayed up. One second after that, `_refresh_camera_closed_reference` recaptured the office reference on a blind timer and stored a picture of the tablet as the reference for "office visible".

From there everything inverts. `is_camera_up` compares the centre patch against that reference, so the fly read the tablet as the office and the office as the tablet. Once the operator lowered it by hand, `cam_inhib` was driven at the full sensory rate for the rest of the run. Per ADR 0006 that pins the GABAergic inhibitor clusters and zeroes the giant fiber, which is the same catatonia experiment 09 chased down in a different disguise. After 17:51:58 every light check in the log carries the reason `guard`. The brain had stopped contributing.

The detector helped none of this. `is_camera_up` read only the newest frame in the buffer, so a single frame of the office fan or the animated poster could trip a 100 MSE threshold on its own.

## Decision
Lowering the tablet becomes a closed loop that ends on evidence rather than on a click having been sent.

`MonitorControl` owns the whole tablet state and is the only thing that writes `state.camera_open`. When the drive fades or the power cap expires it starts `_lower_monitor`, which issues the slide, waits out `close_settle_sec`, and asks the screen. If the office is back it re-anchors the reference and reports success. If the office is not back it issues `nudge_camera_bar`, a gesture that drives the cursor onto the bar and off again, and asks once more. Only after both gestures have failed does it warn, and it warns with the measured MSE so the operator can tell a stuck tablet from a stale reference. The fly keeps believing the tablet is up, retries every `lower_retry_sec`, and recovers on its own the moment the tablet actually comes down, whoever lowered it.

`_reanchor_office_reference` refuses to capture while the detector still reads the tablet. The reference can therefore drift slowly with the office as the night wears on, which is what experiment 09 wanted, but it can never flip to a picture of the tablet. That single guard is what breaks the cascade above.

The two motor programs are made mutually exclusive in the loop rather than by luck. The camera decision now runs first, `can_look` requires the tablet to be down, and the tablet is not allowed to rise while a look is queued or running. `_saccade_task` also waits for the office before it touches a light button, because the request and the effector are separate coroutines and a frame boundary sits between them.

Competition between the two stays where ADR 0014 put it. A search drive above `camera_release_forage_bias` is one of the ways watching ends, so a fly that badly wants to check a hallway puts the tablet down first instead of reaching through it.

`is_camera_up` now takes the minimum MSE across the whole capture buffer, the same way the hallway detectors already did. A transient animation frame no longer reads as a raised tablet, because every recent frame has to disagree with the reference before the fly believes it.

## Consequences
- The fly can no longer be left blind by a click that did not land, and the run says so in the log and in the session report under `Lowerings That Needed Retry`.
- A failed lowering costs roughly two seconds before the retry, against a night that was previously lost outright.
- `MotorRefrac` loses its `camera` field and the camera refractory moves into `MonitorControl`, which is the only thing that knows when the tablet really came down.
- Light checks and camera pulls can no longer collide, at the cost of one frame of lag on `state.forage_bias`, which the monitor reads from the previous frame to avoid a circular dependency inside the loop.
- `close_camera` accepts `force`, because the worker's own `camera_state` guard would otherwise swallow every retry.
- Detection is now roughly 80ms slower to notice the tablet going up, which is the buffer depth, and considerably less likely to be wrong.
- The gesture question is still open. It is not known which of the two gestures FNAF actually responds to, only that the fly now finds out on its own and reports what happened.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Tablet lowering closed into a loop and the office reference protected | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
