# Experiment 10: Reading the Night Backwards

## What I Saw

Two things out of the 2026-09-17 run. The movement finally looked natural,
which is the ADR 0012 and ADR 0013 work landing and was genuinely satisfying to
watch. But the fly kept reaching for the hallway lights before it had put the
tablet away, and then partway through the night it stopped putting the tablet
away at all. I ended up lowering it by hand.

There is no "monitor lowered" line to grep for, because I never wrote one, so
the whole thing had to be reconstructed backwards out of the log I did have.
Hence the title.

## A Coincidence That Is Not One

```
17:50:47 INFO DNp09 drive reached the bound (1.01), camera pull triggered
17:50:47 INFO right light check, drift (search drive -1.13)
```

Same second. Those two cannot both happen, because the tablet is physically
covering the office light buttons. What I found is that the engine loop was
evaluating `can_look` near the top of the frame and the camera block near the
bottom, so a single frame could queue a look, raise the tablet underneath it,
and then hand the effector a command it had no way of carrying out.

I had been assuming this was a decision problem and was ready to go re-tune
`SearchDrive`. It isn't. Both drives picked perfectly sensible things. It is
the order the frame acted on them in, which is a much more boring bug and took
me much longer to see because I was looking at the wrong layer.

## The Reference That Became A Photograph Of The Tablet

`camera_watch_max_sec` is 6 seconds, so the release lands around 17:50:53.
Five seconds later:

```
17:50:58 WARNING the camera-closed reference has disagreed with the screen for 5s
```

The fly thought the tablet was down and the screen was telling it otherwise.
`close_camera` was fire and forget at that point, and the gesture slides the
cursor away from the tablet bar rather than onto it, so the simplest reading is
that the tablet just never came down.

Then the part that actually ruins the night. One second after the close was
issued, `_refresh_camera_closed_reference` fired on its own timer and
recaptured the office reference from whatever happened to be on screen. What
was on screen was the tablet. From that moment `is_camera_up` was comparing the
office against a picture of the tablet, so it read each one as the other, and
when I finally lowered the thing by hand the detector latched to `True` and sat
there:

```
17:52:28 WARNING the camera-closed reference has disagreed with the screen for 65s
```

`cam_inhib` runs straight off that signal at the full sensory rate, and per ADR
0006 that pins the GABAergic clusters and zeroes the Giant Fiber. Which shows
up exactly where you would expect:

```
17:52:04 INFO left light check, guard (search drive -0.72)
17:52:07 INFO right light check, guard (search drive -2.15)
17:52:28 INFO left light check, guard (search drive +1.16)
17:52:43 INFO left light check, guard (search drive -0.97)
```

Every single reason after 17:51:58 is `guard`. The brain had stopped
contributing anything and the starvation backstop was carrying the entire
night, which is precisely the metronome ADR 0012 exists to delete. So the
search drive did not regress. It was gagged, and I nearly went and "fixed" a
component that was working.

This is experiment 09 again wearing a different costume. There the reference
was captured once at boot and never refreshed. Here it refreshes too eagerly
and against the wrong frame. Opposite mistakes, identical ending: a stuck
`True` and a fly that has gone quiet.

## What Was Wrong With The Detector Itself

`is_camera_up` compared only the newest frame in the buffer against the
reference, with `mse_trigger` sitting at 100. The office has a fan turning and
a poster that flips, so a single frame against a threshold that low is close to
a coin toss, and sure enough the log carries two of these warnings from before
any camera pull had happened at all. The hallway detectors had already solved
this by reading across the buffer instead of off one frame. The camera detector
never got the same treatment.

## The Fix, And What I Still Don't Know

Lowering is now a loop that ends on evidence rather than on optimism. Issue the
slide, wait out the settle, ask the screen. If the office is back, re-anchor
the reference and report success. If it isn't, drive the cursor onto the tablet
bar and off again and ask a second time. Only then warn, and warn with the
measured MSE attached, so that next time I can tell a genuinely stuck tablet
apart from a stale reference instead of guessing. ADR 0015 has the rest.

The guard that actually breaks the cascade is much smaller than any of that:
the reference is never captured while the detector still reads the tablet. It
can drift with the office all night, which is what experiment 09 asked for, and
it can never become a photograph of the tablet.

What I still don't know is which gesture FNAF really listens for. The fly now
tries both and records which one worked, so the next night answers it without
me having to guess.

## The Panel

Separate problem, same day. I looked at the activity panel with the simulation
not even running and it was a solid white cloud. With nothing firing, the only
thing on screen is `BASE_ALPHA`, which was 0.20 per point, additive, with
138,639 points drawn into 180 by 180 pixels. That works out to 4.3 points per
pixel on average and several times that over the optic lobes, so the floor
alone clips to white before a single spike ever arrives.

Serving the real geometry against a synthetic feed reproduced it exactly, which
made it cheap to fit instead of guessing at alpha values. Brightness now
follows both how much of the network is firing and how densely the cloud lands
on the canvas, so the panel sits dark while the fly idles and swells when the
network is actually working. Numbers are in ADR 0016.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Reconstruction of the 2026-09-17 night, the poisoned office reference, and the panel saturation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Rewritten in the logbook voice used by the rest of the folder | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
