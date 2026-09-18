# ADR 0014: The Monitor Rises on Accumulated DNp09 Drive

## Status
Accepted. Supersedes the trigger in ADR 0010; its removal of the CPG clock stands.

## Context
ADR 0010 replaced a sine-wave metronome with a rule that reads well: pull the camera whenever DNp09 spikes, because a descending command neuron firing *is* the command. It measured DNp09 firing twice in 300 frames without any injected current and concluded the cluster was spontaneously active.

ADR 0013 showed what that activity really was. The network was oscillating globally, 5.55% of all neurons firing together every frame, and DNp09 fired when the wave happened to sweep through it. The rate was erratic in a way a rate should not be (7, 0, 0, 5, 5 across five otherwise identical conditions), because it was not a rate. Once the gain came down, the cluster fired **once in 2500 frames**, and a night that waits for that never raises the tablet at all. A 195-second run on 2026-09-17 logged zero camera pulls.

So the mechanism was not just fragile, it was borrowed from the pathology that ADR 0013 removed.

## Decision
`ExploreDrive` accumulates DNp09's own subthreshold membrane potential to a bound, the same shape as the search decision in ADR 0012 and reading the same kind of signal. Measured at the calmed gain over 2500 frames, that potential is a usable decision variable in exactly the way the eye drift is: lag-1 autocorrelation 0.963, deviation averaging 17.1 mV with a spread of 12.5, the same ratio the eye drift has.

A real spike still raises the tablet outright, with no accumulation required. ADR 0010 was right about what a spike means; it was only wrong that one would ever arrive.

Both decisions share `AdaptiveSignal`, which subtracts a slow baseline and divides by a running average of the remaining magnitude. That is what let the search constants survive ADR 0013 untouched, and it is why this one is written in the same dimensionless units rather than in millivolts that mean something different at every gain.

The accumulator is **not reset when the tablet goes up**. It keeps running, and the tablet comes down when the drive falls back under `release_ratio` of the bound. One variable with hysteresis: watching ends because the exploratory drive faded, not because a timer expired. `camera_watch_max_sec` survives as a hard power cap and was raised from 1.5s to 6.0s, because at 1.5s the cap fired first every single time and the hysteresis never got a turn.

The accumulator reflects at zero rather than running negative. A cluster quieter than usual is not evidence against exploring later; it is just no evidence for it now. That makes the wait a first-passage time rather than a saturation, which is why the intervals come out irregular.

Constants were fitted by replaying the recorded trace through the shipped class at the frame rate this machine manages:

```
ratio  leak  | pulls  /min  gap med  gap min  gap max  watch  blind%
  1.0  0.95  |     9   1.4     39.9     22.5    112.2    3.5    7.2%
```

One pull roughly every 40 seconds, which is close to what the seizing network produced by accident (37s), with watches averaging 3.5 seconds.

## Consequences
- The tablet comes up again, and for a reason: the report now says whether each pull came from a DNp09 spike or from accumulated drive, and whether each release came from the drive fading or from the power cap.
- The fly is blind for about 7% of the night, against roughly 4% before. A raised tablet holds the GABAergic inhibitors at full drive and the Giant Fiber cannot answer a door while it is up, so this is a real cost paid for a visible behaviour. `camera_watch_max_sec` is the knob if a night shows it costing too much power.
- Intervals are irregular by construction, 22s to 112s in replay around a 40s median, rather than clustering at a refractory floor.
- `ExploreDynamics` loses `trace_leak` and `release_drive_threshold` and gains the accumulator's constants. `engine.explore_drive`, the leaky trace of spikes, is gone; `engine.explore_membrane` replaces it.
- A cluster of two neurons is a thin signal to read a membrane potential from. It works because the accumulator integrates over seconds, but a wider DNp09 population would be a better input and is the obvious next improvement.
- The camera still decides only *whether* to look, never *which* camera. `camera_1c` and `camera_4b` remain unused in `MotorCalibration`.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Monitor raised on accumulated DNp09 membrane potential instead of waiting for a spike | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
