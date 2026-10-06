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
The tablet reads Pirate Cove through LC9 and LC31a, and what DNp09 answers to is remembered on the left through LPLC2 and LC4.

- Raising the tablet taps CAM 1C. This is a fixed motor gesture, recorded as such, in the same class as the pan delay.
- The cove is compared against a bank of frames captured at the start of the night with the curtain closed. The feed is the whole camera view with the map, its label, the clock and the power readout masked out, because the gap in the curtain, the sign and the far end of the west hall all sit outside the 360 pixel square the feed first read. Each frame is slid sideways against its nearest references before they are compared, since the camera pans about 160 pixels each way and a bank recorded over three seconds covers only part of that sweep. The distance is the mean of the three strongest cells of 40 by 40 pixels rather than the mean over the frame, the way a columnar lobula population reports a small object wherever it is instead of averaging it away. That distance above the bank's own noise, over `figure_span_mse`, drives LC9 and LC31a on the left.
- A DNp09 spike while the cove is readable stores an object memory on the left, as strong as the figure drive at that moment, fading with `object_memory_sec`. Flies keep heading for a landmark for seconds after it vanishes (Neuser et al. 2008) and stay in a defensive state for tens of seconds after a visual threat (Gibson et al. 2015). A spontaneous DNp09 spike on a closed curtain stores nothing, because the figure drive is zero. A weaker sighting never overwrites a stronger memory, and a memory that would feed less than one spike a second per neuron counts as gone.
- The memory drives LPLC2 and LC4 on the left at its current level, whether the tablet is up or down. No rule says to close the door. With the tablet up DNp04 answers, and with the tablet down the Giant Fiber answers, which renews the door hold of ADR 0015.
- CAM 2A is not looked at. Until version 1.3 a DNp09 spike moved the gaze there and the hall drove LPLC2 and LC4. Foxy reaches the door 1.7 seconds after CAM 2A first shows him, and reading the hall, firing DNp04, lowering the tablet and closing the door do not fit in that. Left unwatched, he takes 25 seconds from leaving the cove. The hall also could not be read. Its lamp flickers, the camera pans further than the bank covers, and the map covers most of his run, so on a recorded night 3 the empty hall and Foxy running gave overlapping distances under every metric tried.
- A DNp04 spike while the tablet is up drops the tablet, waits for the camera map to leave the screen and only then closes the door on that side (ADR 0015).
- A watch only counts as boring once the feed has been readable for `camera_watch_min_sec`. Counted from the raise, as it first was, every watch on 2026-10-01 ended 0.7 to 1.0 seconds in, before the 1.2 second settle had passed, and CAM 1C never reached the brain once in a night Foxy won. Counted from the moment the feed is readable, the same night's watches fed 0.02 to 0.27 of figure drive while Foxy changed in the cove. That sits around the 0.25 the table above needs for DNp09, so a peeking Foxy is noticed weakly and rarely pursued, and the empty cove with its sign has not yet been caught on a watch.
- On 2026-10-02 a night 2 was played by hand while every CAM 1C and CAM 2A frame was saved, and the old square read the empty cove at 0.04 of figure drive. Replayed through the reading above, against nine closed-curtain frames from the same night, the stages separate cleanly, and `figure_span_mse` moved from 1000 to 1500 so the empty cove lands near 0.6.

```
CAM 1C, night 2              contrast     figure drive
closed curtain (noise)       2 to 278     0
Foxy peeking                 530 to 1335  0.14 to 0.67, median 0.42
Foxy out of the curtain      788 to 1549  0.31 to 0.82, median 0.58
empty cove with the sign     1172, 1192   0.57, 0.58
```

- A night 3 recorded on 2026-10-03 read a closed curtain at contrast near 1000 on some watches. The MUTE CALL button and the blinking recording dot sit at the top left of the view and were outside the mask, and CAM 1C pans about 320 pixels in total, more than the 200 the alignment could slide. The top left mask grew to cover both and `pan_reach` moved to 360, after which the closed curtain of that night reads at the bank's noise.
- With the tablet down and the same loom drive, DNp01 answered 6/6 from 0.02 in trials started from rest. In a continuous run the network adapts and the Giant Fiber stops answering once the memory falls to about 0.1. Four runs per strength, tablet up for the first 1.5 seconds, gave the figures below. `object_memory_sec` is 10 because Foxy needs 25 seconds from the cove to the door and the camera refractory brings the tablet back to the cove after 15, where a cove that is still empty refreshes the memory.

