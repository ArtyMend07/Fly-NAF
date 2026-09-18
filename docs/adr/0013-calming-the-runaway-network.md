# ADR 0013: Calming the Runaway Network

## Status
Accepted.

## Context
The live panel from ADR 0009 shows every spiking neuron as a lit point. Watching a night, the operator reported that the whole brain appeared to detonate several times a second. The panel was not lying.

Measured over 600 frames with nothing on screen and no stimulus of any kind:

```
spiking neurons per frame : mean 7689 of 138,639  (5.55% of the brain)
autocorrelation lag 1     : -0.94
autocorrelation lag 2     : +0.95
first frames              : 1143, 1074, 1940, 3046, 4122, 5625, 7080, 9501, 7139, ...
```

Two separate pathologies. The network **ramps out of rest and saturates** within eight frames. And the negative lag-1 with a positive lag-2 is a period-two oscillation: the count alternates high, low, high, low from frame to frame (`6663, 8237, 6709, 7570, 7073, 8043`), which is the network ringing at the Nyquist frequency of its own one-step synaptic delay. Neither is background activity. It is a seizure, and the fly was acting on spikes drawn from it.

The obvious suspect was the noise. `scale_poisson` (250) times `w_scale` (0.275) injects **68.75 mV per Poisson spike** against a threshold **7 mV** above rest, so `subliminal_noise_hz` was never subliminal; every noise spike was an order of magnitude over threshold. That is a real defect in the naming and in the number, but a sweep showed it is not what sustains the runaway:

```
noise  arousal | %/frame   lag1    lag2
  8.0     10.0 |  5.57%   -0.90   +0.95
  0.5     10.0 |  5.18%   -0.80   +0.96     <- sixteen times less noise, same ringing
  1.0      3.0 |  2.22%   -0.22   +0.28
  1.0      1.0 |  0.80%   -0.11   -0.16
```

Cutting the noise sixteenfold moves the firing rate by four tenths of a percent and leaves the oscillation intact. What sets the regime is `arousal_multiplier`, which multiplies every FlyWire synaptic weight by ten.

## Decision
`arousal_multiplier` drops from 10.0 to 3.0 and `subliminal_noise_hz` from 8.0 to 1.0.

The decisive question was whether a quieter network still answers a threat, because calming a brain that no longer closes doors would be worthless. It does, and it answers sooner:

```
candidate       arousal noise | rest %   lag1 | GF idle  GF on threat  latency
as shipped        10.0   8.0  |  5.57%  -0.94 |  0/250      45/100        10f
calmer network     3.0   1.0  |  2.18%  +0.03 |  1/250      41/100         7f
calmer network     1.0   1.0  |  0.79%  -0.67 |  3/250      44/100         5f
```

At 3.0/1.0 the ringing is gone (lag-1 +0.03 against -0.94), resting activity is less than half, the false-alarm rate is unchanged at one frame in 250, and the escape reflex reaches the Giant Fiber three frames earlier. 1.0 is calmer still and closer to real Drosophila firing rates, but triples the false alarms and was held back as the next step rather than taken now.

## Consequences
- The panel becomes readable. At 2.18% the points that light are sparse enough to show which regions are active, instead of 7,700 somata igniting together every frame.
- **The search decision needed no refitting at all**, which was not obvious beforehand and is the one thing that made this change cheap. The eye drift collapses in absolute terms and keeps its shape exactly:

  ```
                       sd      lag-1    |deviation| mean / sd
  arousal 10 / n 8   45.4 mV  +0.991    36.4 / 27.1   (ratio 0.74)
  arousal  3 / n 1    6.5 mV  +0.974     5.3 /  3.7   (ratio 0.70)
  arousal  1 / n 1    1.6 mV  +0.958     1.2 /  0.9   (ratio 0.75)
  ```

  `SearchDrive` divides by a running average of the deviation's own magnitude, and `gain_ratio` is expressed against that. Both are dimensionless, so a sevenfold change in millivolts passes through them untouched. The divisive normalisation was put there for a different reason, the monitor shifting the network's state, and paid for itself here.
- **The camera pull did not survive**, and had to be rebuilt. DNp09 fired 5 times in 1200 frames at the old gain and once in 2500 at the new one. ADR 0010 read that as a spontaneous rate; it was the synchronised wave sweeping through the cluster. A pull that depended on it was a lottery ticket, not a decision. ADR 0014 replaces it.
- Every constant fitted against a measurement of this network before today was fitted in the seizing regime and is now suspect on principle, even where it still passes. The door hold, the vision thresholds and the motor timings are all in wall-clock or screen units rather than spike units, so none of them read the network directly, but that is luck rather than design.
- `subliminal_noise_hz` keeps its name while no longer matching it. The honest repair is `scale_poisson`, which is what makes a single noise spike worth ten thresholds; that is a separate change with its own calibration and has not been made.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recurrent gain lowered to stop the network oscillating in lockstep | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
