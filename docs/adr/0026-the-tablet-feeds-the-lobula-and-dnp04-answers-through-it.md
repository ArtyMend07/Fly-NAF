# ADR 0026: The Tablet Feeds the Lobula, and DNp04 Answers Through It

## Status
Accepted. Resolves the open point left by ADR 0014, that the tablet decided only whether to look and never which camera.

## Context
Foxy is only visible through the tablet. He advances from Pirate Cove (CAM 1C) while no camera is in use, runs down the west hall (CAM 2A) to the left door once he leaves, and any camera stalls him. The fly raised the tablet on whatever camera the game last showed, and nothing on that screen reached a neuron, so Foxy could not be perceived at all.

The door reflex cannot be reused through the tablet. ADR 0006 gates the Giant Fiber with GABAergic inhibitors while the tablet is up, and those inhibitors supply 35 percent of DNp01's input. Among the other looming descending neurons, DNp04 receives 1,671 synapses from LC4 and LPLC2 on the left and only 6.8 percent of its input from the same inhibitors. DNp09, which already raises the tablet, takes its largest visual input from LC9 and LC31a, lobula columns tuned to fly sized objects and used in pursuit (Bidaye et al. 2020, Klapoetke et al. 2022).

The table below was measured on the running engine with the inhibitors at full drive, six trials of forty frames each.

```
condition, tablet up     DNp01 left   DNp04 left   DNp09
nothing on screen        0/6          0/6          0/6
loom 0.10                0/6          0/6          0/6
loom 0.25 to 1.00        0/6          6/6 @ 3      0/6
figure 0.10              0/6          0/6          2/6 @ 4
figure 0.25 to 1.00      0/6          0/6          6/6 @ 3
```

## Decision
The tablet reads the west side through two lobula channels, chosen by the camera being watched.

- Raising the tablet taps CAM 1C. This is a fixed motor gesture, recorded as such, in the same class as the pan delay.
- The cove is compared against a bank of frames captured at the start of the night with the curtain closed. Taking the nearest frame in the bank absorbs the camera pan. The distance above the bank's own noise, over `figure_span_mse`, drives LC9 and LC31a on the left.
- A DNp09 spike while the cove is readable moves the gaze to CAM 2A, once per raise. The object has left and the fly follows it.
- In CAM 2A the same distance drives LPLC2 and its growth per second drives LC4, the size and velocity split of the door reflex.
- A DNp04 spike while the tablet is up drops the tablet, closes the door on that side, recentres the view and re-anchors the office before the lowering counts as done.

`env/tablet_feed.py` captures and compares the feed, `night/tablet/` holds the transduction, the gaze, the per-frame watch and the start-of-night references, and the door bookkeeping moves out of the engine loop into `night/doors.py` so the Giant Fiber and DNp04 close doors through one path.

## Consequences
- Which descending neuron answers is decided by the connectome. Neither channel reaches the other's readout, and the Giant Fiber stays gated throughout, so `test_inhibition.py` keeps its guarantee and now also asserts the dissociation.
- Seeing Foxy in the cove keeps DNp09 depolarised, which keeps the tablet up longer, which stalls him. That behaviour is not written anywhere, it follows from DNp09 already controlling the tablet.
- Bonnie standing in 2A drives LPLC2 without growth and still wakes DNp04, so the left door closes early. That is a correct defensive reading and costs power.
- The spans that convert image distance into drive are game-side constants that have not been fitted against a recorded Foxy. `debug_tablet.py` prints them live, and traces now carry the tablet drive so they can be refitted from recorded nights.
- The CAM 2A button position is inferred from CAM 4B and needs confirming on screen.
- The start of the night gains one tablet raise of about eight seconds to record the two banks. Foxy is stalled for all of it.
- The escape is a chain of motor actions, and lowering the tablet plus panning to the left door takes over a second. Whether that fits inside Foxy's run is the first thing a recorded night has to answer.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | CAM 1C drives LC9 and LC31a, DNp09 pursues to CAM 2A, CAM 2A drives LPLC2 and LC4, DNp04 closes the door | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 |
