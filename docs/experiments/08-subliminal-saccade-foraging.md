# Experiment 08: Killing the Random Number Generator

## The Problem

After Night 2, I realized how poor the gameplay was when the fly's screening heavily relies on  `random.choice(['left', 'right'])`, Even though the reflexes are real. 

The spikes that close doors when Bonnie shows up at the hallway are genuinely propagating through the 138k-neuron connectome. But the part where it decides to look for danger in the first place? That was `random.uniform(4.0, 7.0)` setting a timer and then Python flipping a coin. There was no biology in that loop. I could have written the same foraging behavior in 3 lines of shell script.

It felt wrong to call the project a connectome simulation when the most behaviorally interesting action (the proactive threat-checking) was running entirely outside the brain.

## The Approach

I started thinking about how actual insect foraging works at a neural level. I searched it up, and apparently it does it because the spontaneous background activity of its nervous system builds up a bias somewhere and eventually spills over into a motor command. This is called Spontaneous Background Activity, and it is the reason flies seem to randomly decide to groom or walk in bursts even when there is nothing in the environment triggering them.

The implementation ended up being simpler than I expected:

1. At each simulation step, a small uniform random current (`subliminal_noise_hz = 8.0 Hz`) is injected into every neuron, the connectome equivalent of thermal noise.
2. The `_engine_task` already calls `engine.step()` at 20 FPS. After each step, `model.v` (the raw membrane potential tensor, before any spike threshold) is read for the left and right motor neuron indices.
3. A normalized bias `(l - r) / (l + r + epsilon)` is computed. When this bias exceeds a threshold (`subliminal_bias_threshold = 0.3`) in either direction, the fly activates the light on that side.
4. A refractory period prevents it from jittering back and forth immediately after a saccade.

## What the Numbers Looked Like

First test, 5 frames with no stimulus, no stress: `l=-55.97 mV`, `r=-86.43 mV`, `bias=-0.21`. The right hemisphere was considerably more hyperpolarized at rest, which means after enough noise accumulates the fly would tend to check its right side first. That is the natural asymmetry of the connectome showing up in behavior without any code telling it what to do.

## Why I did that?

The new system produces the same rough timing statistics emergently, but the which side and exactly when decisions now come directly from the brain (or topology of the FlyWire graph). Two runs of the simulation with identical game states might produce slightly different checking patterns because the Poisson noise seed is stochastic.

## Consequences

- Seems more real.
- The `subliminal_noise_hz` and `subliminal_bias_threshold` parameters in `config.py` need calibration. At 8 Hz noise and threshold 0.3, checking intervals were roughly equivalent to the old 4-7 second range in bench tests. This may shift after real game runs.
- If the brain becomes heavily stressed, noise-driven saccade dynamics might be disrupted. 

## Follow-up, 2026-09-16: it did not actually work...

The first night that printed the bias next to every light check showed `+0.00`
on 25 of 27 checks, arriving every 2.1 seconds, strictly alternating. The
starvation guard from ADR 0008 was picking every single side and the bias was
only being printed beside it. Two checks logged a bias whose sign pointed at
the opposite side from the one taken, which is the proof.

I think the idea in this document was right, but the wiring was not. The integrator lived
in `_saccade_task`, the same coroutine that awaits the motor for the two
seconds a look takes, and the eye only sees during a look — so the fly was
asleep for exactly the window in which its own evidence arrived, and zeroed
what little survived at every decision. Outside a look both eye clusters get
nothing but the 8 Hz noise, so the bias sat at zero by construction.

What replaced it keeps the premise of this experiment and fixes the reading.
The signal is the same spontaneous activity, but read as the *difference in
membrane potential between the two eye populations* rather than as a spike
ratio, and it turns out to be a far better signal than it looked here: lag-1
autocorrelation 0.985, sign holding for about two seconds at a time. It is
integrated to a bound in `SearchDrive`, outside the coroutine that blocks.
ADR 0012 has the measurements.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Documented replacing the random draw with subthreshold noise | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-15 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-15 |
| 1.1 | Follow-up on the bias never leaving zero in practice, and why | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-16 |
