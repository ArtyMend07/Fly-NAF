# Experiment 12: Every Neuron In Someone Else's Place

## What I Saw

The new panel replays the synapses that fired on the way to a DNp01 spike, and
the replay looked wrong in a way I could not name. Red lines crossed the whole
brain in every direction, a hub of them sat in no region I recognised, and the
trace from the eye cluster to the giant fiber looked like a bowl of noodles
rather than a pathway. My first guess was the trace. The walk keeps the three
strongest inputs per neuron, and DNp01 does collect input from half the brain,
so maybe that is simply what it looks like. I cut the cap from 600 synapses to
160 and it became a smaller bowl of noodles.

## The Mesh That Would Not Fit

What actually gave it away was trying to add the outline of the brain, which
the panel never had. navis-flybrains publishes the FlyWire brain surface, so I
fetched it and tried to line it up with the soma positions the panel draws. It
would not line up. The x span matched and the other two did not, and no
rotation, scale or shift fixed that. A least squares fit of the soma file
against the positions in the FlyWire annotation supplement, matched by root id,
left a median error of 232 micrometres, which is most of the width of the
brain. The correlation between the two, axis by axis, was zero to the third
decimal.

So the file had the right root ids in the right order and coordinates that
belonged to none of them. The cloud was shaped like a brain, because it was a
brain's worth of positions, and every neuron was sitting in the place of
another one. The eye cluster lit up in random corners, DNp01 was somewhere in
the optic lobe for all I knew, and every panel screenshot since the 3D view
was added showed that. Nobody noticed, me included, because a shuffled brain
still looks like a brain from the outside.

## Where The File Came From

`fetch_data.py` downloads the FlyWire Codex release, and the Codex file is not
the one that was on disk. The Codex file has `root_id,position,supervoxel_id`
with the position written as `[x y z]` in nanometres and several rows for some
neurons. The file on disk had `pt_root_id,x,y,z`, centred on zero, with far
more decimals than a voxel position ever carries. The panel's parser only
understood the second layout and read it by row, never by id. So the parser
could not have read what `fetch_data.py` fetches, and anyone installing from
scratch would have had a panel that failed to start, while this machine had one
that started and lied.

I do not know where the second file came from. It predates the fetch script.

## The Fix

The panel now reads the Codex file and looks each neuron up by root id. The
first position the Codex lists for a neuron matches the annotation supplement
exactly, with a median distance of zero, and it covers all 138,639 neurons in
the model. `fetch_data.py` checks the header and replaces a soma file in any
other layout. I kept the old file as a `.bak` while checking the fix and then deleted it,
since there was nothing in it worth keeping.

With the positions right, the brain outline fits without any adjustment
beyond a shared centre and scale, and the neurons that land outside it are the
photoreceptors, whose cell bodies really are outside the brain, in the retina.
The replay changed completely. The trace now starts at a knot of eye cluster
neurons in the left optic lobe and fans into the central brain toward DNp01.
That is the escape pathway experiment 03 described, drawn by the panel for the
first time, and the bowl of noodles was never a property of the connectome.

## What I Take From It

A visualisation of real data is only as honest as the join between the data
and the picture, and that join had no test at all. There is one now, which
feeds a small Codex file with its rows out of order and checks that each id
gets its own position.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | The shuffled soma positions, how the brain outline exposed them, and the fix | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 |
| 1.1 | Noted that the old soma file was deleted | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 |
