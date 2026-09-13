# ADR 0007: Central Pattern Generator for Foraging

## Status
Proposed

## Context
The fly currently operates exclusively on reactive reflexes (stimulus -> response). To survive Nights 3 to 5, it needs to proactively open the camera to check on Foxy. In standard bot development, this is handled by a fixed timer (`time.sleep(5)` or `last_check + 5s`). This approach is deterministic and unbiological. Flies do not run precise timers; their spontaneous exploration (foraging) is driven by rhythmic internal states and neural noise.

## Decision
I decided to model a Central Pattern Generator (or CPG). A CPG is a biological oscillator that generates rhythmic motor patterns even in the absence of sensory input. I mapped the `DNp09` descending neurons, which are responsible for forward walking and exploration in Drosophila. 
I will inject a continuous, slow sinusoidal wave current into the DNp09 neurons in the pytorch simulation loop. As the wave crests, the accumulating voltage causes DNp09 to spike, triggering the `open_camera()` motor action. 

## Consequences
- **Positive:** Behavior becomes stochastic and organic. The fly checks the camera on a natural biological rhythm rather than a hardcoded loop.
- **Positive:** Synergizes perfectly with ADR 0006. The CPG opens the camera, and the GABAergic network instantly inhibits the resulting visual panic reflex.
- **Negative:** Introduces continuous math processing (sine calculations) on the engine loop, slightly increasing computational overhead.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Initial ADR for CPG rhythm | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-07 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-07 |
