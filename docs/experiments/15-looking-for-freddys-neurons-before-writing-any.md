# Experiment 15: Looking For Freddy's Neurons Before Writing Any

Freddy has no pathway. The hallway reflex covers Bonnie and Chica, the cove covers Foxy, and nothing in the fly reacts to Freddy at all. Before adding one I wanted to know which neurons could carry it, and I had a list of candidates that sounded reasonable. Most of that list did not survive, so this records what was checked and what is left. No code changed.

Every candidate went through three filters. It has to exist in the FlyWire 783 release with synapses onto a descending neuron, that descending neuron has to fire on the running engine when the candidate is driven, and a paper has to report the same link in a real fly.

### What The Connectome Says

All the candidate types exist in the annotation table. Direct synapses from the left population of each type onto the descending neurons:

```
source    DNp01  DNp02  DNp03  DNp04  DNp06  DNp09  DNp11
LPLC2       458      5     11    607    485     34     17
LC4         374    525    366   1064     58      0    570
LC9           0      0      0      0      0    385    275
LC31a         0      0      0      0    245    338      9
LPLC1         0      0    848      8    509      0    410
LC11          0      0      0      0      0      0      0
LC10a         0      0      0      0      0      0     33
LC6           0      0      0      0     45      1      3
LC16          0      0      0      0      0      0      0
```

- The populations already in use are the largest inputs of their readouts. LPLC2 and LC4 lead DNp01 and DNp04, LC9 and LC31a lead DNp09.
- LPLC1 is the largest input of DNp06 (1023 synapses over both sides) and the second largest of DNp03 (893, after LPLC4 with 955). It barely touches DNp04, and `find_motor_pathway.py` needs 6 synapses to get there.
- LC11 has no direct synapse onto any of these. It reaches DNp09 in 2 synapses through PVLP150.
- LC10a reaches DNa02 in 2 synapses through AOTU025 and none of the escape neurons.
- LC16 to MDN takes 3 synapses on the left and 5 on the right, at about three times the cost of the LPLC2 to DNp01 path.
- The ring neurons of the ellipsoid body are all GABAergic and get their visual input from the medulla through MeTu and TuBu. LC9 to EPG takes 6 synapses.

`find_motor_pathway.py` only follows excitatory synapses and returns the cheapest path, so it shows a route exists. It does not show the readout fires.

### What The Engine Says

Freddy would be seen on the tablet, so the trials ran with the tablet inhibitors at full drive. Each cell is trials answered out of 10, forty frames each, and the median frame of the first spike. Every readout is the one on the driven side.

```
tablet up                DNp03             DNp04   DNp06   DNp09
nothing on screen        0/10              0/10    0/10    0/10
LPLC1 left 0.10          1/10              0/10    0/10    0/10
LPLC1 left 0.15          10/10 @ 4.5       0/10    0/10    0/10
LPLC1 left 0.25 to 1.00  10/10 @ 3         0/10    0/10    1/10 at most
LPLC1 right 0.10         2/10              0/10    0/10    1/10
LPLC1 right 0.15         9/10 @ 10         0/10    0/10    0/10
LPLC1 right 0.25         10/10 @ 6         0/10    0/10    0/10
LPLC1 right 1.00         10/10 @ 4         0/10    0/10    1/10
```

- I expected DNp06 and got DNp03. DNp06 stayed silent under LPLC1 alone at every level. It needed LPLC1 and LC31a together at 1.00, or those two plus LPLC2 at 0.50.
- The inhibitors do not explain that by themselves. They supply about 7 percent of DNp06's input, close to the 5 percent they supply to DNp04, which does fire with the tablet up. What differs is the share LPLC1 has: 509 of the 10488 synapses onto the left DNp06 against 848 of the 5021 onto the left DNp03.
- The channels stay apart at working levels. The figure channel (LC9 and LC31a) fired DNp03 in 2 of 10 trials at most. The loom channel (LPLC2 and LC4) at 0.25 fired it in 1 of 10, and only at 1.00 did it cross over, which is expected since LC4 feeds DNp03 directly.
- With Foxy's channels driven on the left and LPLC1 on the right in the same trial, DNp09 or DNp04 answered on the left and DNp03 on the right, 10 of 10 each.
- LC11 added nothing to the figure channel. On the left at 0.10, DNp09 answered 4 of 10 with or without it, and at 0.15 it answered 10 of 10 either way. Alone, LC11 reached DNp09 only from 0.50, around frame 9 (six trials).
- In the hallway with the tablet down, DNp01, DNp02, DNp03, DNp04, DNp06 and DNp11 all answered the eye on frame 3 in 6 of 6 trials. Reading more of them as a vote would add nothing the Giant Fiber does not already say.

