# ADR 0020: A Short List Of Knobs With Measured Bounds

## Status
Accepted. Amended on 2026-10-26, when `looming_eye` joined the list.

## Context
`config.py` holds fourteen frozen dataclasses and no validation of any kind.
`frozen=True` prevents mutation after construction, it does not check a value, so
every number in the file is accepted exactly as written. Two of them take the
process down on the spot. A `drive_leak_per_frame` of 1.0 divides by zero in
`search_drive.py`, and a `target_fps` of 0 divides by zero in `main.py`. Several
more do something worse than crash, which is to quietly change the regime the
network runs in while the run appears fine.

Anyone curious enough to open the file finds no way to tell the difference
between a number that is safe to play with and a number that is load bearing.
`arousal_multiplier` is one line away from the LIF constants adapted from
upstream, and it is applied after the weight cache is built, so changing it does
not even invalidate a cache. It is the easiest number in the project to change
and the one that most thoroughly invalidates the biological claim.

## Decision
A separate `src/tuning.py` exposes seven parameters, each with a range taken
from a measurement rather than from taste, and reads them from a `tuning.toml`
that is generated on first run. Values outside the range are clamped and the
clamp is reported when the run starts. Unknown names are reported and ignored.
Nothing else in `config.py` is reachable this way.

The ranges for `arousal_multiplier` and `subliminal_noise_hz` come from the
sweep in ADR 0013 and stop where that sweep stopped. Ten is not an extreme
setting for arousal, it is the documented seizure, with 5.55 percent of the
brain firing at rest and the count ringing at the Nyquist frequency of the
one step synaptic delay.

`base_sensory_rate_hz` is deliberately not on the list. At 1000 Hz with a 1 ms
step the Poisson probability already saturates at 1.0, so raising it does
nothing at all, and offering it would teach the wrong lesson to the first person
who tries to make the fly more alert.

The neural parameters and the FlyWire root id clusters stay unreachable. They
are the claim, not a setting.

Since 2026-10-26 the list has an eighth entry, `looming_eye`, which takes 0 or 1
and picks how a lit hallway reaches the brain (ADR 0001, experiment 20). At 0 the
eye is the threshold of ADR 0001. At 1 it is read the way the tablet reads a
camera. The cell size, the noise per cell and the floor, span and ceiling of the
share stay in `config.py`, since they were set from the saved frames and moving
one of them moves what the fly can see.

The same change makes `map_neuron_ids_to_indices` report how many root ids it
dropped and refuse a cluster that resolved to nothing. Dropping was silent
before, and a cluster that resolves to an empty index list makes its neuron
unable to fire for the rest of the run with no diagnostic anywhere.

## Consequences
Someone can make the fly jumpier, calmer, more or less curious, or quicker to
panic, and watch what changes, without being able to turn the simulation into
something that is no longer a fly. The cost is that the interesting extremes are
now out of reach from the tuning file, which is the intent. Reaching them means
editing `config.py`, and that is the right amount of friction for a change that
invalidates the ADRs.

`OverlayPanel` and the unused camera coordinates were removed in the same pass.
Nothing read them, and dead settings in a file people are now invited to edit are
worse than no settings.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the tuning surface and why the ranges stop where they do | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 |
| 1.1 | Added `looming_eye` to the list | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 |
