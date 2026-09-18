# ADR 0010: Spontaneous DNp09 Activity Replaces the CPG Clock

## Status
Partially superseded by ADR 0014.

Removing the CPG clock stands. The replacement trigger does not: the spontaneous
DNp09 firing measured below was the network oscillating globally rather than the
cluster deciding anything, and once ADR 0013 calmed the network it fell to one
spike in 2500 frames. ADR 0014 keeps the spike as the command and accumulates
DNp09's subthreshold potential underneath it.

Supersedes ADR 0007.

## Context
ADR 0007 drove the camera pull with a central pattern generator: `step()` injected `peak_current` into the DNp09 cluster whenever a `math.sin(t * 0.03 * 2pi)` wave crossed `spike_threshold`, and `_engine_task` integrated the resulting spikes until `explore_integral` passed 25. The sine has a 33.3 second period, so the tablet came up on a fixed schedule no matter what was happening in the office. DNp09 fired for real and the spike propagated through the connectome for real, but the decision of when belonged to `time.time()`, not to the brain. The integrator existed only to stop the camera from being pulled on every frame of a CPG peak.

Three 90-second runs against the real connectome, driven exactly as production drives it, measured DNp09 with the rates buffer correctly zeroed:

```
cpg off, pure network dynamics     explore_spikes=2    frames_firing=2/900    gf_spikes=0
cpg tonic only (base 50, no peak)  explore_spikes=0    frames_firing=0/900    gf_spikes=0
cpg as configured (1000 / 50)      explore_spikes=434  frames_firing=218/900  gf_spikes=0
```

The configured CPG fires DNp09 in 218 of 900 frames, matching the fraction of the sine cycle above threshold, which confirms `peak_current=1000` works but also confirms the metronome. More usefully, the cluster fires on its own without any injected current, purely from background noise and recurrent input, and the Giant Fiber stays silent while it does so, so spontaneous exploration cannot manufacture a false door slam. Tonic current adds nothing: 0 versus 2 spikes is noise at this sample size.

## Decision
The sine and the integrator are removed. `step()` no longer writes to the DNp09 indices at all, so the cluster receives the same background noise as every other neuron plus whatever the connectome delivers to it, and `_engine_task` pulls the camera on any DNp09 spike once `camera_refractory_sec` has elapsed. A descending command neuron firing is the command; accumulating 25 of them was an artifact of the clock that made it fire continuously.

`explore_drive` is redefined from the sine's phase to a leaky trace of DNp09's own spiking, so the release logic that closes the camera when interest decays keeps working against a quantity that now means what its name says.

## Consequences
- The camera comes up on irregular, connectome-generated timing rather than every 33.3 seconds.
- The measured spontaneous rate is roughly one spike per 45 seconds and is noisy at this sample size. Camera pulls become rare and unevenly spaced, and a quiet stretch of several minutes is possible. `subliminal_noise_hz` is the honest knob if the rate needs raising, since it raises excitability across the whole network rather than hand-feeding one cluster.
- Rare pulls are strictly good for survival. Nothing reads the monitor's contents, so a raised tablet is pure cost: it holds the GABAergic inhibitors at full drive and the Giant Fiber cannot answer a door for as long as it is up.
- `CpgDynamics` is replaced by `ExploreDynamics`, which keeps only the trace leak and the release threshold.
- The inhibition path of ADR 0006 and the light path in `_saccade_task` are untouched.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | CPG clock replaced by the spontaneous activity of DNp09 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
| 1.1 | Trigger marked as superseded by ADR 0014 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.2 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
