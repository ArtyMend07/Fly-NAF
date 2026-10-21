# Experiment 17: A Shuffled Brain Does Not Play

"The fly plays better than I do" is also true of a twenty-line script, so it says nothing about the connectome. The question here is whether the behaviour comes from the FlyWire wiring or from the code around it: the screen reading, the accumulators, the door bookkeeping. If a brain with the same parts and random wiring played the same way, the credit would belong to the scaffolding.

The controls are taken from other projects in the awesome-fly list. [drosophila-brain-mlx](https://github.com/Kisame76/drosophila-brain-mlx#does-the-wiring-matter) shuffles the connectome so that "every neuron keeps its number of incoming and outgoing connections and the signs and sizes of its outgoing synapses, but each connection goes to a random target", and there MN9 goes from 67.30 Hz to silent. [Doodle Fly](https://github.com/dtecx/doodle-fly#is-it-really-playing) swaps the eyes. [Fly Self Driving](https://github.com/suanmiao/fly-self-driving) and [20fly8](https://github.com/dtecx/20fly8#is-it-really-learning) report rewired and shuffled controls of their own.

### The Controls

- **Shuffled wiring**, the drosophila-brain-mlx control, three seeds. Every postsynaptic index of the 15,091,983 connections is permuted among them, so each neuron keeps its in-degree, its out-degree and the weights it sends. 0.38 percent of the connections land on a pair that already exists and are summed into it, and the total weight each neuron sends is unchanged.
- **Eyes swapped.** Every left input population is fed what the right one would see and the other way round, the hallway, the tablet and the wide-field channels alike. The readouts are not touched.
- **Inhibitors cut.** The GABAergic camera inhibitors of ADR 0006 still fire while the tablet is up, but their outgoing synapses are removed.

`python -m flynaf.scripts.measure_controls` runs each brain through eight stimuli, eight trials of forty frames from a reset network, and then through the night 3 recorded on 2026-10-16, 2618 frames fed with the eye and tablet input that night produced. It takes about 35 minutes and writes `logs/controls.json`.

### The Stimuli

Trials out of 8 in which each readout fired, and the median frame of its first spike.

```
FlyWire                     DNp01 L   DNp01 R   DNp04 L   DNp04 R   DNp09 L   DNp09 R
nothing on screen           6 @ 9.5   6 @ 9.5   0         0         2 @ 10    1 @ 11
left hallway                8 @ 3     8 @ 5     8 @ 3     0         8 @ 4     1 @ 7
right hallway               8 @ 5     8 @ 3     0         8 @ 3     0         8 @ 4
left hallway, tablet up     0         0         8 @ 3     0         0         0
right hallway, tablet up    0         0         0         8 @ 3     0         8 @ 6
figure on 1C                0         0         0         0         8 @ 3     0
figure on 4B                0         1 @ 1     0         0         0         8 @ 3
loom on 1C                  0         0         8 @ 3     0         0         0
```

On the FlyWire wiring each stimulus lands on its own readout and its own side. Both Giant Fibers fire on a hallway, but the one on the side of the threat answers two frames earlier, and a look ends on the first spike. With the tablet up the inhibitors silence both. The "nothing on screen" row is the reset network settling, and replayed over a night the same brain fired the Giant Fiber on 11 of 2580 idle frames.

```
shuffle 0                   DNp01 L   DNp01 R   DNp04 L   DNp04 R   DNp09 L   DNp09 R
left hallway                8 @ 14    8 @ 19.5  5 @ 32    8 @ 10    0         8 @ 8
left hallway, tablet up     8 @ 9     8 @ 20    8 @ 28    0         1 @ 1     7 @ 9
figure on 1C                2 @ 29    8 @ 23.5  8 @ 20.5  0         0         0
loom on 1C                  8 @ 21    8 @ 22.5  6 @ 31.5  0         0         8 @ 13
```

The shuffles answer late, on the wrong side or with the wrong neuron, and each seed differently. The tablet no longer silences the Giant Fiber, and a figure on CAM 1C, which should only wake DNp09, fires the Giant Fiber, which in the game would close a door for looking at a camera. Seeds 1 and 2 are in the JSON and fail in other ways: seed 1 fires the right Giant Fiber on nothing at all in 8 of 8 trials, seed 2 fires both on seven of the eight conditions, nothing on screen included.

```
eyes swapped                DNp01 L   DNp01 R   DNp04 L   DNp04 R   DNp09 L   DNp09 R
left hallway                8 @ 5.5   8 @ 3     0         8 @ 3     0         8 @ 4
figure on 1C                0         0         0         0         0         8 @ 3
loom on 1C                  0         0         0         8 @ 3     0         0

inhibitors cut              DNp01 L   DNp01 R   DNp04 L   DNp04 R   DNp09 L   DNp09 R
left hallway, tablet up     8 @ 3     8 @ 5     8 @ 3     0         8 @ 4     1 @ 8
figure on 1C                8 @ 6     8 @ 6     8 @ 6     1 @ 27    8 @ 3     0
loom on 1C                  8 @ 3     8 @ 5     8 @ 3     0         8 @ 5     0
```

With the eyes swapped every answer is as clean as on the FlyWire wiring and on the other side. With the inhibitors cut the Giant Fiber fires through the tablet, and a figure on the cove now wakes both escape neurons as well as DNp09. The separation of the two tablet channels in ADR 0026 is held by those inhibitors, not by the code that feeds them.

### The Recorded Night

```
                                     FlyWire  shuffle 0  shuffle 1  shuffle 2  eyes swapped  inhibitors cut
hallway threats, own side first          7        0          3          3          0              7
hallway threats, other side first        0        0          0          2          7              0
hallway threats, unanswered              1        8          5          3          1              1
frames with a DNp01 spike               18      163        276        405         15            155
idle frames with a DNp01 spike          11      161        271        394          8            124
tablet-feed frames DNp04 answered        0       11          6          1          0             25
tablet-feed frames DNp09 answered       37        5          1          8         38             47
tablet raises the DNp09 drive asked     22       43         37         45         25             23
```

The FlyWire brain answers 7 of the 8 hallway threats of the night on the right side, and the eyes swapped answer the same 7 on the wrong one, which in the game is the door opposite the animatronic. The shuffles answer between none and three, and fire the Giant Fiber with nothing in either hallway hundreds of times, each one a door shut for nothing.

### What The Controls Found Against The Project

- **How often the tablet goes up says nothing about the wiring.** The shuffles ask for the tablet 37 to 45 times against 22. The DNp09 accumulator of ADR 0014 adapts to the scale of its own signal, so any DNp09 that fluctuates enough crosses its bound. What the wiring decides is what happens during a watch.
- **The defensive state was firing the Giant Fiber with nothing in the hallway.** Replayed with the memory drive the night was recorded with, the FlyWire brain fired DNp01 on 141 idle frames. Of the 141 frames that had a spike in the live night, 128 came with the door already shut, the defensive state driving LPLC2 and LC4 and the eye not driven at all. That drive renewed door holds, pulled seven left looks in 21 seconds to a door already shut, and fired the left DNp04 during a CAM 4B watch. The state now holds the door directly and no longer reaches the eye (ADR 0011, ADR 0026), and the same night replayed without it fires DNp01 on 11 idle frames.

### What Changed In The Code

- `DefensiveState` has no drive any more. `DoorControl` keeps a door shut while the hold or the defensive state of that side stands above `release_threshold`, and `defence_sec` moves from 10 to 15 seconds, so a full-strength escape holds the door about 21 seconds, inside the 18.0 to 25.7 seconds the Giant Fiber used to hold it and near the 20 seconds Gibson et al. (2015) measured for the state to fade.
- A look ends once the eye has gone `light_quiet_frames` (4) frames without driving its cluster (ADR 0012).
- `ConnectomeEngine` takes an optional `rewire`, a function of the weights and the neuron map, applied before the model is built. `neural/rewiring.py` holds the shuffle and the cut.
- Replay feeds the brain the eye and the tablet only. Older traces keep their memory drive for the replay page.

### What This Saves, Estimated On The Same Night

The night lost power before 6 AM. Read against its log, with the new rules applied by hand:

- The first left door, 19.8 seconds, was closed by the Giant Fiber on a defensive state fed by a peek, which neither version 1.6 of ADR 0026 nor this one would do.
- The 54.9 second hold was renewed by the left DNp04 firing on the state during a CAM 4B watch. At most about 21 seconds remain.
- The 21 looks that found an empty hallway over twelve frames would have lasted four, about 19 seconds less of light.

That is about 53 seconds of door and 19 of light in 304 seconds, roughly 7 percent of the battery, or about 12 percent over a whole night. The earlier estimate of what the fly lacks to reach 6 AM was about 20 percent, so this closes most of the gap and not all of it. These are estimates from one log, since every action changes what follows, and only a live night measures them.

### What Is Not Measured Yet

- A live night with the defensive state holding the door.
- Whether 21 seconds of hold after an empty cove is enough. Foxy runs 25 seconds after leaving the cove, and the fly has to read the cove again before then. Vigilance brings the tablet back sooner, and a cove still empty fires DNp04 and adds to the state.
- `test_inhibition.py::test_metu4_adds_nothing_to_what_the_descending_neurons_do_on_a_sighting` fails about two runs in three on the right side, by 5 Giant Fiber frames against a tolerance of 3.5. Nothing in this change touches what it stimulates, and it is left for a separate look.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Shuffled wiring, swapped eyes and cut inhibitors against the FlyWire brain on stimuli and on a recorded night, and the defensive state moved out of the eye into the door hold | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-17 |