Two asymmetries showed up that matter for anything built on the right side:

- The right DNp03 has 366 input synapses in this release and the left has 5021. From ipsilateral LPLC1 that is 45 against 848. It still fires, later and with fewer spikes, and it looks like an incomplete reconstruction.
- DNp09 is more sensitive on the right. A figure of 0.05 on the right fired it 10 of 10, while 0.10 on the left gave 4 of 10. A mirror of the cove circuit would not behave like the original.

Trials with the tablet down start from a reset network, and several descending neurons spike there with nothing driven, so only the tablet-up numbers are used above.

### What The Papers Say

- LPLC1 to DNp03 is reported. Tanaka and Clark write that they "focused our experiments on five major neuron types postsynaptic to LPLC1: DNp03, DNp06, PVLP112/113, and PLP219" and that "In addition to LPLC1, DNp03 receive inputs from LPLC4 and LC4, and DNp06 from LC4, 6, and 31" ([bioRxiv 2021](https://www.biorxiv.org/content/10.1101/2021.12.11.472218v1.full)). That matches the table above.
- DNp03 answers looming on its own side. Croke et al. report that "DNp03 receives excitatory input from visual projection neuron (VPN) populations, including LPLC1, LPLC4, LC4, LC22, and LC23" and found it "strongly biased to the presentation of looming stimuli ipsilateral but not contralateral to its soma" ([Current Biology 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12977095/)).
- The same neuron is tied to flight. Buchsbaum and Schnell report that "looming stimuli only elicit spikes during flight and not rest" ([bioRxiv 2024](https://www.biorxiv.org/content/10.1101/2024.08.22.608914v1.full)). The model has no flight state, so it fires DNp03 where a resting fly would only depolarise it.
- LC11 to DNp09 is not supported. Tanaka and Clark showed that "LC11 is necessary for a visual object-induced stopping behavior in walking flies" and then "saw no effect of silencing DNp09, a descending neuron that is implicated in loom induced freezing" ([Current Biology 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC8716191/)). Bidaye et al. did see DNp09 respond when LC11 was activated strongly, and found that "LC11 and P9 are connected via an intermediate neuron" ([Neuron 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9435592/)). The paper does not name that neuron, and PVLP150 is the one the path search above returned. So the route exists and carries signal, and the behaviour LC11 is known for does not depend on it.
- DNp09 itself is as ADR 0026 uses it. Zacarias et al. found that "optogenetic activation of both DNp09 neurons induces running and freezing in a state-dependent manner" ([Nature Communications 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6135764/)).

### What Is Left

One candidate passed all three filters, LPLC1 on the right driving DNp03 on the right while the tablet is up. LC11, LC10a, LC16 with MDN, the vote in the hallway and the ellipsoid body are dropped for now.

Nothing was implemented, because the screen half is unmeasured:

- Where the CAM 4B button sits on the map.
- What an empty CAM 4B looks like across its pan, for the reference bank.
- How much contrast a dark Freddy produces there. Experiment 14 already showed a dark figure can read as nothing.
- How the gaze would choose between CAM 1C and CAM 4B, which today is a fixed gesture to 1C.

All four need a live night with Freddy off the stage. The flight-state point and the thin right DNp03 would have to be written into whatever ADR takes this up.

The measurements came from `find_motor_pathway.py` and from a throwaway copy of `measure_tablet_pathways.py` with LPLC1, LC11, LC10a and LPLC4 added as stimulus populations and the extra descending neurons as readouts. That copy is not in the repository.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Candidate neurons for a Freddy pathway checked against the connectome, the running engine and the literature, with LPLC1 to DNp03 the only one left | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-09 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-09 |
