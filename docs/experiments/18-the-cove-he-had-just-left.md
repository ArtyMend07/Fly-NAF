# Experiment 18: The Cove He Had Just Left

On the night 4 of 2026-10-22 Foxy stood out of the curtain for two minutes, from the look at 251 seconds to the one at 367, and the fly read him eleven times without DNp04 firing, which is what ADR 0026 asks of a figure that does not move. At 378 seconds the cove was empty and the left door open. Read against the closed curtain the empty cove differed by 0.31 of the view, and read against the last look, at Foxy standing out nine seconds before, by 0.11. Since version 1.10 of ADR 0026 the loom is fed only the change that is also new since the last look, so the eye saw almost nothing. DNp04 stayed silent, the door stayed open, and Foxy came through it about 25 seconds later.

Two ways out of this were wrong. A threshold on the share would be a rule written in Python, not the eye. Dropping the comparison with the last look would bring back what version 1.10 fixed, every look at a Foxy standing out firing DNp04 and shutting the door for minutes. The question here is whether the comparison can fade the way habituation fades in flies, so that a cove empty for the second time in a row reads as new while a figure that stood the same way ten seconds before does not.

[Gibson et al. 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4452410/) saw the escape habituate when about twenty shadows came 10 to 20 seconds apart. The looks at the cove come about 10 to 15 seconds apart, so a decrement that lasts across one gap and fades over a few is in the range the flies show. Version 1.11 of ADR 0026 takes away what the last look already explains in proportion to exp(-t/`look_recovery_sec`), with t the seconds since that look ended.

### The Measurement

```bash
uv run python -m flynaf.scripts.measure_look_recovery 20261021_235649 20261022_001329
```

The script takes every look at CAM 1C in the two nights recorded with `run.py --frames` on 2026-10-21 and 2026-10-22, 31 looks in all, and reads each frame again from `logs/frames/` against the CAM 1C reference bank kept on disk and against the frames of the look before it, with that look fading over each recovery time. "Never" is the version 1.10 eye, the last look subtracted in full. Each look's drive is cycled to twenty frames, fed to the engine with the tablet up after eleven settling frames, and run six times, because a look cut short by an escape held only a few frames and a short look underrates DNp04. It needs the FlyWire data and the saved frames, and no game.

Each look was sorted by what the saved frame shows, and the two nights give the same answer for each kind:

```
CAM 1C, looms as median of the look, DNp04 trials fired out of 6

                                            last look fades over
                                   looks    never        20 s         30 s
Foxy coming out of the curtain       3     0.32-0.41    0.38-0.49    0.38-0.44
                                           6/6 each     6/6 each     6/6 each
the cove just left                   3     0.00-0.02    0.25-0.52    0.17-0.40
                                           0/6 each     6/6 each     6/6 each
Foxy standing out                   17     0.00         0.00-0.19    0.00-0.06
                                           0/6 each     6/6 once     0/6 each
Foxy peeking behind the curtain      4     0.00         0.00         0.00
the curtain closed                   2     0.00         0.00         0.00
the cove empty again, 10 s later     2     0.00         0.00         0.00
```

The three looks at a cove just left, one per row:

```
                                          never        20 s         30 s
2026-10-21  204.7 s, door shut            0.00 0/6     0.25 6/6     0.17 6/6
2026-10-22  170.0 s, door shut            0.00 0/6     0.52 6/6     0.40 6/6
2026-10-22  377.9 s, door open            0.02 0/6     0.33 6/6     0.24 6/6
```

The one Foxy standing out that fired at 20 seconds is the look at 266.1 seconds on 2026-10-22, 0.19 against 0.06 at 30 seconds.

### What This Shows

- **The version 1.10 eye cannot see a cove just left.** DNp04 fired in none of the six trials on any of the three, with the door shut twice and open once. The open door is the look after which Foxy came in.
- **A fading last look brings them back without bringing Foxy back.** At 30 seconds all three cove-just-left looks and all three exits fire every time, and none of the 17 looks at a Foxy standing out does. At 20 seconds the same 6 fire, and so does one of the 17.
- **The fading does not touch what had no change to begin with.** The closed curtain, the peeking Foxy and the cove empty for the second time read 0.00 under every recovery time, because what the last look takes away cannot exceed what the reference bank shows.

`look_recovery_sec` is 30 seconds. Below that a Foxy standing out begins to fire, and the margin above the exits is wide, the weakest cove-just-left look still driving 0.17 against 0.06 for the strongest standing Foxy.

### What Changed With It

The fading opened two problems that version 1.11 of ADR 0026 also handles, and both come from the same replay:

- An escape from a cove just left drives the loom at 0.17 to 0.40, and fed by the loom the defensive state fell under the release level within five seconds, while Foxy takes 25 from the cove to the door. Each escape now adds a constant to the state, as each shadow does in the leaky integrator of Gibson et al., and holds the door for about 21 seconds.
- A Foxy standing out looms a little again under the fading, and on these nights a DNp09 spike fell on such a frame in 6 of the 17 looks, which under version 1.10 would have sent the gaze to an empty CAM 2A. The gaze now follows the cove only while the defensive state from an escape still holds the door.

### The Live Night

The night 4 of 2026-10-26 ran version 1.11 live, recorded with `--frames`. Foxy showed in the curtain at 110 seconds and DNp04 fired on that look, dropped the tablet and shut the left door. He then peeked from the curtain for a minute, five looks at loom 0.00 to 0.06 and no escape. At 183 seconds the cove was empty and read a loom between 0.08 and 0.27 against the last look, in the range this replay found for a cove just left. The view was readable for 1.8 seconds before the fly tired of it, and DNp04 fired 0.22 seconds after the tablet had started down. That spike was dropped, the empty cove counted as a clear view, the left door was open, and Foxy came in at 201 seconds.

The replay above cycles each look's drive to twenty frames, and on the live night the cove was readable for eighteen, so DNp04 answered one frame after the view had ended. Version 1.12 of ADR 0026 counts a DNp04 spike during the lowering against the view the tablet came down from.

### What Is Not Measured Yet

- A live night 4 with version 1.12 of ADR 0026.
- The power the 21-second holds cost. Every escape from the cove holds the left door at least that long, Foxy coming out included, where the loom-sized state held it 13.6 to 27.8 seconds on these two nights.
- How often a look inside those 21 seconds glances at an empty CAM 2A while Foxy is still in the cove.
- The reference bank read here is the one on disk today. A bank recorded anew at the start of a night would move every share a little.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Replayed every look at the cove of two recorded nights with the last look fading over 20 and 30 seconds and without fading | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-24 |
| 1.1 | Added the live night 4 of 2026-10-26, where DNp04 answered the cove just left after the tablet had started down | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 |
