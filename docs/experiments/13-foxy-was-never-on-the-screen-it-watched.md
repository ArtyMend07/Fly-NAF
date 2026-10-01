# Experiment 13: Foxy Was Never On The Screen It Watched

## What I Saw

Night 3 is where Foxy starts moving, and the fly never once went looking for
him. The camera buttons for Pirate Cove and the east hall had been sitting in
`MotorCalibration` since the second pull request, measured and never pressed,
and at some point I deleted them because nothing read them. That should have
been the clue. My first assumption was that the tablet simply came up too
rarely, so I went back to the reports, and the pulls were fine, roughly one
every forty seconds as ADR 0014 had fitted.

## Two Things That Were Never Wired

The tablet came up on whatever camera the game had last shown, which on a
fresh night is the show stage. So the fly was raising the monitor and staring
at Freddy. Worse, nothing it saw there reached a neuron at all. While the
monitor was up the vision loop measured one thing, whether the monitor was up,
and used that to drive the GABAergic inhibitors. The picture itself went
nowhere. The fly was not ignoring Foxy, it had no way to see him.

That still left the question of what the fly should see. A camera feed is not
a hallway with a light on it, and I did not want to invent a pathway. So
before writing anything I went to the connectome for what it already has for
an object that appears and one that approaches.

## What The 783 Release Actually Contains

The first thing I checked was the eye itself. The two clusters from
experiment 03 are LPLC2, fifty per side, and the release has 108 on the left
and 102 on the right, so the fly was looking at doors with half its looming
detectors. The other half of the looming input to the giant fiber was not
there at all. LC4 gives DNp01 374 and 431
synapses against 458 and 622 from LPLC2, and von Reyn's work splits the two
neatly, LC4 carrying how fast the shape grows and LPLC2 how large it is.

The second was DNp09, which raises the tablet. Its largest visual inputs are
LC9 and LC31a, 385 and 338 synapses on the left, and LC9 belongs to the
lobula columns tuned to fly sized objects that males use to pursue females.
DNp09 is the pursuit neuron from Bidaye's walking paper and the freezing
neuron from Zacarias. A neuron that means "an object is out there, go after
it" already raises the monitor, and nothing had ever shown it an object.

## The Wall I Hit

The obvious plan was to show the west hall to the looming populations and let
DNp01 close the door. It cannot work. With the tablet up the inhibitors are at
full drive, and 35 percent of everything DNp01 receives comes from them.
`test_inhibition.py` exists precisely to prove the giant fiber stays silent
then. I spent a while wondering whether to weaken that, which would have
meant the fly could slam a door through the tablet, which the game does not
allow either.

What got me out was listing every looming descending neuron and asking how
much of its input the inhibitors own. DNp02 18 percent, DNp06 7.6, DNp11 4.7,
DNp04 6.8. DNp04 also takes 1,671 synapses from LC4 and LPLC2 on the left, more
than the giant fiber does. It is one of the parallel escape neurons that drive
the slower takeoff when the giant fiber does not fire first.

## Measuring It Instead Of Believing It

I ran the engine as it runs at night, with the inhibitors at their real rate
and their refractory period intact, six trials of forty frames each, and
recorded the frame of the first spike.

| Condition, tablet up | DNp01 left | DNp04 left | DNp09 |
|---|---|---|---|
| Nothing on screen | 0 of 6 | 0 of 6 | 0 of 6 |
| Looming at 0.10 | 0 of 6 | 0 of 6 | 0 of 6 |
| Looming at 0.25 | 0 of 6 | 6 of 6, frame 3 | 0 of 6 |
| Looming at 1.00 | 0 of 6 | 6 of 6, frame 3 | 0 of 6 |
| Figure at 0.10 | 0 of 6 | 0 of 6 | 2 of 6, frame 4 |
| Figure at 0.25 | 0 of 6 | 0 of 6 | 6 of 6, frame 3 |

It is a clean double dissociation. Looming wakes DNp04 and nothing else, a
figure wakes DNp09 and nothing else, and the giant fiber stays gated through
both. With the tablet down the same eye still answers the hallway at frame 3,
now through DNp01, DNp04 and DNp09 together. I did not have to choose a
threshold for any of it, because the brain chooses one somewhere between a
tenth and a quarter of the span on both channels.
`src/scripts/measure_tablet_pathways.py` reproduces the table.

## What The Fly Does Now

The tablet always comes up on Pirate Cove. The cove is compared against a bank
of frames recorded at the start of the night, while the curtain is still
closed, and the distance drives LC9 and LC31a on the left. When DNp09 fires
the gaze follows the object down the west hall to 2A, once per raise. In 2A
the distance drives LPLC2 and its growth drives LC4, and when DNp04 fires the
fly drops the tablet, closes the left door, comes back to centre and checks the
office before it trusts the inhibitors are off again. Which camera to open
first is a fixed gesture and I would rather say so than dress it up.

Any camera already stalls Foxy, so the fly watching the cove longer when
something is in it is the strategy a good player uses, and here it falls out
of a neuron that was already doing the watching.

## What Is Not Measured Yet

Everything on the game side. The spans that turn an image distance into a
drive level, 1000 for both channels and 3000 per second for growth, are placed
so a clearly visible Foxy lands well above a quarter of the span, but I have
not recorded him. The 2A button position comes from the symmetry with 4B and
has to be checked. `src/scripts/debug_tablet.py` prints the live levels for
one camera so the spans can be fitted, and every trace now records the tablet
drive frame by frame, so a night with Foxy in it can be replayed through the
brain the same way the hallways are.

The part I trust least is time. The run from 2A to the office is short, and
lowering the tablet, panning to the door and pressing it takes most of it.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Why the fly never saw Foxy, the cell types behind the fix and the double dissociation that justifies it | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 |
