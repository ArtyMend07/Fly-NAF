# Experiment 16: Freddy Is A Memory Problem

Experiment 15 looked for a Freddy pathway and kept one candidate, LPLC1 driving DNp03 on the right. Before building on it I went back to how Freddy plays, and the game asks for something different from what that candidate does. This records the game rules, the right half of the tablet channels measured on the engine, and how far a sighting turns the fly toward CAM 4B on its own.

### What The Game Asks For

The rules below come from the Technical FNaF wiki, which reads them from the game's code. I did not check the executable.

- Freddy walks 1A, 1B, 7, 6, 4A, 4B and gets a movement opportunity every 3.02 seconds. He moves when a roll from 1 to 20 is at or under his AI level, which is 1 or 2 on night 3, 1 on night 4, 3 on night 5 and 4 on night 6, and does not rise during the night ([AI Levels](https://technicalfnaf.fandom.com/wiki/AI_Levels_(Fnaf_1))).
- Cameras stall him. The two wiki pages disagree on how. One says "If you are using cameras, he will fail every movement" ([Movement Opportunities](https://technicalfnaf.fandom.com/wiki/Movement_Opportunities_(Fnaf_1))) and the other that he "can be stalled by looking at him in the camera" ([Freddy Fazbear](https://technicalfnaf.fandom.com/wiki/Freddy_Fazbear_(Fnaf_1))).
- From CAM 4B he enters the office only when CAM 4B is not selected, the monitor is up, the right door is open and his roll succeeds. With the door closed he goes back to CAM 4A. Inside, he has "a 25% chance every second to jumpscare the player while the cameras are down" (same page).
- Any camera stalls Foxy, "for every camera flip regardless of whether or not CAM 1C is selected" (same page).

So the one dangerous moment is a raised tablet on another camera while Freddy waits at CAM 4B and the right door is open. Watching CAM 4B holds him still, and there is no race against a running animatronic, so the 50 times slower than real time brain is not the limit here. What the fly needs is to remember that something was in the corner and to keep that side covered until it has looked again. Chica also shows on CAM 4B on her way to the right door, so one channel serves both.

### Why LPLC1 Was Dropped

- Tanaka and Clark tie LPLC1 to "the geometry of positional changes of objects on near-collision courses", and its activity "drives slowing" in walking flies ([Current Biology 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9177691)). Freddy on CAM 4B does not approach across the screen. He is there in one frame and not in the previous one, which is what the object columns LC9 and LC31a already report for Foxy.
- DNp03 is tied to flight (experiment 15) and the model has no flight state.
- The right DNp03 has 366 input synapses in the 783 release against 5021 on the left.
- Closing a door from the tablet already goes through DNp04, so DNp03 would need an action of its own that the game does not have.

### The Right Half Of The Tablet Channels

Weights in the model are three times the synapse count. Divided back, the right side of each channel:

```
source        DNp01 R   DNp04 R   DNp09 L   DNp09 R
LC9 right         0         0         0       866
LC31a right       0         0         0       425
LPLC2 right     622       605         0        30
LC4 right       431       790         0         0

share of input from the tablet inhibitors
DNp01  left 35.5%   right 32.7%
DNp04  left  4.9%   right  4.8%
DNp09  left  1.8%   right  0.6%
```

Tablet up, eight trials of forty frames, trials answered and median first-spike frame:

```
condition          DNp01 R    DNp04 R    DNp09 L    DNp09 R
nothing on screen   0/8        0/8        0/8        0/8
figure right 0.05   0/8        0/8        0/8        8/8 @ 4
figure right 0.10   0/8        0/8        0/8        8/8 @ 3
figure right 0.25+  0/8        0/8        0/8        8/8 @ 3
loom right 0.10     1/8 @ 2    3/8 @ 11   0/8        0/8
loom right 0.25     0/8        8/8 @ 3    0/8        1/8 @ 7
loom right 0.50     0/8        8/8 @ 3    0/8        1/8 @ 9
loom right 1.00     0/8        8/8 @ 3    0/8        8/8 @ 6

figure left 0.05    0/8        0/8        0/8        0/8
figure left 0.10    0/8        0/8        4/8 @ 4.5  0/8
figure left 0.25+   0/8        0/8        8/8 @ 3    0/8
```

- The double dissociation of experiment 13 holds on the right. A figure wakes DNp09 and a loom wakes DNp04, and the Giant Fiber stays gated by the inhibitors.
- DNp09 never answered a figure across the midline, on either side, at any level. Until now the tablet took the side of a threat from the camera it was showing. It can come from the DNp09 that fired instead.
- The right DNp09 answers a figure of 0.05 every time, where the left one needs 0.10 to 0.25. CAM 4B therefore needs a bank whose noise really reads zero, and its own figure span.
- A loom at full strength reaches the right DNp09 by frame 6. A defensive state that strong also pushes the fly toward the tablet, which I did not test further.

### Does A Sighting Turn The Fly Toward CAM 4B

The tablet opens on the watched camera of the side the search drive leans to (`gaze.py`), CAM 1C on the left and CAM 4B on the right. The defensive state drives LPLC2 and LC4, which are also the populations the search drive reads as the eye. If a sighting on one side tilts the eye, the next raise should open on that side's camera without any rule saying so. This holds for the cove, which still feeds the defensive state. The corner no longer does (see the live night below), and its pull on the camera choice now comes from vigilance.

Each trial below starts from a reset network with the tablet down. The defensive state is set at the given strength and fades over its usual 10 seconds, and `SearchDrive` is fed the eye membrane difference and the eye spike counts every frame. Eight trials of ten seconds each:

```
sighting       leans right, median share of frames   giant fiber frames, median
none           0.54 (0.42 to 0.66)                    0
left 0.25      0.00                                    29
left 0.60      0.00                                    45
right 0.25     1.00                                    35.5
right 0.60     1.00                                    47.5
right 1.00     1.00                                    49
```

The none row is the run started with the left trials. The one started with the right trials gave 0.55 (0.28 to 0.73).

From a quarter of the span upwards, the drive leans to the sighted side on every frame for the whole ten seconds, and with nothing seen it splits close to even. A Freddy read on CAM 4B should therefore bring the next raise back to CAM 4B, which stalls him, and the same lean sends the light checks to the right door. The 4/20 players' habit of parking on CAM 4B has the same effect, and here nobody wrote it down as a rule.

Since experiment 17 the defensive state no longer drives LPLC2 and LC4, so this lean is gone. The pull back to a sighted camera now comes from vigilance alone.

### What Changed In The Code

- DNp09 is read per side (`explore_left`, `explore_right`). The pooled readout still drives the monitor, and a figure counts on the side whose DNp09 fired.
- `watched` now holds CAM 1C and CAM 4B, and each `CameraButton` carries its own `figure_span_mse`. CAM 4B starts with the CAM 1C value of 1500 until a live night gives it one.
- A figure raises a vigilance trace on its side, and only CAM 1C also feeds the defensive state. Vigilance raises the gain of the DNp09 accumulator and draws the camera choice back to its side. Empty views habituate their side for the next choice (ADR 0026).

`python -m flynaf.scripts.measure_freddy_pathway` reproduces the first table, and `test_inhibition.py` asserts that a figure stays on its own side.

### On The Live Game, 2026-10-16

Four nights 3 were played. Three of them were cut short by problems that had nothing to do with the corner: a recalibration with the doors already closed (ADR 0018), a tablet that rose too rarely (ADR 0014) and camera references taken during the night's opening card (ADR 0026). The fourth ran with those fixed and the defensive version of CAM 4B.

- The CAM 4B button at (1087, 641) opens the East Hall Corner.
- An empty CAM 4B read 0.00 on every view against its own bank, with noise floors of 208 to 349 across nights, so the right DNp09's sensitivity did not turn the empty corner into a figure.
- Chica in the corner read 1.00. DNp09 on the right answered, DNp04 on the right dropped the tablet and the right door closed before she reached it, twice. Freddy did not reach the corner on any of the four nights.
- With a rule that held each door until its camera read clear, the left door was shut 239 of 454 seconds, once for 172 seconds at a stretch while Foxy peeked from the cove, and the right door 81 seconds, 62 of them for Chica still standing in the corner. The tablet rose 14 times, 1.85 a minute. The fly reached 5AM and the power ran out.

That night is why CAM 4B no longer closes a door and the clearing rule is gone.

### What Is Not Measured Yet

- What Freddy reads in the corner. Experiment 14 showed a dark figure can read as nothing, and he is darker than Chica.
- Whether vigilance brings the fly back to CAM 4B often enough to hold Freddy, and what the night costs in power without the right door. These need a night 4 or 5, since on night 3 Freddy rarely reaches the corner.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Freddy's rules from the game, the right half of the tablet channels, the lean a sighting gives the search drive, and the first live nights with CAM 4B, after which the corner raises vigilance instead of closing a door | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-16 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-16 |
| 1.1 | Noted that the lean through the defensive state went away with experiment 17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-17 |
