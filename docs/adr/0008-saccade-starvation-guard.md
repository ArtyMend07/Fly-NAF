# ADR 0008: Starvation Guard on Saccade Side Selection

## Status
Superseded by ADR 0012.

The guard described here worked, but the bias it was meant to protect never
functioned, so the guard became the only mechanism selecting sides and turned
the fly into a 2.1-second metronome. ADR 0012 keeps a guard at a far longer
interval and rebuilds the decision itself.

## Context
`get_left_sensory_rate()`/`get_right_sensory_rate()` are the only path by which real screen content reaches the LPLC2 clusters: `_vision_task` zeroes `left_rate`/`right_rate` whenever `state.check_left`/`check_right` is `False`, and those flags are only raised for the `light_inspection_time` window of an active saccade. Which side a saccade checks was decided purely by `bias = (integral_l - integral_r) / (integral_l + integral_r)`, itself built from `l_sensory_count`/`r_sensory_count` spikes that only exist while a previous check was already looking that way. With no floor on how long a side can go unchecked, an empirical run reproduced exactly this: Bonnie stood at the left door for the length of the test and the fly kept saccading without ever forcing a look at that side, so the Giant Fiber never received a real stimulus to react to and the door never closed.

## Decision
`decide_saccade_side()` tracks the wall-clock time each side was last actually checked. If either side's wait exceeds `FORAGING_PARAMS.saccade_starvation_sec` (2.5s), that side is forced regardless of what the noise-driven bias says; between two starved sides, the longer-waiting one wins. The bias-driven choice is preserved as the default path when neither side is starved, so `camera_open` and `saccade_refractory_sec` still gate saccades exactly as before. The forced check still goes through the same light-on, MSE-driven `get_left_sensory_rate()`/`get_right_sensory_rate()` path as a bias-triggered one; nothing bypasses the connectome's own threat evaluation.

## Consequences
- Both doors now have a bounded worst-case blind window (`saccade_starvation_sec`) instead of an unbounded one dependent on when internal noise happens to swing the bias past `subliminal_bias_threshold`.
- `saccade_starvation_sec` is a new tuning surface: too low turns the fly into a strict left-right metronome regardless of bias; too high reopens the original blind spot.
- The side-selection logic moved out of `_saccade_task`'s loop body into a standalone `decide_saccade_side()` so it is unit-testable without driving the real asyncio loop or the vision/motor I/O.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Record of the starvation guard in the saccade side selection | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.1 | Marked as superseded by ADR 0012 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.2 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
