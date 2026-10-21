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

### Amendment, 2026-10-16: the accumulator leaks in the brain's time

The fit above converted wall-clock seconds into frames at the nominal 10 per second, so the drive leaked by the clock rather than by the brain. That held while the engine managed about 5.5 frames a second, where each engine step counted as 1.8 frames and the accumulator spanned about 11 steps. Once spike propagation became event driven the engine reached 9.7 frames a second, each step counted as about one frame, and the same leak spanned about 20 steps of brain time. DNp09's potential has a lag-1 autocorrelation of 0.963 per step, so a window twice as long averages its excursions away and the drive reaches the bound less often. Replaying recorded nights through the class gives the crossings per minute below.

```
night                     frames/s   crossings/min, clock leak   crossings/min, step leak
night 3 that reached 5AM  5.5        3.42                        2.93
2026-10-05                4.5        3.39                        3.06
2026-10-01                8.6        2.56                        3.72
2026-10-16                9.6        1.34                        2.68
```

On 2026-10-16 the tablet came up twice in three minutes and Foxy reached the left door during a gap of 107 seconds.

The accumulator now counts engine steps and leaks with DNp09's own membrane time constant, `exp(-steps_per_frame * dt / tau_mem)`, 0.905 a step, which is within a percent of the 0.912 a step the fitted constants worked out to on the night that reached 5AM. The integration window is about 20 ms of brain time, the same as the membrane it reads, and `drive_leak_per_frame` is gone from `ExploreDynamics`. On 12,000 quiet frames replayed with the monitor's refractory, minimum watch and cap, the tablet comes up 2.13 times a minute at 9.7 frames a second with a median gap of 27 seconds and a longest gap of 55, against 1.5 and 96 with the clock leak. Live, about half the crossings fall while a light check is pending and are lost, as on the night that reached 5AM, where 14 raises came from about 26 crossings.

The rate in wall-clock time now follows the engine. An engine that falls well short of `target_fps` raises the tablet less often in game time, and the session report's engine rate is where that shows.

### Amendment, 2026-10-16: an alert fly keeps a faster tempo

Past a point the brain was no longer what set how often the tablet came up. The 15 second refractory after each watch was, and it was the same for a calm fly and for one that had just seen Foxy leave the cove. A simulation of Foxy's movement opportunities, with the 0.83 to 17.48 second lock that follows each lowering, gives the runs he makes in a night against the gap between raises.

```
night (Foxy's AI)   40 s   27 s   22 s   15 s   10 s
3      (2)           2.0    1.5    1.1    0.4    0.1
4      (6)           6.8    5.1    3.9    1.9    0.7
5      (5)           5.6    4.2    3.2    1.6    0.5
tablet up            11%    16%    20%    29%    44%
```

At the 27 seconds of a calm fly a night 4 has about five runs to answer, and each knock on the closed door costs more power than the last.

The vigilance of ADR 0026 is now the fly's arousal, and it sets the tempo as well as the gain. The refractory before the next raise and the pause before the next light check are divided by `1 + arousal_quickening * arousal`, so at full vigilance they are a third as long. The minimum watch is left alone, because it is what DNp09 needs to answer a weak figure (ADR 0026, version 1.5). A fixed refractory was a number chosen by hand that stopped the brain's own urgency from showing. One that shortens with arousal keeps a pause after each act, as any motor program has, and lets what the fly has seen set how often it acts. On the 12,000 quiet frames, with `arousal_quickening` at 2.0:

```
arousal   raises/min   median gap   longest gap   tablet up
0         2.13         26.8 s       55.2 s        15%
0.5       3.83         13.6 s       32.2 s        27%
1.0       4.75         11.3 s       24.8 s        34%
```

The cost is blindness. While the tablet is up the Giant Fiber is gated and no light is checked, and from night 4 Bonnie and Chica reach the doors often enough for that to matter. Vigilance fades over 30 seconds, so the tempo stays fast only while the fly keeps seeing things.

## Consequences
- The tablet comes up again, and for a reason:

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
| 1.2 | The accumulator leaks per engine step with DNp09's membrane time constant, after the faster engine halved how often the drive reached the bound, and arousal shortens the refractory between raises and between light checks | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-16 |