```
memory     DNp04 fires   last Giant Fiber spike   door hold ends
4 s        0.2 s         5.3 to 9.0 s             10.1 to 13.8 s
8 s        0.2 s         10.3 to 16.2 s           15.1 to 21.0 s
10 s       0.2 s         13.2 to 20.9 s           18.0 to 25.7 s
```

- A night run on 2026-10-04 watched CAM 1C ten times and read 0.37 to 1.00 of figure drive on nine of them, yet stored one memory. The inhibitors hyperpolarise DNp09 during the 1.2 second settle, so after it the neuron needs 6 to 7 engine frames to answer a figure of 0.4, 5 at 0.6 and 4 at 1.0, eight trials each, which is 0.8 to 1.2 seconds on that night's frames. `camera_watch_min_sec` was 0.8, so on four watches DNp09 spiked one or two frames after the fly had already given up the watch, with nothing left to remember. The last of them read 1.00 about seventeen seconds before the night ended. `camera_watch_min_sec` is now 2.0, which also covers most answers to a figure of 0.2 (9 to 17 frames).
- The camera map can take longer than `flip_confirm_sec` to appear on the very first raise of a night. Five nights that started with the eye references loaded from disk raised the tablet about 0.1 seconds after the office appeared, missed the map and found the tablet up a few seconds later, so those nights never recorded a bank and the tablet fed nothing at all. The start-of-night raise now waits up to `start_raise_patience_sec` for the map before giving up, and logs how late it came. It never repeats the gesture, because a second flip during a slow raise would put the tablet back down.

`env/tablet_feed.py` captures and compares the feed, `night/tablet/` holds the transduction, the gaze, the per-frame watch and the start-of-night references, and the door bookkeeping moves out of the engine loop into `night/doors.py` so the Giant Fiber and DNp04 close doors through one path.

## Consequences
- Which descending neuron answers is decided by the connectome. Neither channel reaches the other's readout, and the Giant Fiber stays gated while the tablet is up, so `test_inhibition.py` keeps its guarantee, asserts the dissociation, and asserts that a remembered figure keeps the Giant Fiber answering once the tablet is down.
- Seeing Foxy in the cove keeps DNp09 depolarised, which keeps the tablet up longer, which stalls him. That behaviour is not written anywhere, it follows from DNp09 already controlling the tablet.
- Foxy peeking through the curtain reads about 0.42, enough for DNp09 and for a memory, so the left door can close for about twenty seconds while he is still in the cove. That costs power and has not been measured on a full night.
- A raise that comes while the memory is still above about 0.15 makes DNp04 fire again and drops the tablet before the cove is read. The door is closed at that point, and the next raise reads the cove.
- The figure span is fitted on one night of Foxy in the cove. `debug_tablet.py` prints the level live, and traces carry the tablet drive so it can be refitted from recorded nights.
- Reading the whole view costs about 50 milliseconds a frame with the wider pan reach, so the feed computes it on its own capture thread and the vision loop only collects the latest value. The in-game panel can no longer sit over the camera view, since it would cover the gap in the curtain. A game that leaves no room beside it now gets the panel elsewhere on the screen or none (ADR 0009).
- The start of the night gains one tablet raise to record the CAM 1C bank. Foxy is stalled for all of it.
- The escape is a chain of motor actions, and lowering the tablet plus panning to the left door takes over a second. It now starts when the cove is seen changed, with up to 25 seconds in hand. The whole chain is tested on the engine and on recorded frames. The one live night so far stored a single memory, which closed the left door four seconds later through the Giant Fiber and held it 22.5 seconds, and a live night with the longer watch is still owed.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | CAM 1C drives LC9 and LC31a, DNp09 pursues to CAM 2A, CAM 2A drives LPLC2 and LC4, DNp04 closes the door | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 |
| 1.1 | Described the escape against the camera map instead of the office reference | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
| 1.2 | Counted the minimum watch from the moment the feed is readable and recorded the drive Foxy produced | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
| 1.3 | Read the whole camera view, aligned to the pan and measured by its strongest cells, refitted the figure span on a recorded night 2 and waited for a slow first raise | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-02 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-02 |
| 1.4 | Dropped the CAM 2A pursuit. A DNp09 spike on the cove stores an object memory that drives LPLC2 and LC4, so DNp04 closes the door and the Giant Fiber holds it. Masked the MUTE CALL corner and widened the pan reach | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-04 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-04 |
| 1.5 | Raised the minimum watch to 2.0 seconds after a live night where DNp09 answered the cove just after the watch had ended | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-04 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-04 |
