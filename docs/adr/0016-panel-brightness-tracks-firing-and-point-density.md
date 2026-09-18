# ADR 0016: Panel Brightness Tracks Firing and Point Density

## Status
Accepted. Extends ADR 0009, which decided where the panel sits and not how it is drawn.

## Context
The in-game panel was a white blob. The operator produced it with the simulation not running at all, which rules out the network and points at the renderer.

The cause is additive blending with a fixed floor. Every one of the 138,639 points contributed `BASE_ALPHA = 0.20` whether or not anything was firing, and the in-game panel draws all of them into 180 by 180 pixels. That is 4.3 points per pixel before any spike arrives, and in the optic lobes it is far more, so the floor alone sums past white long before the shader gets to add glow. Reproducing the panel at its real size and pixel ratio gave exactly the image the operator sent.

Firing made it worse rather than better. At the 2.18% per frame that ADR 0013 measured as the calmed resting rate, the glow term took a firing point to alpha 0.95 and 2.55 times its colour, and grew it to 5 times its area, so the core saturated again with room to spare. The panel was therefore white when the brain was idle and white when it was busy, which is the same as showing nothing.

The side panel, the fallback when there is no room over the game, is the same cloud in 620 by 1040 and roughly 17 times sparser. The old constants were tuned for that geometry and were never going to survive the move into the corner of the game.

## Decision
Brightness is derived rather than fixed, from two things the page already knows.

The first is how busy the brain is. The stream handler already counts the neurons in each frame, so the share of the population firing is smoothed and mapped onto a range. A quiet brain draws at `BASE_QUIET` with `GLOW_QUIET`, and a brain at `ACTIVITY_FULL` draws at the busy end of both. The panel is therefore dim when nothing is happening and visibly swells when the network is working, which is the reading the panel exists to give.

The second is how densely the cloud lands on the canvas. `resize` computes the rendered pixel count, including device pixel ratio, against the 180 by 180 the constants were tuned at, and scales both uniforms by that ratio up to a ceiling of 12. The same constants now hold for the in-game corner, the side panel and a high density display, because what saturates is points per pixel and that is what is being compensated.

Resting points also drop from 0.75 of their colour to 0.45, and a firing point grows by 0.8 of the base size instead of 3.4, since area is what overlaps.

Values were fitted by serving the real geometry with a synthetic spike feed and reading the panel at 180 by 180 with pixel ratio 1, which is the condition that produced the operator's screenshot.

```
firing/frame  uBase   uGlow   result
       0.0%   0.016   0.100   lobes and central brain separable, nothing clipped
       0.2%   0.017   0.104   calm, colours intact
       2.2%   0.030   0.160   clearly brighter, still no white core
```

Nothing about the point cloud's position, scale, rotation or camera framing was touched. `resize` keeps the same fit and only gains the density measurement ahead of it.

## Consequences
- The panel now reads as an instrument. Idle is dark, activity is bright, and the difference is the thing worth looking at.
- The constants are geometry independent, so moving the panel or changing its size no longer requires refitting.
- A sustained runaway would still saturate, which is acceptable, because the panel looking wrong when the network is wrong is information.
- `uSpike` and `uLift` exist as uniforms rather than literals so the next fit can be done live against a running night instead of by editing and reloading.
- The density ceiling of 12 means a panel much larger than the side panel would stay dimmer than tuned. Nothing in the project uses one.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Panel brightness derived from network activity and on-screen point density | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
