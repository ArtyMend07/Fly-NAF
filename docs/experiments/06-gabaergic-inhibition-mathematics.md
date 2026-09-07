# Experiment 06: GABAergic Inhibition Mathematics

While testing both fly eyes, I realized that I needed a way to stop the fly from smashing the doors out of panic every time it opens the camera tablet (Probably because the gray UI scares the fly). Rather than putting an `if not camera_up` lock in the software, I searched the FlyWire dataset for GABAergic interneurons that connect to the Giant Fibers.

I started by taking the absolute strongest inhibitory neuron I could find (`720575940635119723`) and pitting it against the entire left eye cluster. 

I wrote `tests/test_inhibition.py` to simulate this localized battle in pytorch without booting up the game. The first run was a mathematical disaster (The same stupid error with 1 neuron only lol).

### The Spatial Summation Problem
The initial test fired 200 Hz into 50 LPLC2 neurons and 200 Hz into 1 LHAD1g1 inhibitor. The result:

```text
===========================================
TEST 1: PANIC REFLEX (VISUAL THREAT ONLY)
===========================================
Giant Fiber Spikes: 1.0
RESULT: Normal startle response triggered. Door would CLOSE.

===========================================
TEST 2: CAMERA INHIBITION (THREAT + CAMERA)
===========================================
Giant Fiber Spikes: 1.0
RESULT: Failure. Inhibition was not strong enough.
```

The physics worked exactly as they should have. Even though that single inhibitor had 130 synapses, it was physically impossible for it to overpower the spatial summation of 50 excitatory neurons firing in unison. The voltage leaked through and the Giant Fiber spiked.

### The Biological Correction
To fix this, I ran a data mining script (`mine_inhibitors.py`) directly on the 2025 Parquet connectivity matrix. I filtered for `top_nt == 'gaba'` on all presynaptic neurons hitting the Giant Fibers, sorted them by weight, and extracted the top 50 for each side. I grouped these 50 into a true inhibitory cluster in the config.

The rematch was 50 LPLC2 vs 50 GABAergic neurons. After fixing a bug where the PyTorch model failed to clear its refractory state between runs, the second pass yielded the correct biological outcome:

```text
===========================================
TEST 1: PANIC REFLEX (VISUAL THREAT ONLY)
===========================================
Giant Fiber Spikes: 3.0
RESULT: Normal startle response triggered. Door would CLOSE.

===========================================
TEST 2: CAMERA INHIBITION (THREAT + CAMERA)
===========================================
Giant Fiber Spikes: 0.0
RESULT: SUCCESS! The GABAergic interneuron completely neutralized the panic reflex mathematically.
The fly is looking at the camera safely.
```

The negative voltage from the GABA synapses entirely smothered the excitatory drive from the visual field. We successfully blinded the panic reflex using nothing but pure connectome topology.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Initial documentation of the GABAergic tests | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-07 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-07 |
