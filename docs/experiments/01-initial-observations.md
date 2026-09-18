# Phase 1: Experimental Observations

Field notes from getting Phase 1 to run at all. None of this is a formal
claim, it is just what I ran into while the simulated biology and the game
were meeting each other for the first time.

## 1. The Shadow Trap Calibration

Turning the hallway light on in-game did not trip the brightness threshold
(`> 50.0`) at the coordinates I had calibrated (X=425, Y=486), which made no
sense to me until I watched it happen a few times.

The game uses a directional light cone, and the pixel I had picked sits in the
shadow of the doorway. The brightness there only spikes when an actual 3D model
steps into the cone and bounces light back into the shadow. So the light alone
does nothing, and an animatronic standing in it does.

That turned out to be free. The detector is immune to the player flicking the
light on to peek down the hallway, because that is exactly the case that
doesn't move the pixel.

## 2. In-Game Viewport Panning Drift

The mouse kept landing slightly off-target even though `SetCursorPos` uses
absolute coordinates, which had me suspecting the OS before I suspected the
game.

It is the pan mechanic. The office view slides with the mouse position, so if
the viewport isn't pinned hard against the left boundary (by slamming the
cursor into the edge of the screen) during both calibration and execution, all
the UI elements drift horizontally underneath the coordinates I recorded. I
measured a ~66 pixel gap between two calibration attempts that differed by
nothing except where the view happened to be sitting.

Which means the camera has to be rigidly locked to the boundary before any
click is trustworthy. Every screen coordinate in the project inherits that
assumption.

## 3. Biological Inhibitory Absorption

I traced the signal from the Sugar GRNs to the P9 motor neurons with a
throwaway script from that phase, expecting a leg reflex out the other end.

Nothing arrived. I injected a biologically maximum saturation, 10,000 Hz, which
is a 1.0 firing probability per step, into the sensory neurons for 100
milliseconds. Out of 138,639 neurons the burst woke exactly 611 interneurons,
and the wave died out completely before reaching P9. Zero spikes.

I was annoyed at the time, but it is the connectome doing its job. The real
network does not let a sugar stimulus turn into a violent leg contraction, and
that inhibitory filtering is presumably why a fly is not permanently twitching.
It is also why Phase 1 needed the bypass in ADR 0003, and why the graph search
routing had to be Phase 2 rather than an afterthought.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Initial version | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 |
| 1.1 | Rewritten in the logbook voice used by the rest of the folder, and dropped the reference to a script that no longer ships | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
