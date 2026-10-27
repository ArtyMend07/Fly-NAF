# Experiment 20: What The Eye Was Shown

The hallway reaches the brain as one number. When the distance between the lit hallway and the nearest empty view passes `mse_threshold` (40), every LPLC2 and LC4 neuron on that side and the MeTu4 wide-field neurons are driven at full rate, and below it nothing is (ADR 0001). The network never decides how much is enough, since the threshold already did. The tablet has read its cameras differently since ADR 0026: the share of the view that differs from the empty references drives LPLC2 and LC4 with a level, and a change across most of the view drives only MeTu4.

The Giant Fiber sums two features in flies. LPLC2 supplies the whole size component of its looming response and LC4 the angular velocity, and a model that adds a linear velocity term to a Gaussian size term reproduces its response ([Ache et al. 2019](https://doi.org/10.1016/j.cub.2019.01.079)). LPLC2 does not respond to wide-field translation or to a luminance change without motion ([Klapoetke et al. 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC7457385/)). The question here is whether the hallway can be read the way the tablet is, the share of the window as LPLC2's size and its growth as LC4's velocity, without losing the animatronics the threshold catches.

### The Network Answers In Proportion

Before any picture, the left eye cluster was driven at a fraction of its full rate from a settled network, for the twelve frames a driven look holds the light, after 60 quiet ones, ten trials per level.

```
level of the left eye     0.05    0.08    0.12    0.2     0.3     0.5     1.0
left DNp01 answered       0/10    0/10    0/10    10/10   10/10   10/10   10/10
median first frame        -       -       -       10      7       6       4
```

The right DNp01 never fired. Below about a sixth of the rate the Giant Fiber stays silent within a look, and above it the answer comes sooner the stronger the drive. The decision the threshold made in Python is one the network can make.

### The Measurement

```bash
uv run python -m flynaf.scripts.measure_hallway_eye
```

The script reads three things again, with no game.

- **Every detection the threshold eye has saved** in `logs/vision_debug`, 112 pairs of the frame seen and the empty view it was compared with, from 2026-10-01 to 2026-10-22. A pair is written when a look first drives the eye, so each one drove the whole cluster at full rate during a look.
- **Every lit hallway in the four nights** recorded with `run.py --frames` on 2026-10-21 and 2026-10-22, 332 frames, matched to the trace for the door state and with the frames where the tablet was up left out.
- **The left Giant Fiber's answer** to the drive each eye gives Bonnie, Chica and a shadow, from a settled network, ten trials each.

The share is the fraction of 40-pixel cells whose mean squared difference from the empty view, after the same downscale and blur the tablet uses, passes 100. It takes about four minutes and writes `logs/hallway_eye.json`.

### What The Saved Detections Were

Each pair was sorted by what the frame shows.

```
                                                  pairs   mse          share         looming eye
Bonnie in the left doorway                           6    117          0.22          looming
Bonnie's shadow in the closed left window           18    76-146       0.16-0.33     looming
Chica at the right window, door open or shut        14    284-533      0.31-0.38     looming
Freddy in the office after the power ran out         4    376          0.23          looming
the office panned aside, the closed window dark      4    371-389      0.30-0.49     looming
the office shifted, the light coming on, a door      4    51-272       0.02-0.08     nothing
static, other windows, camera views, office pans    62    1056-43247   0.64-1.00     wide field
```

All 38 pairs with an animatronic at a door still drive LPLC2. Of the 70 pairs with no animatronic, the looming eye stops 66. The 62 above 0.6 all read above 1000, and every detection above 1500 was already found to be something bright and large covering the eye in ADR 0001. The ones nearest the ceiling were checked by eye: the "IT'S ME" screen at 0.64, the brain panel itself at 0.66, a camera view of the backstage door at 0.80, the office panned to the desk at 0.65 and 0.83. The four it lets through are the office panned a third of the way to the desk, at 0.30 and 0.32, and the closed window gone dark, at 0.49. Freddy after the power ran out reaches LPLC2 too, and nothing the fly does then changes anything.

Every one of the 70 drove the whole eye cluster at full rate during a look, and at full rate the Giant Fiber answers in ten trials out of ten, so each was most likely a door shut or a hold renewed for nothing. The looming eye sends 62 of them to MeTu4 only and 4 to nothing.

### What The Recorded Nights Show

```
lit hallway                               frames   mse      share    looming eye
left, empty                                  88    0.9-1.6  0        nothing
left, Bonnie in the doorway                   4    118.5    0.215    looming
left shut, empty window                      39    1.7      0        nothing
left shut, shadow                            43    77-96    0.13-0.22  looming
right, empty                                142    0.8-1.4  0        nothing
screen not showing the office                16    >12000   0.69-1   wide field
```

FNAF draws each hallway from a few pre-rendered images, so the empty ones read exactly zero, and no empty frame of any night drives the looming eye. The 16 frames above 12000 show something other than the office with the tablet recorded as down, and the trace has no look running in any of them. The four nights had no Chica at the right window in a recorded frame.

### What The Giant Fiber Does With It

```
left DNp01, settled network, 10 trials       answered   median frame   right DNp01 frames
threshold eye, any figure                     10 of 10        4                0
looming eye, Bonnie (share 0.22)              10 of 10        7                0
looming eye, Chica (share 0.31)               10 of 10        5                0
looming eye, shadow (share 0.13)               0 of 10        -                0
looming eye, static (share 1.0)                0 of 10        -                0
```

Bonnie is answered three frames later, 0.3 seconds at 10 frames per second, still inside the twelve frames a driven look holds the light, and three runs of the script put his median between 7 and 8. Chica is answered one frame later. MeTu4 driven at full rate by the static does not reach the Giant Fiber. The faint shadow does not fire the Giant Fiber, but it keeps driving the eye, so a look at it is not a clear look and the door it is behind does not reopen (ADR 0011).

### What Changed With It

- `night/hallway.py` holds both eyes. `ThresholdEye` is the eye of ADR 0001. `LoomingEye` turns the share into `loom_size` for LPLC2 and `wide_field` for MeTu4 at `(share − 0.10) / 0.30`, the floor and span the tablet uses, adds `loom_speed` for LC4 from how fast the share grew over the last engine frame, and sends a share of 0.60 or more to MeTu4 alone. The first reading of a look compares against nothing seen, so an animatronic found by the light reads as one that appeared.
- `looming_eye` in `tuning.toml` picks the eye, and 0, the threshold, stays the default until a live night has been run with 1 (ADR 0020).
- The drive of each side goes to the brain as `hallway_drive`, recorded in the trace from version 5 and replayed from it. A side with no `hallway_drive` falls back to `left_rate` and `right_rate`, so older traces and the controls replay as before.

### What Is Not Measured Yet

- A live night with `looming_eye = 1` that meets an animatronic in a hallway, and how much power it saves. The night 4 of 2026-10-26 ran with it, and every look before Foxy came in from the cove found an empty hallway.
- Chica in a recorded night, beyond the 14 saved pairs.
- Whether a share of 0.6 or more ever comes from an animatronic. None of the 112 pairs did.
- The office panned aside and the closed window gone dark still reach LPLC2. Telling a pan from a figure would need the eye to know where the fly last turned, which ADR 0011 raises with Kim, Fitzgerald and Maimon (2015) and nothing implements.
- The ceiling and the floor were set on these images. A bank recorded on another screen or at another size would move every share.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Read every saved detection and every lit hallway of four nights as a share of the window, and measured the Giant Fiber on the levels it gives | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 |
