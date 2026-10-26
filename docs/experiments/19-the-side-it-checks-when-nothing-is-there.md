# Experiment 19: The Side It Checks When Nothing Is There

Which hallway the fly lights next is decided by the search drive of ADR 0012, an accumulator of the voltage difference between the two eye clusters (drift), their spike counts (evidence) and the ring neurons of the ellipsoid body (memory), with a guard that forces a look at a side left unchecked for 30 seconds. On the five live nights of 2026-10-21 and 2026-10-22 drift started between 12 and 33 looks a night, and the guard forced between 5 of 22 and 29 of 60. Every neuron also gets 1 Hz of subliminal noise (ADR 0013). If the drift were that noise, the choice of hallway would be noise with extra steps, and the guard would be doing the rest.

The question is whether the choice of side depends on the FlyWire wiring, and in which situation.

### The Measurement

```bash
uv run python -m flynaf.scripts.measure_look_choice --seeds 0 1
```

The script runs the night's look loop with no game: the engine, the search drive, the ring memory and the saccade refractory period, at 10 frames per second. A look waits `light_activation_settle_sec`, reads the hallway and ends after `light_quiet_frames` when nothing is there. It runs four brains:

- **FlyWire**, the wiring the nights use.
- **Shuffles 0 and 1**, the control of experiment 17, every connection sent to a random target with each neuron's degrees and outgoing weights kept.
- **Unwired**, every synaptic weight set to zero, so the only activity is the subliminal noise and whatever the eye is fed.

Each brain first runs 3000 frames, five minutes, with both hallways empty. Then it runs 24 sightings, alternating sides: a look in which that hallway drives the eye until its Giant Fiber answers or the look ends, followed by the next look the drive asks for. It takes about 15 minutes and writes `logs/look_choice.json`.

```
                                         FlyWire     shuffle 0     shuffle 1       unwired
idle looks                                    49            81            86            34
idle looks to the left                        32            72            77            25
idle side switches                      25 of 48      18 of 80      18 of 85      18 of 33
idle median wait (s)                         3.1           2.6           2.6           2.6
idle looks by drift                           30             3             1             0
idle looks by memory                          14            69            76            24
idle looks by guard                            5             9             9            10
sightings answered by the giant fiber         24            19            10             0
next look back to the sighted side      24 of 24      13 of 24      13 of 24       4 of 24
next looks by guard                            3             5             5            21
```

No idle look of any brain was started by evidence, since an empty hallway drives neither eye.

### What This Shows

- **The drift belongs to the network and not to the noise.** It started 30 of the 49 idle looks of the FlyWire brain and none of the 34 of the unwired one, which gets the same noise. The accumulator divides its input by its own running scale, so white noise averages out before it reaches the bound, and what crosses it is the slow fluctuation of a recurrent network.
- **With nothing to see, that fluctuation carries no information about the hallways.** The FlyWire brain switched sides 25 times in 48 looks, where a coin gives 24, and went left 32 times out of 49. When both hallways are empty, the side it checks next is its own spontaneous asymmetry. That is the fly choosing, and not a judgement about where the threat is.
- **After a sighting the choice depends on the wiring.** The FlyWire brain went back to the side it had just seen something on 24 times out of 24, 12 of them by memory and 9 by drift. The shuffles went back 13 times out of 24, which is chance, and the unwired brain 4 times, with the guard deciding 21 of its next looks. The unwired brain gets the same eye input during the sighting, so the return does not come from the input itself.
- **The memory term is calibrated to FlyWire.** `ring_resting_*` and `ring_sighting_*` were measured on the FlyWire ring neurons (ADR 0012), and on another brain they read a permanent memory of the left side, which is why the shuffles looked left 72 and 77 times, almost all of it by memory. Their idle numbers measure that calibration as much as their wiring, and the 13 of 24 after a sighting is the fairer comparison.
- **The guard is a small part of it without the game.** It forced 5 of the 49 FlyWire looks here. On the live nights the share was higher, and this run cannot say why, since it has no tablet, doors or lights to slow the looks down.

### What Changed With It

Nothing in the night. `controls.py` gained the unwired brain, and `measure_look_choice.py` is new.

### What Is Not Measured Yet

- Whether the looks the drift starts on a live night find an animatronic more often than chance. The traces do not record which look found what, and the saved frames of the nights recorded with `--frames` could answer it.
- The eyes-swapped brain, and shuffle seeds beyond two.
- Why the guard forces more looks on a live night than here.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Ran the look loop with no game on the FlyWire brain, two shuffles and a brain without synapses, idle and after a sighting | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-26 |
